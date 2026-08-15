#!/usr/bin/env python3
"""
Content-sample audit of archived objects for one host.

Answers "are these preserved bytes evidence, or technical noise?"
before spending the acquisition window expanding a host. Classifies a
sample of objects into:

    REAL_CONTENT        substantive page text
    THIN_REAL_PAGE      little text, but real content
    REDIRECT_STUB       meta-refresh / tiny redirect page
    BOT_CHALLENGE       JS-challenge / access-denied interstitial
    APPLICATION_SHELL   JS app skeleton with no server-rendered text
    ERROR_RESPONSE      error page served with HTTP 200
    OTHER / MISSING

Never deletes anything — observations already preserved stay
preserved; this informs whether to keep expanding the host.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

CHALLENGE_MARKERS = [
    "enable javascript", "javascript is required", "javascript disabled",
    "access denied", "request unsuccessful", "pardon our interruption",
    "checking your browser", "verify you are a human", "captcha",
    "akamai", "incapsula", "imperva", "cloudflare", "distil",
    "bot detection", "unusual traffic",
]

ERROR_MARKERS = [
    "page not found", "404", "not available", "error has occurred",
    "temporarily unavailable",
]

TAG_RE = re.compile(rb"<[^>]+>")
SCRIPT_RE = re.compile(rb"<(script|style)[^>]*>.*?</\1>", re.S | re.I)


def visible_text(data: bytes) -> bytes:
    return TAG_RE.sub(b" ", SCRIPT_RE.sub(b" ", data))


def classify(data: bytes) -> str:
    low = data[:200000].lower()

    for marker in CHALLENGE_MARKERS:
        if marker.encode() in low:
            return "BOT_CHALLENGE"

    if b"http-equiv" in low and b"refresh" in low and len(data) < 4096:
        return "REDIRECT_STUB"

    text = b" ".join(visible_text(data).split())

    title = b""
    m = re.search(rb"<title[^>]*>(.*?)</title>", low, re.S)
    if m:
        title = m.group(1)

    for marker in ERROR_MARKERS:
        if marker.encode() in title:
            return "ERROR_RESPONSE"

    if len(text) < 200:
        if b"<div id=" in low or b"<noscript" in low or b"window." in low:
            return "APPLICATION_SHELL"
        return "REDIRECT_STUB" if len(data) < 2048 else "OTHER"

    if len(text) < 800:
        return "THIN_REAL_PAGE"

    return "REAL_CONTENT"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="manifest.jsonl")
    parser.add_argument("--root", default=".")
    parser.add_argument("--host", required=True)
    parser.add_argument("--max-size", type=int, default=4096)
    parser.add_argument("--sample", type=int, default=150)
    args = parser.parse_args()

    candidates = []

    with open(args.manifest, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue

            record = json.loads(line)

            if (
                record.get("sha256")
                and args.host in record.get("url", "")
                and (record.get("content_length") or 0) <= args.max_size
            ):
                candidates.append(record)

    if not candidates:
        print(f"No archived objects <= {args.max_size}B for {args.host}")
        return 1

    rng = random.Random(20260815)
    sample = rng.sample(candidates, min(args.sample, len(candidates)))

    counts = Counter()
    examples = defaultdict(list)

    for record in sample:
        path = Path(args.root) / record["object_path"]

        if not path.exists():
            counts["MISSING"] += 1
            continue

        label = classify(path.read_bytes())
        counts[label] += 1

        if len(examples[label]) < 3:
            examples[label].append(record["url"])

    total = sum(counts.values())
    print(f"Sampled {total} of {len(candidates)} objects "
          f"<= {args.max_size}B on {args.host}:")

    for label, n in counts.most_common():
        print(f"  {label}: {n} ({100 * n // total}%)")

        for url in examples[label]:
            print(f"      e.g. {url[:100]}")

    noise = sum(
        counts[k] for k in
        ("BOT_CHALLENGE", "APPLICATION_SHELL", "REDIRECT_STUB",
         "ERROR_RESPONSE", "MISSING")
    )
    verdict = "NOISY" if noise > total / 2 else "MOSTLY_REAL"
    print(f"VERDICT: {verdict} ({noise}/{total} non-evidentiary)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
