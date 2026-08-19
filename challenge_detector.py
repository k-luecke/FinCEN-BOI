#!/usr/bin/env python3
"""
Challenge-aware response classification.

A 200 response is not content. This module classifies a retrieval
outcome into explicit non-content states so that bot challenges,
interstitials, and application shells are never counted as captured
public records — and genuine thin pages are never falsely rejected.

Classifications:

    REAL_CONTENT            validated document/page content
    THIN_REAL_CONTENT       validated content, unusually small
    BOT_CHALLENGE           anti-automation challenge page
    ACCESS_INTERSTITIAL     access-control interstitial (e.g. a 403
                            with challenge markup, or a redirect to an
                            unblock endpoint)
    APPLICATION_SHELL       JS bootstrap shell without server-rendered
                            content
    REDIRECT_STUB           meta-refresh/JS redirect page, no content
    ERROR_RESPONSE          plain HTTP error (404/410/5xx/429/...)
    UNKNOWN_RESPONSE        cannot be confidently classified

Design rules:

- Multiple signals; never classify on byte size alone.
- The original response is an observation to preserve, not to delete.
- Detection never triggers evasion: a BOT_CHALLENGE result routes to
  alternate-source resolution, not to challenge solving.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

DETECTOR_VERSION = "1.0.0"

REAL_CONTENT = "REAL_CONTENT"
THIN_REAL_CONTENT = "THIN_REAL_CONTENT"
BOT_CHALLENGE = "BOT_CHALLENGE"
ACCESS_INTERSTITIAL = "ACCESS_INTERSTITIAL"
APPLICATION_SHELL = "APPLICATION_SHELL"
REDIRECT_STUB = "REDIRECT_STUB"
ERROR_RESPONSE = "ERROR_RESPONSE"
UNKNOWN_RESPONSE = "UNKNOWN_RESPONSE"

NON_CONTENT = {
    BOT_CHALLENGE,
    ACCESS_INTERSTITIAL,
    APPLICATION_SHELL,
    REDIRECT_STUB,
    ERROR_RESPONSE,
    UNKNOWN_RESPONSE,
}

# Vendor challenge fingerprints. Matched case-insensitively against the
# body. Presence of any vendor marker on a small/contentless page is a
# strong challenge signal; on a full content page it may just be the
# site's bot-management JS tag, so markers alone are never decisive.
VENDOR_MARKERS = {
    "akamai": (
        "_abck", "bm-verify", "ak_bmsc", "bazadebezolkohpepadr",
        "/akam/", "akamai", "sec-cpt", "bm_sz",
    ),
    "cloudflare": (
        "cf-browser-verification", "__cf_chl", "challenge-platform",
        "checking your browser", "just a moment", "cf_chl_opt",
        "turnstile", "cdn-cgi/challenge",
    ),
    "perimeterx": ("_pxhd", "px-captcha", "perimeterx", "_pxvid"),
    "imperva": ("_incapsula_resource", "incapsula", "imperva"),
    "datadome": ("datadome",),
    "aws-waf": ("awswaf", "aws-waf-token", "challenge.js#"),
}

GENERIC_CHALLENGE_PHRASES = (
    "access denied",
    "request unsuccessful",
    "pardon our interruption",
    "verify you are human",
    "verifying you are human",
    "are you a robot",
    "unusual traffic",
    "enable javascript and cookies to continue",
    "please enable cookies",
    "captcha",
    "bot detection",
    "automated access to this site has been blocked",
    "your request has been blocked",
    "browser check",
    "checking if the site connection is secure",
)

# Hosts that are themselves access-control interstitial endpoints; a
# redirect into one of these is an ACCESS_INTERSTITIAL observation.
INTERSTITIAL_HOST_MARKERS = (
    "unblock.",
    "block.",
    "challenge.",
    "captcha.",
    "validate.perfdrive.com",
)

DOCUMENT_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".xml": "xml",
    ".json": "json",
    ".zip": "zip",
    ".csv": "csv",
    ".xlsx": "spreadsheet",
    ".docx": "word",
}

_TAG_RE = re.compile(rb"<script[^>]*>.*?</script>|<style[^>]*>.*?</style>",
                     re.IGNORECASE | re.DOTALL)
_HTML_RE = re.compile(rb"<[^>]+>")
_TITLE_RE = re.compile(rb"<title[^>]*>(.*?)</title>",
                       re.IGNORECASE | re.DOTALL)
_META_REFRESH_RE = re.compile(
    rb"""<meta[^>]+http-equiv\s*=\s*["']?refresh["']?[^>]*>""",
    re.IGNORECASE,
)
_URL_IN_REFRESH_RE = re.compile(rb"url\s*=\s*([^\"'>\s]+)", re.IGNORECASE)


