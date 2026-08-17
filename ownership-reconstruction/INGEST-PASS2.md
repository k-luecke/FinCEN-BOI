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
| entities | 660 |
| people | 254 |
| edges | 966 (228 BENEFICIAL_OWNER · 704 PARENT · 23 UNKNOWN_CONTROL_ROLE · 11 RELATED_ORGANIZATION) |
| names (DBA/FORMER/LEGAL history) | 311 |
| unresolved | 342 (+ 26 merge candidates) |

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
