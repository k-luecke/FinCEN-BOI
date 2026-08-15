# Coverage report

Generated 2026-08-15T20:14:32.765806+00:00 from committed inventory + manifest.

**Reading this table:** a host at the sitemap cap (5000 URLs/host) is bounded by *discovery budget*, not by the end of its collection — those rows are a first slice. Archive size is never a proxy for share-of-BOI preserved: the CTA-filed database is confidential and not publicly downloadable.

| Host | Discovered | Attempted | Archived | Ceiling hit? | Bytes | Median obj | p95 obj |
|------|-----------:|----------:|---------:|--------------|------:|-----------:|--------:|
| bsaaml.ffiec.gov | 0 | 3 | 0 | no | 0 | — | — |
| bsaefiling.fincen.gov | 0 | 16 | 8 | no | 11,642,555 | 1,352,619 | 3,118,512 |
| congress.gov | 0 | 3 | 0 | no | 0 | — | — |
| fincen.gov | 0 | 9 | 6 | no | 199,724 | 32,778 | 35,808 |
| gao.gov | 0 | 2 | 2 | no | 224,036 | 112,018 | 130,688 |
| home.treasury.gov | 19,549 | 8,792 | 8,745 | YES — sitemap cap 5000/host | 2,886,103,790 | 113,586 | 598,957 |
| judiciary.house.gov | 0 | 994 | 988 | no | 632,521,243 | 184,343 | 1,200,637 |
| justice.gov | 0 | 2 | 2 | no | 635,168 | 317,584 | 528,113 |
| ncua.gov | 9,407 | 1,571 | 1,569 | YES — sitemap cap 5000/host | 312,406,605 | 60,325 | 614,906 |
| occ.gov | 0 | 5 | 5 | no | 836,766 | 78,416 | 461,953 |
| oig.treasury.gov | 72 | 226 | 226 | no | 163,729,203 | 117,012 | 2,980,022 |
| oversight.house.gov | 19,450 | 5,259 | 5,189 | YES — sitemap cap 5000/host | 439,315,205 | 59,600 | 65,681 |
| treasury.gov | 0 | 3 | 2 | no | 303,046 | 151,523 | 178,677 |
| vault.fbi.gov | 9,535 | 5,026 | 5,024 | YES — sitemap cap 5000/host | 226,351,769 | 21,960 | 22,775 |
| www.congress.gov | 0 | 13 | 3 | no | 6,218,875 | 315,625 | 5,096,640 |
| www.fdic.gov | 21,249 | 5,098 | 5,095 | YES — sitemap cap 5000/host | 376,745,481 | 69,296 | 91,913 |
| www.federalregister.gov | 317 | 452 | 0 | no | 0 | — | — |
| www.federalreserve.gov | 0 | 17 | 15 | no | 1,326,205 | 82,878 | 146,236 |
| www.ffiec.gov | 0 | 14 | 0 | no | 0 | — | — |
| www.fincen.gov | 2,870 | 4,119 | 4,094 | no | 836,438,193 | 34,760 | 793,673 |
| www.gao.gov | 0 | 4,230 | 4,222 | no | 574,657,590 | 84,116 | 145,599 |
| www.govinfo.gov | 30,317 | 2,295 | 2,288 | YES — sitemap cap 5000/host | 2,693,450,376 | 45,324 | 1,363,171 |
| www.justice.gov | 30,000 | 5,785 | 5,777 | YES — sitemap cap 5000/host | 191,917,654 | 2,518 | 101,504 |
| www.ncua.gov | 0 | 6 | 6 | no | 1,139,755 | 73,871 | 591,447 |
| www.occ.gov | 15,237 | 5,630 | 5,627 | YES — sitemap cap 5000/host | 1,543,515,422 | 66,199 | 1,158,664 |
| www.sec.gov | 30,000 | 5,008 | 4,991 | YES — sitemap cap 5000/host | 6,339,700,493 | 132,673 | 1,615,095 |
| www.treasury.gov | 0 | 602 | 95 | no | 10,978,323 | 110,609 | 186,860 |

## Known bulk datasets not yet acquired

**www.sec.gov**
- EDGAR companyfacts.zip (403 on 2026-08-15; weekly retry)
- EDGAR full filing archives (per-filing corpus far beyond web pages)
- EDGAR full-text search corpus

**www.govinfo.gov**
- GovInfo bulk data collections (FR XML, CFR, court opinions)

**www.federalregister.gov**
- Full FR document XML via API (only FinCEN-agency docs enumerated)

**www.congress.gov**
- congress.gov API corpus (bills, reports, hearings; needs API key connector)

**www.gao.gov**
- GAO reports corpus (no sitemap; needs listing-page/API enumeration)

**Not yet onboarded (source families)**
- IRS Form 990 e-file bulk XML (irs.gov)
- SAM.gov entity registration extracts
- USAspending award/recipient bulk data
- FEC bulk data
- 50-state corporate registries + UCC (all jurisdictions at RESEARCH)
- County recorder/assessor records
- Regulatory licensing datasets (Form ADV, NMLS, FCC, FERC, ...)
