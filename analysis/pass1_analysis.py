#!/usr/bin/env python3
"""First analysis pass over committed Content Pass 1 outputs.

Reads only committed inputs (content-pass-1/) plus, optionally, the
reassembled derived-text tree for span resolution:

    cat derived-release-staging/derived-content-pass-1.tar.zst.part0* \
        > /tmp/derived.tar.zst   # verify against sha256sums.txt, then extract

Usage:
    python3 analysis/pass1_analysis.py [--derived-root PATH] [--out PATH]

Produces analysis/pass1-analysis.json and prints a summary. Deterministic:
fixed sampling seed, no network, no LLM.
"""

import argparse
import collections
import gzip
import json
import random
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PASS1 = REPO / "content-pass-1"

# Doc counts as "ownership-bearing" if it carries any of these categories
# (same definition as CONTENT-PASS-1-REPORT.md section 5).
OWNERSHIP_CATEGORIES = {
    "OWNERSHIP_EXPLICIT",
    "CONTROL_EXPLICIT",
    "PARENT_SUBSIDIARY",
    "STRUCTURED",
}

# The one Treasury sidebar program-listing line that escaped boilerplate
# suppression (CONTENT-PASS-1-REPORT.md section 4 caveat). Every instance
# shares this exact nav context around the match.
SIDEBAR_BEFORE = "Terrorist Finance Tracking Program"
SIDEBAR_AFTER = "Financial Action Task Force"

# Pass-2 bucket mapping (content_pass_2/observe.py tiers A..E).
PASS2_BUCKETS = {
    "OWNERSHIP_EXPLICIT": "A_OWNERSHIP",
    "CONTROL_EXPLICIT": "B_CONTROL",
    "PARENT_SUBSIDIARY": "C_PARENT_SUBSIDIARY",
    "SHELL_NOMINEE": "D_SHELL_NOMINEE",
    "FINANCIAL_FLOW": "E_FINANCIAL_FLOW",
}

VERB_RE = re.compile(
    r"\b(owns?|owned|holds?|held|controls?|controlled|acquired?|acquires?|"
    r"purchased?|transferred?|merged?|is|are|was|were|became|operates?|"
    r"formed|established|incorporated|registered)\b",
    re.IGNORECASE,
)


def read_jsonl_gz(path):
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def read_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def is_sidebar_boilerplate(cand):
    return (
        cand["host"] == "home.treasury.gov"
        and SIDEBAR_BEFORE in cand.get("context_before", "")
        and SIDEBAR_AFTER in cand.get("context_after", "")
    )


def clean_year(document_date):
    """Return a plausible year (1900..2026) or None."""
    if not document_date:
        return None
    m = re.match(r"(\d{4})", str(document_date))
    if not m:
        return None
    year = int(m.group(1))
    return year if 1900 <= year <= 2026 else None


def text_path(derived_root, sha256):
    return derived_root / "text" / sha256[:2] / (sha256[2:] + ".txt")


