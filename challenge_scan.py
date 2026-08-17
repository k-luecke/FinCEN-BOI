#!/usr/bin/env python3
"""
Corpus-wide challenge scan.

Reads the append-only manifest (and the URL inventory for document
metadata) and classifies every URL's latest observation with the
challenge detector. Where stored bytes are available locally (right
after a crawl, or in CI) they are used; otherwise classification runs
in metadata-only mode with corpus-level evidence (host challenge
patterns) injected as extra signals.

Outputs (all deterministic, sorted by URL, atomic replace):

    recovery/challenge-observations.jsonl   every non-content or
                                            suspect observation
    recovery/document-identities.jsonl      resolved document identity
                                            per challenged URL
    acquisition/doj-recovery-queue.jsonl
    acquisition/federal-register-recovery-queue.jsonl
    acquisition/congress-recovery-queue.jsonl
    acquisition/gao-recovery-queue.jsonl

Nothing here fetches anything; the scan is a pure function of
committed state. The original challenge observations are preserved,
never deleted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

from challenge_detector import (
    ACCESS_INTERSTITIAL,
    BOT_CHALLENGE,
    DETECTOR_VERSION,
    ERROR_RESPONSE,
    NON_CONTENT,
    UNKNOWN_RESPONSE,
    classify_response,
    source_family,
)

# Host-pattern evidence: a host shows a "tokenized challenge" pattern
# when many small HTML "successes" exist and nearly every one has a
# unique hash (real templated sites share boilerplate hashes far more
# often; per-URL challenge tokens make every response unique).
HOST_PATTERN_MIN_COUNT = 50
HOST_PATTERN_SMALL_BYTES = 4096
HOST_PATTERN_UNIQUE_RATIO = 0.9

TIER0_KEYWORDS = (
    "fincen", "beneficial-ownership", "beneficial_ownership",
    "corporate-transparency", "corporate_transparency", "/boi",
    "boi-", "bank-secrecy", "bank_secrecy", "boss-", "ctareporting",
)
TIER1_KEYWORDS = (
    "money-launder", "moneylaunder", "enforcement", "opa/pr", "usao",
    "fraud", "forfeiture", "kleptocracy", "sanctions", "shell-compan",
    "criminal", "tax-division", "financial-crime", "fcpa", "bribery",
    "corruption", "oig", "inspector-general",
)


def tier_for(url: str, family: str) -> int:
    lowered = url.lower()
    if family in ("fincen", "federal_register"):
        # The Federal Register failures here are the FinCEN agency
        # document collection — the core evidence chain.
        return 0
    if any(k in lowered for k in TIER0_KEYWORDS):
        return 0
    if any(k in lowered for k in TIER1_KEYWORDS):
        return 1
    return 2


def slug_title(url: str) -> str | None:
    segments = [s for s in urlparse(url).path.split("/") if s]
    if not segments:
        return None
    slug = segments[-1]
    if "." in slug and slug.rsplit(".", 1)[-1].isalnum() and len(
            slug.rsplit(".", 1)[-1]) <= 5:
        slug = slug.rsplit(".", 1)[0]
    words = slug.replace("_", "-").split("-")
    if len(words) < 2:
        return None
    return " ".join(words).strip().capitalize() or None


def identity_id(family: str, key: str) -> str:
    return hashlib.sha256(f"{family}|{key}".encode()).hexdigest()[:16]


def atomic_write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True, ensure_ascii=False)
                    + "\n")
    os.replace(tmp, path)


def load_latest_records(manifest: Path) -> dict[str, dict]:
    latest: dict[str, dict] = {}
    with manifest.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            url = record.get("url")
            if url:
                latest[url] = record
    return latest


def load_inventory_metadata(inventory: Path) -> dict[str, dict]:
    metadata: dict[str, dict] = {}
    if not inventory.exists():
        return metadata
    with inventory.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("document_number") or record.get("title"):
                metadata[record.get("url", "")] = record
    return metadata


def host_challenge_patterns(latest: dict[str, dict]) -> dict[str, dict]:
    """Hosts whose small-HTML 'successes' are per-URL unique-hash."""
    stats: dict[str, dict] = defaultdict(
        lambda: {"count": 0, "hashes": set()}
    )
    for record in latest.values():
        if not record.get("sha256"):
            continue
        ctype = (record.get("content_type") or "").lower()
        length = record.get("content_length") or 0
        if "html" in ctype and 0 < length < HOST_PATTERN_SMALL_BYTES:
            host = (urlparse(record["url"]).hostname or "").lower()
            stats[host]["count"] += 1
            stats[host]["hashes"].add(record["sha256"])

    patterns = {}
    for host, entry in stats.items():
        if entry["count"] < HOST_PATTERN_MIN_COUNT:
            continue
        ratio = len(entry["hashes"]) / entry["count"]
        if ratio >= HOST_PATTERN_UNIQUE_RATIO:
            patterns[host] = {
                "small_html_count": entry["count"],
                "unique_hash_ratio": round(ratio, 4),
            }
    return patterns


def read_body(record: dict, objects_root: Path | None) -> bytes | None:
    """Stored bytes for a manifest record, when locally present."""
    object_path = record.get("object_path")
    if not object_path:
        return None
    path = Path(object_path)
    if not path.is_absolute() and objects_root is not None:
        candidate = objects_root / path
        if candidate.exists():
            path = candidate
    try:
        return path.read_bytes()
    except OSError:
        return None


def classify_record(
    record: dict,
    body: bytes | None,
    host_patterns: dict[str, dict],
):
    url = record["url"]
    host = (urlparse(url).hostname or "").lower()
    extra = []
    if host in host_patterns:
        extra.append("host_challenge_pattern")

    if body is None and record.get("sha256"):
        # Metadata-only mode: the stored bytes live in release assets,
        # not this checkout. Corpus evidence must carry the decision.
        ctype = (record.get("content_type") or "").lower()
        length = record.get("content_length") or 0
        family = source_family(url)
        signals = ["detection_mode:metadata_only"] + extra
        if (
            "host_challenge_pattern" in extra
            and "html" in ctype
            and 0 < length < HOST_PATTERN_SMALL_BYTES
        ):
            signals.append(f"small_html_success:{length}")
            signals.append("expected_document_body_missing")
            from challenge_detector import Classification
            return Classification(
                BOT_CHALLENGE, signals, vendor=None, confidence="MEDIUM"
            )
        if family == "gao" and "html" in ctype and 0 < length < 4096:
            signals.append(f"small_html_success:{length}")
            signals.append("host_size_outlier")
            from challenge_detector import Classification
            return Classification(
                UNKNOWN_RESPONSE, signals, confidence="LOW"
            )
        if (
            url.lower().endswith(".pdf")
            and "html" in ctype
        ):
            signals.append("expected_document_got_html")
            from challenge_detector import Classification
            return Classification(
                UNKNOWN_RESPONSE, signals, confidence="LOW"
            )
        from challenge_detector import Classification
        return Classification("REAL_CONTENT", signals, confidence="LOW")

    return classify_response(
        url=url,
        status=record.get("http_status"),
        content_type=record.get("content_type"),
        body=body,
        final_url=record.get("final_url"),
        error=record.get("error"),
        extra_signals=extra,
    )


def build_identity(url: str, family: str, inventory_meta: dict,
                   observation_sha: str | None, tier: int) -> dict:
    meta = inventory_meta.get(url, {})
    document_number = meta.get("document_number")
    title = meta.get("title") or slug_title(url)
    key = document_number or url
    identity = {
        "identity_id": identity_id(family, key),
        "source_family": family,
        "original_url": url,
        "title": title,
        "publication_date": meta.get("publication_date"),
        "document_number": document_number,
        "document_type": meta.get("document_type"),
        "case_number": None,
        "docket_number": None,
        "agency": {
            "doj": "Department of Justice",
            "federal_register": "Financial Crimes Enforcement Network",
            "congress": "U.S. Congress",
            "gao": "Government Accountability Office",
            "fincen": "Financial Crimes Enforcement Network",
            "sec": "Securities and Exchange Commission",
        }.get(family),
        "tier": tier,
        "identity_method": (
            "federal_register_api_inventory" if document_number
            else ("url_slug" if title else "unresolved")
        ),
        "source_sha256": observation_sha,
    }
    return identity


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="manifest.jsonl")
    parser.add_argument("--inventory", default="url-inventory.jsonl")
    parser.add_argument("--objects-root", default=None,
                        help="Directory containing archive/ object store "
                             "(bytes-backed classification when present)")
    parser.add_argument("--recovery-dir", default="recovery")
    parser.add_argument("--acquisition-dir", default="acquisition")
    args = parser.parse_args()

    latest = load_latest_records(Path(args.manifest))
    inventory_meta = load_inventory_metadata(Path(args.inventory))
    patterns = host_challenge_patterns(latest)
    objects_root = Path(args.objects_root) if args.objects_root else None

    print(f"URLs (latest observation): {len(latest)}")
    print(f"Host challenge patterns: {json.dumps(patterns, indent=2)}")

    observations = []
    identities = {}
    queues: dict[str, list[dict]] = defaultdict(list)
    counts: Counter = Counter()

    for url in sorted(latest):
        record = latest[url]
        family = source_family(url)
        if family == "web_archive":
            # web.archive.org URLs are recovery-retrieval
            # infrastructure, not requested public records; their
            # transport failures are run telemetry, not challenges.
            continue
        body = read_body(record, objects_root)
        cls = classify_record(record, body, patterns)
        counts[cls.kind] += 1

        if cls.kind not in NON_CONTENT:
            continue

        # 404/410 disappearance observations are handled by the
        # ordinary queue; only technical non-content states route to
        # recovery. Plain transport errors without an interstitial are
        # retryable through the ordinary queue as well.
        status = record.get("http_status")
        plain_error = (
            cls.kind == ERROR_RESPONSE
            and "redirect_to_interstitial_endpoint" not in cls.signals
        )
        if plain_error and status in (404, 410, None, 429) \
                and "unblock" not in (record.get("error") or ""):
            if status in (404, 410):
                continue

        tier = tier_for(url, family)
        obs_sha = record.get("sha256")
        observation = {
            "url": url,
            "final_url": record.get("final_url"),
            "source_family": family,
            "tier": tier,
            "manifest_record_id": record.get("record_id"),
            "response_sha256": obs_sha,
            "http_status": status,
            "content_type": record.get("content_type"),
            "content_length": record.get("content_length"),
            "retrieved_at": record.get("retrieved_at"),
            "error": record.get("error"),
            "classification": cls.kind,
            "confidence": cls.confidence,
            "signals": sorted(set(cls.signals)),
            "vendor": cls.vendor,
            "fingerprint": cls.fingerprint,
            "detector_version": DETECTOR_VERSION,
            "detection_mode": (
                "body" if body is not None else "metadata_only"
            ),
            "headers_preserved": False,
        }
        observations.append(observation)

        identity = build_identity(url, family, inventory_meta,
                                  obs_sha, tier)
        identities[identity["identity_id"]] = identity

        queue_family = {
            "doj": "doj",
            "federal_register": "federal-register",
            "congress": "congress",
            "gao": "gao",
        }.get(family)
        if queue_family:
            queues[queue_family].append({
                "url": url,
                "identity_id": identity["identity_id"],
                "tier": tier,
                "classification": cls.kind,
                "observation_sha256": obs_sha,
                "state": "PENDING",
                "recovery_routes": recovery_routes(family, url),
            })

    recovery_dir = Path(args.recovery_dir)
    acquisition_dir = Path(args.acquisition_dir)

    atomic_write_jsonl(
        recovery_dir / "challenge-observations.jsonl", observations
    )
    atomic_write_jsonl(
        recovery_dir / "document-identities.jsonl",
        sorted(identities.values(), key=lambda i: i["identity_id"]),
    )
    for family in ("doj", "federal-register", "congress", "gao"):
        queue_path = acquisition_dir / f"{family}-recovery-queue.jsonl"

        # Merge with existing queue state: the scan may re-run at any
        # time and must never reset recovery progress (states,
        # attempt counts, cadence timestamps) already recorded.
        existing: dict[str, dict] = {}
        if queue_path.exists():
            with queue_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        row = json.loads(line)
                        existing[row["url"]] = row

        merged = []
        for row in queues.get(family, []):
            prior = existing.get(row["url"])
            if prior:
                for key in ("state", "attempts", "last_attempt_at",
                            "recovered_via", "next_retry_after"):
                    if key in prior:
                        row[key] = prior[key]
            merged.append(row)

        rows = sorted(merged, key=lambda r: (r["tier"], r["url"]))
        atomic_write_jsonl(queue_path, rows)
        print(f"queue {family}: {len(rows)}")

    print("\nClassification of latest observations:")
    for kind, count in counts.most_common():
        print(f"  {kind}: {count}")
    print(f"\nchallenge observations: {len(observations)}")
    print(f"document identities: {len(identities)}")
    return 0


def recovery_routes(family: str, url: str) -> list[str]:
    """Ordered lawful routes to attempt, most-official first."""
    if family == "federal_register":
        return [
            "federal_register_api",
            "govinfo_pdf",
            "web_archive",
            "later_ordinary_retry",
        ]
    if family == "doj":
        return [
            "same_agency_retry_probe",
            "web_archive",
            "later_ordinary_retry",
        ]
    if family == "congress":
        return ["govinfo_package", "web_archive", "later_ordinary_retry"]
    if family == "gao":
        return [
            "same_agency_retry_probe",
            "gao_product_pdf",
            "web_archive",
            "later_ordinary_retry",
        ]
    return ["web_archive", "later_ordinary_retry"]


if __name__ == "__main__":
    sys.exit(main())
