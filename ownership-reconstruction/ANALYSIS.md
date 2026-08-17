# Graph analyses (pass2-observations)

Regenerate with `python3 analyze_graph.py`. Posture weights are analysis-time parameters (see script header); the graph itself stores evidence, not judgments.


Temporal coverage: 807/1007 edges carry a document date (1996-03-13 … 2026-07-28); 351 additionally carry a sentence-stated event date in `valid_from`.


## 1. Multi-hop ownership/control chains (15 maximal distinct node paths of length ≥ 2)

- Bank of Montreal —[PARENT·SELF_REPORTED×41]→ Bankmont Financial Corp —[PARENT·SELF_REPORTED×13]→ Harris Bank —[PARENT·SELF_REPORTED×3]→ Harris Bank Palatine, N.A
  <br>sources: `0265e1135505 · 035a9f081389 · 404a8c8928af`
- Fleet Boston Corp —[PARENT·GOVERNMENT_FIN]→ Fleet National Bank, Providence, Rhode Island —[PARENT·GOVERNMENT_FIN]→ Fleet Mortgage Corporation
  <br>sources: `23d2280116f3 · 2d7c9bf0af5f`
- Wells Fargo & Company —[BENEFICIAL_OWNER·GOVERNMENT_FIN×3]→ Wells Fargo Bank —[PARENT·GOVERNMENT_FIN]→ OmniPlus Capital Corporation
  <br>sources: `8a00ebf52662 · cb8d0119f53b`
- Wells Fargo & Company —[BENEFICIAL_OWNER·GOVERNMENT_FIN×3]→ Wells Fargo Bank —[PARENT·GOVERNMENT_FIN]→ Silver Asset Management Group
  <br>sources: `8a00ebf52662 · e64009612ba8`
- RBC USA Holdco Corp —[PARENT·GOVERNMENT_FIN]→ North Carolina —[BENEFICIAL_OWNER 100.0%·GOVERNMENT_FIN]→ First Union Commercial Corp
  <br>sources: `0b4864d0d344 · e2933e312a49`
- RBC USA Holdco Corp —[PARENT·GOVERNMENT_FIN]→ North Carolina —[PARENT·GOVERNMENT_FIN]→ NationsBank include data on NationsBanc Mortgage Corporation
  <br>sources: `0691a188d954 · 0b4864d0d344`
- Stewardship Financial Corporation —[BENEFICIAL_OWNER·GOVERNMENT_FIN]→ Atlantic Stewardship Bank —[PARENT·GOVERNMENT_FIN]→ Atlantic Stewardship Insurance Company, LLC
  <br>sources: `30aa0c47249a`
- Jones Heward Investments Inc —[PARENT·SELF_REPORTED]→ Jones Heward Investment Management Inc —[PARENT·SELF_REPORTED]→ Jones Heward Investment Counsel Inc
  <br>sources: `045757f2d8db · 5fb62d97a247`
- George Haswani —[BENEFICIAL_OWNER·ADMINISTRATIVE]→ Hesco Engineering —[BENEFICIAL_OWNER·ADMINISTRATIVE]→ IPC
  <br>sources: `f4b0b3de4004`
- Yuri Kovalchuk —[BENEFICIAL_OWNER·ADMINISTRATIVE]→ Bank Rossiya —[BENEFICIAL_OWNER·ADMINISTRATIVE]→ Limited Liability Company Investment Company Abros
  <br>sources: `94d4bc8d1234`
- Evercore Inc. a Delaware corporation —[PARENT·SELF_REPORTED]→ Evercore LP —[BENEFICIAL_OWNER 86.0%·GOVERNMENT_FIN]→ Evercore Trust Company, National Association
  <br>sources: `305f0300f3af · 696039e9af4c`
- Yuri Kovalchuk —[BENEFICIAL_OWNER·ADMINISTRATIVE]→ Bank Rossiya —[BENEFICIAL_OWNER·ADMINISTRATIVE]→ JSB Sobinbank
  <br>sources: `94d4bc8d1234`
- Yuri Kovalchuk —[BENEFICIAL_OWNER·ADMINISTRATIVE]→ Bank Rossiya —[BENEFICIAL_OWNER·ADMINISTRATIVE]→ CJSC Zest
  <br>sources: `94d4bc8d1234`
- New York Community Bancorp —[PARENT·GOVERNMENT_FIN]→ Flagstar Bank —[BENEFICIAL_OWNER·GOVERNMENT_ALL]→ Mortgage Servicing Rights
  <br>sources: `270ecf6a5c13 · a6dbca5cf9a2`
