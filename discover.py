#!/usr/bin/env python3
"""
Public-record URL discovery.

Builds a historical inventory of what public FinCEN-related material
exists, instead of hand-writing more seeds. Two discovery modes:

1. Sitemap enumeration — reads robots.txt for Sitemap: entries (falling
   back to /sitemap.xml) on configured allowlisted hosts, recurses
   sitemap indexes, and collects same-allowlist page URLs.
2. Federal Register API — enumerates every Federal Register document
   published by FinCEN via the public documents API, collecting both
   the HTML and PDF (govinfo.gov) URLs.

Discovery deliberately does NOT fetch page content. It only touches
robots.txt, sitemap XML, and the Federal Register JSON API — all on the
same host allowlist as the crawler — and produces:

- url-inventory.jsonl   one record per URL ever discovered, with
                        first_discovered / last_confirmed timestamps
                        and how it was found. Append-merge: URLs are
                        never dropped from the inventory, so a URL that
                        vanishes from a sitemap keeps its record (its
                        last_confirmed simply stops advancing).
- discovered-seeds.txt  seed-format candidates not already in
                        seeds.txt, ready for review and promotion.

Archiving discovered URLs remains an explicit step:

    python3 archive.py --seeds discovered-seeds.txt
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from datetime import datetime, timezone
from pathlib import Path

from archive import (
    DEFAULT_ALLOWED_HOSTS,
    USER_AGENT,
    host_allowed,
    normalized_host,
    parse_seed,
)

DEFAULT_SITEMAP_HOSTS = [
    "www.fincen.gov",
]

FEDERAL_REGISTER_API = "https://www.federalregister.gov/api/v1/documents.json"
FEDERAL_REGISTER_AGENCY = "financial-crimes-enforcement-network"

# Discovery fetches metadata (robots, sitemaps, API JSON), not records;
# anything bigger than this is not a sitemap.
MAX_FETCH_BYTES = 20 * 1024 * 1024


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fetch_bytes(url: str, delay: float) -> bytes:
    if not host_allowed(url, DEFAULT_ALLOWED_HOSTS):
        raise RuntimeError(f"host not allowlisted: {url}")

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
        },
    )

    with urllib.request.urlopen(request, timeout=60) as response:
        final_url = response.geturl()

        if not host_allowed(final_url, DEFAULT_ALLOWED_HOSTS):
            raise RuntimeError(f"redirect escaped allowlist: {final_url}")

        data = response.read(MAX_FETCH_BYTES + 1)

    if len(data) > MAX_FETCH_BYTES:
        raise RuntimeError(f"metadata fetch exceeds {MAX_FETCH_BYTES} bytes")

    time.sleep(delay)

    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)

    return data


def sitemaps_from_robots(robots_text: str, base_url: str) -> list[str]:
    sitemaps = []

    for line in robots_text.splitlines():
        line = line.strip()

        if line.lower().startswith("sitemap:"):
            location = line.split(":", 1)[1].strip()
            absolute = urllib.parse.urljoin(base_url, location)
            sitemaps.append(absolute)

    return sitemaps


def parse_sitemap(data: bytes) -> tuple[list[str], list[str]]:
    """
    Return (child_sitemap_urls, page_urls) from one sitemap document,
    tolerating both <sitemapindex> and <urlset> roots.
    """

    root = ET.fromstring(data)
    local = root.tag.rsplit("}", 1)[-1]

    locs = [
        element.text.strip()
        for element in root.iter()
        if element.tag.rsplit("}", 1)[-1] == "loc"
        and element.text
        and element.text.strip()
    ]

    if local == "sitemapindex":
        return locs, []

    return [], locs


def discover_sitemap_host(
    host: str,
    delay: float,
    max_sitemaps: int,
    max_urls: int,
) -> dict[str, str]:
    """Return {url: discovered_via} for one host's sitemaps."""

    base = f"https://{host}/"
    queue: list[str] = []
    urls: dict[str, str] = {}

    try:
        robots = fetch_bytes(
            urllib.parse.urljoin(base, "/robots.txt"), delay
        ).decode("utf-8", errors="replace")
        queue = sitemaps_from_robots(robots, base)
    except (urllib.error.URLError, RuntimeError, TimeoutError) as exc:
        print(f"WARN: robots.txt failed for {host}: {exc}", file=sys.stderr)

    if not queue:
        queue = [urllib.parse.urljoin(base, "/sitemap.xml")]

    seen_sitemaps: set[str] = set()
    fetched = 0

    while queue and fetched < max_sitemaps and len(urls) < max_urls:
        sitemap_url = queue.pop(0)

        if sitemap_url in seen_sitemaps:
            continue

        seen_sitemaps.add(sitemap_url)

        if not host_allowed(sitemap_url, DEFAULT_ALLOWED_HOSTS):
            print(
                f"WARN: skipping non-allowlisted sitemap {sitemap_url}",
                file=sys.stderr,
            )
            continue

        try:
            data = fetch_bytes(sitemap_url, delay)
            children, pages = parse_sitemap(data)
        except (
            urllib.error.URLError,
            RuntimeError,
            TimeoutError,
            ET.ParseError,
        ) as exc:
            print(f"WARN: sitemap failed {sitemap_url}: {exc}", file=sys.stderr)
            continue

        fetched += 1
        queue.extend(children)

        for page in pages:
            if len(urls) >= max_urls:
                print(
                    f"WARN: {host} truncated at max_urls={max_urls}; "
                    f"inventory is NOT complete for this host",
                    file=sys.stderr,
                )
                break

            if host_allowed(page, DEFAULT_ALLOWED_HOSTS):
                urls.setdefault(page, f"sitemap:{host}")

    print(
        f"{host}: {fetched} sitemaps read, {len(urls)} URLs",
        file=sys.stderr,
    )

    return urls


