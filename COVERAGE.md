# Coverage report

Generated 2026-11-28T17:47:54.047914+00:00 from committed inventory + manifest.

**Reading this table:** a host at the sitemap cap (5000 URLs/host) is bounded by *discovery budget*, not by the end of its collection — those rows are a first slice. Archive size is never a proxy for share-of-BOI preserved: the CTA-filed database is confidential and not publicly downloadable.

**Non-content**: captures the challenge detector classified as bot challenges / interstitials / application shells — bytes we hold that are *not* the requested record (see RECOVERY-REPORT.md for lawful alternate-route recovery).

| Host | Discovered | Attempted | Archived | Non-content | With content | Ceiling hit? | Bytes | Median obj | p95 obj |
|------|-----------:|----------:|---------:|------------:|-------------:|--------------|------:|-----------:|--------:|
| bsaaml.ffiec.gov | 0 | 3 | 0 | 0 | 0 | no | 0 | — | — |
| bsaefiling.fincen.gov | 0 | 16 | 8 | 0 | 8 | no | 11,642,555 | 1,352,619 | 3,118,512 |
| congress.gov | 0 | 3 | 0 | 0 | 0 | no | 0 | — | — |
| fincen.gov | 0 | 9 | 6 | 0 | 6 | no | 199,724 | 32,778 | 35,808 |
| gao.gov | 0 | 2 | 2 | 0 | 2 | no | 224,036 | 112,018 | 130,688 |
| home.treasury.gov | 9,843 | 12,386 | 12,328 | 0 | 12,328 | YES — sitemap cap 5000/host | 3,158,769,118 | 108,782 | 392,314 |
| judiciary.house.gov | 0 | 994 | 988 | 0 | 988 | no | 632,526,583 | 184,343 | 1,200,637 |
| justice.gov | 0 | 2 | 2 | 0 | 2 | no | 635,168 | 317,584 | 528,113 |
| ncua.gov | 9,512 | 9,828 | 9,825 | 0 | 9,825 | YES — sitemap cap 5000/host | 3,001,965,447 | 61,388 | 1,086,073 |
| occ.gov | 0 | 5 | 5 | 0 | 5 | no | 836,766 | 78,416 | 461,953 |
| oig.treasury.gov | 142 | 296 | 296 | 0 | 296 | no | 166,543,366 | 43,763 | 2,654,059 |
| oversight.house.gov | 5,000 | 17,101 | 16,961 | 0 | 16,961 | YES — sitemap cap 5000/host | 1,169,368,395 | 60,377 | 68,003 |
| treasury.gov | 0 | 3 | 2 | 0 | 2 | no | 303,046 | 151,523 | 178,677 |
| vault.fbi.gov | 5,470 | 10,031 | 10,029 | 0 | 10,029 | YES — sitemap cap 5000/host | 335,116,341 | 21,928 | 22,450 |
| web.archive.org | 0 | 8,942 | 7,831 | 0 | 7,831 | no | 240,492,506 | 242 | 101,753 |
| www.congress.gov | 0 | 78 | 14 | 0 | 14 | no | 30,654,231 | 368,127 | 9,651,232 |
| www.fdic.gov | 5,080 | 17,156 | 17,152 | 0 | 17,152 | YES — sitemap cap 5000/host | 1,267,624,228 | 68,734 | 92,305 |
| www.federalregister.gov | 325 | 785 | 325 | 0 | 325 | no | 1,701,751 | 4,341 | 8,282 |
| www.federalreserve.gov | 0 | 17 | 15 | 0 | 15 | no | 1,326,205 | 82,878 | 146,236 |
| www.ffiec.gov | 0 | 14 | 0 | 0 | 0 | no | 0 | — | — |
| www.fincen.gov | 6,278 | 8,262 | 7,574 | 0 | 7,574 | YES — sitemap cap 5000/host | 981,433,036 | 31,574 | 420,635 |
| www.gao.gov | 0 | 7,729 | 7,673 | 51 | 7,622 | no | 6,715,026,588 | 93,970 | 5,030,953 |
| www.govinfo.gov | 507 | 18,335 | 18,316 | 0 | 18,316 | no | 16,423,861,542 | 45,656 | 1,023,136 |
| www.justice.gov | 5,012 | 5,797 | 5,789 | 4,366 | 1,423 | YES — sitemap cap 5000/host | 193,136,900 | 2,520 | 101,596 |
| www.ncua.gov | 0 | 6 | 6 | 0 | 6 | no | 1,140,089 | 73,871 | 591,447 |
| www.occ.gov | 5,264 | 15,711 | 15,688 | 0 | 15,688 | YES — sitemap cap 5000/host | 3,317,984,697 | 60,504 | 865,012 |
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
