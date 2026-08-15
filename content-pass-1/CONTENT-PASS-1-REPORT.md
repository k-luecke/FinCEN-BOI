# CONTENT PASS 1 — Corpus Reconnaissance Report

**Pass version:** `content-pass-1/1.0.0` (scanner v1.2.0) ·
**Run date:** 2026-08-15 · **Branch:** `claude/fincen-boi-corpus-recon-iwcm41`

This pass answered one question: **what do the preserved objects actually
contain?** It emitted no graph facts — no ownership edges, no entity
merges, no person resolution. Its products are an inventory, extracted
text, document classifications, candidate evidence spans with
source-addressable locators, and a ranked reconnaissance index
(`TOP-CANDIDATES.md`). Everything ran against archived bytes restored
from this repository's own `objects-run-*` releases; **zero requests
were sent to any government host.**

---

## 1. What is actually in the corpus?

38,242 unique content-addressed objects (8.70 GB) captured from 19
government hosts, verified byte-for-byte against `manifest.jsonl`:

| Format (magic-byte sniffed) | Objects |
|---|---|
| HTML | 31,336 |
| PDF | 6,678 |
| ZIP containers (incl. SEC data files, OCC xlsx, EDGAR bulk) | 161 |
| XML | 30 |
| Plain text | 18 |
| Images (jpeg/png) | 19 |

By source family: DOJ 5,001 · FBI Vault 5,001 · Treasury 5,001 · FDIC
5,000 · OCC 4,960 · Congress (oversight.house.gov + judiciary) 4,931 ·
SEC 4,906 · FinCEN 2,872 · GovInfo 494 · Treasury OIG 72 · GAO 3 ·
other 1. Provenance: 33,780 GOV-PUBLIC, 5,002 CONGRESS (retrieval
records). 57 objects have MIME conflicts (claimed vs sniffed); 99
objects are served identically from multiple URLs; 2 URLs have multiple
historical versions preserved.

What the content substantively is:

- **SEC**: ~1,000+ litigation complaints/judgments (the densest
  ownership/control/shell material in the corpus), plus market-structure
  data files and staff documents.
- **OCC**: enforcement actions, licensing/charter decisions
  (subsidiary/holding-company structure), quarterly reports.
- **Treasury**: press releases including hundreds of OFAC designation
  announcements with explicit "owned or controlled by" chains and
  percentages (Assad-regime reconstruction, Crimea/Russia, Gertler,
  Hezbollah finance).
- **FinCEN**: BOI/CTA rule pages, FAQs, toolkit, CDD rule, enforcement
  actions, director speeches, SAR/CTR statistics pages.
- **FDIC**: press releases (incl. receivership equity-interest sales),
  financial institution letters, bank-data pages.
- **FBI Vault**: 5,001 pages — mostly scanned historical PDF parts
  behind HTML viewer pages (main OCR backlog).
- **Congress (oversight.house.gov)**: investigation pages incl. the
  Bidens' influence-peddling timeline, Delphi/GM pension, operations
  reports.
- **GovInfo**: 494 Federal Register PDFs incl. the BOI reporting NPRM
  (FR-2021-12-08) and final rule (FR-2022-09-30).
- **SEC EDGAR bulk**: `submissions.zip` snapshot — **986,468 per-CIK
  JSON filing histories, 5.71 GB uncompressed** — safely indexed, not
  exploded.

## 2. How many objects were successfully examined?

All 38,242 (100%) have inventory records and extraction attempts.
Outcomes: 33,518 OK · 4,318 EMPTY (see §16 — 4,317 are justice.gov
bot-challenge interstitials, a capture defect, not an extraction
defect) · 201 NO_TEXT (scanned PDFs) · 161 containers indexed ·
25 errors · 19 unsupported (images/legacy binary).

## 3. How much text was extracted?

**459,970,182 characters** (~460 MB) across 33,518 documents, stored
under `derived/text/<aa>/<sha256>.txt` (raw extracted representation;
all candidate locators resolve against these files). 533 MB derived
tree including container indexes and boilerplate models.

