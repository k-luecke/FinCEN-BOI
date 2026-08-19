#!/usr/bin/env python3
"""
Union-merge recovery link files by recovery_id.

Usage: merge_recovery_links.py BASE_FILE OURS_FILE OUT_FILE

Used by the recovery workflow's commit step: BASE is the freshest
committed recovery-links.jsonl (from FETCH_HEAD), OURS is this run's
version. Links are append-only observations — a merge may only ever
add rows, never drop or rewrite one.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def load(path: str) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    p = Path(path)
    if not p.exists():
        return rows
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            rows[row.get("recovery_id") or json.dumps(row,
                                                      sort_keys=True)] \
                = row
    return rows


def main() -> int:
    if len(sys.argv) != 4:
        print(__doc__, file=sys.stderr)
        return 2

    base = load(sys.argv[1])
    ours = load(sys.argv[2])

    merged = dict(base)
    added = 0
    for key, row in ours.items():
        if key not in merged:
            merged[key] = row
            added += 1

    out = Path(sys.argv[3])
    with out.open("w", encoding="utf-8") as f:
        for row in sorted(
            merged.values(),
            key=lambda r: (r.get("created_at") or "",
                           r.get("recovery_id") or ""),
        ):
            f.write(json.dumps(row, sort_keys=True, ensure_ascii=False)
                    + "\n")

    print(f"merged links: {len(base)} base + {added} new "
          f"= {len(merged)} total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