@dataclass
class Classification:
    kind: str
    signals: list[str] = field(default_factory=list)
    vendor: str | None = None
    confidence: str = "MEDIUM"      # HIGH | MEDIUM | LOW
    detector_version: str = DETECTOR_VERSION

    @property
    def is_content(self) -> bool:
        return self.kind in (REAL_CONTENT, THIN_REAL_CONTENT)

    @property
    def fingerprint(self) -> str:
        parts = [self.kind]
        if self.vendor:
            parts.append(f"vendor:{self.vendor}")
        parts.extend(sorted(self.signals))
        return "|".join(parts)


def visible_text(body: bytes) -> bytes:
    """Body with scripts/styles/tags stripped — rough visible text."""
    stripped = _TAG_RE.sub(b" ", body)
    stripped = _HTML_RE.sub(b" ", stripped)
    return b" ".join(stripped.split())


def page_title(body: bytes) -> str:
    match = _TITLE_RE.search(body)
    if not match:
        return ""
    return b" ".join(match.group(1).split()).decode(
        "utf-8", errors="replace"
    ).strip()


def expected_content_kind(url: str) -> str | None:
    """What the URL's extension promises, if anything."""
    path = urlparse(url).path.lower()
    for extension, kind in DOCUMENT_EXTENSIONS.items():
        if path.endswith(extension):
            return kind
    return None


def _vendor_hits(lowered: bytes) -> tuple[str | None, list[str]]:
    for vendor, markers in VENDOR_MARKERS.items():
        hits = [m for m in markers if m.encode() in lowered]
        if hits:
            return vendor, [f"vendor_marker:{vendor}:{h}" for h in hits]
    return None, []


def _generic_hits(lowered: bytes) -> list[str]:
    return [
        f"challenge_phrase:{p}"
        for p in GENERIC_CHALLENGE_PHRASES
        if p.encode() in lowered
    ]


def _meta_refresh_target(body: bytes) -> str | None:
    match = _META_REFRESH_RE.search(body)
    if not match:
        return None
    url_match = _URL_IN_REFRESH_RE.search(match.group(0))
    return url_match.group(1).decode("utf-8", "replace") if url_match else ""


def _interstitial_host(url: str | None) -> bool:
    if not url:
        return False
    host = (urlparse(url).hostname or "").lower()
    return any(host.startswith(m) or m in host
               for m in INTERSTITIAL_HOST_MARKERS)


def _looks_like_app_shell(body: bytes, text: bytes) -> list[str]:
    signals = []
    lowered = body.lower()
    if len(text) < 400:
        for marker in (b'id="root"', b"id='root'", b'id="app"',
                       b"id='app'", b'ng-app', b'data-reactroot'):
            if marker in lowered:
                signals.append(
                    "app_shell_mount_point:"
                    + marker.decode("utf-8", "replace")
                )
                break
        script_count = lowered.count(b"<script")
        if script_count >= 2 and len(text) < 300:
            signals.append(f"script_heavy_thin_body:{script_count}")
    return signals


