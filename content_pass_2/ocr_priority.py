"""Part XVI — rank the OCR backlog HIGH/MEDIUM/LOW. No OCR here.

Signals: source family, URL/filename tokens, size/pages, and Pass 1
candidate context from sibling pages (same URL directory) — a scanned
FBI Vault part whose neighbors carry shell/ownership candidates ranks
above an isolated administrative scan.

Usage: python3 -m content_pass_2.ocr_priority
"""
from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone

from content_pass_1.common import OUT_ROOT, REPO_ROOT, log, read_jsonl

PASS2_VERSION = "content-pass-2/1.0.0"
OUT = os.path.join(REPO_ROOT, "content-pass-2", "ocr-priority.jsonl")

HIGH_TOKENS = re.compile(
    r"enforcement|complaint|indictment|exhibit|testimony|shell|launder|"
    r"beneficial|ownership|subsidiar|fraud|bribe|racket|organized[- ]crime|"
    r"la[- ]cosa[- ]nostra|bcci|financial", re.I)
MED_TOKENS = re.compile(r"report|assessment|hearing|memo|investigation|part-\d+", re.I)


def main():
    inv = {r["sha256"]: r for r in
           read_jsonl(os.path.join(OUT_ROOT, "corpus-inventory.jsonl"))}
    # candidate density per URL directory (sibling context)
    dir_cands = defaultdict(int)
    for rec in read_jsonl(os.path.join(OUT_ROOT, "document-classes.jsonl")):
        url = (inv.get(rec["sha256"]) or {}).get("url") or ""
        parent = url.rsplit("/", 2)[0] if url.count("/") > 3 else url
        dir_cands[parent] += rec.get("candidate_count") or 0

    rows = []
    for r in read_jsonl(os.path.join(OUT_ROOT, "ocr-required.jsonl")):
        url = r.get("source_url") or ""
        parent = url.rsplit("/", 2)[0] if url.count("/") > 3 else url
        score = 0
        reasons = []
        if r.get("high_value"):
            score += 2
            reasons.append("pass1 high-value source")
        if HIGH_TOKENS.search(url):
            score += 3
            reasons.append("high-value URL tokens")
        elif MED_TOKENS.search(url):
            score += 1
            reasons.append("medium URL tokens")
        fam = r.get("source_family") or ""
        if fam in ("FBI_VAULT", "DOJ", "CONGRESS_OVERSIGHT", "GOVINFO"):
            score += 2
            reasons.append(f"family {fam}")
        pages = r.get("page_count") or 0
        if 3 <= pages <= 200:
            score += 1
            reasons.append("substantive page count")
        sib = dir_cands.get(parent, 0)
        if sib > 50:
            score += 2
            reasons.append(f"sibling candidate density {sib}")
        elif sib > 10:
            score += 1
            reasons.append(f"sibling candidate density {sib}")
        category = "HIGH" if score >= 6 else ("MEDIUM" if score >= 3 else "LOW")
        rows.append({**{k: r.get(k) for k in
                        ("sha256", "source_url", "host", "source_family",
                         "provenance", "page_count", "size_bytes")},
                     "ocr_priority": category,
                     "priority_score": score,
                     "priority_reasons": reasons,
                     "generated_at": datetime.now(timezone.utc).isoformat(),
                     "pass_version": PASS2_VERSION})
    rows.sort(key=lambda x: -x["priority_score"])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
    from collections import Counter
    log(f"ocr-priority: {dict(Counter(r['ocr_priority'] for r in rows))}")


if __name__ == "__main__":
    main()
