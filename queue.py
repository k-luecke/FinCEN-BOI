#!/usr/bin/env python3
"""
Durable collection queue, derived from the append-only logs.

Queue state is a pure function of (url-inventory.jsonl, seeds.txt,
manifest.jsonl): nothing is ever "in memory only", a crashed worker
leaves no stuck FETCHING rows (its unattempted URLs simply remain
pending), and rebuilding the queue is always safe and idempotent.

States per URL:

    DISCOVERED         known, never attempted -> pending
    ARCHIVED           latest attempt succeeded (bytes hashed+stored)
    NOT_FOUND          latest attempt 404/410 -> observation, no retry
    ACCESS_RESTRICTED  latest attempt 401/403 -> recorded gap, never
                       evaded, no retry
    RATE_LIMITED       latest attempt 429 -> retry-eligible
    TEMPORARY_ERROR    latest attempt 5xx/timeout/network -> retry-
                       eligible
    ROBOTS_DISALLOWED  refused by robots.txt -> recorded, no retry
    MANUAL_REVIEW      host not allowlisted or unclassifiable -> human

Retry-eligible states stop being emitted as pending once a URL has
been attempted --max-attempts times (they stay in the queue file as a
recorded gap).

Outputs:
    queue.jsonl      full queue state (atomic replace)
    --pending-out    seed-format file of pending work, capped at
                     --limit (DISCOVERED first, then retries)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from archive import parse_seed, sanitize_url
from discover import seed_label, seed_provenance

RETRYABLE = {"RATE_LIMITED", "TEMPORARY_ERROR"}
NO_RETRY = {
    "ARCHIVED",
    "NOT_FOUND",
    "ACCESS_RESTRICTED",
    "ROBOTS_DISALLOWED",
    "MANUAL_REVIEW",
}


def classify(record: dict) -> str:
    if record.get("sha256"):
        return "ARCHIVED"

    error = (record.get("error") or "").lower()
    status = record.get("http_status")

    if error == "robots_disallowed":
        return "ROBOTS_DISALLOWED"

    if error == "host_not_allowlisted":
        return "MANUAL_REVIEW"

    if status in (401, 403):
        return "ACCESS_RESTRICTED"

    if status in (404, 410):
        return "NOT_FOUND"

    if status == 429:
        return "RATE_LIMITED"

    return "TEMPORARY_ERROR"


def load_known_urls(inventory: Path, seeds: Path) -> dict[str, dict]:
    known: dict[str, dict] = {}

    if seeds.exists():
        for raw in seeds.read_text(encoding="utf-8").splitlines():
            line = raw.strip()

            if not line or line.startswith("#"):
                continue

            url, provenance, source = parse_seed(line)
            known[sanitize_url(url)] = {
                "provenance": provenance,
                "source": source,
                "origin": "seeds",
            }

    if inventory.exists():
        with inventory.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()

                if not line:
                    continue

                record = json.loads(line)
                url = sanitize_url(record.get("url", ""))

                if url and url not in known:
                    known[url] = {
                        "provenance": seed_provenance(record),
                        "source": seed_label(record),
                        "origin": "inventory",
                    }

    return known


def load_attempts(manifest: Path) -> dict[str, dict]:
    """Last record + attempt count per URL, in file (=time) order."""

    attempts: dict[str, dict] = {}

    if not manifest.exists():
        return attempts

    with manifest.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            url = sanitize_url(record.get("url", ""))

            if not url:
                continue

            entry = attempts.setdefault(
                url, {"count": 0, "last": None, "ever_archived": False}
            )
            entry["count"] += 1
            entry["last"] = record

            if record.get("sha256"):
                entry["ever_archived"] = True

    return attempts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", default="url-inventory.jsonl")
    parser.add_argument("--seeds", default="seeds.txt")
    parser.add_argument("--manifest", default="manifest.jsonl")
    parser.add_argument("--queue-out", default="queue.jsonl")
    parser.add_argument("--pending-out", default=None)
    parser.add_argument("--limit", type=int, default=4000)
    parser.add_argument("--max-attempts", type=int, default=5)
    args = parser.parse_args()

    known = load_known_urls(Path(args.inventory), Path(args.seeds))
    attempts = load_attempts(Path(args.manifest))

    # URLs seen only in the manifest (e.g. link-following) are still
    # part of the queue's world view.
    for url, entry in attempts.items():
        if url not in known:
            last = entry["last"]
            known[url] = {
                "provenance": last.get("provenance", "GOV-PUBLIC"),
                "source": last.get("source"),
                "origin": "crawl",
            }

    rows = []
    counts: dict[str, int] = {}
    pending_new = []
    pending_retry = []

    for url in sorted(known):
        meta = known[url]
        entry = attempts.get(url)

        if entry is None:
            state = "DISCOVERED"
            count = 0
            last_status = None
            last_at = None
        else:
            state = classify(entry["last"])
            count = entry["count"]
            last_status = entry["last"].get("http_status")
            last_at = entry["last"].get("retrieved_at")

        counts[state] = counts.get(state, 0) + 1

        retry_eligible = (
            state in RETRYABLE and count < args.max_attempts
        )

        rows.append({
            "url": url,
            "state": state,
            "attempts": count,
            "retry_eligible": retry_eligible,
            "last_http_status": last_status,
            "last_attempt_at": last_at,
            "provenance": meta["provenance"],
            "source": meta["source"],
            "origin": meta["origin"],
        })

        seed_line = (
            f"{url}|{meta['provenance']}|{meta['source'] or ''}"
        )

        if state == "DISCOVERED":
            pending_new.append(seed_line)
        elif retry_eligible:
            pending_retry.append(seed_line)

    # Atomic queue write: never leave a half-written queue behind.
    queue_path = Path(args.queue_out)
    tmp = queue_path.with_suffix(".tmp")

    with tmp.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")

    os.replace(tmp, queue_path)

    pending = (pending_new + pending_retry)[: args.limit]

    if args.pending_out:
        pending_path = Path(args.pending_out)
        tmp = pending_path.with_suffix(".tmp")
        tmp.write_text(
            "\n".join(pending) + ("\n" if pending else ""),
            encoding="utf-8",
        )
        os.replace(tmp, pending_path)

    print(f"Queue: {len(rows)} URLs")

    for state in sorted(counts):
        print(f"  {state}: {counts[state]}")

    print(
        f"Pending emitted: {len(pending)} "
        f"({len(pending_new)} new, {len(pending_retry)} retry-eligible, "
        f"limit {args.limit})"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
