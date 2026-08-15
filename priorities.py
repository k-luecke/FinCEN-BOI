#!/usr/bin/env python3
"""
Time-sensitive coverage dashboard by priority tier ->
PRESERVATION-PRIORITIES.md + preservation-priorities.json.

Tiers: 0 = FinCEN/CTA/BOI core record; 1 = government evidence that
may preserve otherwise-nonpublic facts; 2 = ownership side channels;
3 = state/county records. Computed from committed inventory+manifest;
regenerated on every state commit.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

from archive import normalized_host, sanitize_url

# host -> (tier, denominator status note)
HOST_TIERS = {
    "www.fincen.gov": (0, "KNOWN_COMPLETE (full sitemap, under cap)"),
    "bsaefiling.fincen.gov": (0, "ACCESS_LIMITED (unreachable from CI)"),
    "home.treasury.gov": (0, "ENUMERABLE"),
    "www.treasury.gov": (0, "ENUMERABLE"),
    "oig.treasury.gov": (0, "KNOWN_COMPLETE (72, under cap)"),
    "www.federalregister.gov": (0, "ACCESS_LIMITED (bot mitigation; use API + govinfo twins)"),
    "www.govinfo.gov": (1, "OPEN_ENDED (bulk collections exist)"),
    "www.congress.gov": (1, "NOT_ONBOARDED (API connector needed)"),
    "judiciary.house.gov": (1, "NOT_ONBOARDED (no sitemap)"),
    "oversight.house.gov": (1, "ENUMERABLE"),
    "www.gao.gov": (1, "NOT_ONBOARDED (no sitemap; listing pages only)"),
    "vault.fbi.gov": (1, "ENUMERABLE"),
    "www.justice.gov": (1, "OPEN_ENDED (quality audit gating expansion)"),
    "www.occ.gov": (1, "ENUMERABLE"),
    "www.fdic.gov": (1, "ENUMERABLE"),
    "ncua.gov": (1, "ENUMERABLE"),
    "www.ncua.gov": (1, "ENUMERABLE"),
    "www.federalreserve.gov": (1, "NOT_ONBOARDED (no sitemap)"),
    "www.ffiec.gov": (1, "ACCESS_LIMITED (403 from CI)"),
    "bsaaml.ffiec.gov": (1, "ACCESS_LIMITED (403 from CI)"),
    "www.sec.gov": (2, "OPEN_ENDED (EDGAR bulk beyond web pages)"),
}

DISCOVERY_CAPS = [30000, 5000]

NOT_ONBOARDED_FAMILIES = [
    ("IRS Form 990 bulk XML", 2),
    ("SAM.gov / USAspending snapshots", 2),
    ("FEC bulk data", 2),
    ("Regulatory licensing datasets (ADV, NMLS, FCC, FERC)", 2),
    ("50-state corporate registries + UCC", 3),
    ("County recorder/assessor records", 3),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", default="url-inventory.jsonl")
    parser.add_argument("--manifest", default="manifest.jsonl")
    parser.add_argument("--out-json", default="preservation-priorities.json")
    parser.add_argument("--out-md", default="PRESERVATION-PRIORITIES.md")
    args = parser.parse_args()

    discovered = defaultdict(int)

    if Path(args.inventory).exists():
        for line in open(args.inventory, encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                discovered[r.get("host") or normalized_host(r.get("url", ""))] += 1

    archived_urls = {}
    last_capture = defaultdict(str)
    temp_fail = defaultdict(int)
    restricted = defaultdict(int)

    if Path(args.manifest).exists():
        for line in open(args.manifest, encoding="utf-8"):
            if not line.strip():
                continue

            r = json.loads(line)
            url = sanitize_url(r.get("url", ""))
            host = normalized_host(url)

            if r.get("sha256"):
                archived_urls[url] = r
                last_capture[host] = max(last_capture[host], r.get("retrieved_at") or "")
            elif r.get("http_status") in (401, 403):
                restricted[host] += 1
            elif r.get("http_status") not in (404, 410):
                temp_fail[host] += 1

    per_host_arch = defaultdict(int)
    per_host_bytes = defaultdict(int)

    for url, r in archived_urls.items():
        host = normalized_host(url)
        per_host_arch[host] += 1
        per_host_bytes[host] += r.get("content_length") or 0

    rows = []

    for host in sorted(set(discovered) | set(per_host_arch)):
        tier, denom = HOST_TIERS.get(host, (1, "UNCLASSIFIED"))
        d = discovered.get(host, 0)
        ceiling = next(
            (f"CEILING_HIT_{cap}" for cap in DISCOVERY_CAPS if d >= cap),
            "no",
        )
        rows.append({
            "source": host, "tier": tier,
            "discovered": d,
            "archived": per_host_arch.get(host, 0),
            "unarchived": max(0, d - per_host_arch.get(host, 0)),
            "bytes": per_host_bytes.get(host, 0),
            "denominator_status": denom,
            "ceiling_hit": ceiling,
            "last_successful_capture": last_capture.get(host) or None,
            "temporary_failures": temp_fail.get(host, 0),
            "access_restricted": restricted.get(host, 0),
            "historical_recovery": "NOT_STARTED",
        })

    for family, tier in NOT_ONBOARDED_FAMILIES:
        rows.append({
            "source": family, "tier": tier, "discovered": 0,
            "archived": 0, "unarchived": None, "bytes": 0,
            "denominator_status": "NOT_ONBOARDED", "ceiling_hit": "n/a",
            "last_successful_capture": None, "temporary_failures": 0,
            "access_restricted": 0, "historical_recovery": "NOT_STARTED",
        })

    rows.sort(key=lambda r: (r["tier"], -(r["unarchived"] or 0)))

    report = {
        "generated_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).isoformat(),
        "sources": rows,
        "high_priority_backlog": sum(
            r["unarchived"] or 0 for r in rows if r["tier"] <= 1
        ),
    }

    tmp = Path(args.out_json).with_suffix(".tmp")
    tmp.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, args.out_json)

    lines = [
        "# Preservation priorities (initial acquisition window)",
        "",
        f"Generated {report['generated_at']}. "
        f"**High-priority (tier 0-1) unarchived backlog: "
        f"{report['high_priority_backlog']:,} URLs.**",
        "",
        "| Tier | Source | Discovered | Archived | Unarchived | Bytes | Denominator | Ceiling | Temp fail | Restricted |",
        "|-----:|--------|-----------:|---------:|-----------:|------:|-------------|---------|----------:|-----------:|",
    ]

    for r in rows:
        lines.append(
            f"| {r['tier']} | {r['source']} | {r['discovered']:,} | "
            f"{r['archived']:,} | "
            f"{'?' if r['unarchived'] is None else format(r['unarchived'], ',')} | "
            f"{r['bytes']:,} | {r['denominator_status']} | {r['ceiling_hit']} | "
            f"{r['temporary_failures']:,} | {r['access_restricted']:,} |"
        )

    lines += ["", "Historical/superseded-source recovery: NOT_STARTED for all "
              "tiers (next phase after current-source frontier).", ""]

    tmp = Path(args.out_md).with_suffix(".tmp")
    tmp.write_text("\n".join(lines), encoding="utf-8")
    os.replace(tmp, args.out_md)

    print(f"priorities: tier0-1 backlog {report['high_priority_backlog']:,} URLs")

    return 0


if __name__ == "__main__":
    sys.exit(main())