def classify_response(
    url: str,
    status: int | None,
    content_type: str | None,
    body: bytes | None,
    final_url: str | None = None,
    error: str | None = None,
    extra_signals: list[str] | None = None,
) -> Classification:
    """
    Classify one retrieval outcome.

    `extra_signals` lets a corpus-level scanner inject host-pattern
    evidence (e.g. "host_challenge_pattern") that a single response
    cannot see; such evidence can upgrade an UNKNOWN_RESPONSE to
    BOT_CHALLENGE but never downgrades detected content.
    """
    signals = list(extra_signals or [])
    body = body or b""
    lowered = body.lower()
    ctype = (content_type or "").lower()

    # --- redirect into an interstitial endpoint --------------------
    interstitial_redirect = _interstitial_host(final_url)
    if error and "redirect escaped allowlist" in error:
        target = error.split(":", 1)[1].strip() if ":" in error else ""
        if _interstitial_host(target):
            interstitial_redirect = True
    if interstitial_redirect:
        signals.append("redirect_to_interstitial_endpoint")
        return Classification(
            ACCESS_INTERSTITIAL, signals, confidence="HIGH"
        )

    # --- plain transport / HTTP errors -----------------------------
    if status is None and not body:
        signals.append(f"transport_error:{(error or 'unknown')[:60]}")
        return Classification(ERROR_RESPONSE, signals, confidence="HIGH")

    vendor, vendor_signals = _vendor_hits(lowered)
    generic_signals = _generic_hits(lowered)

    if status in (401, 403):
        signals.append(f"http_status:{status}")
        if vendor_signals or generic_signals:
            signals += vendor_signals + generic_signals
            return Classification(
                ACCESS_INTERSTITIAL, signals, vendor, confidence="HIGH"
            )
        return Classification(ERROR_RESPONSE, signals, confidence="HIGH")

    if status is not None and (status >= 400 or status == 429):
        signals.append(f"http_status:{status}")
        return Classification(ERROR_RESPONSE, signals, confidence="HIGH")

    # --- expected binary/document formats --------------------------
    expected = expected_content_kind(url)
    if expected == "application/pdf":
        if body.startswith(b"%PDF-"):
            signals.append("pdf_magic_bytes")
            return Classification(
                REAL_CONTENT, signals, confidence="HIGH"
            )
        signals.append("expected_pdf_not_pdf")
        if "html" in ctype:
            signals.append("expected_document_got_html")

    text = visible_text(body)
    is_html = "html" in ctype or b"<html" in lowered[:2000]

    # --- challenge markers ------------------------------------------
    if is_html and (vendor_signals or generic_signals):
        signals += vendor_signals + generic_signals
        # Vendor/challenge markers on a page without meaningful visible
        # text are decisive; on a large real page they are just the
        # site's bot-management tag.
        if len(text) < 600:
            signals.append(f"thin_visible_text:{len(text)}")
            return Classification(
                BOT_CHALLENGE, signals, vendor, confidence="HIGH"
            )
        if vendor and len(text) < 1500:
            return Classification(
                BOT_CHALLENGE, signals, vendor, confidence="MEDIUM"
            )
        # fall through: markers present but page has real text

    # --- redirect stubs ---------------------------------------------
    if is_html:
        refresh_target = _meta_refresh_target(body)
        if refresh_target is not None and len(text) < 300:
            signals.append(f"meta_refresh:{refresh_target[:80]}")
            if _interstitial_host(refresh_target):
                signals.append("meta_refresh_to_interstitial")
                return Classification(
                    ACCESS_INTERSTITIAL, signals, vendor,
                    confidence="HIGH",
                )
            return Classification(
                REDIRECT_STUB, signals, confidence="HIGH"
            )

    # --- expected document, got thin html ---------------------------
    if expected and is_html:
        signals.append("expected_document_got_html")
        if len(text) < 600:
            signals.append(f"thin_visible_text:{len(text)}")
            return Classification(
                BOT_CHALLENGE, signals, vendor, confidence="MEDIUM"
            )

    # --- application shells -----------------------------------------
    if is_html:
        shell_signals = _looks_like_app_shell(body, text)
        if shell_signals:
            signals += shell_signals
            return Classification(
                APPLICATION_SHELL, signals, confidence="MEDIUM"
            )

    # --- corpus-level evidence injected by the scanner --------------
    if "host_challenge_pattern" in signals and is_html and len(text) < 600:
        signals.append(f"thin_visible_text:{len(text)}")
        return Classification(
            BOT_CHALLENGE, signals, vendor, confidence="MEDIUM"
        )

    # --- content ----------------------------------------------------
    if not is_html and body:
        # Non-HTML bytes matching (or absent) declared type: content.
        signals.append(f"non_html_body:{ctype or 'unknown'}")
        return Classification(REAL_CONTENT, signals, confidence="MEDIUM")

    if is_html:
        title = page_title(body)
        if len(text) >= 600:
            signals.append(f"visible_text:{len(text)}")
            return Classification(REAL_CONTENT, signals, confidence="HIGH")
        if len(text) >= 150 and title:
            # Small but has a title and real sentences — genuine thin
            # pages (short notices, stubs) must not be falsely
            # rejected.
            signals.append(f"thin_but_titled:{title[:60]}")
            return Classification(
                THIN_REAL_CONTENT, signals, confidence="MEDIUM"
            )

    signals.append(f"unclassified_thin_response:{len(text)}")
    return Classification(UNKNOWN_RESPONSE, signals, confidence="LOW")


