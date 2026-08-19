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
PARSER_VERSION = "observe/1.1.0"
CP2 = os.path.join(REPO_ROOT, "content-pass-2")
OUT = os.path.join(CP2, "raw-observations.jsonl")
ERRS = os.path.join(CP2, "extraction-errors.jsonl")

# ---- name fragments -------------------------------------------------------
# Corporate suffixes are matched case-insensitively so ALL-CAPS court-caption
# names ("ATLANTA CAPITAL LLC", "GEN-SEE CAPITAL CORPORATION") resolve.
_SUFFIX = (r"(?i:LLC|L\.L\.C\.|Inc\.?|Corp\.?|Corporation|Company|Co\.|Ltd\.?|"
           r"Limited|Incorporated|LP|L\.P\.|LLP|PLLC|PLC|GmbH|N\.V\.|"
           r"Holdings?|Group|Trust|Bank|Bancorp|Bancshares|N\.A\.|"
           r"S\.?A\.?R\.?L\.?|Partners(?:hip)?|Fund|Association)")
# Interior tokens must not be clause connectives (which would let a name
# swallow "…through another LLC") or a corporate suffix token (which would
# let a name run across "IBG LLC. IBG LLC").
_MIDSTOP = (r"(?:through|another|other|certain|various|his|her|their|its|such|"
            r"any|each|that|which|who|whose|is|was|are|were|and|or|"
            r"(?i:LLC|L\.L\.C\.|Inc\.?|Corp\.?|Ltd\.?|LP|LLP|PLLC|PLC|N\.A\.)"
            r"(?=[\s.,]))")
ENT = (r"(?:[A-Z][A-Za-z0-9&.'’\-]*(?:\s+(?!" + _MIDSTOP + r"\s)"
       r"[A-Za-z0-9&.'’\-]+){0,7}?[,]?\s+" + _SUFFIX + r")")
# Prefix-form entities common in OFAC material ("Limited Liability Company
# Garant-SV", "OOO Gazprom Burenie").
PREFIX_ENT = (r"(?:(?:(?:Limited\s+)?Liability\s+Compan(?:y|ies)|"
              r"(?:Open|Closed|Public|Private)\s+Joint[- ]Stock\s+Company|"
              r"Joint[- ]Stock\s+Company|OOO|OAO|ZAO|PAO)\s+"
              r"[A-Z][A-Za-z0-9'’&.\-]*(?:\s+[A-Z][A-Za-z0-9'’&.\-]*){0,3})")
# Definite generic references to a document-defined entity ("the Bank",
# "the Company") — kept verbatim as raw wording; confidence is capped below.
DEFENT = (r"(?:[Tt]he\s+(?:[Pp]roposed\s+)?(?:Bank|Company|Corporation|Trust|"
          r"Venture|Fund|Association|Partnership|Firm|Institution))")
# Surname tokens allow interior capitals (McGhan, DiSanto, O'Brien) but
# must end lowercase so they never stop mid-word.
PERSON = r"(?:[A-Z][a-z]+(?:\s+[A-Z]\.?)?(?:\s+[A-Z][A-Za-z'’\-]*[a-z]){1,2})"
# ALL-CAPS person names from court captions ("MICHAEL W. SMITH").
PERSON_CAPS = r"(?:[A-Z][A-Z'’\-]+(?:\s+[A-Z]\.?)?(?:\s+[A-Z][A-Z'’\-]+){1,2})"
# Single document-defined surname ("Forrest", "Irby", "McNaul") — only used
# inside strict verb frames, never as a general actor.
SURNAME = r"(?:[A-Z][a-z]+[A-Za-z'’\-]*[a-z])"
# Cooperating-source / confidential-witness style codes ("CS-2", "CW-1").
CODE = r"(?:[A-Z]{1,4}-\d{1,3})"
# Bounded proper-noun run ("Central Bank of Iran", "TIAA") for object slots
# inside strict frames only.
TITLECASE = (r"(?:[A-Z][A-Za-z0-9'’&.\-]*(?:\s+(?:of|the|de|la|del|al|el)\s+"
             r"[A-Z][A-Za-z0-9'’&.\-]*|\s+[A-Z][A-Za-z0-9'’&.\-]*){0,6})")
