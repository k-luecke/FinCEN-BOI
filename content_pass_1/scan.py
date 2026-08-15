"""Steps 3–6 & 9 — classification, candidate spans, ranking, boilerplate control.

Two phases:

  phase A (boilerplate): per-host line-frequency analysis over extracted
     HTML text. A normalized line seen in >10% of a host's documents
     (host must have >=20 docs) is boilerplate (nav/footer/legal chrome).
     Boilerplate hashes are stored under derived/reconnaissance/ and
     suppress candidate generation only — raw text is never altered.

  phase B (scan): per document — multi-label classification, high-recall
     candidate span generation with deterministic line/char locators
     against the raw extracted text, per-candidate ranking features and
     REVIEW_PRIORITY score (evidentiary review order, NOT truth
     probability).

Usage:
  python3 -m content_pass_1.scan boilerplate
  python3 -m content_pass_1.scan scan [--workers N]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from multiprocessing import Pool

from .common import (
    OUT_ROOT, PASS_VERSION, RECON_ROOT,
    log, read_jsonl, text_disk_path,
)
from .patterns import (
    AMOUNT, CANDIDATE_PATTERNS, CLASS_PATTERNS, DATE_NEARBY, DEFINITIONAL,
    ENTITY_SUFFIX, PCT, PERSON_NAME, STRUCTURAL_PATTERNS,
)

SCANNER_VERSION = "1.1.0"
BOILER_DIR = os.path.join(RECON_ROOT, "boilerplate")
CLASSES_PATH = os.path.join(OUT_ROOT, "document-classes.jsonl")
CANDIDATES_PATH = os.path.join(OUT_ROOT, "evidence-candidates.jsonl")

MAX_SPANS_PER_CAT_PER_DOC = 40
CONTEXT_CHARS = 300
MIN_BOILER_DOCS = 20
BOILER_FRACTION = 0.10

# module-global state for worker processes
_BOILER = {}
_INV = {}


def line_key(line: str) -> str:
    norm = re.sub(r"\s+", " ", line).strip().lower()
    if len(norm) < 20 or len(norm) > 400:
        return ""
    return hashlib.blake2b(norm.encode(), digest_size=8).hexdigest()


# ------------------------------------------------------------------ phase A
def build_boilerplate():
    inv = list(read_jsonl(os.path.join(OUT_ROOT, "corpus-inventory.jsonl")))
    by_host = defaultdict(list)
    for rec in inv:
        if rec.get("sniffed_mime") == "text/html":
            by_host[rec["host"]].append(rec["sha256"])
    os.makedirs(BOILER_DIR, exist_ok=True)
    for host, shas in sorted(by_host.items()):
        out = os.path.join(BOILER_DIR, host + ".json")
        if os.path.isfile(out):
            log(f"boilerplate: {host} already built")
            continue
        if len(shas) < MIN_BOILER_DOCS:
            with open(out, "w") as fh:
                json.dump({"host": host, "docs": len(shas), "hashes": []}, fh)
            continue
        counts = Counter()
        docs_seen = 0
        for sha in shas:
            tp = text_disk_path(sha)
            if not os.path.isfile(tp):
                continue
            docs_seen += 1
            seen = set()
            with open(tp, encoding="utf-8") as fh:
                for line in fh:
                    k = line_key(line)
                    if k and k not in seen:
                        seen.add(k)
                        counts[k] += 1
        thresh = max(5, int(docs_seen * BOILER_FRACTION))
        hashes = [k for k, c in counts.items() if c >= thresh]
        with open(out, "w") as fh:
            json.dump({"host": host, "docs": docs_seen, "threshold": thresh,
                       "hashes": hashes}, fh)
        log(f"boilerplate: {host}: {len(hashes)} boilerplate lines "
            f"(docs={docs_seen}, threshold={thresh})")


# ------------------------------------------------------------------ phase B
def _load_boiler(host: str):
    if host not in _BOILER:
        path = os.path.join(BOILER_DIR, host + ".json")
        hashes = set()
        if os.path.isfile(path):
            with open(path) as fh:
                hashes = set(json.load(fh).get("hashes", []))
        _BOILER[host] = hashes
    return _BOILER[host]


DATE_URL = re.compile(r"/(20[0-2]\d|19\d\d)[/-](\d{1,2})\b")
DATE_TEXT = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|October|"
    r"November|December)\s+(\d{1,2}),?\s+((?:19|20)\d{2})\b")


def guess_date(url: str, text_head: str):
    m = DATE_TEXT.search(text_head)
    if m:
        months = ["January", "February", "March", "April", "May", "June", "July",
                  "August", "September", "October", "November", "December"]
        return f"{m.group(3)}-{months.index(m.group(1)) + 1:02d}-{int(m.group(2)):02d}"
    m = DATE_URL.search(url or "")
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}"
    m = re.search(r"\b((?:19|20)\d{2})\b", text_head)
    if m:
        return m.group(1)
    return None


PROV_WEIGHT = {"CONGRESS": 3, "COURT": 3, "FOIA": 2, "GOV-PUBLIC": 2}
FAMILY_WEIGHT = {"DOJ": 2, "SEC": 2, "CONGRESS_OVERSIGHT": 2, "CONGRESS_JUDICIARY": 2,
                 "CONGRESS_GOV": 2, "GAO": 2, "FBI_VAULT": 2, "GOVINFO": 1,
                 "FINCEN": 1, "TREASURY_OIG": 1}
CAT_WEIGHT = {"OWNERSHIP_EXPLICIT": 5, "PARENT_SUBSIDIARY": 4, "CONTROL_EXPLICIT": 4,
              "SHELL_NOMINEE": 4, "FINANCIAL_FLOW": 3, "BOI_CTA": 3, "SAR_BSA": 3,
              "FORMATION_DISSOLUTION": 2, "ROLE_TITLE": 2, "STRUCTURED": 5}
URL_HINT = re.compile(r"press-release|enforcement|complaint|indictment|plea|"
                      r"sentenc|consent-order|cease|charged|convicted|guilty|opa/pr", re.I)


def rank_candidate(cat_list, para, rec, matched_text):
    feats = {}
    score = 0.0
    prov = rec.get("provenance") or ""
    score += PROV_WEIGHT.get(prov, 0)
    feats["provenance_weight"] = PROV_WEIGHT.get(prov, 0)
    fw = FAMILY_WEIGHT.get(rec.get("source_family") or "", 0)
    score += fw
    feats["family_weight"] = fw
    if URL_HINT.search(rec.get("url") or ""):
        score += 2
        feats["url_enforcement_hint"] = 2
    cw = max(CAT_WEIGHT.get(c, 1) for c in cat_list)
    score += cw
    feats["category_weight"] = cw
    if PCT.search(para):
        score += 3
        feats["has_percentage"] = 3
    if AMOUNT.search(para):
        score += 2
        feats["has_amount"] = 2
    if PERSON_NAME.search(para) and ENTITY_SUFFIX.search(para):
        score += 3
        feats["person_and_entity"] = 3
    if DATE_NEARBY.search(para):
        score += 1
        feats["has_date"] = 1
    if DEFINITIONAL.search(matched_text) or DEFINITIONAL.search(para[:200]):
        score -= 2
        feats["definitional"] = -2
    if len(matched_text) < 40 and not ENTITY_SUFFIX.search(para):
        score -= 1
        feats["short_generic"] = -1
    return score, feats


def scan_doc(rec):
    sha = rec["sha256"]
    tp = text_disk_path(sha)
    if not os.path.isfile(tp):
        return None
    with open(tp, encoding="utf-8") as fh:
        text = fh.read()
    if not text.strip():
        return None
    boiler = _load_boiler(rec.get("host") or "")

    lines = text.split("\n")
    offsets = []
    pos = 0
    for ln in lines:
        offsets.append(pos)
        pos += len(ln) + 1
    is_boiler = [bool(line_key(ln)) and line_key(ln) in boiler for ln in lines]
    # page number per line for PDFs (\f markers survive extraction)
    page_of = None
    if "\f" in text:
        page_of = []
        pg = 1
        for ln in lines:
            page_of.append(pg)
            pg += ln.count("\f")

    searchable = "\n".join(ln for ln, b in zip(lines, is_boiler) if not b)

    classes = sorted(name for name, pat in CLASS_PATTERNS.items()
                     if pat.search(searchable))
    head = text[:3000]
    doc_date = guess_date(rec.get("url"), head)
    title = None  # filled by caller from extraction status if available

    candidates = []
    overflow = Counter()
    cand_seq = 0

    def emit(cat, pname, m, li):
        nonlocal cand_seq
        line = lines[li]
        start = offsets[li] + m.start()
        end = offsets[li] + m.end()
        cb = text[max(0, start - CONTEXT_CHARS):start]
        ca = text[end:end + CONTEXT_CHARS]
        para = cb + line[m.start():m.end()] + ca
        cats = [cat]
        score, feats = rank_candidate(cats, para, rec, m.group(0))
        cand_seq += 1
        candidates.append({
            "candidate_id": f"{sha[:16]}-{cand_seq:04d}",
            "source_sha256": sha,
            "source_url": rec.get("url"),
            "host": rec.get("host"),
            "provenance": rec.get("provenance"),
            "source_family": rec.get("source_family"),
            "document_class": classes,
            "document_date": doc_date,
            "page_number": page_of[li] if page_of else None,
            "line_start": li + 1,
            "line_end": li + 1,
            "character_start": start,
            "character_end": end,
            "matched_terms": [pname],
            "matched_text": m.group(0)[:500],
            "matched_groups": list(m.groups())[:6] if m.groups() else None,
            "context_before": cb[-CONTEXT_CHARS:],
            "context_after": ca[:CONTEXT_CHARS],
            "candidate_category": cats,
            "review_priority": round(score, 2),
            "ranking_features": feats,
            "pass_version": PASS_VERSION,
            "scanner_version": SCANNER_VERSION,
        })

    for cat, pats in CANDIDATE_PATTERNS.items():
        n_before = len(candidates)
        for li, (line, b) in enumerate(zip(lines, is_boiler)):
            if b or not line.strip():
                continue
            for pname, pat in pats:
                for m in pat.finditer(line):
                    if len(candidates) - n_before >= MAX_SPANS_PER_CAT_PER_DOC:
                        overflow[cat] += 1
                    else:
                        emit(cat, pname, m, li)
    n_before = len(candidates)
    for pname, pat in STRUCTURAL_PATTERNS:
        for li, (line, b) in enumerate(zip(lines, is_boiler)):
            if b:
                continue
            for m in pat.finditer(line):
                if len(candidates) - n_before >= MAX_SPANS_PER_CAT_PER_DOC:
                    overflow["STRUCTURED"] += 1
                else:
                    emit("STRUCTURED", pname, m, li)

    doc_record = {
        "sha256": sha,
        "source_url": rec.get("url"),
        "host": rec.get("host"),
        "provenance": rec.get("provenance"),
        "source_family": rec.get("source_family"),
        "document_class": classes if classes else ["UNCLASSIFIED"],
        "document_date": doc_date,
        "candidate_count": len(candidates),
        "candidate_overflow": dict(overflow) or None,
        "candidate_categories": sorted({c for cd in candidates
                                        for c in cd["candidate_category"]}),
        "doc_review_priority": round(
            sum(sorted((c["review_priority"] for c in candidates), reverse=True)[:10]), 2),
        "searchable_chars": len(searchable),
        "boilerplate_lines_suppressed": sum(is_boiler),
        "pass_version": PASS_VERSION,
        "scanner_version": SCANNER_VERSION,
    }
    return doc_record, candidates


def _worker(rec):
    try:
        return scan_doc(rec)
    except Exception as exc:
        return {"sha256": rec["sha256"], "scan_error": f"{type(exc).__name__}: {exc}"[:300]}


def run_scan(workers=4):
    done = set()
    if os.path.isfile(CLASSES_PATH):
        for rec in read_jsonl(CLASSES_PATH):
            done.add(rec["sha256"])
    todo = []
    for rec in read_jsonl(os.path.join(OUT_ROOT, "corpus-inventory.jsonl")):
        if rec["sha256"] in done:
            continue
        todo.append({k: rec.get(k) for k in
                     ("sha256", "host", "url", "provenance", "source_family")})
    log(f"scan: {len(todo)} documents to scan ({len(done)} done)")

    CHUNK = 500
    with Pool(workers) as pool, \
            open(CLASSES_PATH, "a", encoding="utf-8") as cls_out, \
            open(CANDIDATES_PATH, "a", encoding="utf-8") as cand_out:
        for i in range(0, len(todo), CHUNK):
            chunk = todo[i:i + CHUNK]
            for result in pool.imap_unordered(_worker, chunk, chunksize=25):
                if result is None:
                    continue
                if isinstance(result, dict) and "scan_error" in result:
                    cls_out.write(json.dumps(
                        {"sha256": result["sha256"],
                         "document_class": ["UNCLASSIFIED"],
                         "scan_error": result["scan_error"],
                         "pass_version": PASS_VERSION}, sort_keys=True) + "\n")
                    continue
                doc, cands = result
                cls_out.write(json.dumps(doc, sort_keys=True, ensure_ascii=False) + "\n")
                for c in cands:
                    cand_out.write(json.dumps(c, sort_keys=True, ensure_ascii=False) + "\n")
            cls_out.flush()
            cand_out.flush()
            log(f"scan: checkpoint {min(i + CHUNK, len(todo))}/{len(todo)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["boilerplate", "scan"])
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    if args.mode == "boilerplate":
        build_boilerplate()
    else:
        run_scan(args.workers)


if __name__ == "__main__":
    main()
