# observe/1.1.0 — grammar coverage upgrade

**Run date:** 2026-08-17 · against the Content Pass 1 (2026-08-15) derived
text tree restored from `derived-release-staging/` (verified
`d7eba7da…`). Deterministic; no LLM classification; every observation
carries a source-addressable locator and verbatim `raw_text`.

## Result

**530 unique raw observations** (was 113 under observe/1.0.0 — 4.7×),
with 274 duplicate matches from overlapping candidate spans now
suppressed instead of emitted (`duplicate_span` in
`observe-stats.json`). Largest buckets: `alias_of` 253 (d/b/a, a/k/a,
f/k/a chains — new), `designation_controller` 85 (OFAC "designated for
being owned or controlled by X" — new), `subsidiary_of` 51,
`transferred_to` 46, `controlled_by` 31, `owned_by` 21.

## What changed

- Corporate suffixes match case-insensitively, so ALL-CAPS court-caption
  names resolve ("ATLANTA CAPITAL LLC", "SEISMA OIL RESEARCH, LLC").
- Entity interior tokens exclude clause connectives and embedded
  suffixes, so names no longer swallow "…through another LLC" or run
  across sentence boundaries ("IBG LLC. IBG LLC").
- New name classes used only inside strict frames: definite
  document-defined references ("the Bank" — confidence capped at 0.55
  via `GENERIC_NAME_RE`), single defined surnames ("Irby"), ALL-CAPS
  person names, cooperating-source codes ("CS-2"), bounded proper-noun
  runs ("Central Bank of Iran"), comma name lists ("Lucas, Nunns and
  McNaul"), and OFAC prefix-form entities ("Limited Liability Company
  Garant-SV").
- Surname tokens allow interior capitals (McGhan, O'Brien) but must end
  lowercase, so they never stop mid-word.
- New grammars: appositive subsidiary/owner ("X, a wholly-owned
  subsidiary of Y"), `alias_of` (slash forms + "doing business as" only
  — prose "formerly known as" renames non-corporate things),
  `designation_controller`, `holding_company_of`, `affiliate_of`,
  `pct_interest_in`; verb coverage extended (will/would own, purchased,
  obtained, retained; compound qualifiers "direct, wholly-owned").
- Amounts tolerate OCR-spaced thousands ("$695, 000") and ranges
  ("between $300,000 to $400,000" records the lower bound).
- Court-caption prefixes stripped from names ("DEFENDANTS DAVID GREENE"
  → "DAVID GREENE").

## QC

Random 20-observation sample reviewed at each of three iterations;
tuning rounds removed the two observed false-positive classes
("formerly known as" on non-corporate renames; name-list merging via a
TITLECASE "and" connector) and the truncation classes listed above.
Residual known noise: caption run-ons can prepend docket fragments to a
subject, and OCC heading glue can pollute an object string — the
relation itself is correct and `raw_text` preserves ground truth; these
are resolution-layer concerns.

## Reproduce

```sh
# restore derived/ per derived-release-staging/README.md, then:
gunzip -k content-pass-1/corpus-inventory.jsonl.gz
python3 -m content_pass_2.observe
```