ACTOR = f"(?:{PREFIX_ENT}|{ENT}|{DEFENT}|{PERSON_CAPS}|{PERSON}|{CODE})"
# Comma list of defined names ("Nunns, Lucas, McNaul, Kilgariff and their
# affiliated entities") — captured verbatim as one raw slot.
NAMELIST = (rf"(?:{SURNAME}|{PERSON})(?:,\s+(?:{SURNAME}|{PERSON})){{1,6}}"
            rf"(?:,?\s+and\s+(?:{SURNAME}|{PERSON}|their\s+affiliated\s+entities))?")
PCT = r"(\d{1,3}(?:\.\d+)?)\s?(?:%|percent)"
QUAL = r"(sole|majority|minority|principal|controlling|co-|part|50/50|indirect|beneficial)"
# Compound subsidiary qualifiers ("direct, wholly-owned").
SUBQUAL = (r"((?:direct|indirect|wholly[- ]\s*owned|majority[- ]owned)"
           r"(?:,?\s+(?:direct|indirect|wholly[- ]\s*owned|majority[- ]owned))*)")

# Tier A — ownership. Each: (name, regex, mapping of group->slot)
TIER_A = [
    ("owned_by", re.compile(
        rf"({ENT}|{DEFENT}|{TITLECASE})\s*(?:\([^)]{{0,60}}\)\s*)?(?:,\s*(?:which|and)\s+)?"
        rf"(?:is|was|were|are)\s+(?:an?\s+[\w\s-]{{0,30}}\s+)?"
        rf"(?:beneficially\s+)?owned(?:\s+and\s+(?:operated|controlled|managed))?\s+by\s+"
        rf"({NAMELIST}|{ACTOR})"),
     {"object": 1, "subject": 2}),
    ("owns_pct_of", re.compile(
        rf"({ACTOR}|{TITLECASE})\s+(?:currently\s+|indirectly\s+|directly\s+)?"
        rf"(?:owns?|owned|holds?|held|acquired|purchased|obtained|retains?|retained|"
        rf"will\s+own|would\s+own)\s+"
        rf"(?:approximately\s+|about\s+|at\s+least\s+|up\s+to\s+)?{PCT}\s+of\s+"
        rf"(?:the\s+)?(?:[\w\s-]{{0,40}}?\s+)?(?:shares?|stock|equity|interests?|units|"
        rf"membership\s+interests?|ownership)?\s*(?:of|in)?\s*({ENT}|{DEFENT})"),
     {"subject": 1, "percentage": 2, "object": 3}),
    ("pct_interest_in", re.compile(
        rf"({ACTOR}|{TITLECASE})\s+(?:currently\s+|indirectly\s+|directly\s+)?"
        rf"(?:owns?|owned|holds?|held|acquired|purchased|obtained|retains?|retained|"
        rf"will\s+own|would\s+own)\s+"
        rf"(?:approximately\s+|about\s+|at\s+least\s+|up\s+to\s+)?(?:an?\s+)?{PCT}\s+"
        rf"(?:ownership|equity|membership|profits?)\s+interests?\s+in\s+"
        rf"(?:the\s+)?({ENT}|{DEFENT}|{TITLECASE})"),
     {"subject": 1, "percentage": 2, "object": 3}),
    ("owner_of", re.compile(
        rf"({PERSON})\s*,?\s*(?:is|was|as)?\s*(?:the|a)\s+{QUAL}?\s*owner"
        rf"(?:\s+and\s+[\w\s]{{0,25}})?\s+of\s+({ENT})"),
     {"subject": 1, "qualifier": 2, "object": 3}),
    ("owner_of_appositive", re.compile(
        rf"({ACTOR}|{SURNAME})\s*,\s*(?:the|a)\s+{QUAL}?\s*"
        rf"(?:beneficial\s+)?owner\s+of\s+(?:the\s+)?({ENT}|{DEFENT}|{TITLECASE})"),
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
        rf"({ENT})\s+holds\s+{PCT}\s+of\s+the\s+shares"
        rf"(?:\s+(?:of|in)\s+(?:the\s+)?({ENT}|{TITLECASE}))?"),
     {"subject": 1, "percentage": 2, "object": 3}),
]

