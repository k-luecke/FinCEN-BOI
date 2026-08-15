"""Parts II–V, IX, XIII–XV — raw observation extraction (Tiers A–E).

Consumes Pass 1 candidate spans from the tier buckets, restricted to the
Part IV priority source families, re-reads the raw extracted text around
each span, and applies strict sentence-level grammars. Output is the RAW
OBSERVATION layer: source wording is never discarded; nothing here is a
graph edge.

Tiers: A ownership · B control · C parent/subsidiary · D shell/nominee
(only when a specific entity/person is named) · E financial flows (only
literal participants).

Usage: python3 -m content_pass_2.observe
"""
from __future__ import annotations

import gzip
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone

from content_pass_1.common import OUT_ROOT, REPO_ROOT, log, read_jsonl, text_disk_path
from .postures import assign_posture

PASS2_VERSION = "content-pass-2/1.0.0"
PARSER_VERSION = "observe/1.4.0"
CP2 = os.path.join(REPO_ROOT, "content-pass-2")
OUT = os.path.join(CP2, "raw-observations.jsonl")
ERRS = os.path.join(CP2, "extraction-errors.jsonl")

# ---- name fragments -------------------------------------------------------
SUFFIX = (r"(?:LLC|L\.L\.C\.|Inc\.?|Corp\.?|Corporation|Company|Co\.|Ltd\.?|LP|"
          r"L\.P\.|LLP|PLLC|Holdings?|Group|Trust|Bank|N\.A\.|S\.?A\.?R\.?L\.?|"
          r"Partners(?:hip)?|Fund|Ventures?|Capital|Financial|Investments?)")
# Interior name tokens must be capitalized (or one of a small set of
# legitimate lowercase name words) so captures cannot cross relative
# clauses ("Ripple Labs that was incorporated as …"). Interior tokens
# may not carry trailing periods (which are sentence boundaries —
# "Bank Tejarat. Bank" must not fuse); initials like "N.A."/"U.S." are
# matched explicitly.
NAMEWORD = (r"(?:[A-Z]\.(?:[A-Z]\.?)+|[A-Z][A-Za-z0-9&'’\-]*|"
            r"of|the|de|la|del|van|von|and|&|en|for)")
ENT = (r"(?:(?:the\s+)?[A-Z][A-Za-z0-9&.'’\-]*(?:\s+" + NAMEWORD + r"){0,7}?[,]?\s+"
       + SUFFIX + r")")
# Parent-position entity names may carry internal commas
# ("Reynolds, Teague, Thurman Financial Corp.").
ENT_COMMA = (r"(?:(?:the\s+)?[A-Z][A-Za-z0-9&.'’\-]*"
             r"(?:,?\s+" + NAMEWORD + r"){0,7}?,?\s+" + SUFFIX + r")")
# Post-capture extension: suffix-anchored lazy matches stop at the first
# suffix word ("Revolut Holdings" in "Revolut Holdings US Inc").
NAME_EXT = re.compile(
    r"^(?:\s+(?:US|USA|N\.?A\.?|II|III|IV|[A-Z][A-Za-z&.'’\-]*)){0,3}?"
    r"\s+(?:LLC|L\.L\.C\.|Inc\.?|Corp\.?|Corporation|Ltd\.?|LP|LLP|PLLC|"
    r"Company|Bank|Trust|Fund(?:ing)?)\b")
PERSON = r"(?:[A-Z][a-z]+(?:\s+[A-Z]\.?)?(?:\s+[A-Z][a-z]+){1,2})"
# Defined terms and short handles ("the Venture", "the FDIC–Receiver",
# "MCHI", "CS-3", bare surname "Tabaja") — acceptable in the by/of
# position of an explicit construct; preserved raw, resolved later.
DEFTERM = r"(?:the\s+[A-Z][A-Za-z\-–]+(?:\s+[A-Z][A-Za-z\-–]+){0,3})"
ABBR = r"(?:[A-Z]{2,6}(?:-\d+)?)"
SURNAME = r"(?:[A-Z][a-z]{2,})"
ACTOR = f"(?:{ENT}|{PERSON})"
BYACTOR = f"(?:{ENT_COMMA}|{PERSON}|{DEFTERM}|{ABBR}|{SURNAME})"
PCT = r"(\d{1,3}(?:\.\d+)?)\s?(?:%|percent)"
QUAL = r"(sole|majority|minority|principal|controlling|co-|part|50/50|indirect|beneficial)"
AMT = r"\$\s?([\d,]+(?:\.\d{2})?)\s*(million|billion)?"

