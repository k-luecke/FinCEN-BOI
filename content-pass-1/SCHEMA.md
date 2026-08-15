# Content Pass 1 — schemas

Corpus reconnaissance over the archived object store. **This pass emits no
graph facts.** Its products are: inventory → extracted text → document
classification → candidate evidence spans → ranked reconnaissance index.
Adjudication of evidence belongs to later passes.

Pipeline (all deterministic; no LLM classification was used in this pass):

```
python3 -m content_pass_1.inventory          # Step 1
python3 -m content_pass_1.extract            # Step 2 (resumable)
python3 -m content_pass_1.scan boilerplate   # Step 9
python3 -m content_pass_1.scan scan          # Steps 3-6 (resumable)
python3 -m content_pass_1.buckets            # Step 8
python3 -m content_pass_1.dedup              # Step 7
python3 -m content_pass_1.finalize           # ocr-required / errors
python3 -m content_pass_1.qc                 # Step 14 sample
python3 -m content_pass_1.metrics_report metrics
python3 -m content_pass_1.metrics_report top
```

Inputs: `manifest.jsonl`, `ledger.jsonl`, and `archive/objects/sha256/…`
(restored from the `objects-run-*` GitHub Releases; tar paths match
`object_path`). Archived source bytes are read-only throughout; every
derived artifact references its source object's SHA-256.

Derived layout (gitignored, reproducible, published as release assets):

```
derived/
  text/<aa>/<sha256>.txt          # raw extracted representation
  metadata/<aa>/<sha256>.container.json   # safe ZIP member indexes
  reconnaissance/boilerplate/<host>.json  # per-host boilerplate line hashes
```

## corpus-inventory.jsonl — one record per unique durable object

| field | meaning |
|---|---|
| `sha256` | content address (primary key across all Pass-1 outputs) |
| `object_path` | tar/store-relative path from the manifest |
| `present_on_disk` / `size_bytes` | restored-object status |
| `claimed_content_type` | HTTP Content-Type at retrieval |
| `sniffed_mime` | magic-byte detection over the stored bytes |
| `mime_conflict` | claimed vs sniffed disagree (extension is never trusted) |
| `host`, `source_family`, `provenance` | origin classification |
| `url`, `final_url`, `retrieved_at` | primary (earliest) retrieval |
| `retrieval_count`, `urls[]` | every retrieval record referencing the object |
| `multi_url_object` | >1 distinct URL served these bytes |
| `url_has_multiple_versions` | some URL for this object also served other bytes (historical versions) |

## extraction-status.jsonl

`sha256`, `extractor` (`lxml-html` / `lxml-xml` / `json-canonical` /
`raw-decode` / `pdftotext` / `zip-index`), `extractor_version`,
`extraction_time`, `extraction_status` (`OK` / `EMPTY` / `NO_TEXT` /
`INDEXED_CONTAINER` / `UNSUPPORTED` / `ERROR` / `OBJECT_MISSING`),
`character_count`, `page_count` (PDF), `title`, `ocr_candidate`.

PDFs get native extraction only; `NO_TEXT` + `ocr_candidate` marks the
OCR backlog (`ocr-required.jsonl`, with a `high_value` flag). No bulk OCR
in Pass 1. ZIPs are safely *indexed* (member cap 2M, 50 GB uncompressed
cap, traversal-path counting, no extraction).

## document-classes.jsonl — one record per scanned document

Zero-or-more classes from the Step-3 vocabulary (`BOI_CTA`, `BOSS`,
`BENEFICIAL_OWNERSHIP`, `CORPORATE_OWNERSHIP`, `SUBSTANTIAL_CONTROL`,
`PARENT_SUBSIDIARY`, `SHELL_COMPANY`, `ENTITY_FORMATION`,
`ENTITY_DISSOLUTION`, `MERGER_ACQUISITION`, `OFFICER_DIRECTOR`,
`MEMBER_MANAGER`, `REGISTERED_AGENT`, `TRUST_NOMINEE`,
`FINANCIAL_TRANSACTION`, `WIRE_TRANSFER`, `BANK_ACCOUNT`, `BSA_AML`,
`SAR_RELATED`, `ENFORCEMENT`, `INVESTIGATION`, `CONGRESSIONAL_EVIDENCE`,
`COURT_RECORD`, `REAL_ESTATE`, `PROCUREMENT`, `SEC_OWNERSHIP`,
`SEC_SUBSIDIARY`, `UCC`, `SANCTIONS`, `LICENSING`, `UNCLASSIFIED`).
Classes are matched against boilerplate-suppressed text only. Also:
`candidate_count`, `candidate_categories`, `doc_review_priority` (sum of
top-10 span priorities), `boilerplate_lines_suppressed`,
`candidate_overflow` (spans beyond the per-category cap of 40 are counted,
not stored).

## evidence-candidates.jsonl — one record per candidate span

Candidate categories: `OWNERSHIP_EXPLICIT`, `CONTROL_EXPLICIT`,
`PARENT_SUBSIDIARY`, `SHELL_NOMINEE`, `ROLE_TITLE`, `FINANCIAL_FLOW`,
`SAR_BSA`, `BOI_CTA`, `FORMATION_DISSOLUTION`, `STRUCTURED` (regex
patterns of the shape PERSON+role+ENTITY, ENTITY+owned-by+X,
ENTITY+subsidiary-of+ENTITY, percent+of+ENTITY; captured groups are kept
verbatim in `matched_groups`, never resolved).

Locators are deterministic against the raw extracted representation:
`line_start`/`line_end` (1-based), `character_start`/`character_end`
(absolute offsets into `derived/text/<aa>/<sha>.txt`), `page_number` for
PDFs (from `\f` markers). `context_before`/`matched_text`/`context_after`
preserve ±300 chars.

`review_priority` is a **review ordering**, not a truth probability:
additive features recorded per candidate in `ranking_features`
(provenance/source-family weights, enforcement-URL hint, category weight,
percentage/amount/person+entity/date co-occurrence, definitional and
short-generic penalties). Nothing is discarded for ranking low.

## Bucket indexes (Step 8)

`ownership-candidates.jsonl`, `control-candidates.jsonl`,
`parent-subsidiary-candidates.jsonl`, `shell-structure-candidates.jsonl`,
`financial-flow-candidates.jsonl`, `boi-cta-candidates.jsonl`,
`sar-bsa-candidates.jsonl`, `congressional-candidates.jsonl` — same
record schema as evidence-candidates, filtered and sorted by
`review_priority` descending. Buckets overlap by design.

## near-duplicate-groups.jsonl

Bottom-64 sketches over 5-word shingles; LSH banding (16×4) for candidate
pairs; union-find at estimated Jaccard ≥ 0.85. Advisory only — every
source/provenance observation is preserved; nothing is deleted.

## qc-sample.jsonl

Seeded (RNG seed 20260815) sample: 25 high / 25 medium / 25 low priority
candidates + 25 no-evidence documents. `locator_correct` is machine
verified (offsets must reproduce `matched_text`). `manual_review` fields
(`false_positive`, `false_negative`, `text_extraction_correct`, `notes`)
are filled during review; results summarized in qc-review.md.

## Guarantees

- Archived source bytes are never modified; derived content lives apart.
- Raw extracted text and search-normalized (boilerplate-suppressed) text
  are kept separate; **all locators resolve against the raw form**.
- No candidate is promoted to an ownership/control/graph fact.
- People are not resolved; entities are not merged; shared addresses are
  not converted into ownership; role words are not converted into
  BENEFICIAL_OWNER.
