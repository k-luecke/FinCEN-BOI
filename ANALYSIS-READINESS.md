# Analysis Readiness — First Analysis Pass

Generated 2026-08-17 from the committed Content Pass 1 outputs
(`content-pass-1/`, snapshot of 2026-08-15T13:53Z) by
`analysis/pass1_analysis.py`. Full numbers in
`analysis/pass1-analysis.json`.

## Verdict: can we start analyzing yet?

**Yes — for corpus-level and candidate-span analysis.** Everything
needed is committed and self-contained: 98,780 candidate spans over
33,518 documents with byte-exact locators, document classes,
provenance, near-duplicate groups, and the extracted-text tree
(reassemblable from `derived-release-staging/`, sha256-verified).
Span locators were re-verified for this report: **25/25 randomly
sampled candidates and 20/20 top-ranked candidates resolve exactly**
against the derived text tree.

**No — for the project's headline goal** (quantifying the
ownership-information gap via the control graph). Blockers, in order
of impact:

| Blocker | Status | What unblocks it |
|---|---|---|
| Ownership graph empty | 0 entities, 0 people, 0 edges | Pass 2 must convert candidates to observations at scale |
| Pass 2 yield 0.3% | 113 observations from ~40k candidates | Grammar redesign — see diagnosis below |
| Pass 1 coverage lag | scanned 38,242 objects (Aug 15); corpus now 129,273 objects / 26.3 GB (~70% never scanned) | Re-run Pass 1 over release-asset objects |
| DOJ capture defect | 4,317 of 5,001 justice.gov objects are bot-challenge interstitials | Recrawl with challenge handling |
| Missing sources | federalregister.gov 0/319, congress.gov ≈0, gao.gov 2 docs in snapshot | Recrawl / allowlist fix |
| OCR backlog | 201 scanned PDFs + 5,001 FBI Vault pages (0 candidates extracted from FBI Vault so far) | OCR pass |
| EDGAR bulk unexploded | 986,468 CIK filing histories indexed, not parsed | Structured EDGAR pass |

Any "share of U.S. entities with a publicly identifiable controller"
statistic computed today would be unsound: the denominator is missing
EDGAR, Federal Register, congress.gov, GAO, and most of DOJ.

## First findings (cleaned)

Three corrections were applied on top of the raw Pass-1 numbers; all
three matter for anyone quoting these figures.