# Tier A — ownership. Each: (name, regex, mapping of group->slot)
TIER_A = [
    ("owned_by", re.compile(
        rf"({ENT})\s*(?:\([^)]{{0,60}}\)\s*)?(?:,\s*(?:which|and)\s+)?"
        rf"(?:is|was|were|are)\s+(?:an?\s+[\w\s-]{{0,30}}\s+)?"
        rf"(?:beneficially\s+)?owned(?:\s+and\s+(?:operated|controlled|managed))?\s+by\s+"
        rf"({ACTOR})"),
     {"object": 1, "subject": 2}),
    ("owns_pct_of", re.compile(
        rf"({ENT}|{PERSON}|{DEFTERM}|{ABBR}|{SURNAME})\s+"
        rf"(?:(?:also|now|then|currently|still|collectively|indirectly|directly)\s+)?"
        rf"(?:owns?|owned|holds?|held|acquired)\s+"
        rf"(?:approximately\s+|about\s+|at\s+least\s+|up\s+to\s+)?{PCT}\s+of\s+"
        rf"(?:the\s+)?(?:(?:[a-z][\w-]*\s+){{0,5}})?(?:shares?|stock|equity|interests?|"
        rf"units|membership\s+interests?|ownership)?\s*(?:of|in)?\s*"
        rf"({ENT}|{ABBR}|{DEFTERM})"),
     {"subject": 1, "percentage": 2, "object": 3}),
    ("controlling_interest_in", re.compile(
        rf"(?:({ENT}|{PERSON}|{DEFTERM}|{ABBR})\s[^.\n]{{0,60}}?)?"
        rf"(?:acquir\w+|holds?|held|obtain\w*|purchas\w+|give|gave|grant\w*)\s+"
        rf"an?\s+(?:{PCT}\s+)?controlling\s+interest\s+in\s+"
        rf"({ENT_COMMA}|{ABBR}|{DEFTERM})"),
     {"subject": 1, "percentage": 2, "object": 3}),
    ("owner_of", re.compile(
        rf"({PERSON})\s*,?\s*(?:is|was|as)?\s*(?:the|a)\s+{QUAL}?\s*owner"
        rf"(?:\s+and\s+[\w\s]{{0,25}})?\s+of\s+({ENT})"),
     {"subject": 1, "qualifier": 2, "object": 3}),
    ("founder_sole_owner", re.compile(
        rf"({PERSON})\s+(?:is|was)\s+the\s+(?:founder\s+and\s+)?"
        rf"{QUAL}\s+(?:owner|shareholder|stockholder|member)"
        rf"(?:\s*,\s*officer)?(?:\s*,?\s*and\s+director)?\s+"
        rf"(?:of|to)\s+({ENT})"),
     {"subject": 1, "qualifier": 2, "object": 3}),
    ("beneficial_owner_of", re.compile(
        rf"({ACTOR})\s*(?:,[^,]{{0,60}},)?\s*(?:is|was|became)\s+"
        rf"(?:the|a)\s+(?:sole\s+)?beneficial\s+owner\s+of\s+"
        rf"(?:[\w\s]{{0,30}}?)({ENT}|[\w\s]{{0,40}}account)"),
     {"subject": 1, "object": 2}),
    ("holds_shares_of", re.compile(
        rf"({ENT})\s+holds\s+{PCT}\s+of\s+the\s+shares"),
     {"subject": 1, "percentage": 2, "object": None}),
    ("owned_by_appositive", re.compile(
        rf"({ENT})\s*(?:\([^)]{{0,50}}\)\s*)?,\s*(?:an?\s+)?"
        rf"(?:newly\s+formed\s+)?(?:entity|company|corporation|firm|fund|venture)"
        rf"[^.\n]{{0,40}}?\s+(?:wholly\s+|beneficially\s+|indirectly\s+|directly\s+)?"
        rf"owned(?:\s+(?:and|or)\s+(?:controlled|operated|managed))?\s+by\s+({BYACTOR})"),
     {"object": 1, "subject": 2}),
    ("acquires_pct_interest_in", re.compile(
        rf"({BYACTOR})\s*(?:\([^)]{{0,50}}\)\s*)?,?[^.\n]{{0,120}}?"
        rf"(?:paid|will\s+pay)\s+{AMT}\s+for\s+an?\s+{PCT}\s+"
        rf"(?:equity|ownership|membership)?\s*interest\s+in\s+({ENT})"),
     {"subject": 1, "amount": 2, "amount_scale": 3, "percentage": 4, "object": 5}),
    ("retains_pct_interest_in", re.compile(
        rf"({BYACTOR})\s+(?:will\s+)?(?:retains?|retained|holds?|held|acquires?|"
        rf"acquired|receives?|received|purchases?|purchased)\s+"
        rf"(?:an?\s+)?{PCT}\s+(?:equity|ownership|membership)?\s*interest\s+in\s+"
        rf"(?:each\s+)?({ENT}|{DEFTERM})"),
     {"subject": 1, "percentage": 2, "object": 3}),
    ("owned_controlled_by_loose", re.compile(
        rf"({ENT})\s*(?:\([^)]{{0,50}}\)\s*)?[^.;:\n]{{0,60}}?"
        rf"\b(?:owned\s+(?:and|or)\s+controlled|owned)\s+by\b[^.;:\n]{{0,40}}?"
        rf"({BYACTOR})"),
     {"object": 1, "subject": 2}),
    ("majority_shareholder_of", re.compile(
        rf"({ENT}|{ABBR}|{PERSON})\s+(?:is|was|remains?)\s+the\s+"
        rf"(majority|sole|controlling|principal|largest)\s+"
        rf"(?:shareholder|stockholder|member|owner)\s+of\s+({ENT_COMMA})"),
     {"subject": 1, "qualifier": 2, "object": 3}),
]

