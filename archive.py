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
import uuid

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
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


def fetch(
    url: str,
    provenance: str,
    source: Optional[str],
    out: Path,
    manifest: Path,
    allowed_hosts: set[str],
    max_bytes: int,
) -> Record:

    record_id = str(uuid.uuid4())

    if not host_allowed(url, allowed_hosts):
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
            error="host_not_allowlisted",
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

    for index, (url, provenance, source) in enumerate(seeds, 1):
        print(f"[{index}/{len(seeds)}] {url}")

        record = fetch(
            url=url,
            provenance=provenance,
            source=source,
            out=out,
            manifest=manifest,
            allowed_hosts=DEFAULT_ALLOWED_HOSTS,
            max_bytes=args.max_bytes,
        )

        if record.sha256:
            print(
                f"  {record.http_status} "
                f"{record.content_length} bytes "
                f"sha256:{record.sha256}"
            )
        else:
            print(f"  ERROR: {record.error}")

        if index != len(seeds):
            time.sleep(args.delay)

    return 0


if __name__ == "__main__":
    sys.exit(main())
