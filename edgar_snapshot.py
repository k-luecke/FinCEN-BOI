#!/usr/bin/env python3
"""
SEC EDGAR bulk-data snapshot connector (P2, ownership sources).

Archives SEC's nightly bulk files — purpose-built public archival side
channels — into the standard content-addressed store with manifest
records, streaming to disk (never loading multi-GB files into RAM)
and hashing while writing.

    submissions.zip   all EDGAR filing metadata
    companyfacts.zip  all XBRL company facts

Snapshots are preserved as dated immutable objects: a later snapshot
with different bytes is a second object, never an overwrite.
Extraction of ownership edges happens later, against archived bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import random
import sys
import time
import urllib.error
import urllib.request
import uuid

from pathlib import Path

from archive import (
    DEFAULT_ALLOWED_HOSTS,
    Record,
    append_jsonl,
    host_allowed,
    utc_now,
)
from proxy_pool import ProxyPool
import proxy_pool as proxy_control

# SEC's automated-access policy asks for a declared User-Agent with
# contact information; the repository is the contact point.
USER_AGENT = (
    "FinCEN-BOI-Public-Archive/0.1 "
    "(+https://github.com/k-luecke/FinCEN-BOI; "
    "public-record preservation)"
)

BULK_FILES = [
    (
        "https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip",
        "SEC EDGAR bulk submissions",
    ),
    (
        "https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip",
        "SEC EDGAR bulk company facts",
    ),
]

CHUNK = 1024 * 1024


def stream_fetch(
    url: str,
    out: Path,
    manifest: Path,
    source: str,
    max_bytes: int,
    max_retries: int,
    proxy_pool: ProxyPool | None = None,
) -> bool:
    record_id = str(uuid.uuid4())

    for attempt in range(max_retries + 1):
        tmp = out / f".download-{record_id}.tmp"
        proxy = proxy_pool.next() if proxy_pool else None

        try:
            if proxy:
                proxy_control.install(proxy)

            request = urllib.request.Request(
                url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"}
            )

            with urllib.request.urlopen(request, timeout=300) as response:
                final_url = response.geturl()

                if not host_allowed(final_url, DEFAULT_ALLOWED_HOSTS):
                    raise RuntimeError(
                        f"redirect escaped allowlist: {final_url}"
                    )

                status = response.status
                content_type = response.headers.get("Content-Type")
                hasher = hashlib.sha256()
                size = 0

                with tmp.open("wb") as f:
                    while True:
                        chunk = response.read(CHUNK)

                        if not chunk:
                            break

                        size += len(chunk)

                        if size > max_bytes:
                            raise RuntimeError(
                                f"exceeds max_bytes={max_bytes}"
                            )

                        hasher.update(chunk)
                        f.write(chunk)

            digest = hasher.hexdigest()
            dest = out / "objects" / "sha256" / digest[:2] / digest[2:]

            if dest.exists():
                tmp.unlink()
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                os.replace(tmp, dest)

            record = Record(
                record_id=record_id,
                retrieved_at=utc_now(),
                url=url,
                final_url=final_url,
                provenance="GOV-PUBLIC",
                source=source,
                http_status=status,
                content_type=content_type,
                content_length=size,
                sha256=digest,
                object_path=str(dest),
                error=None,
            )
            append_jsonl(manifest, record)
            print(f"  {status} {size} bytes sha256:{digest}")
            return True

        except Exception as exc:
            tmp.unlink(missing_ok=True)

            if proxy:
                proxy_pool.mark_dead(proxy)

            if attempt < max_retries:
                delay = min(30.0 * (2 ** attempt), 300.0)
                delay += random.uniform(0.0, 5.0)
                print(
                    f"  retry {attempt + 1}/{max_retries} in "
                    f"{delay:.0f}s ({exc})",
                    file=sys.stderr,
                )
                time.sleep(delay)
                continue

            record = Record(
                record_id=record_id,
                retrieved_at=utc_now(),
                url=url,
                final_url=None,
                provenance="GOV-PUBLIC",
                source=source,
                http_status=getattr(exc, "code", None),
                content_type=None,
                content_length=None,
                sha256=None,
                object_path=None,
                error=str(exc),
            )
            append_jsonl(manifest, record)
            print(f"  ERROR: {exc}")
            return False

        finally:
            if proxy:
                proxy_control.clear()

    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="archive")
    parser.add_argument("--manifest", default="run-manifest.jsonl")
    parser.add_argument("--delay", type=float, default=30.0)
    parser.add_argument(
        "--max-bytes", type=int, default=8 * 1024 * 1024 * 1024
    )
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument(
        "--use-proxies",
        action="store_true",
        help=(
            "Route fetches through a freshly built pool of free SOCKS5 "
            "proxies, rotating to the next on failure. Use when sec.gov "
            "is blocking the runner's own IP outright."
        ),
    )
    parser.add_argument("--proxy-pool-size", type=int, default=8)
    parser.add_argument("--proxy-validate-timeout", type=float, default=5.0)
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    proxy_pool = None
    if args.use_proxies:
        print("Building proxy pool from free SOCKS5 aggregators...")
        proxy_pool = ProxyPool.build(
            want=args.proxy_pool_size,
            timeout=args.proxy_validate_timeout,
        )
        print(f"  {len(proxy_pool)} validated proxies")
        if not len(proxy_pool):
            print("No live free proxies found; aborting.", file=sys.stderr)
            return 1

    successes = 0

    for index, (url, source) in enumerate(BULK_FILES, 1):
        print(f"[{index}/{len(BULK_FILES)}] {url}")

        if stream_fetch(
            url,
            out,
            Path(args.manifest),
            source,
            args.max_bytes,
            args.max_retries,
            proxy_pool,
        ):
            successes += 1

        if index != len(BULK_FILES):
            time.sleep(args.delay)

    print(f"Snapshots archived: {successes}/{len(BULK_FILES)}")

    return 0 if successes else 1


if __name__ == "__main__":
    sys.exit(main())