TIER_B = [
    ("controlled_by", re.compile(
        rf"({ENT})\s*(?:,[^,]{{0,80}},)?\s*(?:is|was|were|are)\s+"
        rf"(?:owned\s+(?:and/or\s+|or\s+|and\s+)?)?controlled\s+by\s+({ACTOR})"),
     {"object": 1, "subject": 2}),
    ("designated_owned_controlled", re.compile(
        rf"({ENT})\s+(?:was|is|were)\s+designated\s+for\s+being\s+owned\s+or\s+"
        rf"controlled\s+by\s+({ACTOR})"),
     {"object": 1, "subject": 2}),
    ("controls", re.compile(
        rf"({ACTOR})\s+(?:owns\s+and\s+)?controls\s+({ENT})"),
     {"subject": 1, "object": 2}),
    ("controlling_person_of", re.compile(
        rf"({ACTOR})\s*,?\s*(?:is|was|as)?\s*(?:the|a)\s+controlling\s+"
        rf"(?:person|shareholder|stockholder|member|party)\s+of\s+({ENT})"),
     {"subject": 1, "object": 2}),
    ("exercises_control", re.compile(
        rf"({ACTOR})\s+exercise[sd]?\s+(?:substantial\s+|significant\s+|complete\s+)?"
        rf"control\s+over\s+({ENT})"),
     {"subject": 1, "object": 2}),
    ("controlled_by_appositive", re.compile(
        rf"({ENT}|{ABBR})\s*(?:\([^)]{{0,50}}\)\s*)?,?\s*"
        rf"(?:an?\s+)?(?:entit(?:y|ies)|compan(?:y|ies)|private\s+company|"
        rf"corporation)?\s*(?:that\s+(?:is|was|were|are)\s+)?"
        rf"(?:in)?directly\s+(?:owned\s+and\s+)?controlled\s+by\s+({BYACTOR})"),
     {"object": 1, "subject": 2}),
    ("entity_controlled_by", re.compile(
        rf"({ENT})\s*(?:\([^)]{{0,50}}\)\s*)?,?\s*"
        rf"(?:an?\s+)?(?:entit(?:y|ies)|compan(?:y|ies)|private\s+company|"
        rf"Canadian\s+company|corporation)\s*,?\s+"
        rf"(?:owned\s+and\s+)?controlled\s+by\s+({BYACTOR})"),
     {"object": 1, "subject": 2}),
    ("that_x_controlled", re.compile(
        rf"({ENT}|{DEFTERM})\s+that\s+({PERSON}|{SURNAME})\s+"
        rf"(?:owned\s+and\s+)?controlled"),
     {"object": 1, "subject": 2}),
    ("owned_and_controlled_by", re.compile(
        rf"({ENT})\s*(?:\([^)]{{0,50}}\)\s*)?,?[^.\n]{{0,60}}?"
        rf"owned\s+and\s+controlled\s+by\s+({BYACTOR})"),
     {"object": 1, "subject": 2}),
]