def discover_federal_register(
    delay: float,
    max_pages: int,
) -> dict[str, dict]:
    """
    Return {url: metadata} for every FinCEN document in the Federal
    Register, including govinfo.gov PDF URLs.
    """

    query = urllib.parse.urlencode(
        {
            "conditions[agencies][]": FEDERAL_REGISTER_AGENCY,
            "per_page": 100,
            "order": "oldest",
            "fields[]": [
                "html_url",
                "pdf_url",
                "document_number",
                "publication_date",
                "title",
                "type",
            ],
        },
        doseq=True,
    )

    next_url: str | None = f"{FEDERAL_REGISTER_API}?{query}"
    found: dict[str, dict] = {}
    pages = 0

    while next_url and pages < max_pages:
        try:
            payload = json.loads(fetch_bytes(next_url, delay))
        except (
            urllib.error.URLError,
            RuntimeError,
            TimeoutError,
            json.JSONDecodeError,
        ) as exc:
            print(f"WARN: Federal Register page failed: {exc}", file=sys.stderr)
            break

        pages += 1

        for document in payload.get("results", []):
            meta = {
                "discovered_via": "federal-register-api",
                "document_number": document.get("document_number"),
                "publication_date": document.get("publication_date"),
                "title": document.get("title"),
                "document_type": document.get("type"),
            }

            for key in ("html_url", "pdf_url"):
                url = document.get(key)

                if url and host_allowed(url, DEFAULT_ALLOWED_HOSTS):
                    found.setdefault(url, meta)

        next_url = payload.get("next_page_url")

    if next_url:
        print(
            f"WARN: Federal Register truncated at max_pages={max_pages}; "
            f"inventory is NOT complete",
            file=sys.stderr,
        )

    print(
        f"federal-register: {pages} pages read, {len(found)} URLs",
        file=sys.stderr,
    )

    return found


def load_inventory(path: Path) -> dict[str, dict]:
    inventory: dict[str, dict] = {}

    if not path.exists():
        return inventory

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            record = json.loads(line)
            inventory[record["url"]] = record

    return inventory


