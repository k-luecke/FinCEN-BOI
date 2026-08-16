"""Parts XVII–XIX — lawful recovery/priority acquisition queues.

- DOJ: the 4,317 Akamai bot-challenge captures are classified
  NON_CONTENT_TECHNICAL_RESPONSE (original retrieval observations are
  retained untouched in the manifest). Recovery = later ordinary public
  retrieval attempts plus official-feed alternatives. No bot-protection
  circumvention of any kind.
- Congress/GAO: citation mining over the 460M extracted characters for
  congress.gov/gao.gov/govinfo.gov URLs and GAO report numbers, focused
  on BOI/CTA/BSA/ownership topics; govinfo package URLs preferred over
  hostile HTML hosts.
- FinCEN: fincen.gov URLs cited inside archived documents but never
  captured (link-following was off for most crawls).

Usage: python3 -m content_pass_2.recovery_queues
"""
from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from urllib.parse import urlsplit

from content_pass_1.common import (
    OUT_ROOT, REPO_ROOT, log, read_jsonl, text_disk_path,
)

PASS2_VERSION = "content-pass-2/1.0.0"
ACQ_ROOT = os.path.join(REPO_ROOT, "acquisition")

URL_RE = re.compile(
    r"https?://(?:www\.)?(congress\.gov|gao\.gov|govinfo\.gov|fincen\.gov|"
    r"justice\.gov)(/[\w\-./%?=&#+]*)", re.I)
GAO_NUM_RE = re.compile(r"\bGAO[- ](\d{2})[- ](\d{2,4}[A-Z]{0,3})\b")
TOPIC_RE = re.compile(
    r"beneficial ownership|corporate transparency|BOI\b|BOSS\b|shell compan|"
    r"money launder|bank secrecy|\bBSA\b|\bSAR\b|\bAML\b|FinCEN|financial crimes|"
    r"corporate ownership|anonymous compan", re.I)


