"""Derive ocr-required.jsonl and extraction-errors.jsonl from the
extraction status log, with a value-signal so OCR (a later targeted pass)
can be prioritized. No OCR is performed in Pass 1.

Usage: python3 -m content_pass_1.finalize
"""
from __future__ import annotations

import json
import os
import re

from .common import OUT_ROOT, PASS_VERSION, log, read_jsonl

HIGH_VALUE_FAMILY = {"FBI_VAULT", "DOJ", "CONGRESS_OVERSIGHT", "CONGRESS_JUDICIARY",
                     "CONGRESS_GOV", "GAO", "GOVINFO", "TREASURY_OIG", "FINCEN", "SEC"}
HV_URL = re.compile(r"enforcement|complaint|indictment|exhibit|report|hearing|"
                    r"testimony|assessment|consent|order|vault", re.I)


def main():
    inv = {r["sha256"]: r for r in
           read_jsonl(os.path.join(OUT_ROOT, "corpus-inventory.jsonl"))}
    ocr, errors = [], []
    for s in read_jsonl(os.path.join(OUT_ROOT, "extraction-status.jsonl")):
        rec = inv.get(s["sha256"], {})
        if s.get("ocr_candidate"):
            fam = rec.get("source_family") or ""
            url = rec.get("url") or ""
            hv = fam in HIGH_VALUE_FAMILY or bool(HV_URL.search(url))
            ocr.append({
                "sha256": s["sha256"],
                "source_url": url,
                "host": rec.get("host"),
                "source_family": fam,
                "provenance": rec.get("provenance"),
                "page_count": s.get("page_count"),
                "size_bytes": rec.get("size_bytes"),
                "native_chars": s.get("character_count"),
                "high_value": hv,
                "reason": "native PDF text below threshold; likely scanned",
                "pass_version": PASS_VERSION,
            })
        if s.get("extraction_status") == "ERROR":
            errors.append({
                "sha256": s["sha256"],
                "source_url": rec.get("url"),
                "host": rec.get("host"),
                "sniffed_mime": s.get("sniffed_mime"),
                "extractor": s.get("extractor"),
                "error": s.get("error"),
                "pass_version": PASS_VERSION,
            })
    ocr.sort(key=lambda r: (not r["high_value"], r["sha256"]))
    for name, rows in (("ocr-required.jsonl", ocr),
                       ("extraction-errors.jsonl", errors)):
        with open(os.path.join(OUT_ROOT, name), "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n")
        log(f"finalize: {name}: {len(rows)}")


if __name__ == "__main__":
    main()
