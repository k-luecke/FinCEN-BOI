"""Shared constants and helpers for Content Pass 1 (corpus reconnaissance).

Pass 1 turns archived bytes into: inventory -> extracted text ->
classification -> candidate evidence spans -> ranked reconnaissance index.
It never emits graph facts. See content-pass-1/SCHEMA.md.
"""
from __future__ import annotations

import os
import sys

# The repo root contains queue.py (the crawler's durable work queue), which
# shadows the stdlib `queue` module that multiprocessing imports lazily.
# Resolve stdlib `queue` first, with the repo root off sys.path.
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if "queue" not in sys.modules:
    _removed = [p for p in sys.path if os.path.abspath(p or ".") == _REPO]
    for p in _removed:
        sys.path.remove(p)
    import queue  # noqa: F401  (forces stdlib resolution into sys.modules)
    for p in _removed:
        sys.path.insert(0, p)

import hashlib
import json

PASS_VERSION = "content-pass-1/1.0.0"

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVE_ROOT = os.path.join(REPO_ROOT, "archive")
DERIVED_ROOT = os.path.join(REPO_ROOT, "derived")
TEXT_ROOT = os.path.join(DERIVED_ROOT, "text")
META_ROOT = os.path.join(DERIVED_ROOT, "metadata")
RECON_ROOT = os.path.join(DERIVED_ROOT, "reconnaissance")
OUT_ROOT = os.path.join(REPO_ROOT, "content-pass-1")

MANIFEST = os.path.join(REPO_ROOT, "manifest.jsonl")
LEDGER = os.path.join(REPO_ROOT, "ledger.jsonl")

# Host -> source family. Everything else falls back to OTHER_GOV.
SOURCE_FAMILIES = {
    "www.fincen.gov": "FINCEN",
    "bsaefiling.fincen.gov": "FINCEN",
    "bsaaml.ffiec.gov": "FFIEC",
    "www.ffiec.gov": "FFIEC",
    "home.treasury.gov": "TREASURY",
    "oig.treasury.gov": "TREASURY_OIG",
    "www.sec.gov": "SEC",
    "www.justice.gov": "DOJ",
    "vault.fbi.gov": "FBI_VAULT",
    "www.occ.gov": "OCC",
    "www.fdic.gov": "FDIC",
    "oversight.house.gov": "CONGRESS_OVERSIGHT",
    "judiciary.house.gov": "CONGRESS_JUDICIARY",
    "www.congress.gov": "CONGRESS_GOV",
    "www.federalregister.gov": "FEDERAL_REGISTER",
    "www.govinfo.gov": "GOVINFO",
    "www.gao.gov": "GAO",
    "www.federalreserve.gov": "FEDERAL_RESERVE",
    "www.ncua.gov": "NCUA",
}


def source_family(host: str) -> str:
    return SOURCE_FAMILIES.get(host or "", "OTHER_GOV")


def object_disk_path(sha256: str) -> str:
    return os.path.join(ARCHIVE_ROOT, "objects", "sha256", sha256[:2], sha256[2:])


def text_disk_path(sha256: str) -> str:
    return os.path.join(TEXT_ROOT, sha256[:2], sha256[2:] + ".txt")


def read_jsonl(path):
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def append_jsonl(path, records):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, sort_keys=True, ensure_ascii=False) + "\n")


def write_jsonl(path, records):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, sort_keys=True, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def sniff_mime(head: bytes) -> str:
    """Deterministic magic-byte MIME detection on the first bytes of an object."""
    if not head:
        return "empty"
    if head.startswith(b"%PDF-"):
        return "application/pdf"
    if head.startswith(b"PK\x03\x04") or head.startswith(b"PK\x05\x06"):
        return "application/zip"
    if head.startswith(b"\x1f\x8b"):
        return "application/gzip"
    if head.startswith(b"\x28\xb5\x2f\xfd"):
        return "application/zstd"
    if head.startswith(b"%!PS"):
        return "application/postscript"
    if head.startswith(b"\x89PNG"):
        return "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"GIF8"):
        return "image/gif"
    if head.startswith(b"II*\x00") or head.startswith(b"MM\x00*"):
        return "image/tiff"
    if head.startswith(b"\xd0\xcf\x11\xe0"):
        return "application/x-ole-storage"  # legacy .doc/.xls/.ppt/.msg
    if head.startswith(b"{\\rtf"):
        return "application/rtf"
    stripped = head.lstrip()
    low = stripped[:256].lower()
    if low.startswith(b"<?xml"):
        # XHTML served as XML still reads better through the HTML path.
        if b"<html" in head.lower():
            return "text/html"
        return "application/xml"
    if low.startswith(b"<!doctype html") or low.startswith(b"<html") or b"<html" in low:
        return "text/html"
    if stripped[:1] in (b"{", b"["):
        try:
            json.loads(head.decode("utf-8", "strict"))
            return "application/json"
        except Exception:
            # Prefix of a larger JSON document.
            if stripped[:1] == b"{" and b'"' in stripped[:64]:
                return "application/json"
    try:
        head.decode("utf-8")
        return "text/plain"
    except UnicodeDecodeError:
        pass
    try:
        head.decode("latin-1")
        return "text/plain"
    except UnicodeDecodeError:
        return "application/octet-stream"


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)