1. **Treasury sidebar boilerplate: exactly 5,000 candidates removed.**
   One navigation line ("…Terrorist Finance Tracking Program **Money
   Laundering** Financial Action Task Force…") escaped the 400-char
   boilerplate cap and accounts for **11.8% of all SAR_BSA
   candidates** (42,453 raw → 37,453 clean).
2. **Near-duplicate adjustment.** 1,529 groups / 6,385 non-canonical
   duplicate docs removed; shrinks candidate counts a further ~5%.
3. **Date-guess artifact.** 2,121 candidates (all sec.gov court
   judgments) carry `document_date=1934` — the parser is reading
   "Securities Exchange Act of 1934" citations as the document date
   (the URLs show 2008–2019 filings). **Pre-2000 bars in any year
   histogram are statute citations, not document ages.** 35 further
   docs have junk future dates.

### Candidate counts (raw → boilerplate-removed → dedup-adjusted)

| Category | Raw | Clean | Dedup |
|---|---|---|---|
| SAR_BSA | 42,453 | 37,453 | 35,529 |
| PARENT_SUBSIDIARY | 17,014 | 17,014 | 16,094 |
| FINANCIAL_FLOW | 10,250 | 10,250 | 9,817 |
| ROLE_TITLE | 8,850 | 8,850 | 8,246 |
| OWNERSHIP_EXPLICIT | 6,763 | 6,763 | 6,514 |
| FORMATION_DISSOLUTION | 4,261 | 4,261 | 3,967 |
| SHELL_NOMINEE | 3,804 | 3,804 | 3,643 |
| CONTROL_EXPLICIT | 2,654 | 2,654 | 2,569 |
| BOI_CTA | 2,592 | 2,592 | 2,538 |
| STRUCTURED | 139 | 139 | 122 |

Ownership-bearing documents: **4,024 clean / 3,816 dedup-adjusted**
(14.1% of the 27,133 canonical text-bearing docs).

### Which sources actually carry ownership evidence

Ownership-bearing rate = docs with OWNERSHIP_EXPLICIT ∪
CONTROL_EXPLICIT ∪ PARENT_SUBSIDIARY ∪ STRUCTURED, per docs scanned:

| Family | Scanned | Own-bearing (dedup) | Rate |
|---|---|---|---|
| GOVINFO | 494 | 156 | **31.8%** |
| OCC | 4,875 | 1,453 | **31.6%** |
| FINCEN | 2,872 | 485 | 18.1% |
| SEC | 4,603 | 585 | 13.6% |
| TREASURY | 5,001 | 643 | 13.5% |
| FDIC | 5,000 | 411 | 8.4% |
| DOJ | 684 | 39 | 5.9% |
| CONGRESS_OVERSIGHT | 4,912 | 38 | 0.8% |
| FBI_VAULT | 5,001 | 0 | 0% (scans, pending OCR) |

OCC licensing/enforcement orders and govinfo compilations are the
densest per-document sources; SEC's rate is understated because its
densest material (litigation PDFs, EDGAR bulk) is under-covered in
this snapshot. The DOJ row is 684 *real* pages (the 4,317
interstitials never reached extraction).

Top-ranked candidates resolve to genuine ownership chains — e.g. the
FDIC Signature Bridge receivership release (priority 18/18): "Hancock
JV Bidco L.L.C., an entity indirectly controlled by Blackstone, Inc.
… paid $1.2 billion for a 20 percent equity interest in SIG CRE 2023
Venture LLC … wholly owned by the FDIC–Receiver." All 20 top spans
verified byte-exact.

## Why Pass 2 converts only 0.3% — diagnosis

Structural-feature sampling of `no_grammar_match` candidates (40 per
bucket, seed 20260817; see `pass2_grammar_miss_diagnosis` in the
JSON):

- **Most missed candidates are *mentions*, not *assertions*.** In
  C_PARENT_SUBSIDIARY, D_SHELL_NOMINEE, and E_FINANCIAL_FLOW, ~70%
  of sampled misses have no relational verb near the span
  ("subsidiaries", "shell companies", "wire transfers" as bare noun
  phrases) — no grammar can extract an edge from these. The honest
  ceiling for sentence-grammar extraction is far below 100% of
  candidates; the right denominator for Pass-2 recall is the
  verb-bearing subset.
- **B_CONTROL is the opposite and is the quick win: 38/40 sampled
  misses *do* have a relational verb nearby** — spans literally
  include "controlled by" and "controlling shareholder" — yet the
  grammars matched only 2 of 2,652 control candidates. The existing
  patterns appear to require overly strict sentence shapes
  (both entity names in fixed positions). Loosening B-tier grammars
  should multiply yield in the category that matters most for the
  graph.
- **~half of sampled misses sit in nav/list/table fragments**
  (≥4 newlines in ±100 chars), arguing for a layout-aware
  pre-filter before grammar matching rather than more regex.

## Data-integrity flags (not fixed here — surfaced for review)

1. **Stale status docs.** `COLLECTION-REPORT.md` and
   `PERSISTENCE-STATUS.md` (both "as of 2026-08-15T04:15Z") still say
   "Durably archived so far: 0 URLs, 0 bytes" while `metrics.json`
   (2026-08-17) reports 124,141 archived URLs / 26.3 GB verified.
   Anyone reading the docs first gets the wrong picture.
2. **Possible recurring state clobber.** Commit `0e19d6d` added
   `COVERAGE.md`, `PRESERVATION-PRIORITIES.md`, `audit_objects.py`,
   and `.github/workflows/audit-sample.yml`; none exist at HEAD, and
   the intervening bot commits only touch the six state files.
   History already contains two repair commits for this failure mode
   (`631ac2b`, `3c807f2`) — the concurrent-workflow checkout/commit
   race appears to still be live.

## Reproducing

```bash
# 1. Reassemble + verify the derived text tree
cat derived-release-staging/derived-content-pass-1.tar.zst.part0* > /tmp/derived.tar.zst
sha256sum /tmp/derived.tar.zst   # d7eba7dae5a8...  (see sha256sums.txt)
zstd -d < /tmp/derived.tar.zst | tar -x -C /tmp/derived-tree

# 2. Run the analysis (deterministic, stdlib-only)
python3 analysis/pass1_analysis.py --derived-root /tmp/derived-tree/derived
```

Without `--derived-root` the script still produces all aggregate
statistics; the flag adds span resolution and verification.