def classify_doj_challenges():
    """Tag the interstitial captures NON_CONTENT_TECHNICAL_RESPONSE and
    build the recovery queue (ordinary re-retrieval; no evasion)."""
    inv = {r["sha256"]: r for r in
           read_jsonl(os.path.join(OUT_ROOT, "corpus-inventory.jsonl"))}
    challenges = []
    for s in read_jsonl(os.path.join(OUT_ROOT, "extraction-status.jsonl")):
        if s.get("extraction_status") != "EMPTY":
            continue
        rec = inv.get(s["sha256"])
        if not rec or rec.get("host") != "www.justice.gov":
            continue
        disk = os.path.join(REPO_ROOT, rec["object_path"] or "")
        head = b""
        if os.path.isfile(disk):
            with open(disk, "rb") as fh:
                head = fh.read(2048)
        is_challenge = b"bm-verify" in head or b"interstitial" in head
        challenges.append({
            "sha256": s["sha256"],
            "url": rec.get("url"),
            "capture_classification": ("NON_CONTENT_TECHNICAL_RESPONSE"
                                       if is_challenge else "EMPTY_CONTENT"),
            "recovery_paths": [
                {"method": "ORDINARY_RETRY", "url": rec.get("url"),
                 "note": "later ordinary public retrieval attempt; "
                         "standard crawler, no evasion"},
                {"method": "OFFICIAL_FEED",
                 "url": "https://www.justice.gov/sitemap.xml",
                 "note": "sitemap-led rediscovery of moved/renamed pages"},
            ],
            "pass_version": PASS2_VERSION,
        })
    os.makedirs(ACQ_ROOT, exist_ok=True)
    path = os.path.join(ACQ_ROOT, "doj-recovery-queue.jsonl")
    with open(path, "w", encoding="utf-8") as fh:
        for r in challenges:
            fh.write(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n")
    n_chal = sum(1 for c in challenges
                 if c["capture_classification"] == "NON_CONTENT_TECHNICAL_RESPONSE")
    log(f"doj-recovery-queue: {len(challenges)} entries "
        f"({n_chal} confirmed challenge pages)")
    return challenges


def mine_citations():
    """Scan every extracted text for cross-host citations + GAO numbers."""
    inv = list(read_jsonl(os.path.join(OUT_ROOT, "corpus-inventory.jsonl")))
    known = set()
    for rec in read_jsonl(os.path.join(REPO_ROOT, "ledger.jsonl")):
        known.add((rec.get("url") or "").rstrip("/"))
    found = defaultdict(lambda: {"count": 0, "topical": 0, "sources": set()})
    gao_reports = defaultdict(lambda: {"count": 0, "topical": 0, "sources": set()})
    for rec in inv:
        tp = text_disk_path(rec["sha256"])
        if not os.path.isfile(tp):
            continue
        with open(tp, encoding="utf-8") as fh:
            text = fh.read()
        for m in URL_RE.finditer(text):
            host = m.group(1).lower()
            url = f"https://www.{host}{m.group(2)}"
            url = url.rstrip(".,;:)\"'").rstrip("/")
            if len(url) > 300 or url in known:
                continue
            ctx = text[max(0, m.start() - 200):m.end() + 200]
            e = found[url]
            e["count"] += 1
            e["topical"] += 1 if TOPIC_RE.search(ctx) else 0
            if len(e["sources"]) < 5:
                e["sources"].add(rec["sha256"])
        for m in GAO_NUM_RE.finditer(text):
            num = f"GAO-{m.group(1)}-{m.group(2)}"
            ctx = text[max(0, m.start() - 200):m.end() + 200]
            e = gao_reports[num]
            e["count"] += 1
            e["topical"] += 1 if TOPIC_RE.search(ctx) else 0
            if len(e["sources"]) < 5:
                e["sources"].add(rec["sha256"])
    return found, gao_reports


def emit_queues(found, gao_reports):
    now = datetime.now(timezone.utc).isoformat()
    qs = {"congress": [], "gao": [], "fincen": [], "govinfo": []}
    for url, e in found.items():
        host = urlsplit(url).hostname or ""
        row = {
            "url": url,
            "citation_count": e["count"],
            "topical_citations": e["topical"],
            "priority": round(e["topical"] * 3 + min(e["count"], 10), 2),
            "citing_sha256": sorted(e["sources"]),
            "discovery_source": "pass1-extracted-text-citation-mining",
            "generated_at": now,
            "pass_version": PASS2_VERSION,
        }
        if "congress.gov" in host:
            qs["congress"].append(row)
        elif "gao.gov" in host:
            qs["gao"].append(row)
        elif "fincen.gov" in host:
            qs["fincen"].append(row)
        elif "govinfo.gov" in host:
            qs["govinfo"].append(row)
    for num, e in gao_reports.items():
        qs["gao"].append({
            "url": f"https://www.gao.gov/products/{num}",
            "gao_report": num,
            "citation_count": e["count"],
            "topical_citations": e["topical"],
            "priority": round(e["topical"] * 3 + min(e["count"], 10) + 2, 2),
            "citing_sha256": sorted(e["sources"]),
            "discovery_source": "pass1-extracted-text-gao-number-mining",
            "generated_at": now,
            "pass_version": PASS2_VERSION,
        })
    names = {"congress": "congress-priority-queue.jsonl",
             "gao": "gao-priority-queue.jsonl",
             "fincen": "historical-fincen-queue.jsonl",
             "govinfo": "govinfo-priority-queue.jsonl"}
    for key, rows in qs.items():
        rows.sort(key=lambda r: -r["priority"])
        path = os.path.join(ACQ_ROOT, names[key])
        with open(path, "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n")
        log(f"{names[key]}: {len(rows)}")
    return qs


def emit_seeds(challenges, qs, retry_limit=4500):
    """One combined recovery seed file, host-diverse by construction."""
    lines = []
    n = 0
    for c in challenges:
        if c["capture_classification"] == "NON_CONTENT_TECHNICAL_RESPONSE" \
                and n < retry_limit:
            lines.append(f"{c['url']}|GOV-PUBLIC|DOJ recovery retry")
            n += 1
    caps = {"congress": 800, "gao": 1500, "fincen": 2500, "govinfo": 1500}
    prov = {"congress": "CONGRESS", "gao": "GOV-PUBLIC",
            "fincen": "GOV-PUBLIC", "govinfo": "GOV-PUBLIC"}
    label = {"congress": "Congress priority", "gao": "GAO priority",
             "fincen": "FinCEN historical", "govinfo": "GovInfo priority"}
    for key, rows in qs.items():
        for r in rows[:caps[key]]:
            lines.append(f"{r['url']}|{prov[key]}|{label[key]}")
    path = os.path.join(ACQ_ROOT, "seeds-recovery-batch1.txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    log(f"seeds-recovery-batch1.txt: {len(lines)} URLs")


def main():
    challenges = classify_doj_challenges()
    found, gao_reports = mine_citations()
    qs = emit_queues(found, gao_reports)
    emit_seeds(challenges, qs)


if __name__ == "__main__":
    main()
