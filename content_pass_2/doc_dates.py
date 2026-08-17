"""Document-date extraction for observation-bearing sources.

For every distinct source document referenced by raw observations,
extract a single document date from the archived text (and, failing
that, the URL), deterministically and with the extraction basis
recorded. Priority order, most specific first:

  1. edgar-filed        EDGAR SGML header "FILED AS OF DATE: YYYYMMDD"
  2. edgar-event-date   13D/G "(Date of Event Which Requires Filing…)"
  3. document-dateline  first "Month D, YYYY" in the head of the text
  4. document-dateline-numeric  first ISO / M/D/Y date in the head
  5. url                a YYYY-MM-DD (or YYYY/MM/DD) inside the URL

Writes content-pass-2/document-dates.jsonl:
  {"sha256": …, "document_date": "YYYY-MM-DD", "basis": …}

A document date is the date OF the source, never the date a stated
relationship began; the graph keeps the two distinct (source_date vs
valid_from).

Usage: python3 -m content_pass_2.doc_dates
"""
from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from content_pass_1.common import text_disk_path  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OBS = os.path.join(REPO, "content-pass-2", "raw-observations.jsonl")
OUT = os.path.join(REPO, "content-pass-2", "document-dates.jsonl")

MONTHS = {m: i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"])}
_MON = "|".join(MONTHS)

EDGAR_FILED_RE = re.compile(r"FILED AS OF DATE:\s*((?:19|20)\d{6})")
EVENT_DATE_RE = re.compile(
    rf"({_MON})\s+(\d{{1,2}}),?\s+((?:19|20)\d{{2}})\s*\n?\s*"
    r"\(\s*Date\s+of\s+Event")
DATELINE_RE = re.compile(rf"({_MON})\s+(\d{{1,2}}),?\s+((?:19|20)\d{{2}})")
ISO_RE = re.compile(r"\b((?:19|20)\d{2})-(\d{2})-(\d{2})\b")
MDY_RE = re.compile(r"\b(\d{1,2})/(\d{1,2})/((?:19|20)\d{2})\b")
URL_RE = re.compile(r"((?:19|20)\d{2})[-/](\d{1,2})[-/](\d{1,2})")


def _iso(y, mo, d):
    y, mo, d = int(y), int(mo), int(d)
    if not (1930 <= y <= 2026 and 1 <= mo <= 12 and 1 <= d <= 31):
        return None
    return f"{y:04d}-{mo:02d}-{d:02d}"


def extract(sha: str, url: str):
    """(iso_date, basis) or (None, None)."""
    try:
        with open(text_disk_path(sha), encoding="utf-8") as fh:
            head = fh.read(4000)
    except OSError:
        head = ""

    m = EDGAR_FILED_RE.search(head)
    if m:
        s = m.group(1)
        d = _iso(s[:4], s[4:6], s[6:8])
        if d:
            return d, "edgar-filed"
    m = EVENT_DATE_RE.search(head)
    if m:
        d = _iso(m.group(3), MONTHS[m.group(1)], m.group(2))
        if d:
            return d, "edgar-event-date"
    m = DATELINE_RE.search(head[:1500])
    if m:
        d = _iso(m.group(3), MONTHS[m.group(1)], m.group(2))
        if d:
            return d, "document-dateline"
    m = ISO_RE.search(head[:1500])
    if m:
        d = _iso(m.group(1), m.group(2), m.group(3))
        if d:
            return d, "document-dateline-numeric"
    m = MDY_RE.search(head[:1500])
    if m:
        d = _iso(m.group(3), m.group(1), m.group(2))
        if d:
            return d, "document-dateline-numeric"
    m = URL_RE.search(url or "")
    if m:
        d = _iso(m.group(1), m.group(2), m.group(3))
        if d:
            return d, "url"
    return None, None


def main():
    shas = {}
    with open(OBS, encoding="utf-8") as fh:
        for line in fh:
            o = json.loads(line)
            if o.get("source_sha256"):
                shas.setdefault(o["source_sha256"], o.get("source_url") or "")

    rows, hits = [], 0
    for sha in sorted(shas):
        date, basis = extract(sha, shas[sha])
        if date:
            hits += 1
        rows.append({"sha256": sha, "document_date": date, "basis": basis})

    with open(OUT, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True) + "\n")
    print(f"doc_dates: {hits}/{len(rows)} documents dated -> {OUT}")


if __name__ == "__main__":
    main()
