"""Step 1 — corpus inventory.

Reads manifest.jsonl (append-only retrieval ledger) and ledger.jsonl
(per-URL change ledger), joins them against the on-disk content-addressed
object store, sniffs real MIME types, and emits one inventory record per
unique durable object plus aggregate counts.

Usage: python3 -m content_pass_1.inventory
"""
from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from urllib.parse import urlsplit

from .common import (
    LEDGER, MANIFEST, OUT_ROOT, PASS_VERSION,
    log, object_disk_path, read_jsonl, sniff_mime, source_family, write_jsonl,
)


def url_extension(url: str) -> str:
    path = urlsplit(url or "").path
    base = path.rsplit("/", 1)[-1]
    if "." in base:
        ext = base.rsplit(".", 1)[-1].lower()
        if 1 <= len(ext) <= 5 and ext.isalnum():
            return ext
    return ""


def size_bucket(n) -> str:
    if n is None:
        return "unknown"
    for cap, name in ((10_240, "<10KB"), (102_400, "10-100KB"), (1_048_576, "100KB-1MB"),
                      (10_485_760, "1-10MB"), (104_857_600, "10-100MB")):
        if n < cap:
            return name
    return ">=100MB"


def build():
    # Per-URL change history: which URLs have had more than one content hash.
    url_history = {}
    for rec in read_jsonl(LEDGER):
        url_history[rec.get("url")] = rec

    objects = {}          # sha256 -> object record under construction
    retrievals_by_sha = defaultdict(list)
    failures = []
    for rec in read_jsonl(MANIFEST):
        sha = rec.get("sha256")
        if not sha:
            failures.append(rec)
            continue
        retrievals_by_sha[sha].append(rec)

    # URLs that map to >1 sha over time (historical versions).
    shas_by_url = defaultdict(set)
    for sha, recs in retrievals_by_sha.items():
        for r in recs:
            shas_by_url[r["url"]].add(sha)

    inv = []
    for sha, recs in retrievals_by_sha.items():
        recs = sorted(recs, key=lambda r: r.get("retrieved_at") or "")
        primary = recs[0]
        host = urlsplit(primary.get("final_url") or primary.get("url") or "").hostname or ""
        disk = object_disk_path(sha)
        present = os.path.isfile(disk)
        head = b""
        size = None
        if present:
            size = os.path.getsize(disk)
            with open(disk, "rb") as fh:
                head = fh.read(4096)
        claimed = (primary.get("content_type") or "").split(";")[0].strip().lower()
        sniffed = sniff_mime(head) if present else None
        urls = []
        for r in recs:
            urls.append({
                "url": r.get("url"),
                "final_url": r.get("final_url"),
                "retrieved_at": r.get("retrieved_at"),
                "http_status": r.get("http_status"),
                "provenance": r.get("provenance"),
                "source": r.get("source"),
                "parent_url": r.get("parent_url"),
                "depth": r.get("depth"),
            })
        historical = any(len(shas_by_url[r["url"]]) > 1 for r in recs)
        inv.append({
            "sha256": sha,
            "object_path": primary.get("object_path"),
            "present_on_disk": present,
            "size_bytes": size if size is not None else primary.get("content_length"),
            "claimed_content_type": claimed or None,
            "sniffed_mime": sniffed,
            "mime_conflict": bool(present and claimed and sniffed and
                                  claimed not in (sniffed,) and
                                  not _compatible(claimed, sniffed)),
            "host": host,
            "source_family": source_family(host),
            "provenance": primary.get("provenance"),
            "url": primary.get("url"),
            "final_url": primary.get("final_url"),
            "url_extension": url_extension(primary.get("final_url") or primary.get("url")),
            "retrieved_at": primary.get("retrieved_at"),
            "retrieval_count": len(recs),
            "multi_url_object": len({r["url"] for r in recs}) > 1,
            "url_has_multiple_versions": historical,
            "urls": urls,
            "pass_version": PASS_VERSION,
        })

    inv.sort(key=lambda r: r["sha256"])
    write_jsonl(os.path.join(OUT_ROOT, "corpus-inventory.jsonl"), inv)

    agg = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pass_version": PASS_VERSION,
        "unique_objects": len(inv),
        "objects_on_disk": sum(1 for r in inv if r["present_on_disk"]),
        "objects_missing_from_disk": sum(1 for r in inv if not r["present_on_disk"]),
        "total_bytes_on_disk": sum(r["size_bytes"] or 0 for r in inv if r["present_on_disk"]),
        "retrieval_records": sum(r["retrieval_count"] for r in inv),
        "failed_retrieval_records": len(failures),
        "multi_url_objects": sum(1 for r in inv if r["multi_url_object"]),
        "urls_with_multiple_versions": sum(1 for r in inv if r["url_has_multiple_versions"]),
        "mime_conflicts": sum(1 for r in inv if r["mime_conflict"]),
        "by_sniffed_mime": dict(Counter(r["sniffed_mime"] or "absent" for r in inv)),
        "by_claimed_content_type": dict(Counter(r["claimed_content_type"] or "none" for r in inv)),
        "by_host": dict(Counter(r["host"] for r in inv)),
        "by_provenance": dict(Counter(r["provenance"] or "UNCLASSIFIED" for r in inv)),
        "by_source_family": dict(Counter(r["source_family"] for r in inv)),
        "by_url_extension": dict(Counter(r["url_extension"] or "none" for r in inv)),
        "by_size_bucket": dict(Counter(size_bucket(r["size_bytes"]) for r in inv)),
    }
    out = os.path.join(OUT_ROOT, "inventory-aggregates.json")
    os.makedirs(OUT_ROOT, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(agg, fh, indent=2, sort_keys=True)
        fh.write("\n")
    log(f"inventory: {len(inv)} unique objects "
        f"({agg['objects_on_disk']} on disk, {agg['mime_conflicts']} MIME conflicts)")


def _compatible(claimed: str, sniffed: str) -> bool:
    pairs = {
        ("text/html", "text/plain"), ("text/plain", "text/html"),
        ("application/xhtml+xml", "text/html"), ("text/xml", "application/xml"),
        ("application/xml", "text/html"),  # RSS pages served as xml with embedded html
        ("application/json", "text/plain"), ("text/plain", "application/json"),
        ("text/csv", "text/plain"), ("application/octet-stream", "application/zip"),
        ("application/x-zip-compressed", "application/zip"),
        ("binary/octet-stream", "application/zip"),
    }
    return (claimed, sniffed) in pairs or claimed == sniffed


if __name__ == "__main__":
    build()
