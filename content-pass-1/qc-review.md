# QC review — Content Pass 1 (Step 14)

Seeded sample (RNG 20260815): 25 high-priority candidates, 25
medium-priority, 25 low-priority, 25 documents classified as having no
ownership/control candidate evidence. Sample sheet: `qc-sample.jsonl`.
Manual inspection performed against extracted text and archived bytes.

## Mechanical checks

- **locator_correct: 75/75.** Every sampled candidate's
  `character_start`/`character_end` offsets reproduced `matched_text`
  exactly against `derived/text/<aa>/<sha>.txt`.
- **text_extraction_correct: 75/75** — extracted spans read as faithful
  text for their format (one OCR-quality artifact noted below).

## Manual findings (scanner v1.1.0 sample)

**High tier (25):** 18 true positives, including exemplary evidentiary
language: "Carias was the sole **beneficial owner**" (SEC), "Douglas was
the president and **co-owner** of Gold Coast Commodities, Inc." (DOJ),
"Smith, as the **treasurer of KC Acquisition Corp.**, signed the letter
authorizing the transfer" (SEC), "wholly owned **subsidiary** of Anchor
Labs" (OCC). 7 false positives with two systematic causes:

1. `shareholder_of` accepted bare **"member of"** — matched "Ranking
   Member of the Committee", "member of the military service", "member
   of the New York and Georgia bars", "member of CIIC's Board" (5/25).
2. Table-of-contents / table-caption lines ("Table 2: Quarterly Holding
   Company Trading Revenue .....") ranked high in OCC quarterly reports
   (2/25).

**Medium tier (25):** ~19 true positives (mostly generic-but-real
BSA/AML/regulatory discussion, correctly mid-ranked; one excellent OFAC
"owned or **controlled by** Tabaja" span). False positives: FinCEN
navigation-adjacent repeated "Money Laundering" program-listing lines
(3), call-report form cells ("$100,000 through $250,000"), and
`controls_entity` matching the agency name "Office of Foreign Assets
**Control has:** provided a partial list of entities" (1).

**Low tier (25):** dominated by definitional/regulatory boilerplate
("on behalf of", statutory "subsidiaries of insured depository
institutions", organizer tables) — **correctly ranked low**; several are
still genuinely useful (FDIC failed-bank "ACQUIRING INSTITUTION"
records). No action needed: low rank is the intended treatment.

**Negative sample (25 no-evidence documents):** FBI Vault viewer pages,
FinCEN form/notice pages, OCC/FDIC administrative pages — no missed
ownership/control statements observed in excerpts; false_negative rate
in the sample: 0 observed (bounded by excerpt-level inspection).

One extraction-quality artifact: a govinfo consent-judgment PDF renders
with OCR-era spacing ("on behalf of one or more investorsbased on
substantially thesnme facts") — native PDF text preserved as served;
noted, not altered.

## Tuning applied (the single Step-14 tuning round → scanner v1.2.0)

1. `shareholder_of`: bare "member of" removed; now requires
   shareholder/stockholder, or member qualified by
   sole/managing/founding/majority.
2. `controls_entity`: requires verb form ("controls", "controlling",
   "control of/over") so agency names ("…Assets Control has…") no longer
   match.
3. Ranking: −2 `table_or_toc` feature for spans whose context contains
   dot leaders (`.....`) or "Table N:" captions.

(A pre-QC tightening, v1.1.0, had already restricted percentage patterns
to ownership nouns after "N percent of GDP"-type matches surfaced during
the first scan.)

The full scan was re-run at v1.2.0 after these changes. No further
optimization was performed — reconnaissance, not a perfect classifier.
