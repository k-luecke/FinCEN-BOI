"""Part I — evidentiary posture assignment.

Posture describes WHO asserts the relationship and in what capacity —
never whether the underlying proposition is true. DIRECT evidence_class
means "the cited source directly states the relationship", nothing more.
"""
from __future__ import annotations

import re

POSTURES = (
    "SELF_REPORTED",
    "GOVERNMENT_ALLEGATION",
    "GOVERNMENT_FINDING",
    "ADMINISTRATIVE_DESIGNATION",
    "COURT_ALLEGATION",
    "ADJUDICATED_FACT",
    "CONGRESSIONAL_ASSERTION",
    "THIRD_PARTY_ASSERTION",
    "OTHER_DIRECT_ASSERTION",
)

_COMPLAINT = re.compile(r"complaint|amended-?complaint|comp\d|amendedcomplaint", re.I)
_JUDGMENT = re.compile(r"judg|final-?judgment|consent", re.I)
_OFAC_DESIGNATION = re.compile(
    r"designat|sanction|blocked|SDN|specially.designated|magnitsky|E\.?O\.?\s?13", re.I)
_SEC_SELF = re.compile(r"sc-?13[dg]|schedule.?13[dg]|form-?[345]\b", re.I)
_ENF_ORDER = re.compile(r"consent.?order|cease.?and.?desist|civil.?money.?penalt|"
                        r"enforcement|assessment|comptroller-orders", re.I)


def assign_posture(rec: dict, doc_classes, text_head: str) -> tuple[str, str]:
    """(evidentiary_posture, rationale) for a document.

    rec: inventory record (host / source_family / url / provenance).
    Conservative defaults: allegations stay allegations. ADJUDICATED_FACT
    is never assigned automatically in this pass — final-judgment
    documents are COURT_ALLEGATION until a human confirms the specific
    finding was adjudicated rather than recited or consented without
    admission.
    """
    fam = rec.get("source_family") or ""
    url = rec.get("url") or ""
    classes = set(doc_classes or [])

    if fam == "SEC":
        if _SEC_SELF.search(url) or "SEC_OWNERSHIP" in classes and "13" in text_head[:2000]:
            return "SELF_REPORTED", "SEC ownership filing (13D/G / Forms 3-5): filer's own statement"
        if _COMPLAINT.search(url):
            return "GOVERNMENT_ALLEGATION", "SEC complaint: agency allegation, not adjudicated"
        if _JUDGMENT.search(url):
            return "COURT_ALLEGATION", ("judgment document: facts frequently recited from the "
                                        "complaint or consented without admission; not auto-adjudicated")
        if _ENF_ORDER.search(url):
            return "GOVERNMENT_FINDING", "SEC administrative order/settlement finding"
        return "GOVERNMENT_ALLEGATION", "SEC enforcement-adjacent document, default allegation"
    if fam in ("TREASURY", "TREASURY_OIG"):
        if _OFAC_DESIGNATION.search(url) or "SANCTIONS" in classes:
            return "ADMINISTRATIVE_DESIGNATION", "OFAC/Treasury designation narrative"
        return "GOVERNMENT_FINDING", "Treasury publication"
    if fam == "FINCEN":
        if _ENF_ORDER.search(url) or "ENFORCEMENT" in classes:
            return "GOVERNMENT_FINDING", "FinCEN enforcement assessment/order"
        return "GOVERNMENT_FINDING", "FinCEN official publication"
    if fam in ("OCC", "FDIC"):
        if _ENF_ORDER.search(url):
            return "GOVERNMENT_FINDING", "prudential-regulator enforcement/consent order"
        return "GOVERNMENT_FINDING", "prudential-regulator publication"
    if fam == "DOJ":
        return "GOVERNMENT_ALLEGATION", ("DOJ material: charges/complaints are allegations "
                                         "unless conviction is explicit in a later pass")
    if fam.startswith("CONGRESS"):
        return "CONGRESSIONAL_ASSERTION", "congressional publication/exhibit"
    if fam in ("GAO", "GOVINFO", "FEDERAL_REGISTER"):
        return "GOVERNMENT_FINDING", "official government report/regulatory text"
    if fam == "FBI_VAULT":
        return "GOVERNMENT_ALLEGATION", "investigative-file material"
    return "OTHER_DIRECT_ASSERTION", "unmapped source family"