TIER_C = [
    ("subsidiary_of", re.compile(
        rf"({ENT})\s*(?:\([^)]{{0,40}}\)\s*)?,?\s*(?:is|was|will\s+(?:be|remain)|"
        rf"remains?|became)\s+an?\s+(wholly[- ]owned|wholly-\s*owned|indirect|direct|"
        rf"majority[- ]owned)?\s*subsidiary\s+of\s+({ENT})"),
     {"object": 1, "qualifier": 2, "subject": 3}),
    ("parent_of", re.compile(
        rf"({ENT})\s*,?\s*(?:is|was)\s+the\s+parent\s+"
        rf"(?:company|corporation|holding\s+company)\s+of\s+({ENT})"),
     {"subject": 1, "object": 2}),
    ("its_subsidiary", re.compile(
        rf"({ENT})\s*,?\s+(?:and\s+)?its\s+(wholly[- ]owned\s+)?subsidiar(?:y|ies)\s*,?\s+({ENT})"),
     {"subject": 1, "qualifier": 2, "object": 3}),
    ("operates_through_sub", re.compile(
        rf"({ENT})[^.\n]{{0,60}}?operates\s+through\s+({ENT})\s*,?\s+"
        rf"(?:its|a)\s+(wholly[- ]?\s*owned)?\s*subsidiary"),
     {"subject": 1, "object": 2, "qualifier": 3}),
    ("appositive_subsidiary_of", re.compile(
        rf"({ENT}|{DEFTERM}|Bank)\s*(?:\([^)]{{0,50}}\)\s*)?,?\s+"
        rf"(?:is\s+|was\s+|(?:which|that)\s+(?:is|was)\s+)?an?\s+"
        rf"(wholly[- ]\s?owned|indirect|direct|majority[- ]owned)?\s*"
        rf"(?:special[- ]purpose\s+)?subsidiar(?:y|ies)\s+of\s+"
        rf"({ENT_COMMA}|{DEFTERM}|{ABBR})"),
     {"object": 1, "qualifier": 2, "subject": 3}),
    ("subsidiaries_list", re.compile(
        rf"({ENT_COMMA}|{ABBR}|{DEFTERM})(?:['’]s)\s+"
        rf"(?:three|four|five|two|several|various)?\s*"
        rf"(wholly[- ]\s?owned)?\s*subsidiar(?:y|ies)\s*,\s+"
        rf"([A-Z][^.;\n]{{10,220}}?)(?:\s+engaged|\s+were|\s+which|\.|;)"),
     {"subject": 1, "qualifier": 2, "object": 3}),
]

