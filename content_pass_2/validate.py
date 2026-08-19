"""Part XXIV — pre-scale validation sample.

Samples up to 25 observations per category (ownership, control,
parent/subsidiary, shell/nominee, financial flow), mechanically verifies
every locator against the derived raw text (which was itself verified
against archived bytes in Pass 1 QC), and emits a review sheet whose
manual fields are filled during human inspection.

Usage: python3 -m content_pass_2.validate
"""
from __future__ import annotations

import json
import os
import random

from content_pass_1.common import REPO_ROOT, log, read_jsonl, text_disk_path

CP2 = os.path.join(REPO_ROOT, "content-pass-2")
SEED = 20260815


def main():
    rng = random.Random(SEED)
    groups = {"OWNERSHIP": [], "CONTROL": [], "PARENT_SUBSIDIARY": [],
              "SHELL_NOMINEE": []}
    for a in read_jsonl(os.path.join(CP2, "normalized-assertions.jsonl")):
        if not a.get("duplicate_of_prior_sentence"):
            groups[a["assertion_type"]].append(a)
    flows = [f for f in read_jsonl(
        os.path.join(CP2, "financial-flow-observations.jsonl"))
        if not f.get("duplicate_of_prior_sentence")]

    sample = []
    for cat, pool in list(groups.items()) + [("FINANCIAL_FLOW", flows)]:
        for rec in rng.sample(pool, min(25, len(pool))):
            sha = rec["source_sha256"]
            loc = rec["source_locator"]
            tp = text_disk_path(sha)
            locator_ok = None
            if os.path.isfile(tp):
                with open(tp, encoding="utf-8") as fh:
                    text = fh.read()
                window = text[loc["character_start"]:loc["character_end"]]
                probe = rec["raw_text"][:200]
                locator_ok = probe[:120].strip() in window
            sample.append({
                "category": cat,
                "id": rec.get("assertion_id") or rec.get("transaction_observation_id"),
                "observation_id": rec["observation_id"],
                "source_sha256": sha,
                "source_url": rec["source_url"],
                "subject": rec.get("subject_raw") or rec.get("sender"),
                "object": rec.get("object_raw") or rec.get("recipient"),
                "predicate": rec.get("predicate_raw") or "flow",
                "percentage": rec.get("ownership_percentage"),
                "description": rec.get("ownership_description"),
                "amount": rec.get("amount_raw"),
                "evidentiary_posture": rec["evidentiary_posture"],
                "raw_text": rec["raw_text"][:400],
                "locator_correct": locator_ok,
                "manual_review": {
                    "text_correct": None, "entities_correct": None,
                    "predicate_correct": None, "value_correct": None,
                    "posture_correct": None, "resolution_correct": None,
                    "notes": None},
            })
    path = os.path.join(CP2, "validation-sample.jsonl")
    with open(path, "w", encoding="utf-8") as fh:
        for s in sample:
            fh.write(json.dumps(s, sort_keys=True, ensure_ascii=False) + "\n")
    ok = sum(1 for s in sample if s["locator_correct"])
    log(f"validate: {len(sample)} sampled; locators mechanically verified "
        f"{ok}/{len(sample)}")


if __name__ == "__main__":
    main()
