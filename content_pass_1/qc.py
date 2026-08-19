"""Step 14 — quality-control sampling.

Deterministically samples candidates across priority tiers plus documents
classified with no ownership/control evidence, mechanically verifies every
locator (offsets must reproduce matched_text against the raw extracted
representation), and emits a sample sheet for manual review.

Usage: python3 -m content_pass_1.qc
"""
from __future__ import annotations

import json
import os
import random

from .common import OUT_ROOT, PASS_VERSION, log, read_jsonl, text_disk_path

SEED = 20260815
PER_TIER = 25


def main():
    cands = list(read_jsonl(os.path.join(OUT_ROOT, "evidence-candidates.jsonl")))
    cands.sort(key=lambda c: -c["review_priority"])
    n = len(cands)
    hi = cands[: n // 10] or cands
    mid = cands[n // 3: 2 * n // 3] or cands
    lo = cands[-(n // 10):] or cands

    negatives = []
    for rec in read_jsonl(os.path.join(OUT_ROOT, "document-classes.jsonl")):
        cats = set(rec.get("candidate_categories") or [])
        if not cats & {"OWNERSHIP_EXPLICIT", "CONTROL_EXPLICIT",
                       "PARENT_SUBSIDIARY", "SHELL_NOMINEE", "STRUCTURED"}:
            negatives.append(rec)

    rng = random.Random(SEED)
    sample = []
    for tier, pool in (("high", hi), ("medium", mid), ("low", lo)):
        for cand in rng.sample(pool, min(PER_TIER, len(pool))):
            sample.append({"tier": tier, "kind": "candidate", **_verify(cand)})
    for rec in rng.sample(negatives, min(PER_TIER, len(negatives))):
        sample.append({
            "tier": "negative", "kind": "no-evidence-document",
            "sha256": rec["sha256"], "source_url": rec.get("source_url"),
            "document_class": rec.get("document_class"),
            "text_excerpt": _excerpt(rec["sha256"]),
        })

    path = os.path.join(OUT_ROOT, "qc-sample.jsonl")
    with open(path, "w", encoding="utf-8") as fh:
        for rec in sample:
            fh.write(json.dumps(rec, sort_keys=True, ensure_ascii=False) + "\n")
    ok = sum(1 for s in sample if s.get("locator_correct"))
    checked = sum(1 for s in sample if "locator_correct" in s)
    log(f"qc: {len(sample)} sampled; locators verified {ok}/{checked}")


def _verify(cand):
    tp = text_disk_path(cand["source_sha256"])
    locator_ok = None
    if os.path.isfile(tp):
        with open(tp, encoding="utf-8") as fh:
            text = fh.read()
        span = text[cand["character_start"]:cand["character_end"]]
        locator_ok = span == cand["matched_text"][:500]
    return {
        "candidate_id": cand["candidate_id"],
        "sha256": cand["source_sha256"],
        "source_url": cand["source_url"],
        "candidate_category": cand["candidate_category"],
        "matched_terms": cand["matched_terms"],
        "matched_text": cand["matched_text"],
        "context_before": cand["context_before"][-150:],
        "context_after": cand["context_after"][:150],
        "review_priority": cand["review_priority"],
        "locator_correct": locator_ok,
        "manual_review": {"false_positive": None, "false_negative": None,
                          "text_extraction_correct": None, "notes": None},
        "pass_version": PASS_VERSION,
    }


def _excerpt(sha):
    tp = text_disk_path(sha)
    if not os.path.isfile(tp):
        return None
    with open(tp, encoding="utf-8") as fh:
        return fh.read(600)


if __name__ == "__main__":
    main()