TIER_D = [
    ("shell_named", re.compile(
        rf"({ENT})\s*(?:,[^,]{{0,60}},)?\s*(?:is|was|were)\s+"
        rf"(?:nothing\s+more\s+than\s+|merely\s+|simply\s+)?"
        rf"an?\s+(shell|front|shelf|nominee|sham)\s+"
        rf"(?:compan(?:y|ies)|corporation|entit(?:y|ies))"),
     {"object": 1, "qualifier": 2}),
    ("used_shells", re.compile(
        rf"({ACTOR})\s+(?:used|created|formed|established|set\s+up)\s+"
        rf"({ENT})\s*(?:,[^,]{{0,60}},)?\s+as\s+a?\s*(shell|front|nominee|conduit)"),
     {"subject": 1, "object": 2, "qualifier": 3}),
    ("nominee_for", re.compile(
        rf"({ACTOR})\s*,?\s*(?:acted|acting|served|serving)\s+as\s+"
        rf"(?:a\s+)?nominee\s+(?:owner\s+)?(?:for|of)\s+({ACTOR})"),
     {"subject": 1, "object": 2, "qualifier": None}),
    ("front_for", re.compile(
        rf"({ENT}|{ABBR}|{SURNAME})\s+(?:acts?|acted|serves?|served|operates?|"
        rf"operated|functions?|functioned)\s+as\s+a\s+(front|shell|nominee|conduit)\s+"
        rf"(?:compan(?:y|ies)|corporation|entit(?:y|ies))?\s*for\s+"
        rf"[^.\n]{{0,60}}?({ENT_COMMA}|{ABBR}|{DEFTERM}|{PERSON})"),
     {"subject": 1, "qualifier": 2, "object": 3}),
]

# Flow actors may be defendants-groups, abbreviations, defined terms, or
# possessive kin references; flows are observations (never edges), so the
# object capture is looser and confidence is scored accordingly.
FLOWACT = (rf"(?:{ENT_COMMA}|{PERSON}|{DEFTERM}|{ABBR}|{SURNAME}|"
           rf"the\s+[A-Z][A-Za-z]+\s+Defendants?)")
FLOWOBJ = rf"(?:{FLOWACT}[’']s\s+[a-z]{{3,12}}|{FLOWACT}|[\w\s]{{0,30}}account[\w\s]{{0,30}})"
TIER_E = [
    ("transferred_to", re.compile(
        rf"({FLOWACT})\s+(?:(?:also|then|subsequently|later)\s+)?"
        rf"(?:wired|transferred|sent|paid|funneled|diverted|deposited|remitted)\s+"
        rf"(?:approximately\s+|about\s+|at\s+least\s+|more\s+than\s+)?{AMT}"
        rf"[^.\n]{{0,60}}?\s+(?:to|into)\s+({FLOWOBJ})"),
     {"subject": 1, "amount": 2, "amount_scale": 3, "object": 4}),
    ("transferred_recipient_first", re.compile(
        rf"({FLOWACT})\s+(?:(?:also|then|subsequently|later)\s+)?"
        rf"(?:wired|transferred|sent|paid|funneled|diverted|remitted)\s+to\s+"
        rf"({FLOWOBJ})\s+(?:approximately\s+|about\s+|at\s+least\s+|more\s+than\s+)?{AMT}"),
     {"subject": 1, "object": 2, "amount": 3, "amount_scale": 4}),
    ("received_from", re.compile(
        rf"({FLOWACT})\s+(?:received|obtained|collected|raised)\s+"
        rf"(?:approximately\s+|about\s+|at\s+least\s+|more\s+than\s+)?{AMT}\s+"
        rf"(?:from|through)\s+({FLOWOBJ}|[\d,]+\s+investors)"),
     {"object": 1, "amount": 2, "amount_scale": 3, "subject": 4}),
    ("wire_from_to", re.compile(
        rf"wire\s+transfers?\s+of\s+{AMT}\s+from\s+({FLOWOBJ})"
        rf"\s+to\s+({FLOWOBJ})"),
     {"amount": 1, "amount_scale": 2, "subject": 3, "object": 4}),
]

TIERS = [("A_OWNERSHIP", "ownership-candidates.jsonl", TIER_A),
         ("B_CONTROL", "control-candidates.jsonl", TIER_B),
         ("C_PARENT_SUBSIDIARY", "parent-subsidiary-candidates.jsonl", TIER_C),
         ("D_SHELL_NOMINEE", "shell-structure-candidates.jsonl", TIER_D),
         ("E_FINANCIAL_FLOW", "financial-flow-candidates.jsonl", TIER_E)]

