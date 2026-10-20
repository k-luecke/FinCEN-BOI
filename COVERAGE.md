# Coverage report

Generated 2026-10-20T16:58:46.923874+00:00 from committed inventory + manifest.

**Reading this table:** a host at the sitemap cap (5000 URLs/host) is bounded by *discovery budget*, not by the end of its collection — those rows are a first slice. Archive size is never a proxy for share-of-BOI preserved: the CTA-filed database is confidential and not publicly downloadable.

**Non-content**: captures the challenge detector classified as bot challenges / interstitials / application shells — bytes we hold that are *not* the requested record (see RECOVERY-REPORT.md for lawful alternate-route recovery).

| Host | Discovered | Attempted | Archived | Non-content | With content | Ceiling hit? | Bytes | Median obj | p95 obj |
|------|-----------:|----------:|---------:|------------:|-------------:|--------------|------:|-----------:|--------:|
| bsaaml.ffiec.gov | 0 | 3 | 0 | 0 | 0 | no | 0 | — | — |
| bsaefiling.fincen.gov | 0 | 16 | 8 | 0 | 8 | no | 11,642,555 | 1,352,619 | 3,118,512 |
| congress.gov | 0 | 3 | 0 | 0 | 0 | no | 0 | — | — |
| fincen.gov | 0 | 9 | 6 | 0 | 6 | no | 199,724 | 32,778 | 35,808 |
| gao.gov | 0 | 2 | 2 | 0 | 2 | no | 224,036 | 112,018 | 130,688 |
| home.treasury.gov | 9,801 | 12,344 | 12,286 | 0 | 12,286 | YES — sitemap cap 5000/host | 3,155,446,677 | 108,821 | 393,947 |
| judiciary.house.gov | 0 | 994 | 988 | 0 | 988 | no | 632,521,118 | 184,343 | 1,200,637 |
| justice.gov | 0 | 2 | 2 | 0 | 2 | no | 635,168 | 317,584 | 528,113 |
| ncua.gov | 9,470 | 9,786 | 9,784 | 0 | 9,784 | YES — sitemap cap 5000/host | 2,987,757,962 | 61,332 | 1,086,092 |
| occ.gov | 0 | 5 | 5 | 0 | 5 | no | 836,766 | 78,416 | 461,953 |
| oig.treasury.gov | 72 | 226 | 226 | 0 | 226 | no | 163,729,203 | 117,012 | 2,980,022 |
| oversight.house.gov | 5,000 | 17,101 | 16,961 | 0 | 16,961 | YES — sitemap cap 5000/host | 1,169,368,269 | 60,377 | 68,003 |
| treasury.gov | 0 | 3 | 2 | 0 | 2 | no | 303,046 | 151,523 | 178,677 |
| vault.fbi.gov | 5,399 | 9,960 | 9,958 | 0 | 9,958 | YES — sitemap cap 5000/host | 333,594,662 | 21,928 | 22,448 |
| web.archive.org | 0 | 5,835 | 4,921 | 0 | 4,921 | no | 138,257,279 | 244 | 100,518 |
| www.congress.gov | 0 | 78 | 14 | 0 | 14 | no | 30,654,231 | 368,127 | 9,651,232 |
| www.fdic.gov | 5,050 | 17,126 | 17,122 | 0 | 17,122 | YES — sitemap cap 5000/host | 1,265,447,751 | 68,734 | 92,303 |
| www.federalregister.gov | 322 | 779 | 322 | 0 | 322 | no | 1,686,861 | 4,340 | 8,312 |
| www.federalreserve.gov | 0 | 17 | 15 | 0 | 15 | no | 1,326,205 | 82,878 | 146,236 |
| www.ffiec.gov | 0 | 14 | 0 | 0 | 0 | no | 0 | — | — |
| www.fincen.gov | 2,894 | 4,878 | 4,190 | 0 | 4,190 | no | 877,722,940 | 34,828 | 819,515 |
| www.gao.gov | 0 | 7,729 | 7,673 | 54 | 7,619 | no | 6,715,031,083 | 93,970 | 5,030,953 |
| www.govinfo.gov | 504 | 18,332 | 18,313 | 0 | 18,313 | no | 16,422,981,431 | 45,656 | 1,023,618 |
| www.justice.gov | 5,009 | 5,794 | 5,786 | 4,366 | 1,420 | YES — sitemap cap 5000/host | 192,837,021 | 2,520 | 101,573 |
| www.ncua.gov | 0 | 6 | 6 | 0 | 6 | no | 1,140,127 | 73,871 | 591,447 |
| www.occ.gov | 5,102 | 15,549 | 15,544 | 0 | 15,544 | YES — sitemap cap 5000/host | 3,269,823,286 | 60,441 | 861,760 |
| www.sec.gov | 5,001 | 25,009 | 24,961 | 166 | 24,795 | YES — sitemap cap 5000/host | 12,124,987,528 | 56,093 | 742,779 |
| www.treasury.gov | 0 | 602 | 95 | 0 | 95 | no | 10,978,323 | 110,609 | 186,860 |

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