def write_inventory(path: Path, inventory: dict[str, dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for url in sorted(inventory):
            f.write(
                json.dumps(
                    inventory[url], sort_keys=True, ensure_ascii=False
                )
                + "\n"
            )


def merge_discoveries(
    inventory: dict[str, dict],
    discovered: dict[str, dict],
) -> tuple[int, int]:
    now = utc_now()
    added = 0
    confirmed = 0

    for url, meta in discovered.items():
        if url in inventory:
            inventory[url]["last_confirmed"] = now
            confirmed += 1
        else:
            record = {
                "url": url,
                "host": normalized_host(url),
                "first_discovered": now,
                "last_confirmed": now,
            }
            record.update(
                {k: v for k, v in meta.items() if v is not None}
            )
            inventory[url] = record
            added += 1

    return added, confirmed


def seed_label(record: dict) -> str:
    if record.get("discovered_via") == "federal-register-api":
        return "Federal Register"

    return record.get("host", "")


def write_candidate_seeds(
    path: Path,
    inventory: dict[str, dict],
    existing_seed_urls: set[str],
) -> int:
    candidates = [
        record
        for url, record in sorted(inventory.items())
        if url not in existing_seed_urls
    ]

    with path.open("w", encoding="utf-8") as f:
        f.write(
            "# Generated by discover.py — candidate seeds not yet in "
            "seeds.txt.\n"
            "# Review, then either promote lines into seeds.txt or "
            "crawl directly:\n"
            "#   python3 archive.py --seeds discovered-seeds.txt\n"
            "# All URLs are on the crawler's public-host allowlist; "
            "provenance GOV-PUBLIC.\n\n"
        )

        for record in candidates:
            f.write(
                f"{record['url']}|GOV-PUBLIC|{seed_label(record)}\n"
            )

    return len(candidates)


def load_seed_urls(path: Path) -> set[str]:
    urls: set[str] = set()

    if not path.exists():
        return urls

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()

        if not line or line.startswith("#"):
            continue

        url, _provenance, _source = parse_seed(line)
        urls.add(url)

    return urls


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--hosts",
        nargs="*",
        default=DEFAULT_SITEMAP_HOSTS,
        help="Allowlisted hosts to enumerate via sitemaps",
    )
    parser.add_argument("--inventory", default="url-inventory.jsonl")
    parser.add_argument("--out-seeds", default="discovered-seeds.txt")
    parser.add_argument("--seeds", default="seeds.txt")
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--max-sitemaps", type=int, default=50)
    parser.add_argument("--max-urls-per-host", type=int, default=5000)
    parser.add_argument("--max-fr-pages", type=int, default=50)
    parser.add_argument(
        "--skip-federal-register",
        action="store_true",
        help="Skip Federal Register API enumeration",
    )

    args = parser.parse_args()

    discovered: dict[str, dict] = {}

    for host in args.hosts:
        if host.lower() not in DEFAULT_ALLOWED_HOSTS:
            print(
                f"WARN: refusing non-allowlisted host {host}",
                file=sys.stderr,
            )
            continue

        for url, via in discover_sitemap_host(
            host,
            delay=args.delay,
            max_sitemaps=args.max_sitemaps,
            max_urls=args.max_urls_per_host,
        ).items():
            discovered.setdefault(url, {"discovered_via": via})

    if not args.skip_federal_register:
        for url, meta in discover_federal_register(
            delay=args.delay,
            max_pages=args.max_fr_pages,
        ).items():
            discovered.setdefault(url, meta)

    if not discovered:
        # Every source failed (typically network/runner trouble). The
        # inventory is merge-only so nothing is lost, but a silent
        # zero-URL run should be visible, not green.
        print("ERROR: no URLs discovered from any source", file=sys.stderr)
        return 1

    inventory_path = Path(args.inventory)
    inventory = load_inventory(inventory_path)

    added, confirmed = merge_discoveries(inventory, discovered)
    write_inventory(inventory_path, inventory)

    existing = load_seed_urls(Path(args.seeds))
    candidates = write_candidate_seeds(
        Path(args.out_seeds), inventory, existing
    )

    print(f"Inventory: {len(inventory)} URLs "
          f"({added} new, {confirmed} re-confirmed this run)")
    print(f"Candidate seeds not in {args.seeds}: {candidates}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