# ----------------------------------------------------------------------
# Family-specific content validation
# ----------------------------------------------------------------------

def source_family(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if "justice.gov" in host:
        return "doj"
    if "federalregister.gov" in host:
        return "federal_register"
    if "govinfo.gov" in host:
        return "govinfo"
    if "congress.gov" in host:
        return "congress"
    if "gao.gov" in host:
        return "gao"
    if "fincen.gov" in host:
        return "fincen"
    if "treasury.gov" in host:
        return "treasury"
    if "sec.gov" in host:
        return "sec"
    if "fbi.gov" in host:
        return "fbi"
    if "archive.org" in host:
        return "web_archive"
    return "other"


def validate_content(
    url: str,
    status: int | None,
    content_type: str | None,
    body: bytes | None,
    family: str | None = None,
    final_url: str | None = None,
    error: str | None = None,
    extra_signals: list[str] | None = None,
) -> tuple[bool, Classification]:
    """
    Family-aware validation gate for ARCHIVED_CONTENT.

    Returns (ok, classification). ok=True only when the response
    plausibly contains the requested public record; a 200 alone is
    never sufficient.
    """
    family = family or source_family(url)
    cls = classify_response(
        url, status, content_type, body, final_url, error, extra_signals
    )
    if not cls.is_content:
        return False, cls

    body = body or b""
    lowered = body.lower()

    if expected_content_kind(url) == "application/pdf":
        ok = body.startswith(b"%PDF-")
        if not ok:
            cls.kind = UNKNOWN_RESPONSE
            cls.signals.append("family_check:pdf_signature_missing")
        return ok, cls

    if family == "doj" and "html" in (content_type or "").lower():
        # A DOJ article/press-release page carries server-rendered
        # article markup; the Akamai interstitial carries none.
        markers = (b"<article", b'property="og:title"', b"usa-banner",
                   b"node--", b"field--name-body", b"press-release")
        if not any(m in lowered for m in markers):
            cls.signals.append("family_check:doj_article_markup_missing")
            if len(visible_text(body)) < 600:
                cls.kind = UNKNOWN_RESPONSE
                return False, cls
    if family == "federal_register":
        if url.endswith(".json") or "json" in (content_type or "").lower():
            ok = lowered.lstrip().startswith((b"{", b"["))
            if not ok:
                cls.kind = UNKNOWN_RESPONSE
                cls.signals.append("family_check:fr_api_not_json")
            return ok, cls
    return True, cls
