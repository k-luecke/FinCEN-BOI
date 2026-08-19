#!/usr/bin/env python3
"""
Per-source coverage report: distinguishes "the public corpus is mostly
small documents" from "our crawler stopped at artificial ceilings".

For every host: URLs discovered, URLs archived, whether a discovery
ceiling was hit (and which), bytes, median and p95 object size, and
the known bulk datasets not yet acquired for that source family.

Reads only committed state (url-inventory.jsonl, manifest.jsonl).
Writes coverage.json and COVERAGE.md atomically.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from collections import defaultdict
from pathlib import Path

from archive import normalized_host, sanitize_url

# Discovery ceilings in effect when the inventory was built.
SITEMAP_URL_CAP = 5000
SITEMAP_FETCH_CAP = 50
FR_PAGE_CAP = 50

# Known bulk datasets NOT yet acquired, by host / source family.
# Curated; update as connectors land.
KNOWN_BULK_GAPS = {
    "www.sec.gov": [
        "EDGAR companyfacts.zip (403 on 2026-08-15; weekly retry)",
        "EDGAR full filing archives (per-filing corpus far beyond web pages)",
        "EDGAR full-text search corpus",
    ],
    "www.govinfo.gov": [
        "GovInfo bulk data collections (FR XML, CFR, court opinions)",
    ],
    "www.federalregister.gov": [
        "Full FR document XML via API (only FinCEN-agency docs enumerated)",
    ],
    "www.congress.gov": [
        "congress.gov API corpus (bills, reports, hearings; needs API key connector)",
    ],
    "www.gao.gov": [
        "GAO reports corpus (no sitemap; needs listing-page/API enumeration)",
    ],
    "_not_yet_onboarded": [
        "IRS Form 990 e-file bulk XML (irs.gov)",
        "SAM.gov entity registration extracts",
        "USAspending award/recipient bulk data",
        "FEC bulk data",
        "50-state corporate registries + UCC (all jurisdictions at RESEARCH)",
        "County recorder/assessor records",
        "Regulatory licensing datasets (Form ADV, NMLS, FCC, FERC, ...)",
    ],
}


def percentile(sorted_values, p):
    if not sorted_values:
        return None

    k = (len(sorted_values) - 1) * p
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)

    if f == c:
        return sorted_values[f]

    return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", default="url-inventory.jsonl")
    parser.add_argument("--manifest", default="manifest.jsonl")
    parser.add_argument("--challenge-observations",
                        default="recovery/challenge-observations.jsonl")
    parser.add_argument("--out-json", default="coverage.json")
    parser.add_argument("--out-md", default="COVERAGE.md")
    args = parser.parse_args()

    # Non-content captures (bot challenges / interstitials / app
    # shells) per host: archived bytes that are NOT the record.
    non_content_by_host = defaultdict(int)
    challenge_path = Path(args.challenge_observations)

    if challenge_path.exists():
        with challenge_path.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue

                row = json.loads(line)

                if row.get("classification") in (
                    "BOT_CHALLENGE", "ACCESS_INTERSTITIAL",
                    "APPLICATION_SHELL", "REDIRECT_STUB",
                ) and row.get("response_sha256"):
                    non_content_by_host[
                        normalized_host(row.get("url", ""))
                    ] += 1

    discovered = defaultdict(int)
    discovered_by_sitemap = defaultdict(int)

    if Path(args.inventory).exists():
        with open(args.inventory, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue

                record = json.loads(line)
                host = record.get("host") or normalized_host(record.get("url", ""))
                discovered[host] += 1

                if str(record.get("discovered_via", "")).startswith("sitemap:"):
                    discovered_by_sitemap[host] += 1

    # Latest successful object per URL.
    latest_success: dict[str, dict] = {}
    attempted = defaultdict(set)

    if Path(args.manifest).exists():
        with open(args.manifest, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue

                record = json.loads(line)
                url = sanitize_url(record.get("url", ""))
                host = normalized_host(url)
                attempted[host].add(url)

                if record.get("sha256"):
                    latest_success[url] = record

    per_host_sizes = defaultdict(list)
    per_host_archived = defaultdict(int)
    per_host_bytes = defaultdict(int)

    for url, record in latest_success.items():
        host = normalized_host(url)
        size = record.get("content_length") or 0
        per_host_archived[host] += 1
        per_host_bytes[host] += size
        per_host_sizes[host].append(size)

    hosts = sorted(set(discovered) | set(per_host_archived) | set(attempted))
    rows = []

    for host in hosts:
        sizes = sorted(per_host_sizes.get(host, []))
        ceiling = (
            f"YES — sitemap cap {SITEMAP_URL_CAP}/host"
            if discovered_by_sitemap.get(host, 0) >= SITEMAP_URL_CAP
            else "no"
        )
        rows.append({
            "host": host,
            "urls_discovered": discovered.get(host, 0),
            "urls_attempted": len(attempted.get(host, set())),
            "urls_archived": per_host_archived.get(host, 0),
            "non_content_captures": non_content_by_host.get(host, 0),
            "urls_with_content": (
                per_host_archived.get(host, 0)
                - non_content_by_host.get(host, 0)
            ),
            "ceiling_hit": ceiling,
            "bytes": per_host_bytes.get(host, 0),
            "median_object_bytes": int(statistics.median(sizes)) if sizes else None,
            "p95_object_bytes": int(percentile(sizes, 0.95)) if sizes else None,
            "known_bulk_gaps": KNOWN_BULK_GAPS.get(host, []),
        })

    report = {
        "generated_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
        "discovery_ceilings": {
            "sitemap_urls_per_host": SITEMAP_URL_CAP,
            "sitemap_fetches_per_host": SITEMAP_FETCH_CAP,
            "federal_register_pages": FR_PAGE_CAP,
        },
        "hosts": rows,
        "not_yet_onboarded_bulk_sources": KNOWN_BULK_GAPS["_not_yet_onboarded"],
        "interpretation_note": (
            "Hosts at the sitemap cap are bounded by DISCOVERY BUDGET, "
            "not by the natural end of their collections; archive size "
            "is not a proxy for share-of-corpus preserved. The CTA-filed "
            "BOI database is confidential, not publicly downloadable, "
            "and is not represented in any byte count here."
        ),
    }

    tmp = Path(args.out_json).with_suffix(".tmp")
    tmp.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, args.out_json)

    def fmt(n):
        return f"{n:,}" if isinstance(n, int) else ("—" if n is None else str(n))

    lines = [
        "# Coverage report",
        "",
        f"Generated {report['generated_at']} from committed inventory + manifest.",
        "",
        "**Reading this table:** a host at the sitemap cap "
        f"({SITEMAP_URL_CAP} URLs/host) is bounded by *discovery budget*, "
        "not by the end of its collection — those rows are a first slice. "
        "Archive size is never a proxy for share-of-BOI preserved: the "
        "CTA-filed database is confidential and not publicly downloadable.",
        "",
        "**Non-content**: captures the challenge detector classified as "
        "bot challenges / interstitials / application shells — bytes we "
        "hold that are *not* the requested record (see "
        "RECOVERY-REPORT.md for lawful alternate-route recovery).",
        "",
        "| Host | Discovered | Attempted | Archived | Non-content | With content | Ceiling hit? | Bytes | Median obj | p95 obj |",
        "|------|-----------:|----------:|---------:|------------:|-------------:|--------------|------:|-----------:|--------:|",
    ]

    for row in rows:
        lines.append(
            f"| {row['host']} | {fmt(row['urls_discovered'])} | "
            f"{fmt(row['urls_attempted'])} | {fmt(row['urls_archived'])} | "
            f"{fmt(row['non_content_captures'])} | "
            f"{fmt(row['urls_with_content'])} | "
            f"{row['ceiling_hit']} | {fmt(row['bytes'])} | "
            f"{fmt(row['median_object_bytes'])} | {fmt(row['p95_object_bytes'])} |"
        )

    lines += ["", "## Known bulk datasets not yet acquired", ""]

    for host, gaps in KNOWN_BULK_GAPS.items():
        if host == "_not_yet_onboarded" or not gaps:
            continue
        lines.append(f"**{host}**")
        lines += [f"- {g}" for g in gaps]
        lines.append("")

    lines.append("**Not yet onboarded (source families)**")
    lines += [f"- {g}" for g in KNOWN_BULK_GAPS["_not_yet_onboarded"]]
    lines.append("")

    tmp = Path(args.out_md).with_suffix(".tmp")
    tmp.write_text("\n".join(lines), encoding="utf-8")
    os.replace(tmp, args.out_md)

    capped = [r["host"] for r in rows if r["ceiling_hit"] != "no"]
    print(f"Coverage: {len(rows)} hosts; ceiling hit on {len(capped)}: {', '.join(capped)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