## 4. Which source families contain the most ownership/control material?

Documents bearing ownership/control/parent-subsidiary candidates
(OWNERSHIP_EXPLICIT ∪ CONTROL_EXPLICIT ∪ PARENT_SUBSIDIARY ∪
STRUCTURED):

| Family | Own/ctrl docs | Shell docs | Fin-flow docs | SAR/BSA docs |
|---|---|---|---|---|
| OCC | 1,540 | 244 | 438 | 590 |
| Treasury | 675 | 265 | 431 | 5,000* |
| SEC | 624 | 80 | 1,646 | 31 |
| FinCEN | 519 | 249 | 525 | 1,887 |
| FDIC | 422 | 20 | 267 | 456 |
| GovInfo | 157 | 69 | 124 | 294 |
| DOJ | 40 | 24 | 38 | 118 |
| Congress (oversight) | 40 | 31 | 26 | 4 |

\* Treasury's SAR/BSA figure is inflated by a sidebar program-listing
line ("…Money Laundering · Financial Action Task Force…") that exceeds
the 400-char boilerplate-line cap and so escaped suppression; the
ranking layer places these spans at medium/low priority. Treat
Treasury SAR/BSA *document counts* as an upper bound.

**Highest evidentiary density per document: SEC litigation filings**,
which routinely name a natural person, their role, the entities they
own/control, percentages, and money flows in one paragraph. **OFAC
designation press releases** are the best source of explicit
"owned or controlled by" chains with percentages for foreign networks.

## 5. How many documents appear ownership-bearing?

**4,024 documents** (12.0% of text-bearing docs) carry at least one
ownership/control/parent-subsidiary/structured candidate. 13,332
documents (39.8%) carry at least one candidate of any category.

## 6. How many contain explicit ownership language?

**1,610 documents / 6,763 candidate spans** (beneficial-owner phrasing,
owned-by, percent-of-shares/equity, sole/majority owner,
shareholder-of). Additionally 111 documents / 139 spans matched
STRUCTURED patterns (PERSON+role+ENTITY, ENTITY-owned-by-X,
percent-of-equity-of-ENTITY) with capture groups preserved verbatim.

## 7. How many contain explicit control language?

**934 documents / 2,654 candidate spans** (controlled-by,
under-the-control-of, exercises-control, substantial-control,
controlling-person).

## 8. How many contain parent/subsidiary relationships?

**2,920 documents / 17,014 candidate spans** (wholly-owned-subsidiary,
subsidiary-of, parent-company, holding-company, affiliate, d/b/a-f/k/a).

## 9. How many discuss identified shell/nominee structures?

**983 documents / 3,804 candidate spans** (shell/front/shelf company,
nominee, straw owner, SPV, alter ego, layering/intermediaries). Densest
in SEC complaints and Treasury/OFAC designations.

## 10. How many contain specific financial-flow evidence?

**3,502 documents / 10,250 candidate spans** (wire transfers,
$-amount-to/from, bank accounts, proceeds-laundered/funneled,
payments-to-entities). Not normalized into transactions in this pass.

## 11. How much BOI/CTA/BOSS material exists?

**306 documents / 2,592 candidate spans**; 225 documents classified
BOI_CTA, 6 classified BOSS (the Beneficial Ownership Secure System):
the BOI reporting NPRM and final-rule Federal Register PDFs
(FR-2021-12-08, FR-2022-09-30), the FinCEN BOI reporting-rule fact
sheet, and three Treasury press releases. Core cluster: fincen.gov BOI
FAQs, BOI toolkit, reporting-rule fact sheet, CDD final rule, access
guidance, plus 43 OCC / 16 FDIC / 15 SEC docs referencing the regime.
This is the material that documents what FinCEN collected, who could
access it, and under what rules — the record the deletion makes
irreplaceable.

## 12. How much SAR/BSA material exists?

