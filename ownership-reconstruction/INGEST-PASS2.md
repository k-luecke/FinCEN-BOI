# Ingest: content-pass-2 observations → graph (`pass2-observations` files)

**Built 2026-08-17** by `build_ownership_graph.py` (repo root) from the
1,977 raw observations in `content-pass-2/raw-observations.jsonl`
(observe/1.1.0 over the FULL 133k-object corpus — derived release
`derived-pass1-run-32040221002`; the earlier 530-observation build used
the 2026-08-15 38k-object snapshot). Deterministic and re-runnable.
Validated clean by `ownership_schema.py` (0 problems).

## Counts

| Table | Records |
|---|---|
| entities | 743 |
| people | 237 |
| edges | 1,022 |
| names (DBA/FORMER/LEGAL history) | 313 |
| unresolved | 291 (+ 41 merge candidates) |

213 person aliases (a/k/a spellings, d/b/a trade names) are recorded
on person nodes as `name_variants` / `dba_names`-style variants, not as
fabricated entities. 156 observations (financial flows, shell-status
statements) are out of scope for the ownership graph — no assertion in
the closed vocabulary describes them — and remain in `content-pass-2/`.

## Mapping rules

- **BENEFICIAL_OWNER** only for predicates in which the source itself
  states ownership ("owned by", percent-of-shares, beneficial-owner-of,
  "owned or controlled by"), always `evidence_class: DIRECT` — the
  cited sentence is quoted in the source observation and every edge
  carries `source_sha256` + character/line locators into the archived
  bytes. Each edge also carries the observation's `evidentiary_posture`
  (allegation vs finding vs designation), so analysis can weight
  accordingly.
- **UNKNOWN_CONTROL_ROLE** for pure-control statements ("controlled
  by" without ownership wording, "exercises control") — never promoted.
- **PARENT** for subsidiary/holding-company/operates-through frames;
  **RELATED_ORGANIZATION** for affiliates.
- **Aliases** become `names/` history records for entities (d/b/a,
  a/k/a → DBA; f/k/a → FORMER; n/k/a → LEGAL) and name variants for
  people.
- **Owner lists** ("Lucas, Nunns and McNaul") split into one edge per
  named owner; names carrying a corporate suffix are never split.
- Nodes are **names-as-evidenced** (the schema's person rule, applied
  to observation-derived entities as well): a shared normalized string
  is one node; no identity resolution beyond that is attempted, and
  entity `jurisdiction` is `UNKNOWN` pending registry joins.

## Designation-window resolution

When `derived/text` is present, a second stage re-reads a 500-char
window before each OFAC "designated for being owned or controlled by
X" observation and extracts the designated entity from the same
designation clause (strict single-sentence pattern; the controller
must appear after "controlled by"; list glue, count phrases, clause
fragments, and jurisdiction leaks are gated out). At full-corpus scale this resolved 70 of
86 counterparty-missing observations into BENEFICIAL_OWNER edges
at confidence 0.7, tagged `"resolution": "designation-window"` — the
Deripaska, Rotenberg, Bazzi, Tesic, and Tatulian networks among them.

## Dates

Three dates per edge, never conflated: `source_date` = when the
document was published/filed; `valid_from` = when the relationship
applies (a full date stated in the evidence sentence, else the
filing's own event/report-period date); `retrieved_at` = when we
archived it. Both extracted dates carry a basis
(`source_date_basis` / `valid_from_basis`); SEC forms also carry
`source_form`.

`content_pass_2.doc_dates` extracts them deterministically. For SEC
EDGAR documents the authoritative source is the archived
submissions.zip bulk snapshot (per-CIK metadata joined by accession —
pass `--edgar-zip` or set `EDGAR_SUBMISSIONS_ZIP`; object sha
`ec07d8ce…` in release `objects-run-31863924882`). Text datelines,
13D/G event blocks, and URL dates are fallbacks; a document whose head
carries no extractable date stays undated rather than borrowing a
body date.

Coverage: 871/1220 documents publication-dated (533 by EDGAR
metadata), 224 event-dated; 761/959 edges (79%) carry `source_date`,
331 (34%) carry `valid_from`; 234/391 unique relationships (59%) have
a temporal envelope.

## In-document defined-term resolution

Legal documents define short references once and use them throughout
(`Wells Fargo Bank, N.A. ("WFB" or the "Bank")`). `content_pass_2.
defined_terms` extracts 8,944 such definitions across 953 documents
(quoted definitions + initials-verified acronyms; terms defined twice
with different full names are ambiguous and resolve nothing). The
builder resolves party names strictly within their own document,
records the as-stated wording on the edge
(`subject_as_stated`/`object_as_stated`, `resolution: defined-term`),
and restores confidence (0.75) for generic parties that resolved —
recovering 60+ previously sub-threshold observations ("the Bank" in
OCC/SEC material) and dissolving acronym nodes (WFB) into their full
entities.

## Cross-document entity resolution

Two-tier policy, per the dataset ground rule that ambiguity is
recorded, never guessed:

- **Merged automatically** (recorded on the surviving node as
  `merged_from` + `merge_basis`): same-family suffix abbreviations
  unify at the matching key ("Bankmont Financial Corp" ≡
  "…Corporation", Inc ≡ Incorporated, Co ≡ Company, LLC ≡ L.L.C.),
  and alias-evidenced unions where an f/k/a, n/k/a, d/b/a, or a/k/a
  record's target exists as a separate same-kind node. Edges that
  become self-loops after a merge are dropped with a stat.
- **Candidates only** (`unresolved/pass2-merge-candidates.jsonl`, 26
  records): cross-family suffix pairs ("BMO Nesbitt Burns Corp" vs
  "…Inc", "Washington Mutual Bank" vs "Washington Mutual, Inc" — may
  be legally distinct entities), prefix containment ("Wellington
  Group" vs "Wellington Group Holdings LLP"), and bare surnames vs
  full person names. Recorded for review, never merged automatically.

## What goes to `unresolved/` (342)

- 16 — controller stated but the controlled party still outside even
  the widened window (or the name failed strict capture).
- 132 — sub-threshold extraction confidence (document-generic parties
  like "the Bank" needing in-document resolution — mostly OCC/FDIC
  decisions at full-corpus scale).
- 192 — name-quality rejections: generic references, count phrases,
  jurisdiction-form phrases ("Delaware corporation"), heading glue,
  clause fragments, stop-listed non-parties, bare suffix tokens,
  self-loops after sanitation.

## Known limits

Names truncated or polluted by upstream capture noise survive here as
node names ("Pawel" for Pawel P. Dynkowski; merger-clause glue in one
parent name); each edge links back to its observation and archived
source, so these resolve at analysis time without loss. No CTA-filed
BOI data is present or sought; every edge traces to a public record.