def resolve_span(derived_root, cand, pad=120):
    """Return (verified, snippet) for a candidate against the derived tree."""
    path = text_path(derived_root, cand["source_sha256"])
    if not path.exists():
        return None, None
    text = path.read_text(encoding="utf-8", errors="replace")
    start, end = cand["character_start"], cand["character_end"]
    got = text[start:end]
    snippet = text[max(0, start - pad) : end + pad].replace("\n", " ")
    return got == cand["matched_text"], snippet


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--derived-root", type=Path, default=None,
                    help="Path to extracted derived/ tree (contains text/)")
    ap.add_argument("--out", type=Path, default=REPO / "analysis" / "pass1-analysis.json")
    ap.add_argument("--sample-seed", type=int, default=20260817)
    args = ap.parse_args()

    baseline = json.load(open(PASS1 / "metrics.json"))

    # --- near-duplicate canonicalisation: keep lexicographically smallest
    # sha256 of each group, mark the rest as duplicates.
    dup_shas = set()
    dup_groups = 0
    for group in read_jsonl(PASS1 / "near-duplicate-groups.jsonl"):
        dup_groups += 1
        shas = sorted(m["sha256"] for m in group["members"])
        dup_shas.update(shas[1:])

    # --- single pass over all candidates.
    cands_total = 0
    sidebar_count = 0
    by_category_raw = collections.Counter()
    by_category_clean = collections.Counter()  # sidebar removed
    by_category_dedup = collections.Counter()  # sidebar removed + dup docs removed
    by_family_clean = collections.Counter()
    docs_with_cand = set()
    ownership_docs = set()
    ownership_doc_meta = {}  # sha -> (family, year)
    top_candidates = []  # ownership/control, clean, canonical
    grammar_sample_pool = collections.defaultdict(list)
    span_check_pool = []
    rng = random.Random(args.sample_seed)

    for cand in read_jsonl_gz(PASS1 / "evidence-candidates.jsonl.gz"):
        cands_total += 1
        sha = cand["source_sha256"]
        categories = cand["candidate_category"]
        sidebar = is_sidebar_boilerplate(cand)
        if sidebar:
            sidebar_count += 1
        for cat in categories:
            by_category_raw[cat] += 1
            if not sidebar:
                by_category_clean[cat] += 1
                if sha not in dup_shas:
                    by_category_dedup[cat] += 1
        if sidebar:
            continue

        docs_with_cand.add(sha)
        by_family_clean[cand["source_family"]] += 1
        if OWNERSHIP_CATEGORIES & set(categories):
            ownership_docs.add(sha)
            ownership_doc_meta[sha] = (
                cand["source_family"],
                clean_year(cand.get("document_date")),
            )
            if sha not in dup_shas and any(
                c in ("OWNERSHIP_EXPLICIT", "CONTROL_EXPLICIT") for c in categories
            ):
                top_candidates.append(cand)

        # reservoir-style pools (deterministic via seeded rng)
        for cat in categories:
            bucket = PASS2_BUCKETS.get(cat)
            if bucket:
                pool = grammar_sample_pool[bucket]
                if len(pool) < 40:
                    pool.append(cand)
                elif rng.random() < 40 / by_category_clean[cat]:
                    pool[rng.randrange(40)] = cand
        if len(span_check_pool) < 25:
            span_check_pool.append(cand)
        elif rng.random() < 25 / cands_total:
            span_check_pool[rng.randrange(25)] = cand

    # --- reconciliation against the committed metrics.
    recon = {
        "candidates_total": {"computed": cands_total,
                             "baseline": baseline["candidates_total"]},
        "documents_ownership_bearing_raw_note":
            "baseline counts sidebar-affected docs; see cleaned figures",
        "near_duplicate_groups": {"computed": dup_groups,
                                  "baseline": baseline["near_duplicate_groups"]},
    }

    # --- ownership-bearing docs by family (cleaned) and dedup-adjusted.
    own_by_family = collections.Counter(f for f, _ in ownership_doc_meta.values())
    own_docs_dedup = {s for s in ownership_docs if s not in dup_shas}
    own_by_family_dedup = collections.Counter(
        ownership_doc_meta[s][0] for s in own_docs_dedup
    )

    # --- scanned docs per family, for rates.
    scanned_by_family = collections.Counter()
    junk_years = 0
    all_years = collections.Counter()
    for doc in read_jsonl_gz(PASS1 / "document-classes.jsonl.gz"):
        scanned_by_family[doc["source_family"]] += 1
        year = clean_year(doc.get("document_date"))
        if doc.get("document_date") and year is None:
            junk_years += 1
        elif year:
            all_years[year] += 1

    own_years = collections.Counter(
        y for _, y in ownership_doc_meta.values() if y
    )

    family_table = []
    for fam, scanned in scanned_by_family.most_common():
        own = own_by_family.get(fam, 0)
        family_table.append({
            "source_family": fam,
            "documents_scanned": scanned,
            "ownership_bearing_docs": own,
            "ownership_bearing_docs_dedup": own_by_family_dedup.get(fam, 0),
            "ownership_bearing_rate": round(own / scanned, 4) if scanned else 0,
        })

    # --- top candidates by review_priority, spans resolved if tree present.
    top_candidates.sort(key=lambda c: (-c["review_priority"], c["candidate_id"]))
    top_out = []
    derived = args.derived_root
    for cand in top_candidates[:20]:
        entry = {
            "candidate_id": cand["candidate_id"],
            "review_priority": cand["review_priority"],
            "category": cand["candidate_category"],
            "matched_text": cand["matched_text"],
            "source_family": cand["source_family"],
            "source_url": cand["source_url"],
            "document_date": cand.get("document_date"),
        }
        if derived:
            verified, snippet = resolve_span(derived, cand)
            entry["span_verified"] = verified
            entry["snippet"] = snippet
        top_out.append(entry)

    # --- span verification sample.
    span_results = {"checked": 0, "verified": 0, "missing_text_file": 0}
    if derived:
        for cand in span_check_pool:
            verified, _ = resolve_span(derived, cand)
            if verified is None:
                span_results["missing_text_file"] += 1
            else:
                span_results["checked"] += 1
                span_results["verified"] += verified

    # --- why Pass-2 grammars miss: structural features of sampled candidates.
    grammar_diagnosis = {}
    for bucket, pool in sorted(grammar_sample_pool.items()):
        feats = collections.Counter()
        examples = []
        for cand in pool:
            line = (cand.get("context_before", "")[-100:] + cand["matched_text"]
                    + cand.get("context_after", "")[:100])
            span_line = cand["matched_text"]
            has_verb = bool(VERB_RE.search(line))
            navish = line.count("\n") >= 4  # list/nav/table fragment
            titleish = span_line.istitle() or span_line.isupper()
            feats["no_verb_nearby"] += not has_verb
            feats["nav_or_list_context"] += navish
            feats["title_or_caps_span"] += titleish
            if len(examples) < 3:
                examples.append(cand["matched_text"][:80])
        grammar_diagnosis[bucket] = {
            "sampled": len(pool),
            "features": dict(feats),
            "example_spans": examples,
        }

    out = {
        "generated_from": "content-pass-1 outputs of " + baseline["generated_at"],
        "sample_seed": args.sample_seed,
        "reconciliation": recon,
        "treasury_sidebar_boilerplate_candidates": sidebar_count,
        "near_duplicate_docs_removed": len(dup_shas),
        "candidates_by_category": {
            cat: {
                "raw": by_category_raw[cat],
                "boilerplate_removed": by_category_clean[cat],
                "dedup_adjusted": by_category_dedup[cat],
            }
            for cat in sorted(by_category_raw)
        },
        "documents_with_any_candidate_clean": len(docs_with_cand),
        "ownership_bearing_documents_clean": len(ownership_docs),
        "ownership_bearing_documents_dedup": len(own_docs_dedup),
        "ownership_bearing_by_family": family_table,
        "candidates_by_family_clean": dict(by_family_clean.most_common()),
        "document_years_clean": {str(y): c for y, c in sorted(all_years.items())},
        "ownership_doc_years_clean": {str(y): c for y, c in sorted(own_years.items())},
        "documents_with_unparseable_or_junk_date": junk_years,
        "top_ownership_control_candidates": top_out,
        "span_verification": span_results,
        "pass2_grammar_miss_diagnosis": grammar_diagnosis,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")

    print(f"candidates: {cands_total} (baseline {baseline['candidates_total']})")
    print(f"treasury sidebar candidates removed: {sidebar_count}")
    print(f"ownership-bearing docs clean/dedup: {len(ownership_docs)}/{len(own_docs_dedup)}")
    print(f"span verification: {span_results}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