TIER_B = [
    ("controlled_by", re.compile(
        rf"({ENT}|{DEFENT}|{TITLECASE})\s*(?:,[^,]{{0,80}},)?\s*(?:is|was|were|are)\s+"
        rf"(?:owned\s+(?:and/or\s+|or\s+|and\s+)?)?controlled\s+by\s+"
        rf"({NAMELIST}|{ACTOR})"),
     {"object": 1, "subject": 2}),
    ("designated_owned_controlled", re.compile(
        rf"({ENT})\s+(?:was|is|were)\s+designated\s+for\s+being\s+owned\s+or\s+"
        rf"controlled\s+by\s+({ACTOR})"),
     {"object": 1, "subject": 2}),
    ("designation_controller", re.compile(
        rf"designated(?:\s+today)?(?:\s+pursuant\s+to[^,.]{{0,40}})?\s+"
        rf"for\s+being\s+owned\s+or\s+controlled\s+by\s*"
        rf"(?:,[^,]{{0,120}},)?\s*(?:directly\s+or\s+indirectly,\s*)?"
        rf"({ACTOR}|{SURNAME})"),
     {"subject": 1}),
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
]

TIER_C = [
    ("subsidiary_of", re.compile(
        rf"({ENT}|{DEFENT})\s*(?:\([^)]{{0,40}}\)\s*)?,?\s*"
        rf"(?:is|was|will\s+(?:be|remain)|would\s+(?:be|remain)|"
        rf"remains?|became)\s+an?\s+{SUBQUAL}?\s*subsidiary\s+of\s+"
        rf"(?:the\s+)?({ENT}|{DEFENT}|{TITLECASE})"),
     {"object": 1, "qualifier": 2, "subject": 3}),
    ("subsidiary_of_appositive", re.compile(
        rf"({ENT})\s*(?:\([^)]{{0,60}}\)\s*)?,\s*an?\s+{SUBQUAL}?\s*"
        rf"subsidiary\s+of\s+(?:the\s+)?({ENT}|{DEFENT}|{TITLECASE})"),
     {"object": 1, "qualifier": 2, "subject": 3}),
    ("parent_of", re.compile(
        rf"({ENT})\s*,?\s*(?:is|was)\s+the\s+parent\s+"
        rf"(?:company|corporation|holding\s+company)\s+of\s+({ENT})"),
     {"subject": 1, "object": 2}),
    ("holding_company_of", re.compile(
        rf"({ENT})\s*(?:,\s*|\s+(?:is|was|became)\s+)(?:the|a)\s+"
        rf"(?:bank\s+|savings\s+and\s+loan\s+|thrift\s+)?holding\s+company\s+"
        rf"(?:of|for)\s+(?:the\s+)?({ENT}|{DEFENT})"),
     {"subject": 1, "object": 2}),
    ("affiliate_of", re.compile(
        rf"({ENT})\s*(?:,\s*|\s+(?:is|was|remains?|became)\s+)an?\s+affiliate\s+of\s+"
        rf"(?:the\s+)?({ENT}|{DEFENT})"),
     {"subject": 1, "object": 2}),
    # Slash forms and "doing business as" only: prose "also/formerly known
    # as" renames non-corporate things too (holidays, programs, places).
    ("alias_of", re.compile(
        rf"({ACTOR}|{SURNAME})\s*,?\s+"
        rf"(?:d/b/a|a/k/a|f/k/a|n/k/a|a/d/b/a|doing\s+business\s+as)\s+"
        rf"({ENT}|{TITLECASE}|[A-Z][A-Z0-9&.,'’\s\-]{{2,60}})"),
     {"subject": 1, "object": 2}),
    ("its_subsidiary", re.compile(
        rf"({ENT})\s*,?\s+(?:and\s+)?its\s+(wholly[- ]owned\s+)?subsidiar(?:y|ies)\s*,?\s+({ENT})"),
     {"subject": 1, "qualifier": 2, "object": 3}),
    ("operates_through_sub", re.compile(
        rf"({ENT})[^.\n]{{0,60}}?operates\s+through\s+({ENT})\s*,?\s+"
        rf"(?:its|a)\s+(wholly[- ]?\s*owned)?\s*subsidiary"),
     {"subject": 1, "object": 2, "qualifier": 3}),
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
]

# Amount: tolerates OCR-spaced thousands ("$695, 000"); an optional range
# tail ("between $300,000 to $400,000") records the lower bound, and the
# full range stays in raw_text.
_NUM = r"\d{1,3}(?:,\s?\d{3})+(?:\.\d{2})?|[\d,]+(?:\.\d{2})?"
AMT = (rf"\$\s?({_NUM})\s*(million|billion)?"
       rf"(?:\s*(?:to|and|–|—|-)\s*\$?\s?(?:{_NUM})\s*(?:million|billion)?)?")