FAMILY_OK = {"SEC", "TREASURY", "TREASURY_OIG", "FINCEN", "OCC", "FDIC",
             "CONGRESS_OVERSIGHT", "CONGRESS_JUDICIARY", "CONGRESS_GOV", "DOJ",
             "GOVINFO", "GAO"}

DATE_RE = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|October|"
    r"November|December)\s+\d{1,2},?\s+(?:19|20)\d{2}\b|\bin\s+((?:19|20)\d{2})\b")
ROLE_RE = re.compile(
    r"\b(president|chief executive officer|CEO|chief financial officer|CFO|"
    r"chairman|secretary|treasurer|director|officer|founder|managing member|"
    r"sole member|manager|general partner|principal)\b", re.I)


def sentence_bounds(text: str, start: int, end: int):
    """Deterministic sentence window around [start,end)."""
    left = max(text.rfind(". ", 0, start), text.rfind("\n\n", 0, start),
               text.rfind("? ", 0, start), text.rfind("! ", 0, start))
    left = 0 if left < 0 else left + 2
    rights = [text.find(". ", end), text.find("\n\n", end),
              text.find("? ", end), text.find("! ", end)]
    rights = [r for r in rights if r >= 0]
    right = min(rights) + 1 if rights else min(len(text), end + 400)
    if right - left > 900:  # cap runaway "sentences" in tables
        left = max(left, start - 450)
        right = min(right, end + 450)
    return left, right


# Capitalized sentence-starters that signal a capture crossed a heading
# or sentence boundary ("Proposed Operations The Bank").
BOUNDARY_TOKENS = re.compile(
    r"\s+(?:The|This|These|That|Until|Additionally|Please|Proposed|"
    r"Shareholders|Business|Further|For\s+example|IT\s+IS)\s+")
# Reported-speech cue: the sentence attributes the proposition to a third
# party ("a Telegram channel claimed that…"). Flagged, never dropped.
REPORTED_SPEECH = re.compile(
    r"\b(?:claim(?:ed|s)?|alleg\w+|purport\w+|according\s+to|reportedly|"
    r"said\s+to\s+be|described\s+as)\b", re.I)


def clean_name(s):
    if not s:
        return None
    s = re.sub(r"\s+", " ", s)
    # Truncate at a sentence-starter appearing mid-name (boundary crossing);
    # keep the head, which is where the anchored name began.
    m = BOUNDARY_TOKENS.search(s, 1)
    if m and m.start() > 3:
        s = s[:m.start()]
    return s.strip(" ,;:.")


def load_bucket(path):
    if os.path.isfile(path):
        fh = open(path, encoding="utf-8")
    elif os.path.isfile(path + ".gz"):
        fh = gzip.open(path + ".gz", "rt", encoding="utf-8")
    else:
        return
    with fh:
        for line in fh:
            yield json.loads(line)


