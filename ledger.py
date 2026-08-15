#!/usr/bin/env python3
"""
Compute a per-URL change ledger from the append-only manifest.

For every URL that has ever appeared in the manifest, emit one record:

    url
    previous_sha256
    current_sha256
    first_seen
    last_seen
    http_status
    change_type = ADDED | MODIFIED | REMOVED | UNCHANGED | UNAVAILABLE

Semantics, judged from the most recent retrieval of each URL:

    ADDED       first successful retrieval, no earlier success on record
    MODIFIED    latest bytes differ from the previous successful bytes
    UNCHANGED   latest bytes match the previous successful bytes
    REMOVED     the URL succeeded in the past but the latest attempt
                failed (HTTP error, network error, or allowlist redirect
                rejection)
    UNAVAILABLE the URL has never been retrieved successfully

first_seen/last_seen are the timestamps of the first and most recent
*successful* retrievals; http_status comes from the most recent attempt
of any kind. The ledger is a pure function of the manifest — rebuilding
it never loses information, because the manifest itself is append-only.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path


def load_manifest(path: Path) -> "OrderedDict[str, list[dict]]":
    by_url: "OrderedDict[str, list[dict]]" = OrderedDict()

    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, 1):
            line = line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                print(
                    f"WARN: skipping malformed manifest line "
                    f"{line_number}: {exc}",
                    file=sys.stderr,
                )
                continue

            url = record.get("url")

            if not url:
                continue

            by_url.setdefault(url, []).append(record)

    # Manifest lines are appended chronologically, but sort defensively
    # in case manifests from several machines were concatenated.
    for records in by_url.values():
        records.sort(key=lambda r: r.get("retrieved_at") or "")

    return by_url


def ledger_entry(url: str, records: list[dict]) -> dict:
    successes = [r for r in records if r.get("sha256")]
    latest = records[-1]
    latest_ok = bool(latest.get("sha256"))

    first_seen = successes[0]["retrieved_at"] if successes else None
    last_seen = successes[-1]["retrieved_at"] if successes else None

    if latest_ok:
        prior = successes[:-1]
        current_sha256 = latest["sha256"]
        previous_sha256 = prior[-1]["sha256"] if prior else None

        if not prior:
            change_type = "ADDED"
        elif previous_sha256 != current_sha256:
            change_type = "MODIFIED"
        else:
            change_type = "UNCHANGED"
    else:
        current_sha256 = None

        if successes:
            previous_sha256 = successes[-1]["sha256"]
            change_type = "REMOVED"
        else:
            previous_sha256 = None
            change_type = "UNAVAILABLE"

    return {
        "url": url,
        "previous_sha256": previous_sha256,
        "current_sha256": current_sha256,
        "first_seen": first_seen,
        "last_seen": last_seen,
        "http_status": latest.get("http_status"),
        "change_type": change_type,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="manifest.jsonl")
    parser.add_argument("--out", default="ledger.jsonl")
    args = parser.parse_args()

    by_url = load_manifest(Path(args.manifest))

    entries = [
        ledger_entry(url, records)
        for url, records in by_url.items()
    ]
    entries.sort(key=lambda e: e["url"])

    out = Path(args.out)

    with out.open("w", encoding="utf-8") as f:
        for entry in entries:
            f.write(
                json.dumps(entry, sort_keys=True, ensure_ascii=False)
                + "\n"
            )

    counts = Counter(e["change_type"] for e in entries)

    print(f"URLs tracked: {len(entries)}")

    for change_type in (
        "ADDED",
        "MODIFIED",
        "UNCHANGED",
        "REMOVED",
        "UNAVAILABLE",
    ):
        print(f"  {change_type}: {counts.get(change_type, 0)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