TIER_E = [
    ("transferred_to", re.compile(
        rf"({ACTOR}|{TITLECASE})\s+(?:wired|transferred|sent|paid|funneled|diverted|"
        rf"deposited)\s+(?:between\s+)?"
        rf"(?:approximately\s+|about\s+|at\s+least\s+|more\s+than\s+)?{AMT}"
        rf"[^.\n]{{0,120}}?\s+(?:to|into)\s+"
        rf"({ACTOR}|{TITLECASE}|[\w\s]{{0,30}}account[\w\s]{{0,30}})"),
     {"subject": 1, "amount": 2, "amount_scale": 3, "object": 4}),
    ("received_from", re.compile(
        rf"({ACTOR}|{TITLECASE})\s+(?:received|obtained|collected|raised)\s+"
        rf"(?:approximately\s+|about\s+|at\s+least\s+|more\s+than\s+)?{AMT}\s+"
        rf"(?:from|through)\s+({ACTOR}|{TITLECASE}|[\d,]+\s+investors)"),
     {"object": 1, "amount": 2, "amount_scale": 3, "subject": 4}),
    ("wire_from_to", re.compile(
        rf"wire\s+transfer\s+of\s+{AMT}\s+from\s+({ACTOR}|[\w\s]{{0,40}}account)"
        rf"\s+to\s+({ACTOR}|[\w\s]{{0,40}}account)"),
     {"amount": 1, "amount_scale": 2, "subject": 3, "object": 4}),
]

TIERS = [("A_OWNERSHIP", "ownership-candidates.jsonl", TIER_A),
         ("B_CONTROL", "control-candidates.jsonl", TIER_B),
         ("C_PARENT_SUBSIDIARY", "parent-subsidiary-candidates.jsonl", TIER_C),
         ("D_SHELL_NOMINEE", "shell-structure-candidates.jsonl", TIER_D),
         ("E_FINANCIAL_FLOW", "financial-flow-candidates.jsonl", TIER_E)]

# Part IV priority families, plus the regulator families first present at
# full-corpus scale (NCUA, FFIEC, Federal Reserve — enforcement/structure
# material comparable to OCC/FDIC). FBI_VAULT stays out pending OCR.
FAMILY_OK = {"SEC", "TREASURY", "TREASURY_OIG", "FINCEN", "OCC", "FDIC",
             "CONGRESS_OVERSIGHT", "CONGRESS_JUDICIARY", "CONGRESS_GOV", "DOJ",
             "GOVINFO", "GAO", "NCUA", "FFIEC", "FEDERAL_RESERVE"}

DATE_RE = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|October|"
    r"November|December)\s+\d{1,2},?\s+(?:19|20)\d{2}\b|\bin\s+((?:19|20)\d{2})\b")
ROLE_RE = re.compile(
    r"\b(president|chief executive officer|CEO|chief financial officer|CFO|"
    r"chairman|secretary|treasurer|director|officer|founder|managing member|"
    r"sole member|manager|general partner|principal)\b", re.I)
# A definite generic reference ("the Bank") names a party only via the
# document's own defined terms — cap confidence until resolution.
GENERIC_NAME_RE = re.compile(
    r"^(?:the\s+)?(?:proposed\s+)?(?:bank|company|corporation|trust|venture|"
    r"fund|association|partnership|firm|institution)$", re.I)


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


_CAPTION_PREFIX = re.compile(
    r"^(?:defendants?|plaintiffs?|relief\s+defendants?|respondents?)\s+", re.I)


def clean_name(s):
    if not s:
        return None
    s = re.sub(r"\s+", " ", s).strip(" ,;:.")
    return _CAPTION_PREFIX.sub("", s) or None


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
    seen = set()  # overlapping candidate spans that hit the same sentence+grammar
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
                for pname, pat, slots in grammars:
                    m = pat.search(sent)
                    if not m:
                        continue
                    matched_any = True
                    dedup_key = (tier_name, pname, sha, s0, m.start(), m.end())
                    if dedup_key in seen:
                        stats[f"{tier_name}:duplicate_span"] += 1
                        break
                    seen.add(dedup_key)
                    stats[f"{tier_name}:{pname}"] += 1

                    def grp(idx):
                        if idx is None:
                            return None
                        try:
                            return m.group(idx)
                        except Exception:
                            return None

                    subject_raw = clean_name(grp(slots.get("subject")))
                    object_raw = clean_name(grp(slots.get("object")))
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
                    confidence = 0.9 if both else 0.55
                    if any(n and GENERIC_NAME_RE.match(n)
                           for n in (subject_raw, object_raw)):
                        confidence = 0.55
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
                        "extraction_confidence": confidence,
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