- management of United Financial Bancorp, Inc —[PARENT·GOVERNMENT_ALL]→ United Bank —[PARENT·SELF_REPORTED×7]→ UCB Securities, Inc
  <br>sources: `2c0e739645a8 · 67c744645208`

## 2. Controller centrality: structural reach vs evidentiary breadth

`held` = distinct owned/controlled parties; `evidence` = distinct supporting documents; `postures`/`families` = evidentiary breadth (independent assertion types and source hosts). A controller supported across several agencies and postures is corroborated; one supported by many documents from one source is merely persistent.

| Controller | Held | Evidence docs | Postures | Source families | Weighted score | Reach |
|---|---|---|---|---|---|---|
| Oleg Deripaska | 6 | 12 | 1 | 1 | 4.2 | 6 |
| Bazzi | 5 | 5 | 1 | 1 | 3.5 | 5 |
| Western Financial Bank | 3 | 3 | 1 | 1 | 2.7 | 3 |
| Atlas Holding | 3 | 3 | 1 | 1 | 2.7 | 3 |
| Anchor Labs, Inc | 3 | 5 | 1 | 1 | 2.55 | 3 |
| Bank Rossiya | 3 | 3 | 1 | 1 | 2.3 | 3 |
| Wael Bazzi | 3 | 3 | 1 | 1 | 2.3 | 3 |
| Columbia Bank | 3 | 7 | 2 | 1 | 2.16 | 3 |
| SVB Leerink | 3 | 4 | 2 | 1 | 2.16 | 3 |
| Bazzoni | 3 | 3 | 1 | 1 | 2.1 | 3 |
| Leal | 3 | 3 | 1 | 1 | 2.1 | 3 |
| Tesic | 3 | 3 | 1 | 1 | 2.1 | 3 |
| Interactive Brokers Group, Inc | 2 | 2 | 1 | 1 | 1.8 | 2 |
| Company N | 2 | 2 | 1 | 1 | 1.8 | 2 |
| DTCC | 2 | 2 | 1 | 1 | 1.8 | 2 |
| Social Finance, Inc | 2 | 2 | 1 | 1 | 1.8 | 2 |
| JPMCB | 2 | 2 | 1 | 1 | 1.8 | 2 |
| Gjades Shipping Company | 2 | 2 | 1 | 1 | 1.8 | 2 |
| Wells Fargo Bank | 2 | 2 | 1 | 1 | 1.8 | 2 |
| Huntington Bancshares | 2 | 2 | 1 | 1 | 1.8 | 2 |

## 2b. Relationship persistence (91 relationships with multi-document evidence)

Repeated public declaration over time is information: first/last seen use document publication dates.

- **BMO Nesbitt Burns Corp** —[PARENT]→ **BMO Nesbitt Burns, Inc** · 161 documents (161 dated: 2003-06-10 → 2012-09-06) · postures: SELF_REPORTED · sources: sec.gov
- **Bank of Montreal** —[PARENT]→ **Bankmont Financial Corp** · 41 documents (41 dated: 1996-03-13 → 1998-02-18) · postures: SELF_REPORTED · sources: sec.gov
- **Vanguard Group** —[PARENT]→ **Vanguard Fiduciary Trust Company** · 40 documents (40 dated: 2011-02-10 → 2020-02-12) · postures: SELF_REPORTED · sources: sec.gov
- **Nesbitt Burns Corp** —[PARENT]→ **Nesbitt Burns, Inc** · 25 documents (25 dated: 1999-02-12 → 2003-02-11) · postures: SELF_REPORTED · sources: sec.gov
- **Wellington Management Group** —[BENEFICIAL_OWNER]→ **Wellington Group Holdings LLP** · 17 documents (17 dated: 2016-02-11 → 2023-02-06) · postures: SELF_REPORTED · sources: sec.gov
- **Wellington Group** —[BENEFICIAL_OWNER]→ **Wellington Investment Advisors Holdings LLP** · 17 documents (17 dated: 2016-02-11 → 2023-02-06) · postures: SELF_REPORTED · sources: sec.gov
- **Bankmont Financial Corp** —[PARENT]→ **Harris Bank** · 13 documents (13 dated: 1996-03-27 → 1998-02-18) · postures: SELF_REPORTED · sources: sec.gov
- **FMR LLC** —[PARENT]→ **Fidelity Management & Research Company** · 9 documents (9 dated: 2015-02-13 → 2020-02-07) · postures: SELF_REPORTED · sources: sec.gov
- **BIOeCON International Holding N.V** —[UNKNOWN_CONTROL_ROLE]→ **BIOeCON Holding** · 8 documents (8 dated: 2011-07-12 → 2014-08-19) · postures: SELF_REPORTED · sources: sec.gov
- **CON NV** —[UNKNOWN_CONTROL_ROLE]→ **BIOeCON Holding** · 8 documents (8 dated: 2011-07-12 → 2014-08-19) · postures: SELF_REPORTED · sources: sec.gov
- **Newtek Business Services Corp** —[PARENT]→ **Wilshire Holdings I, Inc** · 7 documents (38 dated: 2017-03-13 → 2023-03-16) · postures: GOVERNMENT_ALLEGATION · sources: sec.gov
- **United Bank** —[PARENT]→ **UCB Securities, Inc** · 7 documents (7 dated: 2006-03-30 → 2014-03-13) · postures: GOVERNMENT_ALLEGATION, SELF_REPORTED · sources: sec.gov

