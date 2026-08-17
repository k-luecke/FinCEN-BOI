#!/usr/bin/env python3
"""Ingestion connector: content-pass-2 raw observations -> ownership graph.

Reads content-pass-2/raw-observations.jsonl and writes the
ownership-reconstruction node/edge/name tables (JSONL, one file per
table, suffix `pass2-observations`), conforming to ownership_schema.py.

Ground rules applied here:

- Assertions are what the source says. Ownership-stating predicates map
  to BENEFICIAL_OWNER (evidence_class DIRECT — every observation quotes
  the sentence in which the source itself states the relationship).
  Pure-control predicates map to UNKNOWN_CONTROL_ROLE and are never
  promoted. Structure predicates map to PARENT / RELATED_ORGANIZATION.
- Aliases (d/b/a, a/k/a, f/k/a, n/k/a) become name-history records for
  entities and name_variants for people — never separate graph nodes.
- Ambiguity is recorded, not resolved by guessing: observations with a
  missing counterparty, a document-generic party ("the Bank"), a
  stop-listed name, or sub-threshold extraction confidence go to
  unresolved/, with the reason recorded.
- Financial-flow observations (transferred_to, received_from,
  wire_from_to) and entity-property observations (shell_named) are out
  of scope for the ownership graph: no assertion in the closed
  vocabulary describes them. They remain in content-pass-2/.
- Nodes are names-as-evidenced (like the schema's person rule): two
  sources naming the same normalized string share a node; no identity
  resolution beyond that is attempted here.

Deterministic: stable ids (hash of normalized name), stable ordering,
no wall-clock values in graph records.

Usage: python3 build_ownership_graph.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from collections import Counter, defaultdict

REPO = os.path.dirname(os.path.abspath(__file__))
OBS = os.path.join(REPO, "content-pass-2", "raw-observations.jsonl")
ROOT = os.path.join(REPO, "ownership-reconstruction")
TEXT_ROOT = os.path.join(REPO, "derived", "text")
SUFFIX = "pass2-observations"

# ---- predicate -> handling ------------------------------------------------
OWNERSHIP = {"owned_by", "owns_pct_of", "pct_interest_in", "owner_of",
             "owner_of_appositive", "founder_sole_owner",
             "beneficial_owner_of", "holds_shares_of",
             "designated_owned_controlled"}
CONTROL = {"controlled_by", "controls", "controlling_person_of",
           "exercises_control"}
PARENT_PREDS = {"subsidiary_of", "subsidiary_of_appositive", "its_subsidiary",
                "operates_through_sub", "parent_of", "holding_company_of"}
RELATED = {"affiliate_of"}
ALIAS = {"alias_of"}
NEEDS_COUNTERPARTY_MISSING = {"designation_controller"}
OUT_OF_SCOPE = {"transferred_to", "received_from", "wire_from_to",
                "shell_named", "used_shells", "nominee_for"}

OWNED_CONTROLLED_RE = re.compile(
    r"owned\s+(?:and/or\s+|or\s+|and\s+)?controlled\s+by", re.I)

# ---- name gating ----------------------------------------------------------
GENERIC_RE = re.compile(
    r"^(?:(?:the|this|that|such)\s+)?(?:proposed\s+)?(?:bank|company|"
    r"corporation|trust|venture|fund|association|partnership|firm|"
    r"institution|account|defendants?|issuer|borrower|lender|guarantor|"
    r"purchaser|seller|acquirer|depositor|servicer|sponsor|registrant|"
    r"reporting\s+person)$", re.I)
# A generic-definite tail ("… The Bank") marks OCC-decision heading glue —
# the real party name needs in-document resolution.
GENERIC_TAIL_RE = re.compile(
    r"\b(?:the|this|that)\s+(?:proposed\s+)?(?:bank|company|corporation|"
    r"trust|venture|fund|association)$", re.I)
STOPNAMES = {s.lower() for s in (
    "Alabama Alaska Arizona Arkansas California Colorado Connecticut Delaware "
    "Florida Georgia Hawaii Idaho Illinois Indiana Iowa Kansas Kentucky "
    "Louisiana Maine Maryland Massachusetts Michigan Minnesota Mississippi "
    "Missouri Montana Nebraska Nevada Ohio Oklahoma Oregon Pennsylvania "
    "Tennessee Texas Utah Vermont Virginia Washington Wisconsin Wyoming".split()
)} | {"united states", "united states of america", "america", "congress",
      "treasury", "government", "state", "states", "piano", "artwork",
      # agencies and regulators are never ownership parties in this corpus
      "occ", "fdic", "sec", "fincen", "ncua", "cfpb", "irs", "fbi", "doj",
      "federal reserve", "comptroller of the currency",
      # demographic groups from minority-owned-institution reporting
      "asian americans", "african americans", "native americans",
      "hispanic americans", "women", "minorities", "veterans",
      # jurisdictions and venue words that leak out of "based in …" clauses
      "british virgin islands", "virgin islands", "cayman islands",
      "hong kong", "jersey", "spa", "hotel", "resort", "casino"}
# Count phrases and generic plurals name a set, not a party.
GENERIC_PLURAL_RE = re.compile(
    r"(?:^(?:one|two|three|four|five|six|seven|eight|nine|ten|all|both|"
    r"several|these|those|following)\b.*|.*\b(?:entities|companies|firms|"
    r"individuals)$)", re.I)
PRONOUN_START_RE = re.compile(r"^(?:he|she|it|they|we|who|whose)\b", re.I)

# Sentence fragments and footnote references glued onto a name by
# upstream sentence-window matching.
_SENTENCE_GLUE_RE = re.compile(r"(?<=[a-z]{2})\.\s+(?=[A-Z])")
_FOOTNOTE_GLUE_RE = re.compile(r"(?<=[a-z])\.\d+\s+")
_LEAD_CONNECTIVE_RE = re.compile(
    r"^(?:pursuant\s+to|according\s+to|in\s+re|the)\s+", re.I)
_BARE_SUFFIX_WORDS = {"limited", "ltd", "inc", "llc", "corp", "corporation",
                      "company", "co", "holdings", "holding", "group",
                      "bank", "fund", "association", "partners",
                      "partnership", "trust", "savings", "national",
                      "federal", "commercial", "banking", "state"}
_US_STATES = {s.lower() for s in (
    "Alabama Alaska Arizona Arkansas California Colorado Connecticut Delaware "
    "Florida Georgia Hawaii Idaho Illinois Indiana Iowa Kansas Kentucky "
    "Louisiana Maine Maryland Massachusetts Michigan Minnesota Mississippi "
    "Missouri Montana Nebraska Nevada Ohio Oklahoma Oregon Pennsylvania "
    "Tennessee Texas Utah Vermont Virginia Washington Wisconsin Wyoming".split()
)} | {"new york", "new jersey", "new mexico", "new hampshire",
      "north carolina", "north dakota", "south carolina", "south dakota",
      "rhode island", "west virginia"}


def sanitize(name):
    """Trim sentence/footnote glue that leaked into a captured name."""
    if not name:
        return name
    for splitter in (_SENTENCE_GLUE_RE, _FOOTNOTE_GLUE_RE):
        parts = splitter.split(name)
        if len(parts) > 1:
            name = parts[-1]
    name = _LEAD_CONNECTIVE_RE.sub("", name)
    name = re.sub(r"^[A-Z][a-z]+(?:\s[A-Z][a-z]+)?-based\s+", "", name)
    # SEC filing-header glue ("SCHEDULE 13G Exhibit 1 <name>").
    name = re.sub(r"^(?:(?:SCHEDULE|FORM|EXHIBIT|ITEM|Exhibit|Item|Amendment)"
                  r"\s+[\w./-]{1,10}\s+)+", "", name)
    return name.strip(" ,;:.") or None

SUFFIX_RE = re.compile(
    r"\b(?:LLC|L\.L\.C\.|Inc\.?|Corp\.?|Corporation|Company|Compan(?:y|ies)|"
    r"Co\.|Ltd\.?|Limited|Incorporated|LP|L\.P\.|LLP|PLLC|PLC|GmbH|N\.V\.|"
    r"Holdings?|Group|Trust|Bank|Bancorp|Bancshares|N\.A\.|S\.?A\.?R\.?L\.?|"
    r"Partners(?:hip)?|Fund|Association|OOO|OAO|ZAO|PAO|AD|EOOD|SARL|SA|AG)"
    r"\.?\s*$", re.I)
PERSON_SHAPE_RE = re.compile(
    r"^[A-Z][A-Za-z'’\-]+(?:\s+[A-Z]\.?)?(?:\s+[A-Z][A-Za-z'’\-]+){1,3}$")
ACRONYM_RE = re.compile(r"^[A-Z0-9&\-]{2,8}$")
NAMELIST_SPLIT_RE = re.compile(r",\s+|,?\s+and\s+")
MONTH_DATE_RE = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|October|"
    r"November|December)\s+(\d{1,2}),?\s+((?:19|20)\d{2})\b")
MONTHS = {m: i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"])}


def norm(name: str) -> str:
    """Matching key. Same-family suffix abbreviations canonicalize (Corp ≡
    Corporation); cross-family pairs (Company vs Corp) deliberately do NOT —
    those become merge candidates, never automatic merges."""
    n = re.sub(r"\s+", " ", name).strip(" ,;:.").lower()
    n = re.sub(r"[.,’']", "", n)
    n = re.sub(r"\bincorporated\b", "inc", n)
    n = re.sub(r"\blimited\b", "ltd", n)
    n = re.sub(r"\bcorporation\b", "corp", n)
    n = re.sub(r"\bcompany\b", "co", n)
    n = re.sub(r"\bcompanies\b", "cos", n)
    n = re.sub(r"\bl\s?l\s?c\b", "llc", n)
    n = re.sub(r"\bl\s?p\b", "lp", n)
    n = re.sub(r"\bnational association\b", "na", n)
    n = re.sub(r"\bn\s?a\b", "na", n)
    n = re.sub(r"^the\s+", "", n)
    return n


def gate(name):
    """Reason the name cannot enter the graph, or None if admissible."""
    if not name:
        return "missing party"
    if GENERIC_RE.match(name) or GENERIC_TAIL_RE.search(name):
        return "document-generic reference; needs in-document resolution"
    if norm(name) in STOPNAMES:
        return "stop-listed name (place/agency/group, not an owner party)"
    if len(norm(name)) < 3:
        return "name too short to identify a party"
    if all(w in _BARE_SUFFIX_WORDS for w in norm(name).split()):
        return "bare corporate-suffix token(s), not a name"
    if GENERIC_PLURAL_RE.match(name):
        return "count phrase / generic plural, not a named party"
    toks = norm(name).split()
    if (len(toks) >= 2
            and toks[-1] in ("corporation", "corp", "company", "co", "llc",
                             "bank", "trust")
            and " ".join(toks[:-1]) in _US_STATES):
        return "jurisdiction-form phrase, not a party name"
    if PRONOUN_START_RE.match(name):
        return "clause fragment, not a name"
    if all(len(t) <= 2 for t in name.split()):
        return "initials-only fragment"
    return None


def classify(name: str, role: str) -> str:
    """'entity' | 'person'. role: owner|owned|alias_subject."""
    if SUFFIX_RE.search(name):
        return "entity"
    tokens = name.split()
    if len(tokens) == 1:
        if ACRONYM_RE.match(name):
            return "entity"
        # Single defined surname: an owner is presumed a person (SEC/OFAC
        # defined-term usage), an owned party is presumed an entity.
        return "person" if role in ("owner", "alias_subject") else "entity"
    if PERSON_SHAPE_RE.match(name) and len(tokens) <= 4:
        return "person"
    return "entity"


def maybe_split_owner_list(name: str):
    """Split "Lucas, Nunns and McNaul" style lists; never split names
    that carry a corporate suffix (e.g. "Cravath, Swaine & Moore LLP")."""
    if SUFFIX_RE.search(name):
        return [name]
    parts = [p for p in NAMELIST_SPLIT_RE.split(name) if p]
    if len(parts) < 2:
        return [name]
    if all(len(p.split()) <= 4 and p[:1].isupper() for p in parts):
        return [p for p in parts
                if "affiliated entities" not in p.lower()] or [name]
    return [name]


# ---- designation-counterparty resolution ----------------------------------
# OFAC narratives state "<Entity> is being designated for being owned or
# controlled by <Controller>", but the sentence window that produced the
# observation often opens after <Entity>. When the derived text tree is
# available, re-read a 500-char window ending at the observation span and
# take the LAST designation clause — the one the observation came from.
# `[^.\n]` keeps the captured name inside one sentence; names containing
# periods (e.g. "Co., Ltd.") deliberately fail and stay unresolved rather
# than resolve wrongly.
_DESIG_RE = re.compile(
    r"([A-Z][^.\n]{2,90}?)\s*(?:\([^)]{0,80}\)\s*)?,?\s*"
    r"(?:along\s+with[^,]{0,80},\s*)?"
    r"(?:is|are|was|were)\s+(?:also\s+)?(?:being\s+)?(?:concurrently\s+)?"
    r"designated\b[^.]{0,220}?for\s+being\s+owned\s+or\s+controlled\s+by")
_DESIG_TRAIL_RE = re.compile(
    r",?\s*(?:along\s+with\b.*|based\s+in\b.*|located\s+in\b.*|which\b.*|"
    r"while\b.*|registered\s+in\b.*|(?:is\s+)?an\s+entity\b.*|whose\b.*)$",
    re.I | re.S)
_DESIG_LEAD_RE = re.compile(
    r"^(?:Concurrent(?:ly)?\s+(?:to|with)[^,]{0,60},\s*|"
    r"(?:Today|In\s+addition|Additionally|Finally|Also|Separately)\s*,\s*|"
    r"[A-Z][a-z]+-based\s+|the\s+)+")


def resolve_designated(o):
    """Return the designated-entity name for a designation_controller
    observation, or None if it cannot be resolved strictly."""
    sha = o.get("source_sha256")
    if not sha:
        return None
    path = os.path.join(TEXT_ROOT, sha[:2], sha[2:] + ".txt")
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return None
    s, e = o["character_start"], o["character_end"]
    window = text[max(0, s - 500):e]
    matches = list(_DESIG_RE.finditer(window))
    if not matches:
        return None
    m = matches[-1]
    # The clause must be the observation's own: the stated controller
    # appears shortly after "controlled by".
    subj_tok = (o.get("subject_raw") or "").split()
    if subj_tok and window.find(subj_tok[-1][:14], m.end(), m.end() + 200) < 0:
        return None
    name = _DESIG_TRAIL_RE.sub("", m.group(1)).strip(" ,;:")
    name = re.sub(r"\s*\([^)]{0,60}\)", "", name)
    name = _DESIG_LEAD_RE.sub("", name).strip(" ,;:")
    # Drop any leading lower-case clause fragment before the name proper.
    words = name.split()
    while words and not words[0][:1].isupper():
        words.pop(0)
    name = " ".join(words)
    # List glue that still contains the controller ("X, and Y are being
    # designated…") resolves nothing attributable — leave unresolved.
    subj = o.get("subject_raw") or ""
    if subj and re.search(re.escape(subj) + r"\s*,", name):
        return None
    return name or None


def iso_source_date(date_raw):
    if not date_raw:
        return None
    m = MONTH_DATE_RE.search(date_raw)
    if not m:
        return None
    return f"{int(m.group(3)):04d}-{MONTHS[m.group(1)]:02d}-{int(m.group(2)):02d}"


class Nodes:
    def __init__(self):
        self.entities = {}   # norm -> record
        self.people = {}     # norm -> record
        self.variants = defaultdict(Counter)  # norm -> raw spellings seen

    def add(self, name: str, kind: str) -> str:
        key = norm(name)
        self.variants[key][re.sub(r"\s+", " ", name).strip(" ,;:.")] += 1
        digest = hashlib.sha256(key.encode()).hexdigest()[:16]
        if kind == "entity":
            rec = self.entities.setdefault(key, {
                "entity_id": f"obs-ent:{digest}",
                "legal_name": None,          # filled at finalize
                "jurisdiction": "UNKNOWN",
                "entity_type": None,
                "identity_basis": "name-as-evidenced (content-pass-2)",
            })
            return rec["entity_id"]
        rec = self.people.setdefault(key, {
            "person_id": f"p:obs-{digest}",
            "normalized_name": None,         # filled at finalize
            "name_variants": None,
            "identity_basis": "name-as-evidenced (content-pass-2)",
        })
        return rec["person_id"]

    def finalize(self):
        for key, rec in self.entities.items():
            # Most-seen spelling wins; ties break to the longest.
            best = sorted(self.variants[key].items(),
                          key=lambda kv: (-kv[1], -len(kv[0]), kv[0]))[0][0]
            rec["legal_name"] = best
        for key, rec in self.people.items():
            spellings = sorted(self.variants[key].items(),
                               key=lambda kv: (-kv[1], -len(kv[0]), kv[0]))
            rec["normalized_name"] = spellings[0][0]
            variants = [s for s, _ in spellings[1:]]
            extra = rec.pop("_extra_variants", [])
            merged = sorted(set(variants) | set(extra))
            rec["name_variants"] = merged or None


# ---- cross-document entity resolution -------------------------------------
# Nodes are names-as-evidenced; the same party recurs across documents under
# spelling variants. Two-tier policy:
#   MERGE (recorded on the surviving node as merged_from/merge_basis):
#     - alias-evidenced unions: an f/k/a, n/k/a, d/b/a, or a/k/a record whose
#       target exists as a separate same-kind node names the same party;
#     - same-family suffix abbreviation unions happen upstream in norm().
#   CANDIDATE ONLY (written to unresolved/, never merged automatically):
#     - cross-family suffixes ("X Company" vs "X Corp" may differ legally);
#     - prefix containment ("Wellington Group" vs "Wellington Management
#       Group");
#     - bare surname vs full person name ("Nunns" vs "John Nunns").
_SUFFIXY_TOKENS = {"inc", "corp", "co", "cos", "ltd", "llc", "lp", "llp",
                   "plc", "na", "trust", "bank", "group", "holdings",
                   "holding", "fund", "association", "partners",
                   "partnership", "sa", "ag", "gmbh", "nv"}


def cross_document_resolution(nodes, edges, names, stats):
    parent = {}

    def find(k):
        while parent.get(k, k) != k:
            parent[k] = parent.get(parent[k], parent[k])
            k = parent[k]
        return k

    def union(a, b, basis, bases):
        ra, rb = find(a), find(b)
        if ra == rb:
            return
        parent[max(ra, rb)] = min(ra, rb)
        bases.setdefault(a, set()).add(basis)
        bases.setdefault(b, set()).add(basis)
        stats[f"merge:{basis}"] += 1

    ekey_by_id = {r["entity_id"]: k for k, r in nodes.entities.items()}
    bases = {}

    for rec in names:
        src_key = ekey_by_id.get(rec["entity_id"])
        tgt_key = norm(rec["name"])
        if src_key and tgt_key in nodes.entities and tgt_key != src_key:
            basis = ("name-history f/k/a-n/k/a"
                     if rec["name_type"] in ("FORMER", "LEGAL")
                     else "name-history d/b/a")
            union(("E", src_key), ("E", tgt_key), basis, bases)
    for key, rec in nodes.people.items():
        for v in rec.get("_extra_variants", []):
            tgt = norm(re.sub(r"^d/b/a\s+", "", v))
            if tgt in nodes.people and tgt != key:
                union(("P", key), ("P", tgt), "a/k/a", bases)

    # Apply unions: representative = smallest node id in the group.
    groups = defaultdict(list)
    for kind, table in (("E", nodes.entities), ("P", nodes.people)):
        for key in table:
            groups[find((kind, key))].append((kind, key))
    idmap = {}
    for rep, members in groups.items():
        if len(members) < 2:
            continue
        kind = rep[0]
        table = nodes.entities if kind == "E" else nodes.people
        idf = "entity_id" if kind == "E" else "person_id"
        members_kr = sorted(((k, table[k]) for _, k in members),
                            key=lambda kr: kr[1][idf])
        (keep_key, keep), absorbed = members_kr[0], members_kr[1:]
        keep["merged_from"] = sorted(r[idf] for _, r in absorbed)
        keep["merge_basis"] = sorted(
            set().union(*(bases.get(m, set()) for m in members)) or {"variant"})
        for a_key, r in absorbed:
            idmap[r[idf]] = keep[idf]
            nodes.variants[keep_key] += nodes.variants.pop(a_key)
            if kind == "P":
                keep.setdefault("_extra_variants", []).extend(
                    r.get("_extra_variants", []))
            del table[a_key]

    kept_edges = []
    for e in edges:
        e["subject_id"] = idmap.get(e["subject_id"], e["subject_id"])
        e["object_id"] = idmap.get(e["object_id"], e["object_id"])
        if e["subject_id"] == e["object_id"]:
            stats["merge:dropped-self-loop-edge"] += 1
            continue
        kept_edges.append(e)
    edges[:] = kept_edges
    for rec in names:
        rec["entity_id"] = idmap.get(rec["entity_id"], rec["entity_id"])

    # -- candidates: recorded, never merged --
    cands = []
    ent_keys = sorted(nodes.entities)
    stems = defaultdict(list)
    for k in ent_keys:
        toks = k.split()
        if len(toks) >= 2 and toks[-1] in _SUFFIXY_TOKENS:
            stems[" ".join(toks[:-1])].append(k)
        stems[k].append(k)
    for stem, ks in sorted(stems.items()):
        ks = sorted(set(ks))
        if len(stem.split()) >= 2:
            for i in range(len(ks)):
                for j in range(i + 1, len(ks)):
                    cands.append(("cross-family-suffix", ks[i], ks[j]))
    toklists = [(k.split(), k) for k in ent_keys]
    for i, (ta, ka) in enumerate(toklists):
        if len(ta) < 2:
            continue
        for tb, kb in toklists[i + 1:]:
            if tb[:len(ta)] != ta:
                break
            if len(tb) > len(ta):
                cands.append(("prefix-containment", ka, kb))
    ppl_by_last = defaultdict(list)
    for k in nodes.people:
        toks = k.split()
        if len(toks) >= 2:
            ppl_by_last[toks[-1]].append(k)
    for k in sorted(nodes.people):
        if " " not in k and k in ppl_by_last:
            for full in sorted(ppl_by_last[k]):
                cands.append(("surname-of", k, full))

    out = []
    seen = set()
    for kind, a, b in cands:
        ta = nodes.entities if kind != "surname-of" else nodes.people
        ra, rb = ta.get(a), ta.get(b)
        if not ra or not rb:
            continue
        idf = "entity_id" if kind != "surname-of" else "person_id"
        pair = (kind, ra[idf], rb[idf])
        if pair in seen:
            continue
        seen.add(pair)
        out.append({"candidate_kind": kind, "a_id": ra[idf], "a_key": a,
                    "b_id": rb[idf], "b_key": b,
                    "note": "recorded for review; never merged automatically"})
        stats[f"merge-candidate:{kind}"] += 1
    return sorted(out, key=lambda r: (r["candidate_kind"], r["a_id"], r["b_id"]))


def write_jsonl(path, records):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, sort_keys=True, ensure_ascii=False) + "\n")


def main():
    obs = [json.loads(l) for l in open(OBS, encoding="utf-8")]
    obs.sort(key=lambda r: r["observation_id"])

    nodes = Nodes()
    edges, names, unresolved = [], [], []
    stats = Counter()

    def to_unresolved(o, reason, **extra):
        stats[f"unresolved:{reason.split(';')[0]}"] += 1
        unresolved.append({
            "observation_id": o["observation_id"],
            "reason": reason,
            "predicate_raw": o["predicate_raw"],
            "subject_raw": o.get("subject_raw"),
            "object_raw": o.get("object_raw"),
            "source_url": o.get("source_url"),
            "source_sha256": o.get("source_sha256"),
            "evidentiary_posture": o.get("evidentiary_posture"),
            "raw_text": (o.get("raw_text") or "")[:400],
            **extra})

    def provenance(o):
        return {
            "source_id": o["observation_id"],
            "source_url": o["source_url"],
            "source_date": iso_source_date(o.get("date_raw")),
            "retrieved_at": o["retrieval_date"],
            "source_sha256": o["source_sha256"],
            "source_locator": (f"chars {o['character_start']}-"
                               f"{o['character_end']}; lines "
                               f"{o.get('line_start')}-{o.get('line_end')}"),
        }

    def emit_edge(o, assertion, subj_name, subj_role, obj_name, obj_role,
                  conf=None, extra=None):
        subj_name, obj_name = sanitize(subj_name), sanitize(obj_name)
        for nm, why in ((subj_name, "subject"), (obj_name, "object")):
            reason = gate(nm)
            if reason:
                to_unresolved(o, f"{why}: {reason}")
                return
        if norm(subj_name) == norm(obj_name):
            to_unresolved(o, "subject and object normalize identically")
            return
        subj_id = nodes.add(subj_name, classify(subj_name, subj_role))
        obj_id = nodes.add(obj_name, classify(obj_name, obj_role))
        pct = None
        if o.get("percentage_raw"):
            try:
                pct = min(100.0, max(0.0, float(o["percentage_raw"])))
            except ValueError:
                pct = None
        edges.append({
            "subject_id": subj_id,
            "assertion": assertion,
            "object_id": obj_id,
            "ownership_percent": pct,
            "evidence_class": "DIRECT",
            "confidence": conf if conf is not None else o.get("extraction_confidence"),
            "evidentiary_posture": o.get("evidentiary_posture"),
            "predicate_raw": o["predicate_raw"],
            **(extra or {}),
            **provenance(o)})
        stats[f"edge:{assertion}"] += 1

    for o in obs:
        pred = o["predicate_raw"]
        subj, objn = o.get("subject_raw"), o.get("object_raw")

        if pred in OUT_OF_SCOPE:
            stats["skipped:out-of-scope (flows / entity properties)"] += 1
            continue
        if pred in NEEDS_COUNTERPARTY_MISSING or (
                pred not in ALIAS and not objn):
            resolved = (resolve_designated(o)
                        if pred in NEEDS_COUNTERPARTY_MISSING else None)
            if resolved:
                for owned in maybe_split_owner_list(resolved):
                    emit_edge(o, "BENEFICIAL_OWNER", subj, "owner",
                              owned, "owned", conf=0.7,
                              extra={"resolution": "designation-window"})
                continue
            to_unresolved(o, "counterparty not in sentence window "
                             "(controller known, controlled party upstream)")
            continue
        if (o.get("extraction_confidence") or 0) < 0.9:
            to_unresolved(o, "sub-threshold extraction confidence; "
                             "party naming needs in-document resolution")
            continue

        if pred in OWNERSHIP or pred in CONTROL:
            if pred in OWNERSHIP:
                assertion = "BENEFICIAL_OWNER"
            elif OWNED_CONTROLLED_RE.search(o.get("raw_text") or ""):
                assertion = "BENEFICIAL_OWNER"  # "owned or controlled by"
            else:
                assertion = "UNKNOWN_CONTROL_ROLE"
            for owner in maybe_split_owner_list(subj or ""):
                emit_edge(o, assertion, owner, "owner", objn, "owned")
        elif pred in PARENT_PREDS:
            emit_edge(o, "PARENT", subj, "owner", objn, "owned")
        elif pred in RELATED:
            emit_edge(o, "RELATED_ORGANIZATION", subj, "owned", objn, "owned")
        elif pred in ALIAS:
            subj, objn = sanitize(subj), sanitize(objn)
            reason = gate(subj) or gate(objn)
            if reason:
                to_unresolved(o, reason)
                continue
            kind = classify(subj, "alias_subject")
            marker = "DBA"
            text = o.get("raw_text") or ""
            pos = text.find(objn[:40]) if objn else -1
            window = text[max(0, pos - 30):pos].lower() if pos > 0 else text.lower()
            if "f/k/a" in window:
                marker = "FORMER"
            elif "n/k/a" in window:
                marker = "LEGAL"
            if kind == "entity":
                ent_id = nodes.add(subj, "entity")
                names.append({
                    "entity_id": ent_id,
                    "name": re.sub(r"\s+", " ", objn).strip(" ,;:."),
                    "name_type": marker,
                    **{k: v for k, v in provenance(o).items()
                       if k in ("source_url", "source_id", "retrieved_at")},
                    "sha256": o["source_sha256"],
                    "valid_from": None, "valid_to": None,
                    "jurisdiction": None})
                stats["name-record"] += 1
            else:
                nodes.add(subj, "person")
                rec = nodes.people[norm(subj)]
                extra = rec.setdefault("_extra_variants", [])
                alias_kind = ("dba" if "d/b/a" in window or "doing business"
                              in window else "aka")
                tag = re.sub(r"\s+", " ", objn).strip(" ,;:.")
                extra.append(tag if alias_kind == "aka" else f"d/b/a {tag}")
                stats["person-alias"] += 1
        else:
            to_unresolved(o, f"no mapping for predicate {pred}")

    merge_candidates = cross_document_resolution(nodes, edges, names, stats)

    nodes.finalize()

    ent_rows = sorted(nodes.entities.values(), key=lambda r: r["entity_id"])
    ppl_rows = sorted(nodes.people.values(), key=lambda r: r["person_id"])
    for rec in ppl_rows:
        rec.pop("_extra_variants", None)
    edges.sort(key=lambda r: (r["assertion"], r["subject_id"],
                              r["object_id"], r["source_id"]))
    names.sort(key=lambda r: (r["entity_id"], r["name"], r["source_id"]))
    unresolved.sort(key=lambda r: r["observation_id"])

    write_jsonl(os.path.join(ROOT, "entities", f"{SUFFIX}.jsonl"), ent_rows)
    write_jsonl(os.path.join(ROOT, "people", f"{SUFFIX}.jsonl"), ppl_rows)
    write_jsonl(os.path.join(ROOT, "edges", f"{SUFFIX}.jsonl"), edges)
    write_jsonl(os.path.join(ROOT, "names", f"{SUFFIX}.jsonl"), names)
    write_jsonl(os.path.join(ROOT, "unresolved", f"{SUFFIX}.jsonl"), unresolved)
    write_jsonl(os.path.join(ROOT, "unresolved", "pass2-merge-candidates.jsonl"),
                merge_candidates)

    print(f"entities={len(ent_rows)} people={len(ppl_rows)} "
          f"edges={len(edges)} names={len(names)} unresolved={len(unresolved)} "
          f"merge_candidates={len(merge_candidates)}")
    for k, v in sorted(stats.items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
