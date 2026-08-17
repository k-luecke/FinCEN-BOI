# Ingest: content-pass-2 observations → graph (`pass2-observations` files)

**Built 2026-08-17** by `build_ownership_graph.py` (repo root) from the
530 raw observations in `content-pass-2/raw-observations.jsonl`
(observe/1.1.0 over the 2026-08-15 corpus snapshot). Deterministic and
re-runnable; re-run after each observation refresh — the full-corpus
observation set will replace these files via the same command.
Validated clean by `ownership_schema.py` (0 problems).

## Counts

| Table | Records |
|---|---|
| entities | 156 |
| people | 104 |
| edges | 101 (55 BENEFICIAL_OWNER · 41 PARENT · 4 UNKNOWN_CONTROL_ROLE · 1 RELATED_ORGANIZATION) |
| names (DBA/FORMER/LEGAL history) | 126 |
| unresolved | 139 |

117 person aliases (a/k/a spellings, d/b/a trade names) are recorded
on person nodes as `name_variants` / `dba_names`-style variants, not as
fabricated entities. 55 observations (financial flows, shell-status
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

## What goes to `unresolved/` (139)

- 86 — controller stated but the controlled party sits outside the
  sentence window (OFAC "designated for being owned or controlled by
  X" narratives; the designated entity needs paragraph-level
  resolution — top of the follow-up list, since each names a real
  controller).
- 22 — sub-threshold extraction confidence (document-generic parties
  like "the Bank" needing in-document resolution).
- 31 — name-quality rejections: generic references, heading glue,
  stop-listed places/agencies/demographic groups, bare suffix tokens,
  self-loops after sanitation.

## Known limits

Names truncated or polluted by upstream capture noise survive here as
node names ("Pawel" for Pawel P. Dynkowski; merger-clause glue in one
parent name); each edge links back to its observation and archived
source, so these resolve at analysis time without loss. No CTA-filed
BOI data is present or sought; every edge traces to a public record.
