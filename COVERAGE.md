# Coverage report

Generated 2026-11-23T21:39:55.382813+00:00 from committed inventory + manifest.

**Reading this table:** a host at the sitemap cap (5000 URLs/host) is bounded by *discovery budget*, not by the end of its collection — those rows are a first slice. Archive size is never a proxy for share-of-BOI preserved: the CTA-filed database is confidential and not publicly downloadable.

**Non-content**: captures the challenge detector classified as bot challenges / interstitials / application shells — bytes we hold that are *not* the requested record (see RECOVERY-REPORT.md for lawful alternate-route recovery).

| Host | Discovered | Attempted | Archived | Non-content | With content | Ceiling hit? | Bytes | Median obj | p95 obj |
|------|-----------:|----------:|---------:|------------:|-------------:|--------------|------:|-----------:|--------:|
| bsaaml.ffiec.gov | 0 | 3 | 0 | 0 | 0 | no | 0 | — | — |
| bsaefiling.fincen.gov | 0 | 16 | 8 | 0 | 8 | no | 11,642,555 | 1,352,619 | 3,118,512 |
| congress.gov | 0 | 3 | 0 | 0 | 0 | no | 0 | — | — |
| fincen.gov | 0 | 9 | 6 | 0 | 6 | no | 199,724 | 32,778 | 35,808 |
| gao.gov | 0 | 2 | 2 | 0 | 2 | no | 224,036 | 112,018 | 130,688 |
| home.treasury.gov | 9,842 | 12,383 | 12,325 | 0 | 12,325 | YES — sitemap cap 5000/host | 3,158,519,550 | 108,785 | 392,325 |
| judiciary.house.gov | 0 | 994 | 988 | 0 | 988 | no | 632,526,583 | 184,343 | 1,200,637 |
| justice.gov | 0 | 2 | 2 | 0 | 2 | no | 635,168 | 317,584 | 528,113 |
| ncua.gov | 9,508 | 9,824 | 9,821 | 0 | 9,821 | YES — sitemap cap 5000/host | 3,001,706,572 | 61,359 | 1,086,152 |
| occ.gov | 0 | 5 | 5 | 0 | 5 | no | 836,766 | 78,416 | 461,953 |
| oig.treasury.gov | 142 | 296 | 296 | 0 | 296 | no | 166,543,366 | 43,763 | 2,654,059 |
| oversight.house.gov | 5,000 | 17,101 | 16,961 | 0 | 16,961 | YES — sitemap cap 5000/host | 1,169,368,396 | 60,377 | 68,003 |
| treasury.gov | 0 | 3 | 2 | 0 | 2 | no | 303,046 | 151,523 | 178,677 |
| vault.fbi.gov | 5,467 | 10,028 | 10,026 | 0 | 10,026 | YES — sitemap cap 5000/host | 335,048,841 | 21,928 | 22,450 |
| web.archive.org | 0 | 8,942 | 7,830 | 0 | 7,830 | no | 240,478,365 | 242 | 101,753 |
| www.congress.gov | 0 | 78 | 14 | 0 | 14 | no | 30,654,231 | 368,127 | 9,651,232 |
| www.fdic.gov | 5,073 | 17,149 | 17,145 | 0 | 17,145 | YES — sitemap cap 5000/host | 1,267,158,431 | 68,735 | 92,306 |
| www.federalregister.gov | 325 | 785 | 325 | 0 | 325 | no | 1,701,751 | 4,341 | 8,282 |
| www.federalreserve.gov | 0 | 17 | 15 | 0 | 15 | no | 1,326,205 | 82,878 | 146,236 |
| www.ffiec.gov | 0 | 14 | 0 | 0 | 0 | no | 0 | — | — |
| www.fincen.gov | 6,277 | 8,260 | 7,572 | 0 | 7,572 | YES — sitemap cap 5000/host | 981,396,782 | 31,574 | 420,983 |
| www.gao.gov | 0 | 7,729 | 7,673 | 52 | 7,621 | no | 6,715,029,215 | 93,970 | 5,030,953 |
| www.govinfo.gov | 507 | 18,335 | 18,316 | 0 | 18,316 | no | 16,423,861,542 | 45,656 | 1,023,136 |
| www.justice.gov | 5,011 | 5,796 | 5,788 | 4,366 | 1,422 | YES — sitemap cap 5000/host | 193,071,065 | 2,520 | 101,597 |
| www.ncua.gov | 0 | 6 | 6 | 0 | 6 | no | 1,140,089 | 73,871 | 591,447 |
| www.occ.gov | 5,264 | 15,678 | 15,655 | 0 | 15,655 | YES — sitemap cap 5000/host | 3,308,327,871 | 60,481 | 863,821 |
| www.sec.gov | 5,002 | 25,010 | 24,962 | 166 | 24,796 | YES — sitemap cap 5000/host | 12,125,044,306 | 56,093 | 742,776 |
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
