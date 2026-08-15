# CONTENT PASS 2 — Structured Evidence Report

**Pass version:** `content-pass-2/1.0.0` (parser observe/1.4.0) ·
**Run date:** 2026-08-15 · **Branch:** `claude/fincen-boi-corpus-recon-iwcm41`

Pass 2 converted the strongest Pass 1 candidates into structured,
source-addressable observations and a first validated graph nucleus,
while independently dispatching evidence-guided primary-source
acquisition. Acquisition ran on Actions runners in parallel with local
extraction and was never blocked by analysis compute (Part XX).

---

## The feedback loop, realized

```
ARCHIVED SOURCE (38,242 objects) → EXTRACTED TEXT (Pass 1)
→ CANDIDATE SPAN (98,780) → RAW OBSERVATION (357)
→ NORMALIZED ASSERTION (260) → VALIDATED EDGE (102)
→ IDENTIFIERS (260 EDGAR CIK matches) → TARGETED ACQUISITION
  (32,313-filing queue; 12,589-URL batch dispatched)
→ ARCHIVED SOURCE → new evidence (next batch)
```

## Structured evidence produced

- **357 raw observations** (Tier A ownership 81 · B control 18 ·
  C parent/subsidiary 160 · D shell/nominee 1 · E financial flow 97),
  every one carrying sentence-level raw text, deterministic character
  locators, evidentiary posture with rationale, parser version, and the
  Pass 1 candidate_id it descends from. Raw wording is never discarded.
- **260 normalized assertions** (125 same-sentence duplicates flagged,
  not deleted) — 12 with literal ownership percentages, 134 with
  qualitative descriptions preserved verbatim ("majority owner" stays
  "majority owner"; never normalized to 51%).
- **97 financial-flow observations**, all amount-bearing, participants
  literal-only (no inferred parties, no cross-source summation;
  `possible_overlap_group` reserved).
- **102 validated graph edges**: 46 BENEFICIAL_OWNER · 18
  UNKNOWN_CONTROL_ROLE · 38 PARENT, in the ownership-reconstruction
  universal edge format extended with `evidentiary_posture`,
  `reported_speech`, and the full assertion→observation→candidate chain.
  Every edge supports the complete Part XXI walk down to the original
  public URL; edges failing any link were not emitted (10 reported-speech,
  13 name-screen, 5 missing-party, 4 conjunctive-object exclusions).

Posture distribution of edges: 60 GOVERNMENT_FINDING (OCC/FDIC/FinCEN
orders and licensing decisions), 24 ADMINISTRATIVE_DESIGNATION (OFAC),
13 GOVERNMENT_ALLEGATION (SEC/DOJ complaints), 3 CONGRESSIONAL_ASSERTION,
2 COURT_ALLEGATION. **No ADJUDICATED_FACT was auto-assigned** — judgment
documents stay COURT_ALLEGATION until a human confirms a specific finding
was adjudicated rather than recited or consented without admission.

Representative validated chains (all literal, all source-addressable):

- OFAC: Stroytransgaz Group / Stroytransgaz LLC / Stroytransgaz-M /
  Avia Group / Sakhatrans → "owned or controlled by" → Volga Group →
  Timchenko (ADMINISTRATIVE_DESIGNATION).
- OFAC: "Al Qattan also owns **50 percent** of Adam Trading and
  Investment LLC"; "Damascus Cham Holding Company holds **75 percent**
  of the shares" (Mirza JV).
- OCC/FDIC licensing: Anchorage Trust ← Anchor Labs, Inc.; BitGo Trust ←
  BitGo Holdings, Inc.; proposed banks ← Revolut Holdings US Inc /
  Nu Holdings Ltd / Payoneer Global Inc / BMO Financial Corp.
- SEC: "Evolution Capital is owned and controlled by its founder and
  managing member, Valdez" (GOVERNMENT_ALLEGATION).
- FinCEN: LCB → majority shareholder / 51% → Prime Bank Ltd (Gambia).

## Entity/person resolution (conservative by mandate)

