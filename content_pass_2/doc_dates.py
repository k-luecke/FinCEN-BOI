"""Document-date extraction for observation-bearing sources.

Distinguishes two document-level dates (retrieved_at is already carried
on every edge separately):

  publication_date  when the document was published / filed
  event_date        the date the document says its content applies to
                    (13D/G "Date of Event", EDGAR report period)

For SEC EDGAR documents the authoritative source is the archived
submissions.zip bulk snapshot (per-CIK filing metadata joined by
accession number) — deterministic, no text parsing. Text extraction is
the fallback for everything else, most specific first, and a document
whose head carries no extractable date stays undated rather than
borrowing a date from body text.

Bases:
  edgar-metadata               filingDate from submissions.zip
  edgar-metadata-report-period reportDate from submissions.zip
  edgar-filed                  SGML header "FILED AS OF DATE"
  edgar-event-block            13D/G "(Date of Event Which Requires…)"
  document-dateline            first "Month D, YYYY" in the text head
  document-dateline-numeric    first ISO / M/D/Y date in the text head
  url                          a date inside the URL

Writes content-pass-2/document-dates.jsonl:
  {"sha256":…, "publication_date":…, "publication_basis":…,
   "event_date":…, "event_basis":…, "form":…}

Usage:
  python3 -m content_pass_2.doc_dates [--edgar-zip PATH]
  (or set EDGAR_SUBMISSIONS_ZIP; without it the EDGAR join is skipped
  and text fallbacks apply.)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from content_pass_1.common import text_disk_path  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OBS = os.path.join(REPO, "content-pass-2", "raw-observations.jsonl")
OUT = os.path.join(REPO, "content-pass-2", "document-dates.jsonl")

MONTHS = {m: i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"])}
_MON = "|".join(MONTHS)

EDGAR_URL_RE = re.compile(
    r"sec\.gov/Archives/edgar/data/(\d+)/(\d{18})/")
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


class EdgarMeta:
    """Accession -> (filingDate, reportDate, form) via submissions.zip."""

    def __init__(self, zip_path):
        self.zf = zipfile.ZipFile(zip_path) if zip_path else None
        self.names = set(self.zf.namelist()) if self.zf else set()
        self.cache = {}

    def _index(self, member, acc_map):
        data = json.loads(self.zf.read(member))
        recent = data.get("filings", {}).get("recent", data)
        accs = recent.get("accessionNumber") or []
        for i, acc in enumerate(accs):
            acc_map[acc] = (
                (recent.get("filingDate") or [None] * len(accs))[i],
                (recent.get("reportDate") or [None] * len(accs))[i],
                (recent.get("form") or [None] * len(accs))[i])
        return data

    def lookup(self, cik, accession):
        if not self.zf:
            return None
        if cik not in self.cache:
            acc_map = {}
            main = f"CIK{int(cik):010d}.json"
            if main in self.names:
                data = self._index(main, acc_map)
                for extra in data.get("filings", {}).get("files", []):
                    name = extra.get("name")
                    if name in self.names:
                        self._index(name, acc_map)
            self.cache[cik] = acc_map
            if len(self.cache) > 400:
                self.cache.pop(next(iter(self.cache)))
        return self.cache[cik].get(accession)


def text_head(sha, n=4000):
    try:
        with open(text_disk_path(sha), encoding="utf-8") as fh:
            return fh.read(n)
    except OSError:
        return ""


def extract(sha, url, edgar):
    """{publication_date, publication_basis, event_date, event_basis, form}."""
    rec = {"publication_date": None, "publication_basis": None,
           "event_date": None, "event_basis": None, "form": None}

    m = EDGAR_URL_RE.search(url or "")
    if m:
        acc = f"{m.group(2)[:10]}-{m.group(2)[10:12]}-{m.group(2)[12:]}"
        hit = edgar.lookup(m.group(1), acc)
        if hit:
            filed, period, form = hit
            if filed and _iso(*filed.split("-")):
                rec.update(publication_date=filed,
                           publication_basis="edgar-metadata", form=form)
            if period and _iso(*period.split("-")):
                rec.update(event_date=period,
                           event_basis="edgar-metadata-report-period")

    head = text_head(sha)
    if not rec["publication_date"]:
        m = EDGAR_FILED_RE.search(head)
        if m:
            s = m.group(1)
            d = _iso(s[:4], s[4:6], s[6:8])
            if d:
                rec.update(publication_date=d, publication_basis="edgar-filed")
    if not rec["event_date"]:
        m = EVENT_DATE_RE.search(head)
        if m:
            d = _iso(m.group(3), MONTHS[m.group(1)], m.group(2))
            if d:
                rec.update(event_date=d, event_basis="edgar-event-block")
    if not rec["publication_date"]:
        m = DATELINE_RE.search(head[:1500])
        if m:
            d = _iso(m.group(3), MONTHS[m.group(1)], m.group(2))
            if d:
                rec.update(publication_date=d,
                           publication_basis="document-dateline")
    if not rec["publication_date"]:
        for pat, order in ((ISO_RE, (1, 2, 3)), (MDY_RE, (3, 1, 2))):
            m = pat.search(head[:1500])
            if m:
                d = _iso(*(m.group(i) for i in order))
                if d:
                    rec.update(publication_date=d,
                               publication_basis="document-dateline-numeric")
                    break
    if not rec["publication_date"]:
        m = URL_RE.search(url or "")
        if m:
            d = _iso(m.group(1), m.group(2), m.group(3))
            if d:
                rec.update(publication_date=d, publication_basis="url")
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--edgar-zip",
                    default=os.environ.get("EDGAR_SUBMISSIONS_ZIP"))
    args = ap.parse_args()
    edgar = EdgarMeta(args.edgar_zip
                      if args.edgar_zip and os.path.isfile(args.edgar_zip)
                      else None)
    if not edgar.zf:
        print("note: no submissions.zip — EDGAR metadata join skipped")

    shas = {}
    with open(OBS, encoding="utf-8") as fh:
        for line in fh:
            o = json.loads(line)
            if o.get("source_sha256"):
                shas.setdefault(o["source_sha256"], o.get("source_url") or "")

    rows, pub, evt = [], 0, 0
    for sha in sorted(shas):
        rec = extract(sha, shas[sha], edgar)
        pub += bool(rec["publication_date"])
        evt += bool(rec["event_date"])
        rows.append({"sha256": sha, **rec})

    with open(OUT, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True) + "\n")
    print(f"doc_dates: {pub}/{len(rows)} publication-dated, "
          f"{evt} event-dated -> {OUT}")


if __name__ == "__main__":
    main()
