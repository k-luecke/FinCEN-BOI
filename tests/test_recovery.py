#!/usr/bin/env python3
"""Recovery pipeline invariants:

1. challenge responses are never counted as content;
2. genuine thin pages are not routed to recovery;
3. alternate-source recovery links retain provenance;
4. mirror recovery never overwrites original URL history;
5. retries never become evasive (probe cap, 429 host stop, cadence);
6. recovered objects satisfy SHA-256 durability rules.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import archive  # noqa: E402
import recover  # noqa: E402
from recover import RecoveryRun  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def manifest_row(url, sha=None, status=200, ctype="text/html",
                 length=2500, error=None, object_path=None):
    return {
        "record_id": hashlib.sha256(url.encode()).hexdigest()[:8],
        "retrieved_at": "2026-08-15T04:00:00+00:00",
        "url": url,
        "final_url": url if sha else None,
        "provenance": "GOV-PUBLIC",
        "source": None,
        "http_status": status if (sha or error is None) else status,
        "content_type": ctype if sha else None,
        "content_length": length if sha else None,
        "sha256": sha,
        "object_path": object_path,
        "error": error,
        "parent_url": None,
        "depth": 0,
    }


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def synthetic_corpus(root: Path):
    """Manifest with a tokenized-challenge host + one real thin page
    + a challenged FR document whose GovInfo PDF is archived."""
    rows = []
    # 60 DOJ 'successes': small html, every hash unique -> host pattern
    for i in range(60):
        url = f"https://www.justice.gov/opa/pr/case-{i:03d}-money-laundering"
        rows.append(manifest_row(
            url, sha=hashlib.sha256(f"tok{i}".encode()).hexdigest(),
            length=2500,
        ))
    # a genuine thin page on a healthy host
    rows.append(manifest_row(
        "https://www.fincen.gov/news/notice-filers",
        sha=hashlib.sha256(b"thin").hexdigest(), length=380,
    ))
    # challenged FR document (redirect to unblock)
    fr_url = ("https://www.federalregister.gov/documents/2024/09/30/"
              "2024-22197/boi-access-rule")
    rows.append(manifest_row(
        fr_url, status=None,
        error=("redirect escaped allowlist: "
               "https://unblock.federalregister.gov/"),
    ))
    # its official GovInfo PDF, already archived
    pdf_bytes = (FIXTURES / "sample.pdf").read_bytes()
    pdf_sha = hashlib.sha256(pdf_bytes).hexdigest()
    object_path = archive.store_object(root / "archive", pdf_sha,
                                       pdf_bytes)
    rows.append(manifest_row(
        "https://www.govinfo.gov/content/pkg/FR-2024-09-30/pdf/"
        "2024-22197.pdf",
        sha=pdf_sha, ctype="application/pdf", length=len(pdf_bytes),
        object_path=str(object_path),
    ))
    write_jsonl(root / "manifest.jsonl", rows)

    inventory = [{
        "url": fr_url,
        "discovered_via": "federal-register-api",
        "document_number": "2024-22197",
        "title": "Beneficial Ownership Information Access Rule",
        "publication_date": "2024-09-30",
        "host": "www.federalregister.gov",
    }]
    write_jsonl(root / "url-inventory.jsonl", inventory)
    return fr_url, pdf_sha


def run_scan(root: Path):
    return subprocess.run(
        [sys.executable, str(ROOT / "challenge_scan.py"),
         "--manifest", str(root / "manifest.jsonl"),
         "--inventory", str(root / "url-inventory.jsonl"),
         "--recovery-dir", str(root / "recovery"),
         "--acquisition-dir", str(root / "acquisition")],
        capture_output=True, text=True, cwd=ROOT, check=True,
    )


def recovery_args(root: Path, network=False, max_fetches=10):
    return argparse.Namespace(
        manifest=str(root / "manifest.jsonl"),
        recovery_dir=str(root / "recovery"),
        acquisition_dir=str(root / "acquisition"),
        out=str(root / "archive"),
        run_manifest=str(root / "run-manifest.jsonl"),
        delay=0.0,
        max_fetches=max_fetches,
        max_seconds=9000,
        max_bytes=10 * 1024 * 1024,
        network=network,
        archive_fr_api=False,
    )


def load_jsonl(path: Path):
    if not path.exists():
        return []
    return [json.loads(line) for line in
            path.read_text().splitlines() if line.strip()]


class PipelineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.fr_url, self.pdf_sha = synthetic_corpus(self.root)
        run_scan(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    # -- invariant 1 + 2 --------------------------------------------

    def test_challenges_are_not_content_and_thin_pages_survive(self):
        observations = load_jsonl(
            self.root / "recovery" / "challenge-observations.jsonl"
        )
        urls = {o["url"] for o in observations}
        # every tokenized DOJ URL routed to recovery
        self.assertEqual(
            sum(1 for o in observations
                if o["source_family"] == "doj"
                and o["classification"] == "BOT_CHALLENGE"),
            60,
        )
        # the genuine thin FinCEN page was NOT flagged
        self.assertNotIn(
            "https://www.fincen.gov/news/notice-filers", urls
        )
        # FR challenged doc classified as interstitial
        fr = [o for o in observations if o["url"] == self.fr_url]
        self.assertEqual(len(fr), 1)
        self.assertEqual(fr[0]["classification"],
                         "ACCESS_INTERSTITIAL")

    # -- invariant 3 + 6 --------------------------------------------

    def test_official_mirror_link_retains_provenance_and_sha(self):
        run = RecoveryRun(recovery_args(self.root))
        run.recover_federal_register()

        links = load_jsonl(
            self.root / "recovery" / "recovery-links.jsonl"
        )
        self.assertEqual(len(links), 1)
        link = links[0]
        self.assertEqual(link["original_url"], self.fr_url)
        self.assertEqual(link["relationship"], "OFFICIAL_MIRROR")
        self.assertEqual(link["retrieved_sha256"], self.pdf_sha)
        self.assertEqual(link["retrieval_host"], "www.govinfo.gov")
        self.assertEqual(link["publisher"],
                         "Office of the Federal Register")
        self.assertFalse(link["manual_review_required"])
        self.assertIsNotNone(link["document_identity"])

        # SHA-256 durability: the linked object's stored bytes hash
        # to exactly the recorded digest.
        stored = (self.root / "archive" / "objects" / "sha256" /
                  self.pdf_sha[:2] / self.pdf_sha[2:])
        self.assertTrue(stored.exists())
        self.assertEqual(
            hashlib.sha256(stored.read_bytes()).hexdigest(),
            self.pdf_sha,
        )

    def test_recovery_is_idempotent(self):
        for _ in range(2):
            run = RecoveryRun(recovery_args(self.root))
            run.recover_federal_register()
        links = load_jsonl(
            self.root / "recovery" / "recovery-links.jsonl"
        )
        self.assertEqual(len(links), 1)

    # -- invariant 4 ------------------------------------------------

    def test_mirror_recovery_preserves_original_history(self):
        before = (self.root / "manifest.jsonl").read_text()
        observations_before = (
            self.root / "recovery" / "challenge-observations.jsonl"
        ).read_text()

        run = RecoveryRun(recovery_args(self.root))
        run.recover_federal_register()

        # Original manifest untouched; challenge observation retained.
        self.assertEqual(
            (self.root / "manifest.jsonl").read_text(), before
        )
        self.assertEqual(
            (self.root / "recovery" /
             "challenge-observations.jsonl").read_text(),
            observations_before,
        )
        # Re-running the scan must keep recovered queue state.
        run_scan(self.root)
        queue = load_jsonl(
            self.root / "acquisition" /
            "federal-register-recovery-queue.jsonl"
        )
        fr_rows = [r for r in queue if r["url"] == self.fr_url]
        self.assertEqual(fr_rows[0]["state"],
                         "RECOVERED_OFFICIAL_MIRROR")

    # -- invariant 5 ------------------------------------------------

    def test_probe_is_bounded_and_still_challenged_host_backs_off(self):
        run = RecoveryRun(recovery_args(self.root, network=True))
        challenge_body = (FIXTURES / "akamai_challenge.html").read_bytes()

        calls = []

        def fake_fetch(url, provenance, source, expect_family=None):
            calls.append(url)
            record = archive.Record(
                record_id="x", retrieved_at=archive.utc_now(),
                url=url, final_url=url, provenance=provenance,
                source=source, http_status=200,
                content_type="text/html",
                content_length=len(challenge_body),
                sha256=hashlib.sha256(challenge_body).hexdigest(),
                object_path=None, error=None,
            )
            from challenge_detector import validate_content
            ok, cls = validate_content(
                url, 200, "text/html", challenge_body,
                family=expect_family,
            )
            return record, challenge_body, ok, cls

        with mock.patch.object(run, "polite_fetch",
                               side_effect=fake_fetch):
            rows = run.load_queue("doj")
            lifted = run.probe_host("doj", rows)

        self.assertFalse(lifted)
        # Never more than PROBE_SAMPLE direct requests hit a
        # still-challenged host.
        self.assertLessEqual(len(calls), recover.PROBE_SAMPLE)

        # And the full DOJ flow sets a retry cadence instead of
        # hammering: pending rows gain next_retry_after.
        with mock.patch.object(run, "polite_fetch",
                               side_effect=fake_fetch):
            run.recover_doj()
        queue = load_jsonl(
            self.root / "acquisition" / "doj-recovery-queue.jsonl"
        )
        pending = [r for r in queue
                   if r["state"] in ("PENDING", "RETRY_LATER")]
        self.assertTrue(pending)
        self.assertTrue(
            all(r.get("next_retry_after") for r in pending)
        )

    def test_429_stops_host_for_run(self):
        run = RecoveryRun(recovery_args(self.root, network=True))

        def fake_fetch_429(request, url, record_id, provenance,
                           source, out, manifest, allowed_hosts,
                           max_bytes, parent_url, depth):
            raise archive._Retryable(
                Exception("429"), status=429, retry_after=None
            )

        with mock.patch.object(archive, "_fetch_once",
                               side_effect=fake_fetch_429), \
             mock.patch.object(archive.time, "sleep"):
            record, body, ok, cls = run.polite_fetch(
                "https://www.justice.gov/opa/pr/x", "GOV-PUBLIC",
                "test", expect_family="doj",
            )
        self.assertEqual(record.http_status, 429)
        self.assertIn("www.justice.gov", run.host_stopped)
        # Subsequent fetches to the stopped host are refused locally.
        record2, *_ = run.polite_fetch(
            "https://www.justice.gov/opa/pr/y", "GOV-PUBLIC", "test",
        )
        self.assertIsNone(record2)

    def test_degraded_host_is_stopped_after_repeated_failures(self):
        # A host failing at the transport layer (timeouts/TLS/5xx) is
        # stopped for the run instead of being knocked for hours.
        run = RecoveryRun(recovery_args(self.root, network=True))

        def fake_timeout(request, url, record_id, provenance,
                         source, out, manifest, allowed_hosts,
                         max_bytes, parent_url, depth):
            raise archive._Retryable(TimeoutError("timed out"))

        with mock.patch.object(archive, "_fetch_once",
                               side_effect=fake_timeout), \
             mock.patch.object(archive.time, "sleep"):
            for i in range(recover.MAX_TRANSPORT_FAILURES_PER_HOST):
                record, *_ = run.polite_fetch(
                    f"https://web.archive.org/web/x{i}",
                    "WEB-ARCHIVE", "test",
                )
                self.assertIsNotNone(record)

        self.assertIn("web.archive.org", run.host_stopped)
        record, *_ = run.polite_fetch(
            "https://web.archive.org/web/y", "WEB-ARCHIVE", "test",
        )
        self.assertIsNone(record)
        # Other hosts are unaffected.
        self.assertNotIn("www.govinfo.gov", run.host_stopped)

    def test_fetch_budget_is_enforced(self):
        run = RecoveryRun(recovery_args(self.root, network=True,
                                        max_fetches=0))
        record, *_ = run.polite_fetch(
            "https://www.justice.gov/opa/pr/x", "GOV-PUBLIC", "test",
        )
        self.assertIsNone(record)


class ReportTest(unittest.TestCase):
    def test_report_states_and_identity_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            synthetic_corpus(root)
            run_scan(root)
            run = RecoveryRun(recovery_args(root))
            run.recover_federal_register()
            result = subprocess.run(
                [sys.executable, str(ROOT / "recovery_report.py"),
                 "--recovery-dir", str(root / "recovery"),
                 "--acquisition-dir", str(root / "acquisition"),
                 "--report", str(root / "RECOVERY-REPORT.md")],
                capture_output=True, text=True, cwd=ROOT, check=True,
            )
            metrics = json.loads(
                (root / "recovery" / "metrics.json").read_text()
            )
            url_cov = metrics["requested_url_coverage"]
            # Challenges never counted as ARCHIVED_CONTENT.
            self.assertNotIn("ARCHIVED_CONTENT", url_cov)
            self.assertEqual(url_cov.get("UNRESOLVED_CHALLENGE"), 60)
            self.assertEqual(
                url_cov.get("RECOVERED_OFFICIAL_MIRROR"), 1
            )
            self.assertTrue(
                (root / "RECOVERY-REPORT.md").exists()
            )
            unresolved = load_jsonl(
                root / "recovery" / "unresolved-challenges.jsonl"
            )
            self.assertEqual(len(unresolved), 60)


if __name__ == "__main__":
    unittest.main()