## 2c. Alias review queue (32 merge candidates touching active controllers)

Merge candidates ranked by the centrality of their most central member — resolving one high-degree alias improves more of the graph than resolving many leaf nodes. Review decisions belong to a human; nothing here is auto-merged.

| Candidate pair | Kind | Max centrality |
|---|---|---|
| bazzi ~ wael bazzi | surname-of | 3.5 |
| wells fargo bank ~ wells fargo bank na | cross-family-suffix | 1.8 |
| depository trust ~ depository trust co | cross-family-suffix | 1.8 |
| wells fargo bank ~ wells fargo bank na | prefix-containment | 1.8 |
| depository trust ~ depository trust co | prefix-containment | 1.8 |
| depository trust ~ depository trust corp depository trust co | prefix-containment | 1.8 |
| carolina ~ north carolina | surname-of | 1.8 |
| vanguard group ~ vanguard group inc | cross-family-suffix | 1.71 |
| vanguard group ~ vanguard group inc | prefix-containment | 1.71 |
| cmc ~ chase manhattan corp | acronym-initials | 1.65 |
| prigozhin ~ yevgeniy prigozhin | surname-of | 1.4 |
| chase home finance inc ~ chase home finance llc | cross-family-suffix | 0.9 |

## 3. Competing control assertions across documents (1 nodes)

Distinct sources assert different owners/controllers for the same node. Succession vs. contradiction is a review call — every claim below cites its document.


**BIOeCON Holding**
- BIOeCON International Holding N.V — UNKNOWN_CONTROL_ROLE, SELF_REPORTED, 2011-07-12 · `45c882b94c7b280b`
- CON NV — UNKNOWN_CONTROL_ROLE, SELF_REPORTED, 2011-07-12 · `45c882b94c7b280b`
- BIOeCON International Holding N.V — UNKNOWN_CONTROL_ROLE, SELF_REPORTED, 2012-05-25 · `aa6800c53eecdde3`
- CON NV — UNKNOWN_CONTROL_ROLE, SELF_REPORTED, 2012-05-25 · `aa6800c53eecdde3`
- BIOeCON International Holding N.V — UNKNOWN_CONTROL_ROLE, SELF_REPORTED, 2012-10-02 · `4d0ed6e81b32bcd4`
- CON NV — UNKNOWN_CONTROL_ROLE, SELF_REPORTED, 2012-10-02 · `4d0ed6e81b32bcd4`
- BIOeCON International Holding N.V — UNKNOWN_CONTROL_ROLE, SELF_REPORTED, 2013-02-01 · `54ae282587c90e10`
- CON NV — UNKNOWN_CONTROL_ROLE, SELF_REPORTED, 2013-02-01 · `54ae282587c90e10`
- BIOeCON International Holding N.V — UNKNOWN_CONTROL_ROLE, SELF_REPORTED, 2014-07-21 · `443e42857b665338`
- CON NV — UNKNOWN_CONTROL_ROLE, SELF_REPORTED, 2014-07-21 · `443e42857b665338`
- BIOeCON International Holding N.V — UNKNOWN_CONTROL_ROLE, SELF_REPORTED, 2014-07-22 · `1cfdc333b1e8d4f8`
- CON NV — UNKNOWN_CONTROL_ROLE, SELF_REPORTED, 2014-07-22 · `1cfdc333b1e8d4f8`
- BIOeCON International Holding N.V — UNKNOWN_CONTROL_ROLE, SELF_REPORTED, 2014-08-08 · `acb86292e0788941`
- CON NV — UNKNOWN_CONTROL_ROLE, SELF_REPORTED, 2014-08-08 · `acb86292e0788941`
- BIOeCON International Holding N.V — UNKNOWN_CONTROL_ROLE, SELF_REPORTED, 2014-08-19 · `e13c16e9489ec111`
- CON NV — UNKNOWN_CONTROL_ROLE, SELF_REPORTED, 2014-08-19 · `e13c16e9489ec111`
