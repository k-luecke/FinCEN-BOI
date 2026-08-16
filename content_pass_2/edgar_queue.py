"""Part X/XI — evidence-guided EDGAR acquisition queue.

Uses the *archived* EDGAR submissions.zip snapshot (sha256 ec07d8ce…,
986,468 per-CIK filing histories) as an acquisition map. No network.

1. Harvest entity names from Pass 1 candidate spans (ownership, control,
   parent/subsidiary, shell, financial-flow, congressional buckets and
   STRUCTURED captures).
2. Match them (normalized-exact, prioritization only — never entity
   resolution) against registrant names/former names in the snapshot.
3. For matched CIKs, queue priority-form filings: SC 13D(/A), SC 13G(/A),
   Forms 3/4/5, Form D, and 10-K family (EX-21 subsidiary exhibits ride
   inside; the filing index is queued for second-round exhibit fetch).

Output: acquisition/edgar-priority-queue.jsonl + seed file.

Usage: python3 -m content_pass_2.edgar_queue [--workers 4]
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from multiprocessing import Pool

from content_pass_1.common import REPO_ROOT, log, object_disk_path, read_jsonl

PASS2_VERSION = "content-pass-2/1.0.0"
SUBMISSIONS_SHA = "ec07d8cefcbdcd638dac3f7c5d91b6a71759d08190c62d44485851bba5058746"
ACQ_ROOT = os.path.join(REPO_ROOT, "acquisition")
OUT_QUEUE = os.path.join(ACQ_ROOT, "edgar-priority-queue.jsonl")

BUCKETS = {
    "ownership-candidates.jsonl": 5,
    "control-candidates.jsonl": 4,
    "parent-subsidiary-candidates.jsonl": 3,
    "shell-structure-candidates.jsonl": 4,
    "financial-flow-candidates.jsonl": 2,
    "congressional-candidates.jsonl": 3,
}

ENTITY_RE = re.compile(
    r"\b([A-Z][A-Za-z0-9&.,'’\- ]{2,60}?[ .,]"
    r"(?:LLC|L\.L\.C\.|Inc\.?|Corp\.?|Corporation|Company|Co\.|Ltd\.?|"
    r"LP|L\.P\.|LLP|PLLC|Holdings?|Group|Trust|Bank|N\.A\.|Partners(?:hip)?))"
    r"(?=[\s.,;:)\"']|$)")

FORM_PRIORITY = {
    "SC 13D": 10, "SC 13D/A": 9, "SC 13G": 8, "SC 13G/A": 7,
    "10-K": 8, "10-K/A": 7, "10-K405": 7, "20-F": 6,  # EX-21 carriers
    "3": 5, "4": 5, "5": 4, "D": 5, "D/A": 4,
    "8-K": 3,  # M&A/control events; bounded below
}
NAME_JSON_RE = re.compile(rb'"name":"([^"]{1,120})"')
FORMER_RE = re.compile(rb'"formerNames":\[(.*?)\]', re.S)
FORMER_NAME_RE = re.compile(rb'"name":"([^"]{1,120})"')


def norm_name(name: str) -> str:
    s = name.upper()
    s = s.replace("&AMP;", "&")
    s = re.sub(r"[.,'’\"]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s+(LLC|L L C|INC|CORP|CORPORATION|COMPANY|CO|LTD|LP|LLP|"
               r"PLLC|HOLDINGS?|GROUP|TRUST|NA|PARTNERS(?:HIP)?)$", r" \1", s)
    return s


def harvest_names():
    """Entity names from Pass 1 candidate spans, with bucket-weighted relevance."""
    names = defaultdict(lambda: {"score": 0.0, "buckets": set(), "example_sha": None})
    cp1 = os.path.join(REPO_ROOT, "content-pass-1")
    for fname, weight in BUCKETS.items():
        path = os.path.join(cp1, fname)
        src = None
        if os.path.isfile(path):
            src = open(path, "r", encoding="utf-8")
        elif os.path.isfile(path + ".gz"):
            src = gzip.open(path + ".gz", "rt", encoding="utf-8")
        if src is None:
            continue
        with src:
            for line in src:
                c = json.loads(line)
                texts = [c.get("matched_text") or ""]
                for g in c.get("matched_groups") or []:
                    if g:
                        texts.append(g)
                texts.append((c.get("context_before") or "")[-150:])
                texts.append((c.get("context_after") or "")[:150])
                seen_here = set()
                for t in texts:
                    for m in ENTITY_RE.finditer(t):
                        n = norm_name(m.group(1))
                        if len(n) < 6 or n in seen_here:
                            continue
                        seen_here.add(n)
                        rec = names[n]
                        rec["score"] += weight * (1 + c.get("review_priority", 0) / 20.0)
                        rec["buckets"].add(fname.split("-candidates")[0])
                        if rec["example_sha"] is None:
                            rec["example_sha"] = c["source_sha256"]
    # Drop hyper-generic names that would match half of EDGAR.
    GENERIC = {"THE COMPANY", "THE BANK", "THE TRUST", "NATIONAL BANK",
               "HOLDING COMPANY", "THE CORPORATION", "STATE BANK"}
    for g in GENERIC:
        names.pop(g, None)
    return dict(names)


def _scan_chunk(args):
    members, name_keys = args
    zpath = object_disk_path(SUBMISSIONS_SHA)
    hits = []
    with zipfile.ZipFile(zpath) as zf:
        for member in members:
            try:
                raw = zf.read(member)
            except Exception:
                continue
            m = NAME_JSON_RE.search(raw[:4096])
            cand = []
            if m:
                cand.append(m.group(1).decode("utf-8", "replace"))
            fm = FORMER_RE.search(raw[:8192])
            if fm:
                for f in FORMER_NAME_RE.finditer(fm.group(1)):
                    cand.append(f.group(1).decode("utf-8", "replace"))
            matched = None
            for c in cand:
                n = norm_name(c)
                if n in name_keys:
                    matched = n
                    break
            if matched:
                hits.append((member, matched))
    return hits


def scan_snapshot(names, workers):
    zpath = object_disk_path(SUBMISSIONS_SHA)
    with zipfile.ZipFile(zpath) as zf:
        members = [n for n in zf.namelist()
                   if n.startswith("CIK") and n.endswith(".json")
                   and "-submissions-" not in n]
    log(f"edgar_queue: scanning {len(members)} primary CIK files "
        f"for {len(names)} harvested names")
    name_keys = frozenset(names.keys())
    CH = 8000
    chunks = [(members[i:i + CH], name_keys) for i in range(0, len(members), CH)]
    hits = []
    with Pool(workers) as pool:
        for i, part in enumerate(pool.imap_unordered(_scan_chunk, chunks)):
            hits.extend(part)
            if (i + 1) % 15 == 0:
                log(f"edgar_queue: {i + 1}/{len(chunks)} chunks, {len(hits)} matches")
    return hits


def build_queue(names, hits, max_8k=3):
    zpath = object_disk_path(SUBMISSIONS_SHA)
    already = set()
    for rec in read_jsonl(os.path.join(REPO_ROOT, "ledger.jsonl")):
        already.add(rec.get("url"))
    rows = []
    with zipfile.ZipFile(zpath) as zf:
        for member, matched_name in hits:
            data = json.loads(zf.read(member))
            cik = int(data.get("cik") or member[3:13])
            recent = (data.get("filings") or {}).get("recent") or {}
            forms = recent.get("form") or []
            accs = recent.get("accessionNumber") or []
            dates = recent.get("filingDate") or []
            docs = recent.get("primaryDocument") or []
            rel = names[matched_name]
            n8k = 0
            for i, form in enumerate(forms):
                fp = FORM_PRIORITY.get(form)
                if fp is None:
                    continue
                if form == "8-K":
                    n8k += 1
                    if n8k > max_8k:
                        continue
                acc = accs[i]
                acc_nodash = acc.replace("-", "")
                doc = docs[i] if i < len(docs) else ""
                base = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_nodash}"
                url = f"{base}/{doc}" if doc else f"{base}/{acc}.txt"
                is_ex21_carrier = form.startswith(("10-K", "20-F"))
                rows.append({
                    "cik": cik,
                    "registrant_name": data.get("name"),
                    "matched_candidate_name": matched_name,
                    "accession": acc,
                    "form": form,
                    "filing_date": dates[i] if i < len(dates) else None,
                    "document_url": url,
                    "index_url": f"{base}/index.json" if is_ex21_carrier else None,
                    "priority": round(fp * (1 + min(rel["score"], 50) / 25.0), 2),
                    "reason": ("EX-21 subsidiary-exhibit carrier" if is_ex21_carrier
                               else f"priority form {form}")
                              + f"; name matched Pass 1 buckets: "
                              + ",".join(sorted(rel["buckets"])),
                    "already_archived": url in already,
                    "graph_relevance": {"buckets": sorted(rel["buckets"]),
                                        "score": round(rel["score"], 2),
                                        "example_candidate_sha256": rel["example_sha"]},
                    "discovery_source": f"edgar-submissions-snapshot:{SUBMISSIONS_SHA[:16]}",
                    "pass_version": PASS2_VERSION,
                })
    rows.sort(key=lambda r: (-r["priority"], r["filing_date"] or ""), reverse=False)
    os.makedirs(ACQ_ROOT, exist_ok=True)
    with open(OUT_QUEUE, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n")
    log(f"edgar_queue: {len(rows)} filings queued from {len(hits)} matched CIKs")
    return rows


def emit_seeds(rows, limit=8000):
    """Seed-file batch for the crawler: top-priority unarchived documents,
    plus index.json for EX-21 carriers (second-round exhibit discovery)."""
    seen = set()
    lines = []
    for r in rows:
        if r["already_archived"]:
            continue
        for url in ([r["document_url"]] +
                    ([r["index_url"]] if r["index_url"] else [])):
            if url and url not in seen:
                seen.add(url)
                lines.append(f"{url}|GOV-PUBLIC|SEC EDGAR targeted ({r['form']})")
            if len(lines) >= limit:
                break
        if len(lines) >= limit:
            break
    path = os.path.join(ACQ_ROOT, "seeds-edgar-batch1.txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    log(f"edgar_queue: {len(lines)} seed URLs -> {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--seed-limit", type=int, default=8000)
    args = ap.parse_args()
    names = harvest_names()
    log(f"edgar_queue: harvested {len(names)} candidate entity names")
    hits = scan_snapshot(names, args.workers)
    rows = build_queue(names, hits)
    emit_seeds(rows, args.seed_limit)
    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "harvested_names": len(names),
        "matched_ciks": len(hits),
        "queued_filings": len(rows),
        "snapshot_sha256": SUBMISSIONS_SHA,
        "pass_version": PASS2_VERSION,
    }
    with open(os.path.join(ACQ_ROOT, "edgar-queue-meta.json"), "w") as fh:
        json.dump(meta, fh, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