**8,387 documents / 42,453 candidate spans** match SAR/BSA/AML/CTR
families (with the Treasury inflation caveat of §4). High-value core:
FinCEN enforcement actions (1,887 FinCEN docs), FinCEN/FDIC/NYSBD
joint civil-money-penalty assessments, director speeches with SAR
statistics, OCC semiannual risk perspectives, MSB-registration
enforcement pages. All provenance-public; no confidential SAR content
exists in the corpus (and none was sought).

## 13. Which Congressional/government documents appear most evidentially valuable?

From `congressional-candidates.jsonl` (provenance CONGRESS or
congressional-evidence class):

1. **"The Bidens' Influence Peddling Timeline"** (oversight.house.gov)
   — names specific LLCs, accounts and wire transfers; the highest-
   ranked congressional item.
2. **Delphi/GM pension investigation pages** (oversight.house.gov) —
   "funnel funds" language with named counterparties.
3. Oversight operations/investigation pages on energy permitting,
   country-of-origin corporate structures.
4. GovInfo Federal Register BOI rulemaking record (the regulatory
   evidence chain for the CTA).
5. OCC administrative-hearing decisions (classed CONGRESSIONAL_EVIDENCE
   via "hearing before…" phrasing — a classifier artifact worth knowing
   about; they are still evidentially rich enforcement records).

Note: the congress.gov and gao.gov captures are nearly empty (1 and 3
objects) — those bodies' primary material is a known gap (§16).

## 14. Which objects require OCR?

**201 PDFs** flagged `ocr_candidate` (native text below threshold),
listed in `ocr-required.jsonl` with a `high_value` flag; 189 of 201 are
high-value by source (FBI Vault historical files, DOJ, GovInfo,
Treasury OIG). No bulk OCR was run — this is the targeted backlog for
a later pass. (Many FBI Vault *viewer pages* are HTML shells; the
underlying scanned PDFs are the OCR targets.)

## 15. What formats/parsers caused problems?

- 25 PDFs fail `pdftotext` (rc=1; malformed/encrypted) —
  `extraction-errors.jsonl`.
- 19 unsupported objects (11 JPEG, 8 PNG) — mostly seals/graphics.
- 57 MIME conflicts (e.g. `.xlsx` served as octet-stream sniffed as
  ZIP; XHTML served as XML) — resolved by trusting sniffed bytes.
- One govinfo consent judgment renders with OCR-era spacing artifacts
  (preserved as served).
- The repo's own `queue.py` shadows Python's stdlib `queue` inside
  multiprocessing workers — worked around in `content_pass_1/common.py`.

## 16. What obvious corpus gaps remain?

1. **justice.gov: 4,317 of 5,001 captures are Akamai bot-challenge
   interstitials** (`bm-verify` meta-refresh pages, ~2.5 KB each), not
   article content. Only 684 DOJ pages carry real text. DOJ press
   releases/indictments — among the richest public ownership evidence —
   are largely *not yet preserved*. Recrawl needs a challenge-aware
   fetch strategy (slower, cookie-carrying, or via govinfo mirrors).
