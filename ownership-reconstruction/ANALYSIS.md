# Graph analyses (pass2-observations)

Regenerate with `python3 analyze_graph.py`. Posture weights are analysis-time parameters (see script header); the graph itself stores evidence, not judgments.


## 1. Multi-hop ownership/control chains (11 maximal distinct node paths of length ≥ 2)

- Bank of Montreal —[PARENT·SELF_REPORTED×41]→ Bankmont Financial Corp —[PARENT·SELF_REPORTED×13]→ Harris Bank —[PARENT·SELF_REPORTED×3]→ Harris Bank Palatine, N.A
  <br>sources: `0265e1135505 · 035a9f081389 · 404a8c8928af`
- PNC Bancorp —[PARENT·GOVERNMENT_FIN]→ PNC Bank —[PARENT·GOVERNMENT_FIN]→ PNC Preferred Funding LLC
  <br>sources: `324144f914a9 · 67e9acadd78d`
- Wells Fargo & Company —[BENEFICIAL_OWNER·GOVERNMENT_FIN×3]→ Wells Fargo Bank —[PARENT·GOVERNMENT_FIN]→ OmniPlus Capital Corporation
  <br>sources: `8a00ebf52662 · cb8d0119f53b`
- Wells Fargo & Company —[BENEFICIAL_OWNER·GOVERNMENT_FIN×3]→ Wells Fargo Bank —[PARENT·GOVERNMENT_FIN]→ Silver Asset Management Group
  <br>sources: `8a00ebf52662 · e64009612ba8`
- Wells Fargo & Company —[BENEFICIAL_OWNER·GOVERNMENT_FIN×3]→ Wells Fargo Bank —[PARENT·GOVERNMENT_FIN]→ Wells Fargo Home Mortgage, Inc
  <br>sources: `7d1968680b0e · 8a00ebf52662`
- Stewardship Financial —[BENEFICIAL_OWNER·GOVERNMENT_FIN]→ Atlantic Stewardship Bank —[PARENT·GOVERNMENT_FIN]→ Atlantic Stewardship Insurance Company, LLC
  <br>sources: `30aa0c47249a`
- Jones Heward Investments Inc —[PARENT·SELF_REPORTED]→ Jones Heward Investment Management Inc —[PARENT·SELF_REPORTED]→ Jones Heward Investment Counsel Inc
  <br>sources: `045757f2d8db · 5fb62d97a247`
- George Haswani —[BENEFICIAL_OWNER·ADMINISTRATIVE]→ Hesco Engineering —[BENEFICIAL_OWNER·ADMINISTRATIVE]→ IPC
  <br>sources: `f4b0b3de4004`
- Yuri Kovalchuk —[BENEFICIAL_OWNER·ADMINISTRATIVE]→ Bank Rossiya —[BENEFICIAL_OWNER·ADMINISTRATIVE]→ Limited Liability Company Investment Company Abros
  <br>sources: `94d4bc8d1234`
- Yuri Kovalchuk —[BENEFICIAL_OWNER·ADMINISTRATIVE]→ Bank Rossiya —[BENEFICIAL_OWNER·ADMINISTRATIVE]→ JSB Sobinbank
  <br>sources: `94d4bc8d1234`
- Yuri Kovalchuk —[BENEFICIAL_OWNER·ADMINISTRATIVE]→ Bank Rossiya —[BENEFICIAL_OWNER·ADMINISTRATIVE]→ CJSC Zest
  <br>sources: `94d4bc8d1234`

## 2. Controller centrality (posture-weighted)

`held` = distinct owned/controlled parties; `evidence` = distinct supporting documents across those relationships.

| Controller | Held | Evidence docs | Weighted score | Reach |
|---|---|---|---|---|
| Oleg Deripaska | 6 | 12 | 4.2 | 6 |
| Bazzi | 5 | 5 | 3.5 | 5 |
| WFB | 3 | 3 | 2.7 | 3 |
| Wells Fargo Bank | 3 | 3 | 2.7 | 3 |
| Atlas Holding | 3 | 3 | 2.7 | 3 |
| SVB Leerink | 3 | 6 | 2.43 | 3 |
| Bank Rossiya | 3 | 3 | 2.3 | 3 |
| Wael Bazzi | 3 | 3 | 2.3 | 3 |
| Columbia Bank | 3 | 7 | 2.16 | 3 |
| Bazzoni | 3 | 3 | 2.1 | 3 |
| Leal | 3 | 3 | 2.1 | 3 |
| Tesic | 3 | 3 | 2.1 | 3 |
| Anchor Labs, Inc | 2 | 4 | 1.8 | 2 |
| Interactive Brokers Group, Inc | 2 | 2 | 1.8 | 2 |
| Company N | 2 | 2 | 1.8 | 2 |
| DTCC | 2 | 2 | 1.8 | 2 |
| SBFSB | 2 | 2 | 1.8 | 2 |
| JPMCB | 2 | 2 | 1.8 | 2 |
| Gjades Shipping Company | 2 | 2 | 1.8 | 2 |
| Huntington Bancshares | 2 | 2 | 1.8 | 2 |

## 3. Competing control assertions across documents (1 nodes)

Distinct sources assert different owners/controllers for the same node. Succession vs. contradiction is a review call — every claim below cites its document.


**BIOeCON Holding**
- BIOeCON International Holding N.V — UNKNOWN_CONTROL_ROLE, SELF_REPORTED · `1cfdc333b1e8d4f8`
- BIOeCON International Holding N.V — UNKNOWN_CONTROL_ROLE, SELF_REPORTED · `443e42857b665338`
- BIOeCON International Holding N.V — UNKNOWN_CONTROL_ROLE, SELF_REPORTED · `45c882b94c7b280b`
- BIOeCON International Holding N.V — UNKNOWN_CONTROL_ROLE, SELF_REPORTED · `4d0ed6e81b32bcd4`
- BIOeCON International Holding N.V — UNKNOWN_CONTROL_ROLE, SELF_REPORTED · `54ae282587c90e10`
- BIOeCON International Holding N.V — UNKNOWN_CONTROL_ROLE, SELF_REPORTED · `aa6800c53eecdde3`
- BIOeCON International Holding N.V — UNKNOWN_CONTROL_ROLE, SELF_REPORTED · `acb86292e0788941`
- BIOeCON International Holding N.V — UNKNOWN_CONTROL_ROLE, SELF_REPORTED · `e13c16e9489ec111`
- CON NV — UNKNOWN_CONTROL_ROLE, SELF_REPORTED · `1cfdc333b1e8d4f8`
- CON NV — UNKNOWN_CONTROL_ROLE, SELF_REPORTED · `443e42857b665338`
- CON NV — UNKNOWN_CONTROL_ROLE, SELF_REPORTED · `45c882b94c7b280b`
- CON NV — UNKNOWN_CONTROL_ROLE, SELF_REPORTED · `4d0ed6e81b32bcd4`
- CON NV — UNKNOWN_CONTROL_ROLE, SELF_REPORTED · `54ae282587c90e10`
- CON NV — UNKNOWN_CONTROL_ROLE, SELF_REPORTED · `aa6800c53eecdde3`
- CON NV — UNKNOWN_CONTROL_ROLE, SELF_REPORTED · `acb86292e0788941`
- CON NV — UNKNOWN_CONTROL_ROLE, SELF_REPORTED · `e13c16e9489ec111`
