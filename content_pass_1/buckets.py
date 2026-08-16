"""Step 8 — dedicated high-value candidate bucket indexes.

Splits evidence-candidates.jsonl into the special buckets, sorted by
review_priority descending. Buckets overlap by design (a candidate can
appear in several).

Usage: python3 -m content_pass_1.buckets
"""
from __future__ import annotations

import json
import os

from .common import OUT_ROOT, log, read_jsonl

BUCKETS = {
    "ownership-candidates.jsonl":
        lambda c: "OWNERSHIP_EXPLICIT" in c["candidate_category"]
        or (c["candidate_category"] == ["STRUCTURED"]
            and any(t in ("entity_owned_by", "pct_of_entity")
                    for t in c["matched_terms"])),
    "control-candidates.jsonl":
        lambda c: "CONTROL_EXPLICIT" in c["candidate_category"],
    "parent-subsidiary-candidates.jsonl":
        lambda c: "PARENT_SUBSIDIARY" in c["candidate_category"]
        or "entity_subsidiary_of" in c["matched_terms"],
    "shell-structure-candidates.jsonl":
        lambda c: "SHELL_NOMINEE" in c["candidate_category"],
    "financial-flow-candidates.jsonl":
        lambda c: "FINANCIAL_FLOW" in c["candidate_category"],
    "boi-cta-candidates.jsonl":
        lambda c: "BOI_CTA" in c["candidate_category"],
    "sar-bsa-candidates.jsonl":
        lambda c: "SAR_BSA" in c["candidate_category"],
    "congressional-candidates.jsonl":
        lambda c: (c.get("provenance") == "CONGRESS"
                   or (c.get("source_family") or "").startswith("CONGRESS")
                   or "CONGRESSIONAL_EVIDENCE" in (c.get("document_class") or [])),
}


def main():
    matched = {name: [] for name in BUCKETS}
    total = 0
    for cand in read_jsonl(os.path.join(OUT_ROOT, "evidence-candidates.jsonl")):
        total += 1
        for name, pred in BUCKETS.items():
            if pred(cand):
                matched[name].append(cand)
    for name, cands in matched.items():
        cands.sort(key=lambda c: (-c["review_priority"], c["source_sha256"],
                                  c["candidate_id"]))
        path = os.path.join(OUT_ROOT, name)
        with open(path, "w", encoding="utf-8") as fh:
            for c in cands:
                fh.write(json.dumps(c, sort_keys=True, ensure_ascii=False) + "\n")
        log(f"buckets: {name}: {len(cands)}")
    log(f"buckets: {total} candidates total")


if __name__ == "__main__":
    main()
