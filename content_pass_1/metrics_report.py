"""Step 13 — pass metrics, and Step 12 — TOP-CANDIDATES.md generation.

Usage:
  python3 -m content_pass_1.metrics_report metrics
  python3 -m content_pass_1.metrics_report top
"""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone

from .common import OUT_ROOT, PASS_VERSION, log, read_jsonl

BUCKET_FILES = [
    ("ownership-candidates.jsonl", "TOP 50 EXPLICIT OWNERSHIP DOCUMENTS"),
    ("control-candidates.jsonl", "TOP 50 CONTROL DOCUMENTS"),
    ("parent-subsidiary-candidates.jsonl", "TOP 50 PARENT/SUBSIDIARY DOCUMENTS"),
    ("shell-structure-candidates.jsonl", "TOP 50 SHELL-STRUCTURE DOCUMENTS"),
    ("financial-flow-candidates.jsonl", "TOP 50 FINANCIAL-FLOW DOCUMENTS"),
    ("boi-cta-candidates.jsonl", "TOP 50 BOI/CTA/BOSS DOCUMENTS"),
    ("sar-bsa-candidates.jsonl", "TOP 50 SAR/BSA DOCUMENTS"),
    ("congressional-candidates.jsonl", "TOP 50 CONGRESSIONAL EVIDENCE DOCUMENTS"),
]


