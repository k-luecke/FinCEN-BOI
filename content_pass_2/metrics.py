"""Part XXVI — Pass 2 metrics.

Usage: python3 -m content_pass_2.metrics
"""
from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timezone

from content_pass_1.common import REPO_ROOT, log, read_jsonl

CP2 = os.path.join(REPO_ROOT, "content-pass-2")
ACQ = os.path.join(REPO_ROOT, "acquisition")


def count(path):
    p = os.path.join(CP2, path)
    return sum(1 for _ in open(p)) if os.path.isfile(p) else 0


def main():
    obs = list(read_jsonl(os.path.join(CP2, "raw-observations.jsonl")))
    asr = list(read_jsonl(os.path.join(CP2, "normalized-assertions.jsonl")))
    edges = list(read_jsonl(os.path.join(CP2, "validated-edges.jsonl")))
    flows = list(read_jsonl(os.path.join(CP2, "financial-flow-observations.jsonl")))
    ents = list(read_jsonl(os.path.join(CP2, "unresolved-entities.jsonl")))
    people = list(read_jsonl(os.path.join(CP2, "unresolved-people.jsonl")))
    eq = list(read_jsonl(os.path.join(ACQ, "edgar-priority-queue.jsonl")))
    vs = list(read_jsonl(os.path.join(CP2, "validation-sample.jsonl")))

    def by(recs, key):
        return dict(Counter((r.get(key) or "?") for r in recs).most_common())

    def year_of(r):
        d = r.get("source_date") or r.get("document_date") or ""
        return d[:4] if len(d) >= 4 and d[:4].isdigit() else "?"

    metrics = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pass_version": "content-pass-2/1.0.0",
        "raw_observations": len(obs),
        "raw_observations_by_tier": by(obs, "tier"),
        "raw_observations_by_posture": by(obs, "evidentiary_posture"),
        "raw_observations_by_family": by(obs, "source_family"),
        "normalized_assertions": len(asr),
        "assertions_by_type": by(asr, "assertion_type"),
        "assertions_by_posture": by(asr, "evidentiary_posture"),
        "assertions_by_family": by(asr, "source_family"),
        "assertions_by_provenance": by(asr, "provenance_class"),
        "assertions_by_year": dict(sorted(Counter(year_of(a) for a in asr).items())),
        "assertions_reported_speech": sum(1 for a in asr if a.get("reported_speech")),
        "validated_edges": len(edges),
        "edges_by_assertion": by(edges, "assertion"),
        "edges_by_posture": by(edges, "evidentiary_posture"),
        "ownership_edges": sum(1 for e in edges if e["assertion"] == "BENEFICIAL_OWNER"),
        "control_edges": sum(1 for e in edges if e["assertion"] == "UNKNOWN_CONTROL_ROLE"),
        "parent_subsidiary_edges": sum(1 for e in edges if e["assertion"] == "PARENT"),
        "sec_beneficial_ownership_edges": 0,
        "sec_13dg_note": "no 13D/G filings archived yet; targeted EDGAR batch "
                         "dispatched — SEC_13D_G regime extraction is next-batch work",
        "percentage_bearing_ownership": sum(
            1 for a in asr if a.get("ownership_percentage") is not None),
        "qualitative_ownership_descriptions": sum(
            1 for a in asr if a.get("ownership_description")),
        "shell_nominee_observations": sum(
            1 for a in asr if a["assertion_type"] == "SHELL_NOMINEE"),
        "financial_flow_observations": len(flows),
        "amount_bearing_flow_observations": sum(
            1 for f in flows if f.get("amount_usd")),
        "unique_entities": len(ents),
        "entities_probable_match": sum(
            1 for e in ents if e["resolution_status"] == "PROBABLE_MATCH"),
        "entities_ambiguous": sum(
            1 for e in ents if e["resolution_status"] == "AMBIGUOUS"),
        "entities_unresolved": sum(
            1 for e in ents if e["resolution_status"] == "UNRESOLVED"),
        "unique_person_candidates_and_other_actors": len(people),
        "people_resolved": 0,
        "people_note": "no automatic person resolution performed by design",
        "validation_sample": {
            "total": len(vs),
            "verdicts": dict(Counter(
                v["manual_review"]["verdict"] for v in vs)),
            "locator_correct": sum(1 for v in vs if v.get("locator_correct")),
        },
        "ocr_priority": dict(Counter(
            r["ocr_priority"] for r in
            read_jsonl(os.path.join(CP2, "ocr-priority.jsonl")))),
        "acquisition": {
            "edgar_targets_discovered": len(eq),
            "edgar_targets_already_archived": sum(
                1 for r in eq if r.get("already_archived")),
            "edgar_matched_ciks": len({r["cik"] for r in eq}),
            "edgar_batch1_seeds": sum(
                1 for _ in open(os.path.join(ACQ, "seeds-edgar-batch1.txt"))),
            "doj_recovery_queue": sum(
                1 for _ in open(os.path.join(ACQ, "doj-recovery-queue.jsonl"))),
            "congress_queue": sum(
                1 for _ in open(os.path.join(ACQ, "congress-priority-queue.jsonl"))),
            "gao_queue": sum(
                1 for _ in open(os.path.join(ACQ, "gao-priority-queue.jsonl"))),
            "govinfo_queue": sum(
                1 for _ in open(os.path.join(ACQ, "govinfo-priority-queue.jsonl"))),
            "historical_fincen_queue": sum(
                1 for _ in open(os.path.join(ACQ, "historical-fincen-queue.jsonl"))),
            "dispatched_runs": [31891026640, 31891027794],
            "newly_archived_note": "crawl runs in progress on Actions at metrics "
                                   "time; durable counts land in root metrics.json "
                                   "via the standard commit_state pipeline",
        },
    }
    path = os.path.join(CP2, "metrics.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2, sort_keys=True)
        fh.write("\n")
    log(f"pass-2 metrics written to {path}")


if __name__ == "__main__":
    main()
