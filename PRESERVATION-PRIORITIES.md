# Preservation priorities (initial acquisition window)

Generated 2026-08-15T15:33:10.333098+00:00. **High-priority (tier 0-1) unarchived backlog: 116,434 URLs.**

| Tier | Source | Discovered | Archived | Unarchived | Bytes | Denominator | Ceiling | Temp fail | Restricted |
|-----:|--------|-----------:|---------:|-----------:|------:|-------------|---------|----------:|-----------:|
| 0 | home.treasury.gov | 19,549 | 8,742 | 10,807 | 2,885,492,271 | ENUMERABLE | CEILING_HIT_5000 | 7 | 27 |
| 0 | www.federalregister.gov | 317 | 0 | 317 | 0 | ACCESS_LIMITED (bot mitigation; use API + govinfo twins) | no | 506 | 0 |
| 0 | bsaefiling.fincen.gov | 0 | 8 | 0 | 11,642,555 | ACCESS_LIMITED (unreachable from CI) | no | 9 | 0 |
| 0 | oig.treasury.gov | 72 | 226 | 0 | 163,729,203 | KNOWN_COMPLETE (72, under cap) | no | 0 | 0 |
| 0 | www.fincen.gov | 2,870 | 4,094 | 0 | 836,438,194 | KNOWN_COMPLETE (full sitemap, under cap) | no | 6 | 0 |
| 0 | www.treasury.gov | 0 | 95 | 0 | 10,978,323 | ENUMERABLE | no | 19 | 0 |
| 1 | www.govinfo.gov | 30,317 | 1,604 | 28,713 | 2,666,029,053 | OPEN_ENDED (bulk collections exist) | CEILING_HIT_30000 | 6 | 0 |
| 1 | www.justice.gov | 30,000 | 5,777 | 24,223 | 191,917,654 | OPEN_ENDED (quality audit gating expansion) | CEILING_HIT_30000 | 3 | 4 |
| 1 | www.fdic.gov | 21,249 | 5,095 | 16,154 | 376,745,481 | ENUMERABLE | CEILING_HIT_5000 | 1 | 0 |
| 1 | oversight.house.gov | 19,450 | 5,189 | 14,261 | 439,315,205 | ENUMERABLE | CEILING_HIT_5000 | 0 | 0 |
| 1 | www.occ.gov | 15,237 | 5,627 | 9,610 | 1,543,515,422 | ENUMERABLE | CEILING_HIT_5000 | 0 | 0 |
| 1 | ncua.gov | 9,407 | 1,569 | 7,838 | 312,406,605 | ENUMERABLE | CEILING_HIT_5000 | 2 | 0 |
| 1 | vault.fbi.gov | 9,535 | 5,024 | 4,511 | 226,351,769 | ENUMERABLE | CEILING_HIT_5000 | 2 | 0 |
| 1 | fincen.gov | 0 | 6 | 0 | 199,724 | UNCLASSIFIED | no | 3 | 0 |
| 1 | gao.gov | 0 | 1 | 0 | 132,763 | UNCLASSIFIED | no | 0 | 0 |
| 1 | judiciary.house.gov | 0 | 988 | 0 | 632,521,243 | NOT_ONBOARDED (no sitemap) | no | 1 | 1 |
| 1 | justice.gov | 0 | 2 | 0 | 635,168 | UNCLASSIFIED | no | 0 | 0 |
| 1 | occ.gov | 0 | 5 | 0 | 836,766 | UNCLASSIFIED | no | 0 | 0 |
| 1 | treasury.gov | 0 | 2 | 0 | 303,046 | UNCLASSIFIED | no | 1 | 0 |
| 1 | www.congress.gov | 0 | 3 | 0 | 6,218,875 | NOT_ONBOARDED (API connector needed) | no | 0 | 7 |
| 1 | www.federalreserve.gov | 0 | 15 | 0 | 1,326,205 | NOT_ONBOARDED (no sitemap) | no | 0 | 0 |
| 1 | www.gao.gov | 0 | 1,507 | 0 | 194,280,977 | NOT_ONBOARDED (no sitemap; listing pages only) | no | 0 | 0 |
| 1 | www.ncua.gov | 0 | 6 | 0 | 1,139,755 | ENUMERABLE | no | 0 | 0 |
| 2 | www.sec.gov | 30,000 | 4,991 | 25,009 | 6,339,700,493 | OPEN_ENDED (EDGAR bulk beyond web pages) | CEILING_HIT_30000 | 4 | 1 |
| 2 | IRS Form 990 bulk XML | 0 | 0 | ? | 0 | NOT_ONBOARDED | n/a | 0 | 0 |
| 2 | SAM.gov / USAspending snapshots | 0 | 0 | ? | 0 | NOT_ONBOARDED | n/a | 0 | 0 |
| 2 | FEC bulk data | 0 | 0 | ? | 0 | NOT_ONBOARDED | n/a | 0 | 0 |
| 2 | Regulatory licensing datasets (ADV, NMLS, FCC, FERC) | 0 | 0 | ? | 0 | NOT_ONBOARDED | n/a | 0 | 0 |
| 3 | 50-state corporate registries + UCC | 0 | 0 | ? | 0 | NOT_ONBOARDED | n/a | 0 | 0 |
| 3 | County recorder/assessor records | 0 | 0 | ? | 0 | NOT_ONBOARDED | n/a | 0 | 0 |

Historical/superseded-source recovery: NOT_STARTED for all tiers (next phase after current-source frontier).