154 entity nodes: 12 PROBABLE_MATCH (exact normalized-name match to a
single EDGAR registrant; CIK attached, **nodes not merged**), 0 AMBIGUOUS,
142 UNRESOLVED. 36 person-candidate nodes + 21 other actors (defined
terms, abbreviations, confidential-source codes like CS-3) — **zero
automatic person merges**. Defined terms ("the Venture", "the Bank")
remain unresolved nodes with their raw variants preserved; resolving them
to their in-document antecedents is Pass 3 work. Nothing was merged on
name similarity; ambiguity remains ambiguity.

## Validation (Part XXIV)

94-item seeded sample (25 ownership / 18 control / 25 parent-sub /
1 shell / 25 flow — control and shell pools were smaller than 25).
Locators 94/94 mechanically correct. Manual review: **67 fully correct,
18 partial (relationship substance right, a boundary or amount
imperfect), 9 wrong.** Round-1 review found four systematic defects —
period-crossing name fusion ("Bank Tejarat. Bank"), object-prefix
consumption ("[Adam] Trading and Investment LLC"), heading-crossing
captures, missing reported-speech distinction (a FinCEN doc relaying a
Telegram channel's claim) — all fixed in the single sanctioned round
(v1.4.0) and re-verified. The residual wrong-classes (conjunctive
objects, claims-form windows, split amounts) are excluded from edge
emission by mechanical gates and documented above.

## Evidence-guided acquisition (Parts X–XX)

**EDGAR** (from the archived submissions snapshot, zero SEC traffic to
build): 6,432 candidate entity names harvested from Pass 1 buckets →
260 registrant CIKs matched → **32,313 priority-form filings queued**
(SC 13D/A, 13G/A, 10-K EX-21 carriers with index URLs for second-round
exhibit fetch, Forms 3/4/5, D, bounded 8-K) → 8,000-URL batch 1.

**DOJ**: all 4,317 Akamai interstitials classified
`NON_CONTENT_TECHNICAL_RESPONSE` (original retrieval observations
retained); recovery = ordinary later retrieval + sitemap rediscovery.
No bot-protection circumvention attempted or planned.

**Congress/GAO/GovInfo/FinCEN**: citation mining across all 460M
extracted characters → 12 congress.gov + 48 GAO (incl. GAO-20-574, the
BOI-verification report) + 39 govinfo + 173 fincen.gov never-captured
URLs, plus GAO/GovInfo listing roots for a bounded follow-links crawl.

**Dispatched on Actions** (runs 31891026640 bulk-chunked, 31891027794
follow-links): 12,595 URLs total, host-aligned chunks, 1.0–1.5 s
per-host delay, scaled across six independent hosts. State commits and
durable releases flow through the standing `commit_state.sh` pipeline;
the 4,000/day maintenance schedules remain untouched.

**OCR backlog** ranked (Part XVI): 5 HIGH (SEC complaint scans) /
190 MEDIUM / 6 LOW in `ocr-priority.jsonl`. No bulk OCR run; HIGH tier
is the next targeted extraction step after acquisition lands.

## What Pass 2 did NOT do (by design)

- No SEC 13D/G structured extraction yet — none are archived; the
  dispatched EDGAR batch acquires them, and the `SEC_13D_G` ownership
  regime field is reserved so SEC beneficial ownership can never be
  conflated with CTA beneficial ownership.
- No EX-21 parsing yet — exhibit bytes arrive via the queued index URLs.
- No intermediate-structure collapsing, no invented percentages, no
  posture upgrades, no person merges, no cross-source flow summation.
- Shell/nominee narrative yield is 1 observation — Pass 1 flags 983
  shell-discussing documents, but their evidence is diffuse narrative
  that needs paragraph-level (possibly model-assisted, labeled
  MODEL_CLASSIFICATION) extraction in Pass 3.

## Reproduction

```sh
python3 -m content_pass_2.edgar_queue        # acquisition map from archived snapshot
python3 -m content_pass_2.recovery_queues    # DOJ/Congress/GAO/FinCEN queues
python3 -m content_pass_2.ocr_priority
python3 -m content_pass_2.observe            # raw observations (Tiers A-E)
python3 -m content_pass_2.normalize          # assertions + conservative resolution
python3 -m content_pass_2.validate           # Part XXIV sample
python3 -m content_pass_2.edges              # gated edge emission
python3 -m content_pass_2.metrics
```

Full metric breakdowns (by type, family, posture, year, provenance):
`content-pass-2/metrics.json`.