def main():
    os.makedirs(CP2, exist_ok=True)
    inv = {r["sha256"]: r for r in
           read_jsonl(os.path.join(OUT_ROOT, "corpus-inventory.jsonl"))}
    classes = {}
    for rec in load_bucket(os.path.join(OUT_ROOT, "document-classes.jsonl")):
        classes[rec["sha256"]] = rec.get("document_class") or []

    text_cache = {}
    posture_cache = {}
    stats = Counter()
    seq = Counter()
    n_out = 0
    with open(OUT, "w", encoding="utf-8") as out, \
            open(ERRS, "w", encoding="utf-8") as errs:
        for tier_name, bucket, grammars in TIERS:
            for cand in load_bucket(os.path.join(OUT_ROOT, bucket)):
                sha = cand["source_sha256"]
                rec = inv.get(sha) or {}
                if rec.get("source_family") not in FAMILY_OK:
                    stats[f"{tier_name}:skipped_family"] += 1
                    continue
                if sha not in text_cache:
                    tp = text_disk_path(sha)
                    try:
                        with open(tp, encoding="utf-8") as fh:
                            text_cache[sha] = fh.read()
                    except OSError as exc:
                        errs.write(json.dumps({
                            "sha256": sha, "error": str(exc)[:200],
                            "stage": "read_text"}) + "\n")
                        text_cache[sha] = ""
                    if len(text_cache) > 3000:  # bounded memory
                        text_cache.pop(next(iter(text_cache)))
                text = text_cache[sha]
                if not text:
                    continue
                s0, s1 = sentence_bounds(
                    text, cand["character_start"], cand["character_end"])
                sent = text[s0:s1]
                if sha not in posture_cache:
                    posture_cache[sha] = assign_posture(
                        rec, classes.get(sha), text[:3000])
                posture, rationale = posture_cache[sha]

                matched_any = False
                for pname, pat, slots in [(n, p, s) for n, p, s in
                                          [(g[0], g[1], g[2]) for g in grammars]]:
                    m = pat.search(sent)
                    if not m:
                        continue
                    matched_any = True
                    stats[f"{tier_name}:{pname}"] += 1

                    def grp(idx):
                        if idx is None:
                            return None
                        try:
                            return m.group(idx)
                        except Exception:
                            return None

                    def name_grp(idx):
                        """Group text, extended past a premature suffix stop
                        ("Revolut Holdings" -> "Revolut Holdings US Inc")."""
                        val = grp(idx)
                        if not val:
                            return None
                        try:
                            ext = NAME_EXT.match(sent[m.end(idx):])
                        except Exception:
                            ext = None
                        return val + ext.group(0) if ext else val

                    subject_raw = clean_name(name_grp(slots.get("subject")))
                    object_raw = clean_name(name_grp(slots.get("object")))
                    pct_raw = grp(slots.get("percentage"))
                    qual_raw = clean_name(grp(slots.get("qualifier")))
                    amount_raw = grp(slots.get("amount"))
                    scale = grp(slots.get("amount_scale"))
                    if amount_raw and scale:
                        amount_raw = f"{amount_raw} {scale}"
                    dm = DATE_RE.search(sent)
                    rm = ROLE_RE.search(sent)
                    seq[sha] += 1
                    both = bool(subject_raw and object_raw)
                    reported = bool(REPORTED_SPEECH.search(sent))
                    obs = {
                        "observation_id": f"obs:{sha[:16]}:{seq[sha]:04d}",
                        "tier": tier_name,
                        "source_sha256": sha,
                        "source_url": rec.get("url"),
                        "source_id": None,
                        "document_title": None,
                        "document_date": cand.get("document_date"),
                        "retrieval_date": rec.get("retrieved_at"),
                        "provenance_class": rec.get("provenance"),
                        "source_family": rec.get("source_family"),
                        "evidentiary_posture": posture,
                        "posture_rationale": rationale,
                        "page": cand.get("page_number"),
                        "section": None, "item": None, "exhibit": None,
                        "line_start": cand.get("line_start"),
                        "line_end": cand.get("line_end"),
                        "character_start": s0,
                        "character_end": s1,
                        "raw_text": sent[:1200],
                        "subject_raw": subject_raw,
                        "predicate_raw": pname,
                        "object_raw": object_raw,
                        "amount_raw": amount_raw,
                        "percentage_raw": pct_raw,
                        "date_raw": dm.group(0) if dm else None,
                        "role_raw": rm.group(0) if rm else None,
                        "qualifier_raw": qual_raw,
                        "identifier_raw": None,
                        "parser": "content_pass_2.observe",
                        "parser_version": PARSER_VERSION,
                        "extraction_method": "REGEX_SENTENCE_GRAMMAR",
                        "extraction_confidence": 0.9 if both else 0.55,
                        "reported_speech": reported,
                        "candidate_id": cand["candidate_id"],
                        "pass_version": PASS2_VERSION,
                    }
                    out.write(json.dumps(obs, sort_keys=True,
                                         ensure_ascii=False) + "\n")
                    n_out += 1
                    break  # one grammar per candidate span
                if not matched_any:
                    stats[f"{tier_name}:no_grammar_match"] += 1
    log(f"observe: {n_out} raw observations")
    with open(os.path.join(CP2, "observe-stats.json"), "w") as fh:
        json.dump({"generated_at": datetime.now(timezone.utc).isoformat(),
                   "counts": dict(stats.most_common()),
                   "parser_version": PARSER_VERSION}, fh, indent=2)


if __name__ == "__main__":
    main()
