#!/usr/bin/env python3
"""Detector tests: challenges are never content; thin genuine pages
are never falsely rejected; classification is never by size alone."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from challenge_detector import (  # noqa: E402
    ACCESS_INTERSTITIAL,
    APPLICATION_SHELL,
    BOT_CHALLENGE,
    ERROR_RESPONSE,
    REAL_CONTENT,
    REDIRECT_STUB,
    THIN_REAL_CONTENT,
    UNKNOWN_RESPONSE,
    classify_response,
    validate_content,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"

DOJ_URL = ("https://www.justice.gov/opa/pr/"
           "two-defendants-convicted-money-laundering-conspiracy")


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


class GenuineContent(unittest.TestCase):
    def test_doj_real_page_is_content(self):
        cls = classify_response(
            DOJ_URL, 200, "text/html; charset=utf-8",
            fixture("doj_real.html"),
        )
        self.assertEqual(cls.kind, REAL_CONTENT)
        ok, _ = validate_content(
            DOJ_URL, 200, "text/html", fixture("doj_real.html"),
        )
        self.assertTrue(ok)

    def test_thin_genuine_page_not_falsely_rejected(self):
        cls = classify_response(
            "https://www.fincen.gov/news/notice-filers", 200,
            "text/html", fixture("thin_real.html"),
        )
        self.assertIn(cls.kind, (REAL_CONTENT, THIN_REAL_CONTENT))
        self.assertTrue(cls.is_content)

    def test_pdf_magic_bytes_are_content(self):
        cls = classify_response(
            "https://www.govinfo.gov/content/pkg/FR-2024-09-30/pdf/"
            "2024-22197.pdf", 200, "application/pdf",
            fixture("sample.pdf"),
        )
        self.assertEqual(cls.kind, REAL_CONTENT)
        self.assertIn("pdf_magic_bytes", cls.signals)

    def test_fr_api_json_validates(self):
        url = ("https://www.federalregister.gov/api/v1/documents/"
               "2024-22197.json")
        ok, cls = validate_content(
            url, 200, "application/json",
            fixture("fr_api_record.json"),
            family="federal_register",
        )
        self.assertTrue(ok)


class Challenges(unittest.TestCase):
    def test_akamai_challenge_detected(self):
        cls = classify_response(
            DOJ_URL, 200, "text/html", fixture("akamai_challenge.html"),
        )
        self.assertEqual(cls.kind, BOT_CHALLENGE)
        self.assertEqual(cls.vendor, "akamai")
        self.assertFalse(cls.is_content)

    def test_akamai_challenge_never_validates_as_content(self):
        ok, cls = validate_content(
            DOJ_URL, 200, "text/html", fixture("akamai_challenge.html"),
        )
        self.assertFalse(ok)

    def test_cloudflare_challenge_detected(self):
        cls = classify_response(
            "https://www.example-agency.gov/page", 200, "text/html",
            fixture("cloudflare_challenge.html"),
        )
        self.assertEqual(cls.kind, BOT_CHALLENGE)
        self.assertEqual(cls.vendor, "cloudflare")

    def test_app_shell_detected(self):
        cls = classify_response(
            "https://www.gao.gov/reports-testimonies", 200,
            "text/html", fixture("app_shell.html"),
        )
        self.assertEqual(cls.kind, APPLICATION_SHELL)
        self.assertFalse(cls.is_content)

    def test_pdf_url_serving_challenge_html_not_content(self):
        url = "https://www.justice.gov/opa/press-release/file/1/dl.pdf"
        ok, cls = validate_content(
            url, 200, "text/html", fixture("akamai_challenge.html"),
        )
        self.assertFalse(ok)
        self.assertIn("expected_pdf_not_pdf", cls.signals)

    def test_redirect_to_unblock_endpoint_is_interstitial(self):
        cls = classify_response(
            "https://www.federalregister.gov/documents/2024/09/30/"
            "2024-22197/boi-access", None, None, b"",
            error=("redirect escaped allowlist: "
                   "https://unblock.federalregister.gov/"),
        )
        self.assertEqual(cls.kind, ACCESS_INTERSTITIAL)

    def test_meta_refresh_stub(self):
        body = (b"<html><head><meta http-equiv='refresh' "
                b"content='0;url=/somewhere-else'></head>"
                b"<body></body></html>")
        cls = classify_response(
            "https://www.example.gov/page", 200, "text/html", body,
        )
        self.assertEqual(cls.kind, REDIRECT_STUB)


class HttpErrors(unittest.TestCase):
    def test_plain_403_is_error_not_interstitial(self):
        cls = classify_response(
            "https://www.congress.gov/", 403, "text/html",
            b"<html><body>Forbidden</body></html>",
        )
        self.assertEqual(cls.kind, ERROR_RESPONSE)

    def test_403_with_challenge_markup_is_interstitial(self):
        cls = classify_response(
            "https://www.justice.gov/opa/pr/example", 403,
            "text/html", fixture("forbidden_interstitial.html"),
        )
        self.assertEqual(cls.kind, ACCESS_INTERSTITIAL)
        self.assertEqual(cls.vendor, "akamai")

    def test_429_is_error_response(self):
        cls = classify_response(
            "https://www.example.gov/x", 429, "text/html", b"slow down",
        )
        self.assertEqual(cls.kind, ERROR_RESPONSE)

    def test_ordinary_404(self):
        cls = classify_response(
            "https://www.fincen.gov/gone", 404, "text/html",
            b"<html><body>Not found</body></html>",
        )
        self.assertEqual(cls.kind, ERROR_RESPONSE)


class NeverBySizeAlone(unittest.TestCase):
    def test_tiny_html_without_signals_is_unknown_not_challenge(self):
        # Small alone must never produce BOT_CHALLENGE.
        cls = classify_response(
            "https://www.example.gov/tiny", 200, "text/html",
            b"<html><body><p>ok</p></body></html>",
        )
        self.assertEqual(cls.kind, UNKNOWN_RESPONSE)

    def test_host_pattern_evidence_upgrades_thin_html(self):
        cls = classify_response(
            "https://www.justice.gov/archives/x", 200, "text/html",
            b"<html><head><script src='/a/b.js'></script></head>"
            b"<body></body></html>",
            extra_signals=["host_challenge_pattern"],
        )
        self.assertEqual(cls.kind, BOT_CHALLENGE)

    def test_host_pattern_never_downgrades_real_content(self):
        cls = classify_response(
            DOJ_URL, 200, "text/html", fixture("doj_real.html"),
            extra_signals=["host_challenge_pattern"],
        )
        self.assertEqual(cls.kind, REAL_CONTENT)


if __name__ == "__main__":
    unittest.main()
