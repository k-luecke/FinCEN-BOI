"""Step 2 — deterministic text extraction.

Reads content-pass-1/corpus-inventory.jsonl and extracts text from every
supported object into derived/text/<aa>/<sha256>.txt (raw extracted
representation; all candidate locators resolve against these bytes).

- HTML/XML  -> lxml, script/style dropped, block-level newlines
- JSON      -> canonical pretty-print (sorted keys, indent 1)
- TXT/CSV   -> decoded as-is (utf-8 then latin-1)
- PDF       -> pdftotext -enc UTF-8 (native text only; \\f page breaks kept).
               Weak yield => NO_TEXT and OCR-candidate flag. No bulk OCR here.
- ZIP       -> safe member listing only (no extraction): counts, sizes,
               extension histogram recorded to derived/metadata. Guards:
               member cap, total-uncompressed cap, path-traversal check.
- other     -> UNSUPPORTED

Checkpointed: existing status records are honored on resume.
Usage: python3 -m content_pass_1.extract [--workers N]
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import subprocess
import zipfile
from collections import Counter
from datetime import datetime, timezone
from multiprocessing import Pool

from lxml import etree, html as lxml_html

from .common import (
    META_ROOT, OUT_ROOT, PASS_VERSION, TEXT_ROOT,
    log, object_disk_path, read_jsonl, text_disk_path,
)

EXTRACTOR_VERSION = "1.0.0"
STATUS_PATH = os.path.join(OUT_ROOT, "extraction-status.jsonl")

PDF_MIN_TOTAL_CHARS = 200      # below this a PDF is considered textless
PDF_MIN_CHARS_PER_PAGE = 20    # average; scanned PDFs sit near zero
ZIP_MAX_MEMBERS = 2_000_000
ZIP_MAX_TOTAL_UNCOMPRESSED = 50 * 1024**3  # listing only; nothing is inflated

TEXTUAL = {"text/html", "application/xml", "application/json", "text/plain"}


def _decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1", "replace")


def extract_html(raw: bytes):
    doc = lxml_html.fromstring(raw)
    for el in doc.xpath("//script|//style|//noscript"):
        el.getparent().remove(el)
    title = None
    tnodes = doc.xpath("//title/text()")
    if tnodes:
        title = re.sub(r"\s+", " ", tnodes[0]).strip() or None
    # Deterministic block-level text: newline per block element.
    text = doc.text_content()
    # text_content flattens; rebuild with itertext over block boundaries instead.
    parts = []
    BLOCK = {"p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6",
             "br", "table", "section", "article", "header", "footer", "ul",
             "ol", "blockquote", "pre", "td", "th"}
    for el in doc.iter():
        if el.tag in BLOCK and parts and parts[-1] != "\n":
            parts.append("\n")
        if el.text:
            parts.append(el.text)
        if el.tail:
            parts.append(el.tail)
    text = "".join(parts)
    text = re.sub(r"[ \t\r ]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text, title


def extract_xml(raw: bytes):
    root = etree.fromstring(raw, parser=etree.XMLParser(recover=True, huge_tree=True))
    if root is None:
        return "", None
    text = " ".join(t.strip() for t in root.itertext() if t and t.strip())
    text = re.sub(r"[ \t]+", " ", text)
    return text, None


def extract_json_text(raw: bytes):
    obj = json.loads(_decode(raw))
    return json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False), None


def extract_pdf(disk_path: str):
    proc = subprocess.run(
        ["pdftotext", "-enc", "UTF-8", "-q", disk_path, "-"],
        capture_output=True, timeout=120,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"pdftotext rc={proc.returncode}: "
                           f"{proc.stderr[:200].decode('utf-8', 'replace')}")
    text = proc.stdout.decode("utf-8", "replace")
    pages = text.count("\f") + 1 if text else 0
    return text, pages


def index_zip(disk_path: str):
    info = {"member_count": 0, "total_uncompressed": 0, "suspicious_paths": 0,
            "by_extension": Counter(), "truncated": False, "sample_members": []}
    with zipfile.ZipFile(disk_path) as zf:
        for i, zi in enumerate(zf.infolist()):
            if i >= ZIP_MAX_MEMBERS:
                info["truncated"] = True
                break
            info["member_count"] += 1
            info["total_uncompressed"] += zi.file_size
            name = zi.filename
            if name.startswith("/") or ".." in name.split("/"):
                info["suspicious_paths"] += 1
            ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
            info["by_extension"][ext] += 1
            if len(info["sample_members"]) < 20:
                info["sample_members"].append({"name": name[:200], "size": zi.file_size})
            if info["total_uncompressed"] > ZIP_MAX_TOTAL_UNCOMPRESSED:
                info["truncated"] = True
                break
    info["by_extension"] = dict(info["by_extension"].most_common(20))
    return info


def process(rec):
    sha = rec["sha256"]
    mime = rec.get("sniffed_mime")
    disk = object_disk_path(sha)
    status = {
        "sha256": sha,
        "source_url": rec.get("url"),
        "host": rec.get("host"),
        "sniffed_mime": mime,
        "extractor": None,
        "extractor_version": EXTRACTOR_VERSION,
        "extraction_time": datetime.now(timezone.utc).isoformat(),
        "extraction_status": None,
        "character_count": 0,
        "page_count": None,
        "title": None,
        "error": None,
        "ocr_candidate": False,
        "pass_version": PASS_VERSION,
    }
    if not rec.get("present_on_disk"):
        status["extraction_status"] = "OBJECT_MISSING"
        return status
    try:
        raw = None
        text = title = None
        if mime == "text/html":
            with open(disk, "rb") as fh:
                raw = fh.read()
            text, title = extract_html(raw)
            status["extractor"] = "lxml-html"
        elif mime == "application/xml":
            with open(disk, "rb") as fh:
                raw = fh.read()
            text, title = extract_xml(raw)
            status["extractor"] = "lxml-xml"
        elif mime == "application/json":
            with open(disk, "rb") as fh:
                raw = fh.read()
            text, title = extract_json_text(raw)
            status["extractor"] = "json-canonical"
        elif mime == "text/plain":
            with open(disk, "rb") as fh:
                raw = fh.read()
            text, title = _decode(raw), None
            status["extractor"] = "raw-decode"
        elif mime == "application/pdf":
            text, pages = extract_pdf(disk)
            status["extractor"] = "pdftotext"
            status["page_count"] = pages
            stripped = re.sub(r"\s", "", text)
            if len(stripped) < PDF_MIN_TOTAL_CHARS or (
                    pages and len(stripped) / pages < PDF_MIN_CHARS_PER_PAGE):
                status["extraction_status"] = "NO_TEXT"
                status["ocr_candidate"] = True
                status["character_count"] = len(text)
                return status
        elif mime == "application/zip":
            zinfo = index_zip(disk)
            status["extractor"] = "zip-index"
            status["extraction_status"] = "INDEXED_CONTAINER"
            mpath = os.path.join(META_ROOT, sha[:2], sha[2:] + ".container.json")
            os.makedirs(os.path.dirname(mpath), exist_ok=True)
            with open(mpath, "w", encoding="utf-8") as fh:
                json.dump({"sha256": sha, "container": zinfo,
                           "pass_version": PASS_VERSION}, fh, sort_keys=True)
            return status
        else:
            status["extraction_status"] = "UNSUPPORTED"
            return status

        if text is None:
            text = ""
        tpath = text_disk_path(sha)
        os.makedirs(os.path.dirname(tpath), exist_ok=True)
        tmp = tpath + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, tpath)
        status["character_count"] = len(text)
        status["title"] = title
        status["extraction_status"] = "OK" if text.strip() else "EMPTY"
        return status
    except Exception as exc:  # recorded, never fatal to the sweep
        status["extraction_status"] = "ERROR"
        status["error"] = f"{type(exc).__name__}: {exc}"[:500]
        return status


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    done = set()
    if os.path.isfile(STATUS_PATH):
        for rec in read_jsonl(STATUS_PATH):
            done.add(rec["sha256"])

    todo = []
    for rec in read_jsonl(os.path.join(OUT_ROOT, "corpus-inventory.jsonl")):
        if rec["sha256"] not in done:
            todo.append({k: rec[k] for k in
                         ("sha256", "sniffed_mime", "present_on_disk", "url", "host")})
    if args.limit:
        todo = todo[:args.limit]
    log(f"extract: {len(todo)} to process ({len(done)} already done)")
    os.makedirs(TEXT_ROOT, exist_ok=True)
    os.makedirs(os.path.dirname(STATUS_PATH), exist_ok=True)

    CHUNK = 500
    with Pool(args.workers) as pool, open(STATUS_PATH, "a", encoding="utf-8") as out:
        for i in range(0, len(todo), CHUNK):
            chunk = todo[i:i + CHUNK]
            for st in pool.imap_unordered(process, chunk, chunksize=20):
                out.write(json.dumps(st, sort_keys=True, ensure_ascii=False) + "\n")
            out.flush()
            log(f"extract: checkpoint {min(i + CHUNK, len(todo))}/{len(todo)}")


if __name__ == "__main__":
    main()
