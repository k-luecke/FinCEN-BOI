"""Parts V–IX, XXI–XXIII — normalized assertions, conservative resolution,
financial-flow observations.

Raw observations are never modified; every normalized assertion points
back to its observation_id (and through it to candidate, locator, sha256,
retrieval record, original URL — the Part XXI evidence walk).

Resolution is conservative: UNRESOLVED by default; PROBABLE_MATCH only
when a normalized name exactly matches a single EDGAR registrant from the
evidence-guided match set (identifier attached, nodes NOT merged);
AMBIGUOUS when several registrants share the name. Nothing is merged on
name similarity. People are never merged.

Usage: python3 -m content_pass_2.normalize
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone

from content_pass_1.common import REPO_ROOT, log, read_jsonl
from .edgar_queue import norm_name

PASS2_VERSION = "content-pass-2/1.0.0"
NORMALIZER_VERSION = "normalize/1.0.0"
CP2 = os.path.join(REPO_ROOT, "content-pass-2")

SUFFIX_RE = re.compile(
    r"\b(LLC|L\.L\.C\.|Inc\.?|Corp\.?|Corporation|Company|Co\.|Ltd\.?|LP|LLP|"
    r"PLLC|Holdings?|Group|Trust|Bank|N\.A\.|S\.?A\.?R\.?L\.?|Partners(?:hip)?|"
    r"Fund|Ventures?|Capital|Financial|Investments?)\b", re.I)
PERSONISH = re.compile(r"^[A-Z][a-z]+(?:\s+[A-Z]\.?)?(?:\s+[A-Z][a-z]+){1,2}$")
DEFTERMISH = re.compile(r"^the\s", re.I)
MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
DATE_FULL = re.compile(
    r"(January|February|March|April|May|June|July|August|September|October|"
    r"November|December)\s+(\d{1,2}),?\s+((?:19|20)\d{2})")

TIER_ASSERTION = {
    "A_OWNERSHIP": "OWNERSHIP",
    "B_CONTROL": "CONTROL",
    "C_PARENT_SUBSIDIARY": "PARENT_SUBSIDIARY",
    "D_SHELL_NOMINEE": "SHELL_NOMINEE",
}


def classify_actor(name: str) -> str:
    if not name:
        return "MISSING"
    if SUFFIX_RE.search(name):
        return "ENTITY"
    if DEFTERMISH.match(name):
        return "DEFINED_TERM"
    if re.fullmatch(r"[A-Z]{2,6}(?:-\d+)?", name):
        return "ABBREVIATION"
    if PERSONISH.match(name):
        return "PERSON_CANDIDATE"  # may still be a brand ("Ripple Labs")
    if re.fullmatch(r"[A-Z][a-z]{2,}", name):
        return "SURNAME_CANDIDATE"
    return "UNCLASSIFIED"


def node_id(name: str, kind: str) -> str:
    h = hashlib.blake2b(norm_name(name).encode(), digest_size=8).hexdigest()
    prefix = {"ENTITY": "unres:e", "PERSON_CANDIDATE": "unres:p",
              "SURNAME_CANDIDATE": "unres:p"}.get(kind, "unres:x")
    return f"{prefix}:{h}"


def parse_amount(raw):
    if not raw:
        return None
    m = re.match(r"([\d,]+(?:\.\d{2})?)(?:\s+(million|billion))?", raw)
    if not m:
        return None
    v = float(m.group(1).replace(",", ""))
    if m.group(2) == "million":
        v *= 1_000_000
    elif m.group(2) == "billion":
        v *= 1_000_000_000
    return v


def parse_date(raw):
    if not raw:
        return None
    m = DATE_FULL.search(raw)
    if m:
        return f"{m.group(3)}-{MONTHS.index(m.group(1)) + 1:02d}-{int(m.group(2)):02d}"
    m = re.search(r"\b((?:19|20)\d{2})\b", raw)
    return m.group(1) if m else None


def load_edgar_names():
    """normalized registrant name -> set of CIKs (evidence-guided match set)."""
    path = os.path.join(REPO_ROOT, "acquisition", "edgar-priority-queue.jsonl")
    by_name = defaultdict(set)
    if os.path.isfile(path):
        for r in read_jsonl(path):
            if r.get("registrant_name"):
                by_name[norm_name(r["registrant_name"])].add(r["cik"])
    return by_name


def main():
    edgar_names = load_edgar_names()
    assertions, flows = [], []
    nodes = {}   # node_id -> node record
    ambiguous = []
    seen_keys = set()
    seq = 0
    tseq = 0

    for obs in read_jsonl(os.path.join(CP2, "raw-observations.jsonl")):
        subj, obj = obs.get("subject_raw"), obs.get("object_raw")
        dedup_key = (obs["source_sha256"], obs["predicate_raw"],
                     norm_name(subj or ""), norm_name(obj or ""),
                     obs.get("percentage_raw"), obs.get("amount_raw"))
        is_dup = dedup_key in seen_keys
        seen_keys.add(dedup_key)

        if obs["tier"] == "E_FINANCIAL_FLOW":
            tseq += 1
            flows.append({
                "transaction_observation_id": f"txn:{tseq:05d}",
                "observation_id": obs["observation_id"],
                "sender": subj if obs["predicate_raw"] != "received_from" else obj,
                "recipient": obj if obs["predicate_raw"] != "received_from" else subj,
                "sending_bank": None, "intermediary_bank": None,
                "receiving_bank": None,
                "amount_raw": obs.get("amount_raw"),
                "amount_usd": parse_amount(obs.get("amount_raw")),
                "currency": "USD" if obs.get("amount_raw") else None,
                "date_raw": obs.get("date_raw"),
                "date": parse_date(obs.get("date_raw")),
                "account_reference": ("account" in (obj or "").lower()) or None,
                "transaction_count": None,
                "source_sha256": obs["source_sha256"],
                "source_url": obs["source_url"],
                "source_locator": {
                    "character_start": obs["character_start"],
                    "character_end": obs["character_end"],
                    "page": obs.get("page")},
                "evidentiary_posture": obs["evidentiary_posture"],
                "possible_overlap_group": None,
                "duplicate_of_prior_sentence": is_dup or None,
                "raw_text": obs["raw_text"][:600],
                "pass_version": PASS2_VERSION,
            })
            continue

        atype = TIER_ASSERTION[obs["tier"]]
        skind, okind = classify_actor(subj), classify_actor(obj)
        # In these grammars the OWNER/CONTROLLER/PARENT is subject_raw.
        srec = orec = None
        if subj:
            sid = node_id(subj, skind)
            srec = nodes.setdefault(sid, {
                "node_id": sid, "kind": skind, "name_raw_variants": [],
                "name_normalized": norm_name(subj),
                "resolution_status": "UNRESOLVED",
                "candidate_identifiers": {}})
            if subj not in srec["name_raw_variants"]:
                srec["name_raw_variants"].append(subj)
        if obj:
            oid = node_id(obj, okind)
            orec = nodes.setdefault(oid, {
                "node_id": oid, "kind": okind, "name_raw_variants": [],
                "name_normalized": norm_name(obj),
                "resolution_status": "UNRESOLVED",
                "candidate_identifiers": {}})
            if obj not in orec["name_raw_variants"]:
                orec["name_raw_variants"].append(obj)

        # Conservative EDGAR identifier attachment (no merging).
        for rec_ in (srec, orec):
            if rec_ is None or rec_["kind"] != "ENTITY":
                continue
            ciks = edgar_names.get(rec_["name_normalized"])
            if not ciks:
                continue
            if len(ciks) == 1:
                rec_["resolution_status"] = "PROBABLE_MATCH"
                rec_["candidate_identifiers"]["cik"] = sorted(ciks)[0]
            else:
                rec_["resolution_status"] = "AMBIGUOUS"
                rec_["candidate_identifiers"]["cik_candidates"] = sorted(ciks)
                ambiguous.append({
                    "node_id": rec_["node_id"],
                    "name_normalized": rec_["name_normalized"],
                    "cik_candidates": sorted(ciks),
                    "reason": "multiple EDGAR registrants share normalized name",
                })

        seq += 1
        pct = None
        if obs.get("percentage_raw"):
            try:
                pct = float(obs["percentage_raw"])
            except ValueError:
                pct = None
        assertions.append({
            "assertion_id": f"asrt:{seq:05d}",
            "observation_id": obs["observation_id"],
            "candidate_id": obs["candidate_id"],
            "assertion_type": atype,
            "subject_node": srec["node_id"] if srec else None,
            "subject_raw": subj,
            "subject_kind": skind,
            "object_node": orec["node_id"] if orec else None,
            "object_raw": obj,
            "object_kind": okind,
            "predicate_raw": obs["predicate_raw"],
            "ownership_percentage": pct,
            "ownership_description": obs.get("qualifier_raw"),
            "ownership_regime": None,  # SEC_13D_G reserved for filing-derived
            "amount_raw": obs.get("amount_raw"),
            "date_raw": obs.get("date_raw"),
            "source_date": parse_date(obs.get("date_raw")) or obs.get("document_date"),
            "valid_from": None, "valid_to": None,
            "source_sha256": obs["source_sha256"],
            "source_url": obs["source_url"],
            "retrieval_date": obs.get("retrieval_date"),
            "provenance_class": obs.get("provenance_class"),
            "source_family": obs.get("source_family"),
            "source_locator": {
                "character_start": obs["character_start"],
                "character_end": obs["character_end"],
                "page": obs.get("page"),
                "line_start": obs.get("line_start")},
            "evidentiary_posture": obs["evidentiary_posture"],
            "reported_speech": obs.get("reported_speech") or False,
            "extraction_confidence": obs["extraction_confidence"],
            "resolution_confidence": 0.0,
            "duplicate_of_prior_sentence": is_dup or None,
            "raw_text": obs["raw_text"][:600],
            "normalizer_version": NORMALIZER_VERSION,
            "pass_version": PASS2_VERSION,
        })

    with open(os.path.join(CP2, "normalized-assertions.jsonl"), "w") as fh:
        for a in assertions:
            fh.write(json.dumps(a, sort_keys=True, ensure_ascii=False) + "\n")
    with open(os.path.join(CP2, "financial-flow-observations.jsonl"), "w") as fh:
        for f in flows:
            fh.write(json.dumps(f, sort_keys=True, ensure_ascii=False) + "\n")
    ents = [n for n in nodes.values() if n["kind"] == "ENTITY"]
    people = [n for n in nodes.values()
              if n["kind"] in ("PERSON_CANDIDATE", "SURNAME_CANDIDATE")]
    other = [n for n in nodes.values()
             if n["kind"] not in ("ENTITY", "PERSON_CANDIDATE", "SURNAME_CANDIDATE")]
    with open(os.path.join(CP2, "unresolved-entities.jsonl"), "w") as fh:
        for n in sorted(ents, key=lambda x: x["node_id"]):
            fh.write(json.dumps(n, sort_keys=True, ensure_ascii=False) + "\n")
    with open(os.path.join(CP2, "unresolved-people.jsonl"), "w") as fh:
        for n in sorted(people + other, key=lambda x: x["node_id"]):
            fh.write(json.dumps(n, sort_keys=True, ensure_ascii=False) + "\n")
    with open(os.path.join(CP2, "ambiguous-resolutions.jsonl"), "w") as fh:
        for a in ambiguous:
            fh.write(json.dumps(a, sort_keys=True, ensure_ascii=False) + "\n")
    log(f"normalize: {len(assertions)} assertions, {len(flows)} flows, "
        f"{len(ents)} entity nodes, {len(people)} person-candidate nodes, "
        f"{len(other)} other actors, {len(ambiguous)} ambiguous")


if __name__ == "__main__":
    main()
