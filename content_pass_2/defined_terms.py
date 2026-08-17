"""In-document defined-term extraction.

Legal and corporate documents define short references once and use them
throughout: `Wells Fargo Bank, N.A. ("WFB" or the "Bank")`,
`Xinjiang Production and Construction Corps (XPCC)`,
`Jason T. Irby ("Irby")`. This pass extracts those definitions per
document so the graph builder can resolve document-scoped short names
("the Bank", "WFB", "Irby") to the full party name — conservative by
construction:

- resolution is strictly per-document (a term never crosses documents);
- a term defined twice with different full names in one document is
  AMBIGUOUS and resolves nothing (counted, recorded);
- full names are trimmed at sentence boundaries and validated; junk
  captures are dropped rather than guessed.

Writes content-pass-2/defined-terms.jsonl:
  {"sha256":…, "term":…, "term_key":…, "full_name":…, "kind":…,
   "ambiguous": bool}

Usage: python3 -m content_pass_2.defined_terms
"""
from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from content_pass_1.common import text_disk_path  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OBS = os.path.join(REPO, "content-pass-2", "raw-observations.jsonl")
OUT = os.path.join(REPO, "content-pass-2", "defined-terms.jsonl")

# Full name followed by a parenthetical containing one or more quoted
# defined terms: X, N.A. ("WFB" or the "Bank").
PAREN_RE = re.compile(
    r"(?P<full>[^()\n]{4,90}?)\s*\((?P<body>[^()]{2,120})\)")
QUOTED_TERM_RE = re.compile(
    r"[\"“']\s*(?:the\s+)?(?P<term>[A-Z][A-Za-z&.\- ]{0,35}?)\s*[\"”']")
# Acronym definition: Xinjiang Production and Construction Corps (XPCC)
ACR_BODY_RE = re.compile(r"^\s*(?:the\s+)?(?P<acr>[A-Z]{2,6})\s*$")
_SENT_SPLIT_RE = re.compile(r"(?<=[a-z0-9®™\"”])[.!?]\s+(?=[A-Z(])")
_STOPTOK = {"of", "the", "and", "de", "la", "for", "&"}

_norm_ws = re.compile(r"\s+")


def norm_key(s):
    n = _norm_ws.sub(" ", s).strip(" ,;:.").lower()
    n = re.sub(r"[.,’'\"“”]", "", n)
    n = re.sub(r"\bincorporated\b", "inc", n)
    n = re.sub(r"\blimited\b", "ltd", n)
    n = re.sub(r"\bcorporation\b", "corp", n)
    n = re.sub(r"\bcompany\b", "co", n)
    n = re.sub(r"\bl\s?l\s?c\b", "llc", n)
    n = re.sub(r"\bnational association\b", "na", n)
    n = re.sub(r"^the\s+", "", n)
    return n


def clean_full(s):
    """Trim a captured full name to its own sentence and validate."""
    parts = _SENT_SPLIT_RE.split(s)
    s = parts[-1]
    s = _norm_ws.sub(" ", s).strip(" ,;:—-")
    # drop any leading fragment before the name proper
    words = s.split()
    while words and not (words[0][:1].isupper() or words[0][:1].isdigit()):
        words.pop(0)
    s = " ".join(words).strip(" ,;:").rstrip("®™")
    # trailing jurisdiction appositive: "X, Inc., a Maryland corporation"
    s = re.sub(r",\s*an?\s+[A-Z]?[a-z]+(?:\s+[A-Z]?[a-z]+){0,2}\s+"
               r"(?:corporation|company|limited\s+liability\s+company|bank|"
               r"association|partnership)$", "", s, flags=re.I).strip(" ,;:")
    if not (4 <= len(s) <= 90) or not re.search(r"[A-Za-z]{3}", s):
        return None
    if s.lower().startswith(("see ", "under ", "pursuant ", "section ",
                             "item ", "note ", "as ", "in ", "each ")):
        return None
    return s


_CLAUSE_STARTS = {"however", "any", "all", "per", "also", "additionally",
                  "according", "although", "while", "where", "since",
                  "because", "if", "when", "this", "these", "those", "such",
                  "both", "further", "moreover", "additional", "certain"}


def namelike(s):
    """Proper-noun-majority run that starts like a name, not a clause."""
    toks = s.split()
    if not toks or len(toks) > 8:
        return False
    first = re.sub(r"\W", "", toks[0]).lower()
    if first in _CLAUSE_STARTS or first.isdigit():
        return False
    capped = sum(1 for t in toks if t[:1].isupper() or t.isupper()
                 or t.lower() in _STOPTOK)
    return capped / len(toks) >= 0.6


def acronym_tail(full, acr):
    """The trailing tokens of `full` whose initials spell `acr`, or None.
    Trims clause glue: "…stated the Office of the Chief Procurement
    Officer" + OCPO -> "Office of the Chief Procurement Officer"."""
    toks = full.split()
    need = list(acr.upper())
    picked = []
    for t in reversed(toks):
        picked.append(t)
        if t.lower() not in _STOPTOK and t[:1].isalpha():
            if not need or t[0].upper() != need[-1]:
                return None
            need.pop()
            if not need:
                break
    if need:
        return None
    tail = " ".join(reversed(picked))
    return tail if namelike(tail) else None


def extract_terms(text):
    """{term_key: {"term":…, "full":…, "kind":…}} — ambiguous keys removed."""
    found = {}
    ambiguous = set()

    def add(term, full, kind):
        key = norm_key(term)
        fkey = norm_key(full)
        if not key or not fkey or key == fkey or len(key) < 2:
            return
        if len(term.split()) > 4:
            return
        prev = found.get(key)
        if prev and norm_key(prev["full"]) != fkey:
            ambiguous.add(key)
            return
        found[key] = {"term": term, "full": full, "kind": kind}

    for m in PAREN_RE.finditer(text):
        body = m.group("body")
        full = clean_full(m.group("full"))
        if not full:
            continue
        am = ACR_BODY_RE.match(body)
        if am:
            acr = am.group("acr")
            tail = acronym_tail(full, acr)
            if tail:
                add(acr, tail, "acronym")
            continue
        if not namelike(full):
            continue
        for qm in QUOTED_TERM_RE.finditer(body):
            add(qm.group("term"), full, "quoted-definition")

    for key in ambiguous:
        found.pop(key, None)
    return found, len(ambiguous)


def main():
    shas = set()
    with open(OBS, encoding="utf-8") as fh:
        for line in fh:
            o = json.loads(line)
            if o.get("source_sha256"):
                shas.add(o["source_sha256"])

    n_terms = n_docs = n_amb = 0
    with open(OUT, "w", encoding="utf-8") as out:
        for sha in sorted(shas):
            try:
                text = open(text_disk_path(sha), encoding="utf-8").read()
            except OSError:
                continue
            terms, amb = extract_terms(text)
            n_amb += amb
            if terms:
                n_docs += 1
            for key in sorted(terms):
                t = terms[key]
                n_terms += 1
                out.write(json.dumps(
                    {"sha256": sha, "term": t["term"], "term_key": key,
                     "full_name": t["full"], "kind": t["kind"],
                     "ambiguous": False}, sort_keys=True) + "\n")

    print(f"defined_terms: {n_terms} definitions in {n_docs} documents "
          f"({n_amb} ambiguous terms dropped) -> {OUT}")


if __name__ == "__main__":
    main()
