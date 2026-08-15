#!/usr/bin/env python3
"""
Challenge-aware lawful recovery engine.

For every challenged/non-content URL in the acquisition recovery
queues, this resolves the underlying DOCUMENT IDENTITY and tries
lawful public routes, in order:

    1. same-agency official representation (probe an ordinary retry;
       official feeds/APIs/attachment endpoints)
    2. other official federal representation (GovInfo, Federal
       Register API)
    3. public web archive (classified separately as WEB-ARCHIVE)
    4. later ordinary retry (conservative cadence)

Hard boundary — this module never:
    - solves or bypasses CAPTCHAs / JS challenges
    - rotates proxies or identities
    - spoofs fingerprints
    - uses authenticated or hidden endpoints
    - guesses identifiers to reach nonpublic content
    - circumvents rate limits or re-hammers challenged endpoints

Direct retries against a challenged host are limited to a small probe
sample per run: if the probe still returns challenges, every other
direct retry on that host is skipped for the whole run and the queue
moves to alternate routes only. 429s honor Retry-After once and then
stop that host for the run.

Every recovered object is SHA-256'd, stored content-addressed, and
recorded in a run manifest (merged into manifest.jsonl and published
to durable release storage by the same machinery as ordinary crawls).
Provenance keeps original publisher and retrieval host distinct;
original challenge observations are never rewritten or deleted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote, urlparse

import archive
from archive import DEFAULT_ALLOWED_HOSTS, fetch, sanitize_url, utc_now
from challenge_detector import (
    DETECTOR_VERSION,
    validate_content,
)

# Public web archive hosts, permitted for the recovery collector only
# and always classified WEB-ARCHIVE, never as the original record.
WEB_ARCHIVE_HOSTS = {"web.archive.org", "archive.org"}

RECOVERY_ALLOWED_HOSTS = DEFAULT_ALLOWED_HOSTS | WEB_ARCHIVE_HOSTS

CDX_API = (
    "https://web.archive.org/cdx/search/cdx"
    "?url={url}&output=json&filter=statuscode:200"
    "&fl=timestamp,original,statuscode,digest&limit=1&fastLatest=true"
)
WAYBACK_RAW = "https://web.archive.org/web/{timestamp}id_/{url}"

FR_API_DOC = "https://www.federalregister.gov/api/v1/documents/{docnum}.json"

# Ordinary-retry cadence for challenged endpoints: at most one direct
# attempt per URL per cadence window, and only when the host probe
# shows the challenge has been lifted.
RETRY_CADENCE = timedelta(days=7)
PROBE_SAMPLE = 3

DIRECT = "SAME_DOCUMENT"
OFFICIAL_MIRROR = "OFFICIAL_MIRROR"
DERIVED = "DERIVED_REPRESENTATION"
ARCHIVED_VERSION = "ARCHIVED_VERSION"
POSSIBLE_MATCH = "POSSIBLE_MATCH"


def parse_when(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return rows


def atomic_write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True, ensure_ascii=False)
                    + "\n")
    os.replace(tmp, path)


def append_jsonl_row(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def link_key(original_url: str, alternate_url: str,
             relationship: str) -> str:
    return hashlib.sha256(
        f"{original_url}|{alternate_url}|{relationship}".encode()
    ).hexdigest()[:16]


class RecoveryRun:
    def __init__(self, args):
        self.args = args
        self.started_monotonic = time.monotonic()
        self.time_budget_reported = False
        self.out = Path(args.out)
        self.run_manifest = Path(args.run_manifest)
        self.recovery_dir = Path(args.recovery_dir)
        self.acquisition_dir = Path(args.acquisition_dir)
        self.links_path = self.recovery_dir / "recovery-links.jsonl"

        self.identities = {
            row["identity_id"]: row
            for row in load_jsonl(
                self.recovery_dir / "document-identities.jsonl"
            )
        }
        self.existing_links = load_jsonl(self.links_path)
        self.link_keys = {
            link_key(r["original_url"], r["alternate_url"],
                     r["relationship"])
            for r in self.existing_links
        }
        # Latest successful capture per URL from the committed
        # manifest — lets us cross-reference already-archived official
        # mirrors without a single network request.
        self.manifest_success: dict[str, dict] = {}
        manifest = Path(args.manifest)
        if manifest.exists():
            with manifest.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if record.get("sha256"):
                        self.manifest_success[record["url"]] = record

        self.fetches = 0
        self.last_fetch_by_host: dict[str, float] = {}
        self.host_still_challenged: dict[str, bool] = {}
        self.host_stopped: set[str] = set()   # 429'd this run
        self.stats = {
            "links_created": 0,
            "official_mirror": 0,
            "same_document": 0,
            "web_archive": 0,
            "derived": 0,
            "fetches": 0,
            "still_challenged_probes": 0,
            "recovered_urls": set(),
        }

    # -- polite fetch wrapper ---------------------------------------

    def polite_fetch(self, url: str, provenance: str, source: str,
                     expect_family: str | None = None):
        """One ordinary fetch, rate-limited per host, budget-capped.

        Returns (record, body, ok, classification) where ok means the
        response validated as content for the expected family.
        """
        if self.fetches >= self.args.max_fetches:
            return None, None, False, None
        # Wall-clock budget: slow upstreams (archive.org under load can
        # take tens of seconds per response) must never eat the time
        # the run needs to verify, publish, and commit its results.
        elapsed = time.monotonic() - self.started_monotonic
        if elapsed > self.args.max_seconds:
            if not self.time_budget_reported:
                print(
                    f"  wall-clock budget exhausted after "
                    f"{int(elapsed)}s; stopping fetches to leave time "
                    f"for verify/publish/commit",
                    file=sys.stderr,
                )
                self.time_budget_reported = True
            return None, None, False, None
        host = (urlparse(url).hostname or "").lower()
        if host in self.host_stopped:
            return None, None, False, None
        elapsed = time.monotonic() - self.last_fetch_by_host.get(host, 0)
        if elapsed < self.args.delay:
            time.sleep(self.args.delay - elapsed)

        record = fetch(
            url=url,
            provenance=provenance,
            source=source,
            out=self.out,
            manifest=self.run_manifest,
            allowed_hosts=RECOVERY_ALLOWED_HOSTS,
            max_bytes=self.args.max_bytes,
            max_retries=1,
        )
        self.last_fetch_by_host[host] = time.monotonic()
        self.fetches += 1
        self.stats["fetches"] += 1

        if record.http_status == 429:
            # Retry-After was honored inside fetch(); a second 429
            # stops this host for the entire run — never hammer.
            print(f"  429 from {host}; stopping host for this run",
                  file=sys.stderr)
            self.host_stopped.add(host)

        body = None
        if record.object_path:
            try:
                body = Path(record.object_path).read_bytes()
            except OSError:
                body = None

        ok, cls = validate_content(
            url=url,
            status=record.http_status,
            content_type=record.content_type,
            body=body,
            family=expect_family,
            final_url=record.final_url,
            error=record.error,
        )
        return record, body, ok, cls

    # -- recovery links ---------------------------------------------

    def add_link(self, *, original_url: str, identity_id: str | None,
                 alternate_url: str, alternate_family: str,
                 relationship: str, confidence: str,
                 discovery_method: str, retrieved_sha256: str | None,
                 retrieval_time: str | None,
                 original_observation_sha256: str | None,
                 publisher: str | None, retrieval_host: str,
                 manual_review_required: bool,
                 equivalence: str | None = None,
                 represents: str | None = None) -> bool:
        key = link_key(original_url, alternate_url, relationship)
        if key in self.link_keys:
            return False
        row = {
            "recovery_id": key,
            "original_url": original_url,
            "original_observation_sha256": original_observation_sha256,
            "document_identity": identity_id,
            "alternate_url": alternate_url,
            "alternate_source_family": alternate_family,
            "relationship": relationship,
            "confidence": confidence,
            "discovery_method": discovery_method,
            "retrieved_sha256": retrieved_sha256,
            "retrieval_time": retrieval_time,
            "manual_review_required": manual_review_required,
            "publisher": publisher,
            "retrieval_host": retrieval_host,
            "equivalence": equivalence,
            "represents": represents,
            "detector_version": DETECTOR_VERSION,
            "created_at": utc_now(),
        }
        append_jsonl_row(self.links_path, row)
        self.link_keys.add(key)
        self.existing_links.append(row)
        self.stats["links_created"] += 1
        if relationship == OFFICIAL_MIRROR:
            self.stats["official_mirror"] += 1
        elif relationship == DIRECT:
            self.stats["same_document"] += 1
        elif relationship == ARCHIVED_VERSION:
            self.stats["web_archive"] += 1
        elif relationship == DERIVED:
            self.stats["derived"] += 1
        self.stats["recovered_urls"].add(original_url)
        return True

    # -- queue handling ---------------------------------------------

    def load_queue(self, family: str) -> list[dict]:
        return load_jsonl(
            self.acquisition_dir / f"{family}-recovery-queue.jsonl"
        )

    def save_queue(self, family: str, rows: list[dict]) -> None:
        atomic_write_jsonl(
            self.acquisition_dir / f"{family}-recovery-queue.jsonl",
            sorted(rows, key=lambda r: (r.get("tier", 9), r["url"])),
        )

    def recovered_originals(self) -> set[str]:
        return {
            r["original_url"] for r in self.existing_links
            if r["relationship"] in (DIRECT, OFFICIAL_MIRROR,
                                     ARCHIVED_VERSION)
            and r.get("retrieved_sha256")
        }

    # ================================================================
    # Federal Register: FR API record + GovInfo official bytes
    # ================================================================

    def has_link(self, url: str, relationship: str) -> bool:
        return any(
            link["original_url"] == url
            and link["relationship"] == relationship
            and link.get("retrieved_sha256")
            for link in self.existing_links
        )

    def fetch_fr_api_record(self, url: str, docnum: str,
                            obs_sha: str | None) -> str | None:
        """Archive the FR API JSON identity record for one document.

        Returns the official representation URL the record points at
        (FR_API_RECORD --REPRESENTS--> GOVINFO_DOCUMENT), or None.
        """
        api_url = FR_API_DOC.format(docnum=quote(docnum))
        record, body, ok, _cls = self.polite_fetch(
            api_url, "GOV-PUBLIC",
            "Federal Register API document record",
            expect_family="federal_register",
        )
        if not (record and ok and body):
            return None
        represents = None
        try:
            payload = json.loads(body)
            represents = (
                payload.get("pdf_url") or payload.get("body_html_url")
            )
        except (json.JSONDecodeError, AttributeError):
            pass
        self.add_link(
            original_url=url,
            identity_id=None,
            alternate_url=api_url,
            alternate_family="federal_register_api",
            relationship=DERIVED,
            confidence="HIGH",
            discovery_method="federal_register_api",
            retrieved_sha256=record.sha256,
            retrieval_time=record.retrieved_at,
            original_observation_sha256=obs_sha,
            publisher="Office of the Federal Register",
            retrieval_host="www.federalregister.gov",
            manual_review_required=False,
            represents=represents,
        )
        return represents

    def recover_federal_register(self) -> None:
        rows = self.load_queue("federal-register")
        if not rows:
            return
        print(f"\n=== Federal Register: {len(rows)} queued ===")

        for row in rows:
            url = row["url"]
            state = row.get("state", "PENDING")
            identity = self.identities.get(row.get("identity_id") or "")
            docnum = (identity or {}).get("document_number")
            obs_sha = row.get("observation_sha256")

            if state not in ("PENDING", "RETRY_LATER"):
                # Already recovered via GovInfo: still preserve the FR
                # API's own JSON identity record once, so both
                # identities survive (FR_API_RECORD --REPRESENTS-->
                # GOVINFO_DOCUMENT).
                if (state == "RECOVERED_OFFICIAL_MIRROR" and docnum
                        and self.args.network
                        and self.args.archive_fr_api
                        and not self.has_link(url, DERIVED)):
                    self.fetch_fr_api_record(url, docnum, obs_sha)
                continue

            if not docnum:
                # A search/listing page, not a document — identity is
                # the page itself; only a web-archive route applies.
                row["state"] = "NO_DOCUMENT_IDENTITY"
                continue

            recovered = False

            # Route 2a: GovInfo official bytes, possibly already
            # archived by a previous ordinary crawl.
            govinfo_url, govinfo_record = self.find_govinfo_pdf(docnum)
            if govinfo_record:
                self.add_link(
                    original_url=url,
                    identity_id=row.get("identity_id"),
                    alternate_url=govinfo_url,
                    alternate_family="govinfo",
                    relationship=OFFICIAL_MIRROR,
                    confidence="HIGH",
                    discovery_method=(
                        "federal_register_api_inventory_crossref"
                    ),
                    retrieved_sha256=govinfo_record["sha256"],
                    retrieval_time=govinfo_record.get("retrieved_at"),
                    original_observation_sha256=obs_sha,
                    publisher="Office of the Federal Register",
                    retrieval_host="www.govinfo.gov",
                    manual_review_required=False,
                )
                recovered = True

            # Route 1: the FR API's own JSON record for this document
            # (metadata identity; also yields canonical GovInfo URL).
            if self.args.network and (not recovered
                                      or self.args.archive_fr_api):
                represents = self.fetch_fr_api_record(
                    url, docnum, obs_sha
                )
                # If GovInfo bytes were not yet archived, fetch the
                # official PDF the API record points at.
                if not recovered and represents and (
                    (urlparse(represents).hostname or "")
                    .endswith("govinfo.gov")
                ):
                    pdf_record, _pdf_body, pdf_ok, _ = (
                        self.polite_fetch(
                            represents, "GOV-PUBLIC",
                            f"GovInfo FR PDF {docnum}",
                            expect_family="govinfo",
                        )
                    )
                    if pdf_record and pdf_ok:
                        self.add_link(
                            original_url=url,
                            identity_id=row.get("identity_id"),
                            alternate_url=represents,
                            alternate_family="govinfo",
                            relationship=OFFICIAL_MIRROR,
                            confidence="HIGH",
                            discovery_method="federal_register_api",
                            retrieved_sha256=pdf_record.sha256,
                            retrieval_time=pdf_record.retrieved_at,
                            original_observation_sha256=obs_sha,
                            publisher=(
                                "Office of the Federal Register"
                            ),
                            retrieval_host="www.govinfo.gov",
                            manual_review_required=False,
                        )
                        recovered = True

            row["attempts"] = row.get("attempts", 0) + 1
            row["last_attempt_at"] = utc_now()
            if recovered:
                row["state"] = "RECOVERED_OFFICIAL_MIRROR"
                row["recovered_via"] = "govinfo"
            else:
                row["state"] = "RETRY_LATER"
                row["next_retry_after"] = (
                    datetime.now(timezone.utc) + RETRY_CADENCE
                ).isoformat()

        self.save_queue("federal-register", rows)

    def find_govinfo_pdf(self, docnum: str):
        needle = f"/{docnum}.pdf"
        for url, record in self.manifest_success.items():
            if "govinfo.gov" in url and url.endswith(needle):
                ctype = (record.get("content_type") or "").lower()
                if "pdf" in ctype:
                    return url, record
        return None, None

    # ================================================================
    # DOJ: probe, official feeds, then public web archive
    # ================================================================

    def probe_host(self, family: str, rows: list[dict]) -> bool:
        """Ordinary-retry probe: is the challenge still in force?

        Fetches up to PROBE_SAMPLE queued URLs once each. Returns True
        when at least one probe validated as real content (challenge
        lifted); False otherwise. Never more than PROBE_SAMPLE direct
        requests hit a still-challenged host in one run.
        """
        candidates = [r for r in rows
                      if r.get("state") in ("PENDING", "RETRY_LATER")]
        if not candidates:
            return False
        sample = candidates[:PROBE_SAMPLE]
        lifted = False
        for row in sample:
            record, body, ok, cls = self.polite_fetch(
                row["url"], "GOV-PUBLIC",
                f"{family} challenge probe",
                expect_family=family,
            )
            if record is None:
                break
            row["attempts"] = row.get("attempts", 0) + 1
            row["last_attempt_at"] = utc_now()
            if ok:
                lifted = True
                self.add_link(
                    original_url=row["url"],
                    identity_id=row.get("identity_id"),
                    alternate_url=row["url"],
                    alternate_family=family,
                    relationship=DIRECT,
                    confidence="HIGH",
                    discovery_method="ordinary_retry_probe",
                    retrieved_sha256=record.sha256,
                    retrieval_time=record.retrieved_at,
                    original_observation_sha256=(
                        row.get("observation_sha256")
                    ),
                    publisher=family.upper(),
                    retrieval_host=(
                        urlparse(row["url"]).hostname or ""
                    ),
                    manual_review_required=False,
                )
                row["state"] = "RECOVERED_SAME_AGENCY"
                row["recovered_via"] = "ordinary_retry"
            else:
                self.stats["still_challenged_probes"] += 1
                print(
                    f"  probe still non-content "
                    f"({cls.kind if cls else 'no-fetch'}): "
                    f"{row['url'][:90]}"
                )
        return lifted

    def recover_doj(self) -> None:
        rows = self.load_queue("doj")
        if not rows:
            return
        pending = [r for r in rows
                   if r.get("state", "PENDING") in ("PENDING",
                                                    "RETRY_LATER")]
        print(f"\n=== DOJ: {len(rows)} queued, "
              f"{len(pending)} pending ===")
        if not pending:
            self.save_queue("doj", rows)
            return

        # Route 1: same-agency. One ordinary probe sample; if the
        # challenge has lifted, direct re-fetch is the best recovery
        # for every pending URL (budget permitting).
        lifted = self.probe_host("doj", rows)
        print(f"  challenge lifted: {lifted}")

        if lifted:
            for row in pending:
                if row.get("state") not in ("PENDING", "RETRY_LATER"):
                    continue
                if self.fetches >= self.args.max_fetches:
                    break
                record, body, ok, cls = self.polite_fetch(
                    row["url"], "GOV-PUBLIC", "DOJ direct recovery",
                    expect_family="doj",
                )
                if record is None:
                    break
                row["attempts"] = row.get("attempts", 0) + 1
                row["last_attempt_at"] = utc_now()
                if ok:
                    self.add_link(
                        original_url=row["url"],
                        identity_id=row.get("identity_id"),
                        alternate_url=row["url"],
                        alternate_family="doj",
                        relationship=DIRECT,
                        confidence="HIGH",
                        discovery_method="ordinary_retry",
                        retrieved_sha256=record.sha256,
                        retrieval_time=record.retrieved_at,
                        original_observation_sha256=(
                            row.get("observation_sha256")
                        ),
                        publisher="Department of Justice",
                        retrieval_host="www.justice.gov",
                        manual_review_required=False,
                    )
                    row["state"] = "RECOVERED_SAME_AGENCY"
                    row["recovered_via"] = "ordinary_retry"
        else:
            # Route 4 bookkeeping: direct retries wait out the cadence
            # window; no further direct requests hit the challenged
            # host this run.
            next_retry = (
                datetime.now(timezone.utc) + RETRY_CADENCE
            ).isoformat()
            for row in pending:
                if row.get("state") in ("PENDING", "RETRY_LATER"):
                    row["next_retry_after"] = next_retry

        # Route 3: public web archive, tier order, budget-capped.
        if self.args.network:
            by_priority = sorted(
                (r for r in pending
                 if r.get("state") in ("PENDING", "RETRY_LATER")),
                key=lambda r: (r.get("tier", 9), r["url"]),
            )
            for row in by_priority:
                if self.fetches + 2 > self.args.max_fetches:
                    break
                if "web.archive.org" in self.host_stopped:
                    break
                self.recover_via_wayback(row, "doj",
                                         "Department of Justice")

        self.save_queue("doj", rows)

    def recover_via_wayback(self, row: dict, family: str,
                            publisher: str) -> bool:
        """CDX lookup + raw snapshot fetch for one challenged URL."""
        url = row["url"]
        cdx_url = CDX_API.format(url=quote(url, safe=""))
        record, body, _ok, _cls = self.polite_fetch(
            cdx_url, "WEB-ARCHIVE", "Wayback CDX lookup",
            expect_family="web_archive",
        )
        if record is None or not body:
            return False
        row["attempts"] = row.get("attempts", 0) + 1
        row["last_attempt_at"] = utc_now()
        try:
            table = json.loads(body)
        except json.JSONDecodeError:
            # Inconclusive lookup (not a CDX answer) — leave the row
            # pending for a later run; never record it as "no
            # capture exists".
            return False
        snapshot = table[1] if len(table) > 1 else None
        if not snapshot:
            row["state"] = "NO_WEB_ARCHIVE_CAPTURE"
            return False

        timestamp = snapshot[0]
        snapshot_url = WAYBACK_RAW.format(timestamp=timestamp, url=url)
        snap_record, snap_body, ok, cls = self.polite_fetch(
            snapshot_url, "WEB-ARCHIVE",
            f"Wayback snapshot of {family} page",
            expect_family=family,
        )
        if snap_record is None:
            return False
        if not ok:
            row["state"] = "WEB_ARCHIVE_NON_CONTENT"
            return False

        self.add_link(
            original_url=url,
            identity_id=row.get("identity_id"),
            alternate_url=snapshot_url,
            alternate_family="web_archive",
            relationship=ARCHIVED_VERSION,
            confidence="MEDIUM",
            discovery_method=f"wayback_cdx:{timestamp}",
            retrieved_sha256=snap_record.sha256,
            retrieval_time=snap_record.retrieved_at,
            original_observation_sha256=row.get("observation_sha256"),
            publisher=publisher,
            retrieval_host="web.archive.org",
            manual_review_required=False,
        )
        row["state"] = "RECOVERED_WEB_ARCHIVE"
        row["recovered_via"] = "web_archive"
        return True

    # ================================================================
    # Congress / GAO
    # ================================================================

    def recover_congress(self) -> None:
        rows = self.load_queue("congress")
        if not rows:
            return
        print(f"\n=== Congress: {len(rows)} queued ===")
        if self.args.network:
            self.probe_host("congress", rows)
            for row in rows:
                if row.get("state") in ("PENDING", "RETRY_LATER"):
                    self.recover_via_wayback(
                        row, "congress", "U.S. Congress"
                    )
        self.save_queue("congress", rows)

    def recover_gao(self) -> None:
        rows = self.load_queue("gao")
        if not rows:
            return
        print(f"\n=== GAO: {len(rows)} queued ===")
        if self.args.network:
            self.probe_host("gao", rows)
            for row in rows:
                if row.get("state") in ("PENDING", "RETRY_LATER"):
                    self.recover_via_wayback(
                        row, "gao", "Government Accountability Office"
                    )
        self.save_queue("gao", rows)

    # ================================================================

    def run(self) -> None:
        self.recover_federal_register()
        if self.args.network:
            self.recover_doj()
            self.recover_congress()
            self.recover_gao()
        else:
            print("\n(offline mode: only manifest cross-reference "
                  "recovery performed; network routes skipped)")

        print("\n=== run stats ===")
        for key, value in self.stats.items():
            if key == "recovered_urls":
                print(f"  recovered_urls: {len(value)}")
            else:
                print(f"  {key}: {value}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="manifest.jsonl")
    parser.add_argument("--recovery-dir", default="recovery")
    parser.add_argument("--acquisition-dir", default="acquisition")
    parser.add_argument("--out", default="archive")
    parser.add_argument("--run-manifest",
                        default="run-manifest-recovery.jsonl")
    parser.add_argument("--delay", type=float, default=2.0)
    parser.add_argument("--max-fetches", type=int, default=1500,
                        help="Total network fetch budget for this run")
    parser.add_argument("--max-seconds", type=int, default=9000,
                        help="Wall-clock fetch budget; fetching stops "
                             "after this so the run always has time "
                             "to verify, publish, and commit")
    parser.add_argument("--max-bytes", type=int,
                        default=100 * 1024 * 1024)
    parser.add_argument("--network", action="store_true",
                        help="Enable network recovery routes; without "
                             "this only offline manifest "
                             "cross-referencing runs")
    parser.add_argument("--archive-fr-api", action="store_true",
                        help="Also archive the FR API JSON record for "
                             "documents already recovered via GovInfo")
    args = parser.parse_args()

    run = RecoveryRun(args)
    run.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
