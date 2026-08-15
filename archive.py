#!/usr/bin/env python3
"""
Public-record preservation crawler.

Design goals:
- Preserve exact publicly accessible bytes.
- SHA-256 every object.
- Append retrieval records to JSONL.
- Never authenticate.
- Never bypass robots/access controls.
- Never discover/fetch arbitrary external hosts.
- Conservative rate limiting.
- Explicit provenance classification.
- Content-addressed object storage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
import uuid

from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional


USER_AGENT = (
    "FinCEN-BOI-Public-Archive/0.1 "
    "(public-record preservation; contact via repository)"
)

DEFAULT_ALLOWED_HOSTS = {
    "fincen.gov",
    "www.fincen.gov",
    "bsaefiling.fincen.gov",
    "home.treasury.gov",
    "treasury.gov",
    "www.treasury.gov",
    "oig.treasury.gov",
    "ffiec.gov",
    "www.ffiec.gov",
    "bsaaml.ffiec.gov",
    "gao.gov",
    "www.gao.gov",
    "occ.gov",
    "www.occ.gov",
    "fdic.gov",
    "www.fdic.gov",
    "ncua.gov",
    "www.ncua.gov",
    "federalreserve.gov",
    "www.federalreserve.gov",
    "www.govinfo.gov",
    "govinfo.gov",
    "www.federalregister.gov",
    "federalregister.gov",
    "www.justice.gov",
    "justice.gov",
    "vault.fbi.gov",
    "www.congress.gov",
    "congress.gov",
    "judiciary.house.gov",
    "oversight.house.gov",
    "www.sec.gov",
    "sec.gov",
}


@dataclass
class Record:
    record_id: str
    retrieved_at: str
    url: str
    final_url: Optional[str]
    provenance: str
    source: Optional[str]
    http_status: Optional[int]
    content_type: Optional[str]
    content_length: Optional[int]
    sha256: Optional[str]
    object_path: Optional[str]
    error: Optional[str]
    parent_url: Optional[str] = None
    depth: int = 0


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalized_host(url: str) -> str:
    return (urllib.parse.urlparse(url).hostname or "").lower()


def host_allowed(url: str, allowed_hosts: set[str]) -> bool:
    host = normalized_host(url)
    return host in allowed_hosts


def append_jsonl(path: Path, record: Record) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                asdict(record),
                sort_keys=True,
                ensure_ascii=False,
            )
            + "\n"
        )
        f.flush()
        os.fsync(f.fileno())


def store_object(root: Path, digest: str, data: bytes) -> Path:
    # Git-like fanout prevents giant directories.
    path = root / "objects" / "sha256" / digest[:2] / digest[2:]

    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, path)

    return path


def parse_seed(line: str):
    """
    Format:

    URL|PROVENANCE|SOURCE

    Examples:
    https://www.fincen.gov/...|GOV-PUBLIC|FinCEN
    https://judiciary.house.gov/...|CONGRESS|House Judiciary

    Only URL is mandatory.
    """

    pieces = [p.strip() for p in line.split("|", 2)]

    url = pieces[0]
    provenance = pieces[1] if len(pieces) > 1 else "UNCLASSIFIED"
    source = pieces[2] if len(pieces) > 2 else None

    return url, provenance, source


class LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for name, value in attrs:
                if name == "href" and value:
                    self.hrefs.append(value)


def extract_links(
    html_bytes: bytes,
    base_url: str,
    allowed_hosts: set[str],
) -> list[str]:
    """Absolute, fragment-free, allowlisted links from one HTML page."""

    parser = LinkExtractor()

    try:
        parser.feed(html_bytes.decode("utf-8", errors="replace"))
    except Exception:
        return []

    links = []
    seen = set()

    for href in parser.hrefs:
        absolute = urllib.parse.urljoin(base_url, href.strip())
        absolute, _fragment = urllib.parse.urldefrag(absolute)

        if not absolute.startswith(("http://", "https://")):
            continue

        if absolute in seen:
            continue

        seen.add(absolute)

        if host_allowed(absolute, allowed_hosts):
            links.append(absolute)

    return links


class RobotsCache:
    """
    robots.txt decisions for link-following, one fetch per host.

    Explicitly seeded URLs are archival requests and fetched directly;
    URLs reached by following links go through this check. Unreadable
    robots (404 etc.) allows crawling; a 5xx conservatively disallows.
    """

    def __init__(self, user_agent: str) -> None:
        self.user_agent = user_agent
        self.parsers: dict[str, urllib.robotparser.RobotFileParser] = {}

    def allowed(self, url: str) -> bool:
        host = normalized_host(url)
        parser = self.parsers.get(host)

        if parser is None:
            parser = urllib.robotparser.RobotFileParser()

            request = urllib.request.Request(
                f"https://{host}/robots.txt",
                headers={"User-Agent": USER_AGENT},
            )

            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    parser.parse(
                        response.read(1024 * 1024)
                        .decode("utf-8", errors="replace")
                        .splitlines()
                    )
            except urllib.error.HTTPError as exc:
                if exc.code >= 500:
                    parser.disallow_all = True
                else:
                    parser.allow_all = True
            except Exception:
                parser.allow_all = True

            self.parsers[host] = parser

        return parser.can_fetch(self.user_agent, url)


def fetch(
    url: str,
    provenance: str,
    source: Optional[str],
    out: Path,
    manifest: Path,
    allowed_hosts: set[str],
    max_bytes: int,
    parent_url: Optional[str] = None,
    depth: int = 0,
    error: Optional[str] = None,
) -> Record:

    record_id = str(uuid.uuid4())

    if error is None and not host_allowed(url, allowed_hosts):
        error = "host_not_allowlisted"

    if error is not None:
        record = Record(
            record_id=record_id,
            retrieved_at=utc_now(),
            url=url,
            final_url=None,
            provenance=provenance,
            source=source,
            http_status=None,
            content_type=None,
            content_length=None,
            sha256=None,
            object_path=None,
            error=error,
            parent_url=parent_url,
            depth=depth,
        )
        append_jsonl(manifest, record)
        return record

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            final_url = response.geturl()

            # Do not allow redirects to escape the allowlist.
            if not host_allowed(final_url, allowed_hosts):
                raise RuntimeError(
                    f"redirect escaped allowlist: {final_url}"
                )

            status = response.status
            content_type = response.headers.get("Content-Type")

            declared_length = response.headers.get("Content-Length")

            if declared_length:
                try:
                    if int(declared_length) > max_bytes:
                        raise RuntimeError(
                            f"declared object exceeds max_bytes: "
                            f"{declared_length}"
                        )
                except ValueError:
                    pass

            data = response.read(max_bytes + 1)

            if len(data) > max_bytes:
                raise RuntimeError(
                    f"object exceeds max_bytes={max_bytes}"
                )

            digest = sha256(data)
            object_path = store_object(out, digest, data)

            record = Record(
                record_id=record_id,
                retrieved_at=utc_now(),
                url=url,
                final_url=final_url,
                provenance=provenance,
                source=source,
                http_status=status,
                content_type=content_type,
                content_length=len(data),
                sha256=digest,
                object_path=str(object_path),
                error=None,
                parent_url=parent_url,
                depth=depth,
            )

    except (
        urllib.error.HTTPError,
        urllib.error.URLError,
        RuntimeError,
        TimeoutError,
    ) as exc:

        status = getattr(exc, "code", None)

        record = Record(
            record_id=record_id,
            retrieved_at=utc_now(),
            url=url,
            final_url=None,
            provenance=provenance,
            source=source,
            http_status=status,
            content_type=None,
            content_length=None,
            sha256=None,
            object_path=None,
            error=str(exc),
            parent_url=parent_url,
            depth=depth,
        )

    append_jsonl(manifest, record)
    return record


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument("--seeds", required=True)
    parser.add_argument("--out", default="archive")
    parser.add_argument("--manifest", default="manifest.jsonl")
    parser.add_argument("--delay", type=float, default=2.0)

    # Default 100 MB/object.
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=100 * 1024 * 1024,
    )

    parser.add_argument(
        "--follow-links",
        action="store_true",
        help=(
            "Extract <a href> links from fetched HTML and crawl any "
            "that stay on the host allowlist, breadth-first to "
            "closure. Followed links honor robots.txt; explicit "
            "seeds are always fetched."
        ),
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=20000,
        help="Total fetch cap for a follow-links crawl",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=32,
        help="Link depth cap from any seed",
    )

    args = parser.parse_args()

    out = Path(args.out)
    manifest = Path(args.manifest)
    seed_file = Path(args.seeds)

    out.mkdir(parents=True, exist_ok=True)

    seeds = []

    for raw in seed_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()

        if not line or line.startswith("#"):
            continue

        seeds.append(parse_seed(line))

    print(f"Loaded {len(seeds)} seeds.")

    # (url, provenance, source, parent_url, depth)
    frontier = deque(
        (url, provenance, source, None, 0)
        for url, provenance, source in seeds
    )
    enqueued = {url for url, _provenance, _source in seeds}
    robots = RobotsCache("FinCEN-BOI-Public-Archive")

    fetched = 0
    truncated = False

    while frontier:
        if fetched >= args.max_pages:
            truncated = True
            break

        url, provenance, source, parent_url, depth = frontier.popleft()

        print(f"[{fetched + 1}] depth={depth} "
              f"(frontier {len(frontier)}) {url}")

        # Followed links honor robots.txt; explicit seeds (depth 0)
        # are archival requests and are fetched directly.
        robots_error = None

        if depth > 0 and not robots.allowed(url):
            robots_error = "robots_disallowed"

        record = fetch(
            url=url,
            provenance=provenance,
            source=source,
            out=out,
            manifest=manifest,
            allowed_hosts=DEFAULT_ALLOWED_HOSTS,
            max_bytes=args.max_bytes,
            parent_url=parent_url,
            depth=depth,
            error=robots_error,
        )

        if record.sha256:
            print(
                f"  {record.http_status} "
                f"{record.content_length} bytes "
                f"sha256:{record.sha256}"
            )
        else:
            print(f"  ERROR: {record.error}")

        if record.error != "robots_disallowed":
            fetched += 1

            if frontier or args.follow_links:
                time.sleep(args.delay)

        if (
            args.follow_links
            and record.sha256
            and record.content_type
            and "text/html" in record.content_type.lower()
            and depth < args.max_depth
        ):
            data = Path(record.object_path).read_bytes()
            base = record.final_url or url

            for link in extract_links(
                data, base, DEFAULT_ALLOWED_HOSTS
            ):
                if link not in enqueued:
                    enqueued.add(link)
                    frontier.append(
                        (
                            link,
                            "GOV-PUBLIC",
                            normalized_host(link),
                            url,
                            depth + 1,
                        )
                    )

    if truncated:
        print(
            f"WARN: stopped at --max-pages={args.max_pages} with "
            f"{len(frontier)} URLs still in the frontier; "
            f"crawl is NOT complete",
            file=sys.stderr,
        )

    print(f"Fetched {fetched} URLs ({len(enqueued)} discovered).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
