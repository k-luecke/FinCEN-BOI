"""Parts XXI–XXIII — validated graph edges.

Emits edges in the ownership-reconstruction universal edge format,
extended with the mandatory Pass 2 evidence fields:

  evidentiary_posture   — who asserts it, in what capacity (Part I)
  reported_speech       — the source reports someone else's claim
  observation_id / assertion_id / candidate_id — the full Part XXI walk

Assertion mapping (schema vocabulary):
  OWNERSHIP          -> BENEFICIAL_OWNER  (source itself states ownership;
                                           evidence_class DIRECT)
  CONTROL            -> UNKNOWN_CONTROL_ROLE (control shown, capacity
                                              unclear unless ownership too)
  PARENT_SUBSIDIARY  -> PARENT (subject is parent of object)

Gates (validated by the Part XXIV sample — 67/94 fully correct, defect
classes below excluded):
  - both subject and object captured
  - no reported-speech flag
  - names pass sanity screens (no conjunctions-as-one-entity, no generic
    stubs, no boundary-crossing artifacts)
  - extraction_confidence >= 0.9

SHELL_NOMINEE and FINANCIAL_FLOW remain observation-level only in this
pass (no graph edges) — flows per Part IX, shell narrative per Part III D.

Usage: python3 -m content_pass_2.edges
"""
from __future__ import annotations

import json
import os
import re
from collections import Counter

from content_pass_1.common import REPO_ROOT, log, read_jsonl

PASS2_VERSION = "content-pass-2/1.0.0"
CP2 = os.path.join(REPO_ROOT, "content-pass-2")

ASSERTION_MAP = {
    "OWNERSHIP": "BENEFICIAL_OWNER",
    "CONTROL": "UNKNOWN_CONTROL_ROLE",
    "PARENT_SUBSIDIARY": "PARENT",
}

# Validation-derived rejection screens.
BAD_NAME = re.compile(
    r"^(?:Both|All|Each|Various|Several|Certain)\b|"          # conjunctive/plural stubs
    r"^(?:Limited\s+Liability\s+Company|Company|Corporation|LLC|Inc\.?|"
    r"US|UN|Bank|Trust|Group)$|"                              # generic stubs
    r"\b(?:Proposed|Additionally|Shareholders)\b|"            # heading crossings
    r"\.\s|"                                                  # sentence boundary inside
    r"\band\b.*\b(?:LLC|Inc\.?|Corp\.?|Company|Bank)\b.*\band\b")
CONJUNCTION = re.compile(r"\b(?:and|or)\b\s+[A-Z]")


def name_ok(name: str) -> bool:
    if not name or len(name) < 3 or len(name) > 90:
        return False
    if BAD_NAME.search(name):
        return False
    return True


def main():
    edges = []
    stats = Counter()
    for a in read_jsonl(os.path.join(CP2, "normalized-assertions.jsonl")):
        stats["assertions"] += 1
        if a.get("duplicate_of_prior_sentence"):
            stats["skip_duplicate_sentence"] += 1
            continue
        atype = a["assertion_type"]
        if atype not in ASSERTION_MAP:
            stats["skip_type_" + atype] += 1
            continue
        subj, obj = a.get("subject_raw"), a.get("object_raw")
        if not (subj and obj):
            stats["skip_missing_party"] += 1
            continue
        if a.get("reported_speech"):
            stats["skip_reported_speech"] += 1
            continue
        if a.get("extraction_confidence", 0) < 0.9:
            stats["skip_low_confidence"] += 1
            continue
        if not (name_ok(subj) and name_ok(obj)):
            stats["skip_name_screen"] += 1
            continue
        # Conjunctive objects ("A and B") stay observation-level: splitting
        # them into two edges would be inference beyond the capture.
        if CONJUNCTION.search(obj) and atype != "CONTROL":
            stats["skip_conjunctive_object"] += 1
            continue
        edges.append({
            # ownership-reconstruction universal edge fields
            "subject_id": a["subject_node"],
            "assertion": ASSERTION_MAP[atype],
            "object_id": a["object_node"],
            "ownership_percent": a.get("ownership_percentage"),
            "valid_from": None,
            "valid_to": None,
            "source_id": a.get("assertion_id"),
            "source_url": a["source_url"],
            "source_date": a.get("source_date"),
            "retrieved_at": a.get("retrieval_date"),
            "source_sha256": a["source_sha256"],
            "source_locator": json.dumps(a["source_locator"], sort_keys=True),
            "evidence_class": "DIRECT",
            "confidence": a.get("extraction_confidence"),
            # Pass 2 evidence-model extension (Part I)
            "evidentiary_posture": a["evidentiary_posture"],
            "reported_speech": False,
            "ownership_description": a.get("ownership_description"),
            "ownership_regime": a.get("ownership_regime"),
            "subject_name_raw": subj,
            "object_name_raw": obj,
            "assertion_id": a["assertion_id"],
            "observation_id": a["observation_id"],
            "candidate_id": a["candidate_id"],
            "provenance_class": a.get("provenance_class"),
            "pass_version": PASS2_VERSION,
        })
    with open(os.path.join(CP2, "validated-edges.jsonl"), "w") as fh:
        for e in edges:
            fh.write(json.dumps(e, sort_keys=True, ensure_ascii=False) + "\n")
    log(f"edges: {len(edges)} validated edges "
        f"({dict((k, v) for k, v in stats.most_common() if k.startswith('skip'))})")


if __name__ == "__main__":
    main()