def build_metrics():
    inv = list(read_jsonl(os.path.join(OUT_ROOT, "corpus-inventory.jsonl")))
    status = list(read_jsonl(os.path.join(OUT_ROOT, "extraction-status.jsonl")))
    classes = list(read_jsonl(os.path.join(OUT_ROOT, "document-classes.jsonl")))

    st_by = Counter(s["extraction_status"] for s in status)
    mime = Counter(r["sniffed_mime"] or "absent" for r in inv)
    pdf_stat = Counter(s["extraction_status"] for s in status
                       if s.get("sniffed_mime") == "application/pdf")

    class_counter = Counter()
    cat_docs = defaultdict(set)
    class_by_family = defaultdict(Counter)
    year_counter = Counter()
    doc_host = Counter()
    doc_prov = Counter()
    cand_count_total = 0
    for rec in classes:
        for cl in rec.get("document_class") or []:
            class_counter[cl] += 1
            class_by_family[rec.get("source_family") or "?"][cl] += 1
        for cat in rec.get("candidate_categories") or []:
            cat_docs[cat].add(rec["sha256"])
        cand_count_total += rec.get("candidate_count") or 0
        d = rec.get("document_date") or ""
        if len(d) >= 4 and d[:4].isdigit():
            year_counter[d[:4]] += 1
        if rec.get("candidate_count"):
            doc_host[rec.get("host") or "?"] += 1
            doc_prov[rec.get("provenance") or "?"] += 1

    cand_by_cat = Counter()
    cand_by_host = Counter()
    cand_by_family = Counter()
    for c in read_jsonl(os.path.join(OUT_ROOT, "evidence-candidates.jsonl")):
        for cat in c["candidate_category"]:
            cand_by_cat[cat] += 1
        cand_by_host[c.get("host") or "?"] += 1
        cand_by_family[c.get("source_family") or "?"] += 1

    ndg = list(read_jsonl(os.path.join(OUT_ROOT, "near-duplicate-groups.jsonl")))

    metrics = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pass_version": PASS_VERSION,
        "total_durable_objects": len(inv),
        "objects_examined": len(status),
        "objects_text_extracted": st_by.get("OK", 0) + st_by.get("EMPTY", 0),
        "objects_no_extractable_text": st_by.get("NO_TEXT", 0) + st_by.get("EMPTY", 0),
        "extraction_status_counts": dict(st_by),
        "pdf_count": mime.get("application/pdf", 0),
        "pdf_native_text": pdf_stat.get("OK", 0),
        "pdf_ocr_required": pdf_stat.get("NO_TEXT", 0),
        "pdf_errors": pdf_stat.get("ERROR", 0),
        "html_count": mime.get("text/html", 0),
        "xml_count": mime.get("application/xml", 0),
        "json_count": mime.get("application/json", 0),
        "archives_bulk_datasets": mime.get("application/zip", 0),
        "extraction_failures": st_by.get("ERROR", 0),
        "total_extracted_chars": sum(s.get("character_count") or 0 for s in status),
        "documents_scanned": len(classes),
        "documents_with_any_candidates": sum(
            1 for r in classes if r.get("candidate_count")),
        "candidates_total": cand_count_total,
        "documents_ownership_bearing": len(
            cat_docs.get("OWNERSHIP_EXPLICIT", set())
            | cat_docs.get("CONTROL_EXPLICIT", set())
            | cat_docs.get("PARENT_SUBSIDIARY", set())
            | cat_docs.get("STRUCTURED", set())),
        "documents_by_candidate_category": {
            k: len(v) for k, v in sorted(cat_docs.items())},
        "documents_by_class": dict(class_counter.most_common()),
        "documents_with_candidates_by_host": dict(doc_host.most_common()),
        "documents_with_candidates_by_provenance": dict(doc_prov),
        "documents_by_year_guess": dict(sorted(year_counter.items())),
        "candidates_by_category": dict(cand_by_cat.most_common()),
        "candidates_by_host": dict(cand_by_host.most_common()),
        "candidates_by_source_family": dict(cand_by_family.most_common()),
        "documents_by_class_and_family": {
            fam: dict(cnt.most_common(12)) for fam, cnt in
            sorted(class_by_family.items())},
        "near_duplicate_groups": len(ndg),
        "near_duplicate_documents": sum(g["member_count"] for g in ndg),
    }
    path = os.path.join(OUT_ROOT, "metrics.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2, sort_keys=True)
        fh.write("\n")
    log(f"metrics written to {path}")


def _title_index():
    titles = {}
    for s in read_jsonl(os.path.join(OUT_ROOT, "extraction-status.jsonl")):
        if s.get("title"):
            titles[s["sha256"]] = s["title"]
    return titles


def build_top(per_section=50):
    titles = _title_index()
    lines = [
        "# TOP-CANDIDATES — Content Pass 1 reconnaissance index",
        "",
        f"Generated {datetime.now(timezone.utc).isoformat()} · {PASS_VERSION}",
        "",
        "Ranked by REVIEW_PRIORITY — an *evidentiary review order*, not a",
        "truth probability. Every excerpt is the literal archived text; no",
        "claim is made beyond its literal content. One entry per document",
        "per section (its best-ranked candidate span).",
        "",
    ]
    for fname, heading in BUCKET_FILES:
        path = os.path.join(OUT_ROOT, fname)
        if not os.path.isfile(path):
            continue
        best = {}
        for c in read_jsonl(path):
            sha = c["source_sha256"]
            if sha not in best or c["review_priority"] > best[sha]["review_priority"]:
                best[sha] = c
        top = sorted(best.values(), key=lambda c: -c["review_priority"])[:per_section]
        lines += [f"## {heading}", ""]
        if not top:
            lines += ["_No candidates in this bucket._", ""]
            continue
        for i, c in enumerate(top, 1):
            sha = c["source_sha256"]
            title = titles.get(sha) or (c.get("source_url") or "")[:100]
            loc = f"line {c['line_start']}, chars {c['character_start']}-{c['character_end']}"
            if c.get("page_number"):
                loc = f"page {c['page_number']}, " + loc
            excerpt = (c["context_before"][-120:] + "**" + c["matched_text"][:200]
                       + "**" + c["context_after"][:120])
            excerpt = " ".join(excerpt.split())
            reasons = ", ".join(f"{k}={v}" for k, v in
                                sorted(c["ranking_features"].items()))
            lines += [
                f"### {i}. {title}",
                "",
                f"- **Source:** {c.get('source_family')} ({c.get('host')}) · "
                f"provenance {c.get('provenance')} · date {c.get('document_date') or 'unknown'}",
                f"- **URL:** {c.get('source_url')}",
                f"- **SHA-256:** `{sha}`",
                f"- **Locator:** {loc} of extracted text "
                f"(`derived/text/{sha[:2]}/{sha[2:]}.txt`)",
                f"- **Priority {c['review_priority']}** — features: {reasons}",
                f"- **Excerpt:** …{excerpt}…",
                "",
            ]
    path = os.path.join(OUT_ROOT, "TOP-CANDIDATES.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    log(f"TOP-CANDIDATES.md written ({len(lines)} lines)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["metrics", "top"])
    args = ap.parse_args()
    if args.mode == "metrics":
        build_metrics()
    else:
        build_top()


if __name__ == "__main__":
    main()
