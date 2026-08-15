# Preservation priorities (initial acquisition window)

Generated 2026-08-15T22:34:10.263977+00:00. **High-priority (tier 0-1) unarchived backlog: 65,878 URLs.**

| Tier | Source | Discovered | Archived | Unarchived | Bytes | Denominator | Ceiling | Temp fail | Restricted |
|-----:|--------|-----------:|---------:|-----------:|------:|-------------|---------|----------:|-----------:|
| 0 | home.treasury.gov | 19,549 | 8,745 | 10,804 | 2,886,103,790 | ENUMERABLE | CEILING_HIT_5000 | 7 | 27 |
| 0 | www.federalregister.gov | 317 | 0 | 317 | 0 | ACCESS_LIMITED (bot mitigation; use API + govinfo twins) | no | 832 | 0 |
| 0 | bsaefiling.fincen.gov | 0 | 8 | 0 | 11,642,555 | ACCESS_LIMITED (unreachable from CI) | no | 10 | 0 |
| 0 | oig.treasury.gov | 72 | 226 | 0 | 163,729,203 | KNOWN_COMPLETE (72, under cap) | no | 0 | 0 |
| 0 | www.fincen.gov | 2,870 | 4,094 | 0 | 836,438,193 | KNOWN_COMPLETE (full sitemap, under cap) | no | 7 | 0 |
| 0 | www.treasury.gov | 0 | 95 | 0 | 10,978,323 | ENUMERABLE | no | 19 | 0 |
| 1 | www.justice.gov | 30,000 | 5,777 | 24,223 | 191,917,654 | OPEN_ENDED (quality audit gating expansion) | CEILING_HIT_30000 | 3 | 4 |
| 1 | www.govinfo.gov | 30,317 | 14,286 | 16,031 | 3,239,260,677 | OPEN_ENDED (bulk collections exist) | CEILING_HIT_30000 | 13 | 0 |
| 1 | ncua.gov | 9,407 | 1,569 | 7,838 | 312,406,605 | ENUMERABLE | CEILING_HIT_5000 | 2 | 0 |
| 1 | www.fdic.gov | 21,249 | 17,073 | 4,176 | 1,261,747,300 | ENUMERABLE | CEILING_HIT_5000 | 1 | 0 |
| 1 | oversight.house.gov | 19,450 | 16,961 | 2,489 | 1,169,364,395 | ENUMERABLE | CEILING_HIT_5000 | 0 | 0 |
| 1 | fincen.gov | 0 | 6 | 0 | 199,724 | UNCLASSIFIED | no | 3 | 0 |
| 1 | gao.gov | 0 | 2 | 0 | 224,036 | UNCLASSIFIED | no | 0 | 0 |
| 1 | judiciary.house.gov | 0 | 988 | 0 | 632,521,243 | NOT_ONBOARDED (no sitemap) | no | 1 | 1 |
| 1 | justice.gov | 0 | 2 | 0 | 635,168 | UNCLASSIFIED | no | 0 | 0 |
| 1 | occ.gov | 0 | 5 | 0 | 836,766 | UNCLASSIFIED | no | 0 | 0 |
| 1 | treasury.gov | 0 | 2 | 0 | 303,046 | UNCLASSIFIED | no | 1 | 0 |
| 1 | vault.fbi.gov | 9,535 | 9,559 | 0 | 325,876,267 | ENUMERABLE | CEILING_HIT_5000 | 2 | 0 |
| 1 | www.congress.gov | 0 | 3 | 0 | 6,218,875 | NOT_ONBOARDED (API connector needed) | no | 0 | 13 |
| 1 | www.federalreserve.gov | 0 | 15 | 0 | 1,326,205 | NOT_ONBOARDED (no sitemap) | no | 0 | 0 |
| 1 | www.gao.gov | 0 | 4,222 | 0 | 574,657,590 | NOT_ONBOARDED (no sitemap; listing pages only) | no | 0 | 1 |
| 1 | www.ncua.gov | 0 | 6 | 0 | 1,139,755 | ENUMERABLE | no | 0 | 0 |
| 1 | www.occ.gov | 15,237 | 15,451 | 0 | 3,224,990,390 | ENUMERABLE | CEILING_HIT_5000 | 1 | 0 |
| 2 | www.sec.gov | 30,000 | 16,978 | 13,022 | 10,307,139,201 | OPEN_ENDED (EDGAR bulk beyond web pages) | CEILING_HIT_30000 | 6 | 1 |
| 2 | IRS Form 990 bulk XML | 0 | 0 | ? | 0 | NOT_ONBOARDED | n/a | 0 | 0 |
| 2 | SAM.gov / USAspending snapshots | 0 | 0 | ? | 0 | NOT_ONBOARDED | n/a | 0 | 0 |
| 2 | FEC bulk data | 0 | 0 | ? | 0 | NOT_ONBOARDED | n/a | 0 | 0 |
| 2 | Regulatory licensing datasets (ADV, NMLS, FCC, FERC) | 0 | 0 | ? | 0 | NOT_ONBOARDED | n/a | 0 | 0 |
| 3 | 50-state corporate registries + UCC | 0 | 0 | ? | 0 | NOT_ONBOARDED | n/a | 0 | 0 |
| 3 | County recorder/assessor records | 0 | 0 | ? | 0 | NOT_ONBOARDED | n/a | 0 | 0 |

Historical/superseded-source recovery: NOT_STARTED for all tiers (next phase after current-source frontier).
