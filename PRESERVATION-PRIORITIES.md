# Preservation priorities (initial acquisition window)

Generated 2026-08-15T13:36:14.606645+00:00. **High-priority (tier 0-1) unarchived backlog: 124,630 URLs.**

| Tier | Source | Discovered | Archived | Unarchived | Bytes | Denominator | Ceiling | Temp fail | Restricted |
|-----:|--------|-----------:|---------:|-----------:|------:|-------------|---------|----------:|-----------:|
| 0 | home.treasury.gov | 19,549 | 5,001 | 14,548 | 604,445,437 | ENUMERABLE | CEILING_HIT_5000 | 0 | 0 |
| 0 | www.federalregister.gov | 317 | 0 | 317 | 0 | ACCESS_LIMITED (bot mitigation; use API + govinfo twins) | no | 319 | 0 |
| 0 | oig.treasury.gov | 72 | 72 | 0 | 2,383,761 | KNOWN_COMPLETE (72, under cap) | no | 0 | 0 |
| 0 | www.fincen.gov | 2,870 | 2,871 | 0 | 103,969,173 | KNOWN_COMPLETE (full sitemap, under cap) | no | 1 | 0 |
| 1 | www.govinfo.gov | 30,317 | 498 | 29,819 | 134,425,797 | OPEN_ENDED (bulk collections exist) | CEILING_HIT_30000 | 1 | 0 |
| 1 | www.justice.gov | 30,000 | 5,001 | 24,999 | 79,527,411 | OPEN_ENDED (quality audit gating expansion) | CEILING_HIT_30000 | 0 | 0 |
| 1 | www.fdic.gov | 21,249 | 5,000 | 16,249 | 363,689,157 | ENUMERABLE | CEILING_HIT_5000 | 0 | 0 |
| 1 | oversight.house.gov | 19,450 | 4,930 | 14,520 | 301,022,999 | ENUMERABLE | CEILING_HIT_5000 | 0 | 0 |
| 1 | www.occ.gov | 15,237 | 5,000 | 10,237 | 1,416,445,434 | ENUMERABLE | CEILING_HIT_5000 | 0 | 0 |
| 1 | ncua.gov | 9,407 | 0 | 9,407 | 0 | ENUMERABLE | CEILING_HIT_5000 | 0 | 0 |
| 1 | vault.fbi.gov | 9,535 | 5,001 | 4,534 | 108,329,755 | ENUMERABLE | CEILING_HIT_5000 | 0 | 0 |
| 1 | judiciary.house.gov | 0 | 1 | 0 | 55,008 | NOT_ONBOARDED (no sitemap) | no | 0 | 0 |
| 1 | www.gao.gov | 0 | 3 | 0 | 257,069 | NOT_ONBOARDED (no sitemap; listing pages only) | no | 0 | 0 |
| 1 | www.ncua.gov | 0 | 1 | 0 | 65,845 | ENUMERABLE | no | 0 | 0 |
| 2 | www.sec.gov | 30,000 | 4,986 | 25,014 | 6,337,854,210 | OPEN_ENDED (EDGAR bulk beyond web pages) | CEILING_HIT_30000 | 3 | 1 |
| 2 | IRS Form 990 bulk XML | 0 | 0 | ? | 0 | NOT_ONBOARDED | n/a | 0 | 0 |
| 2 | SAM.gov / USAspending snapshots | 0 | 0 | ? | 0 | NOT_ONBOARDED | n/a | 0 | 0 |
| 2 | FEC bulk data | 0 | 0 | ? | 0 | NOT_ONBOARDED | n/a | 0 | 0 |
| 2 | Regulatory licensing datasets (ADV, NMLS, FCC, FERC) | 0 | 0 | ? | 0 | NOT_ONBOARDED | n/a | 0 | 0 |
| 3 | 50-state corporate registries + UCC | 0 | 0 | ? | 0 | NOT_ONBOARDED | n/a | 0 | 0 |
| 3 | County recorder/assessor records | 0 | 0 | ? | 0 | NOT_ONBOARDED | n/a | 0 | 0 |

Historical/superseded-source recovery: NOT_STARTED for all tiers (next phase after current-source frontier).