2. **federalregister.gov: all 319 URLs failed** ("redirect escaped
   allowlist" to an `unblock.federalregister.gov` bot-protection URL).
   Partially mitigated by the 494 govinfo.gov FR PDFs; the FR HTML
   collection remains uncaptured.
3. **congress.gov (1 object, 403) and gao.gov (3 objects)** — hearing
   records, committee reports, GAO audits are essentially absent.
4. **SEC EDGAR companyfacts.zip** got 403 at snapshot time (submissions
   snapshot succeeded).
5. 87 NOT_FOUND, 325 TEMPORARY_ERROR, 4 ACCESS_RESTRICTED URLs from the
   acquisition queue (recorded, retried per policy).
6. Three SEC bulk files exceeded the 100 MB per-object cap.
7. Permanent, by law: the CTA-filed BOI database itself and
   confidential SAR/BSA records (never sought).
8. FBI Vault: HTML viewer pages captured; the underlying scanned PDF
   parts are present but OCR-pending (§14).

## 17. The 20 most valuable documents found (this pass's ranking)

Full locators/excerpts in `TOP-CANDIDATES.md`. Curated across buckets:

1. Treasury/OFAC "Investors Supporting Assad Regime's Corrupt
   Reconstruction" (`sm1037`) — explicit "holds **75 percent of the
   shares**" chains through Damascus Cham Holding.
   `1cd046dad630e1d433906ee313f88c6f4c6e4fb488c652ef137d0cb8ee6e06f3`
2. Treasury/OFAC follow-up (`sm1072`) — "Al Qattan also **owns 50
   percent** of Adam Trading and Investment LLC…".
   `71f2f7c92dcda69497a774634761caed9b74d3f47b783dd6461dbad41d735b46`
3. FDIC Signature Bridge Bank receivership 20% equity-interest sale
   (pr23105) — named JV entity, percentage, $16.8B loan pool.
   `16f2844f3ae5cd9357586525ccac5c5fa4e3d3fabe163e8494afdbcd717a2203`
4. FDIC receivership 5%/95% equity structure (pr23106).
   `36ab5d0affb19d4d720d15567154f3577ac191cd99bcd7b7c6fb4efbbca5341b`
5. SEC v. Dynkowski complaint — top shell-structure document (pump-and-
   dump through nominee/shell chains).
6. SEC amended complaint (McGinn/Smith) — "Smith, as the treasurer of
   KC Acquisition Corp., signed the letter authorizing the transfer…".
7. SEC v. Ling complaint — shell + control + flow density leader.
8. SEC v. Hand complaint — appears in top-8 of four buckets
   (control/shell/flow/parent-subsidiary).
9. Treasury/OFAC Crimea designations — "owned or controlled by"
   networks with named oligarch holdings.
10. Treasury/OFAC Dan Gertler Global Magnitsky designation — 14
    affiliated entities enumerated.
11. Oversight Committee "Bidens' Influence Peddling Timeline" —
    LLC/account/wire specifics reproduced in a congressional record.
12. FinCEN BOI Reporting Rule fact sheet (BOSS-classified core CTA
    record).
13. Federal Register final BOI reporting rule PDF (FR-2022-09-30,
    govinfo). BOSS/system-of-record description.
14. Federal Register BOI NPRM PDF (FR-2021-12-08, govinfo).
15. FinCEN/FDIC/NYSBD joint civil-money-penalty assessments — SAR/BSA
    enforcement with named institutions.
16. FinCEN Director Freis prepared remarks — BOI + SAR statistics in
    one primary source.
17. OCC charter/licensing decision ca1340 (2025) — post-conversion
    "wholly owned subsidiary of Anchor Labs" crypto-bank structure.
18. Capital One SAR-failure enforcement narrative (check-cashing
    businesses; named principals).
19. Treasury "Taxpayers to Recover $2.375 Billion from Ally IPO" —
    government equity-stake unwind with percentages.
20. SEC EDGAR `submissions.zip` snapshot — not a "document" but the
    single highest-leverage structured object: 986,468 CIK filing
    histories enabling Pass-2 officer/subsidiary extraction.
    `ec07d8cefcbdcd638dac3f7c5d91b6a71759d08190c62d44485851bba5058746`

No claim is made beyond the literal content of the cited spans.

## 18. What should CONTENT PASS 2 extract structurally?

Ranked by expected yield per effort:

1. **SEC complaints/judgments** (~1,000+ docs): defendant blocks →
   (person, age, residence), (entity, form, state), role sentences,
   ownership/control sentences, flow sentences. The prose is formulaic;
   deterministic sentence grammars will go far.
2. **OFAC designation press releases**: "X is owned or controlled by Y"
   / "holds N% of Z" chains — near-machine-readable ownership trees.
3. **EDGAR submissions.zip**: structured parse of all 986k filing
   histories; join officers/directors (Forms 3/4/5, DEF 14A), Exhibit
   21 subsidiary lists (via filing index), 13D/G ownership stakes.
4. **OCC/FDIC enforcement + licensing orders**: institution → holding
   company → subsidiary structures; individual respondents with roles.
5. **FDIC receivership/failed-bank pages**: acquiring-institution
   records (already surfacing in candidates).
6. **FinCEN enforcement actions**: MSB principals, institutions,
   penalty facts.
7. **BOI/CTA regulatory corpus**: extract the *system* facts (what BOSS
   collected, access rules, retention) into a structured policy record
   for `policy-history/`.
8. **Congressional timeline pages**: entity/account/date/amount tuples
   with per-claim source anchors.
9. OCR the 201-flag backlog (FBI Vault first), then re-scan those.
10. Recrawl the §16 gaps (DOJ challenge-aware; FR via govinfo).

## 19. SHA-256 of every major derived output

Committed in `content-pass-1/sha256sums.txt` (raw JSONL hashed; `.gz`
copies in git carry identical content, `gzip -n`):

See that file for all 22 digests. Headline artifacts:

- `derived/` tree tarball (533 MB → 95.4 MB, zstd -19), **committed in
  split parts under `derived-release-staging/`** with per-part digests:
  `d7eba7dae5a8f1ed26c00a1ad8e9d411b93012f0f75f53262c7b795ebd2b1fff`
  (reassembled). The reproducibility workflow publishes an equivalent
  release post-merge — content-identical text files, wall-clock
  timestamp fields differ by design in status records — after which the
  staging directory can be deleted (see its README).
- All 38,242 source objects verified against `manifest.jsonl` before
  scanning; source bytes untouched.

## 20. Exact reproduction commands

```sh
# From a clone of this repo at this commit, with ~25 GB free disk:
sudo apt-get install -y zstd poppler-utils
pip install lxml

# 1. Restore archived bytes from this repo's releases (GitHub auth):
gh release download objects-run-31870874176 --dir dl
gh release download objects-run-31863924882 --dir dl
gh release download objects-run-31863450182 --dir dl
cat dl/objects-31863450182.tar.zst.part0* > dl/objects-31863450182.tar.zst
rm dl/objects-31863450182.tar.zst.part0*
for t in dl/*.tar.zst; do zstd -dc "$t" | tar -x; done
# expect: find archive/objects -type f | wc -l  ->  38242

# 2. Run the pass (deterministic; resumable at every stage):
python3 -m content_pass_1.inventory
python3 -m content_pass_1.extract --workers 4
python3 -m content_pass_1.scan boilerplate
python3 -m content_pass_1.scan scan --workers 4
python3 -m content_pass_1.buckets
python3 -m content_pass_1.dedup
python3 -m content_pass_1.finalize
python3 -m content_pass_1.qc
python3 -m content_pass_1.metrics_report metrics
python3 -m content_pass_1.metrics_report top
```

Or dispatch `.github/workflows/content-pass-1.yml`, which performs the
same steps on an Actions runner and publishes the derived artifacts as
a `derived-pass1-run-<id>` release.

---

## Additional pass facts

- **Near-duplicates:** 1,529 groups covering 7,914 documents (same
  press release mirrored across pages, HTML/PDF twins, amended
  versions). Advisory only; nothing deleted.
- **Boilerplate control:** per-host line-frequency models (≥10% of a
  host's docs) suppress nav/footer chrome from candidate generation;
  raw text untouched; one known cap-related miss documented in §4.
- **QC (Step 14):** 100-item seeded sample; locators 75/75 correct;
  one tuning round applied (v1.2.0) — details in `qc-review.md`.
- **No LLM was used** for any classification in this pass; every
  observation is deterministic and re-derivable.
- **Acquisition schedules untouched:** daily archive/discover/collect
  and weekly EDGAR/verify workflows remain as they were.
