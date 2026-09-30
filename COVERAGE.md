# Coverage report

Generated 2026-09-30T18:34:35.263248+00:00 from committed inventory + manifest.

**Reading this table:** a host at the sitemap cap (5000 URLs/host) is bounded by *discovery budget*, not by the end of its collection — those rows are a first slice. Archive size is never a proxy for share-of-BOI preserved: the CTA-filed database is confidential and not publicly downloadable.

**Non-content**: captures the challenge detector classified as bot challenges / interstitials / application shells — bytes we hold that are *not* the requested record (see RECOVERY-REPORT.md for lawful alternate-route recovery).

| Host | Discovered | Attempted | Archived | Non-content | With content | Ceiling hit? | Bytes | Median obj | p95 obj |
|------|-----------:|----------:|---------:|------------:|-------------:|--------------|------:|-----------:|--------:|
| bsaaml.ffiec.gov | 0 | 3 | 0 | 0 | 0 | no | 0 | — | — |
| bsaefiling.fincen.gov | 0 | 16 | 8 | 0 | 8 | no | 11,642,555 | 1,352,619 | 3,118,512 |
| congress.gov | 0 | 3 | 0 | 0 | 0 | no | 0 | — | — |
| fincen.gov | 0 | 9 | 6 | 0 | 6 | no | 199,724 | 32,778 | 35,808 |
| gao.gov | 0 | 2 | 2 | 0 | 2 | no | 224,036 | 112,018 | 130,688 |
| home.treasury.gov | 9,751 | 12,294 | 12,236 | 0 | 12,236 | YES — sitemap cap 5000/host | 3,151,247,906 | 108,845 | 394,765 |
| judiciary.house.gov | 0 | 994 | 988 | 0 | 988 | no | 632,521,324 | 184,343 | 1,200,637 |
| justice.gov | 0 | 2 | 2 | 0 | 2 | no | 635,168 | 317,584 | 528,113 |
| ncua.gov | 9,463 | 9,779 | 9,777 | 0 | 9,777 | YES — sitemap cap 5000/host | 2,987,346,237 | 61,344 | 1,086,152 |
| occ.gov | 0 | 5 | 5 | 0 | 5 | no | 836,766 | 78,416 | 461,953 |
| oig.treasury.gov | 72 | 226 | 226 | 0 | 226 | no | 163,729,203 | 117,012 | 2,980,022 |
| oversight.house.gov | 5,000 | 17,101 | 16,961 | 0 | 16,961 | YES — sitemap cap 5000/host | 1,169,368,125 | 60,377 | 68,003 |
| treasury.gov | 0 | 3 | 2 | 0 | 2 | no | 303,046 | 151,523 | 178,677 |
| vault.fbi.gov | 5,328 | 9,889 | 9,887 | 0 | 9,887 | YES — sitemap cap 5000/host | 332,226,749 | 21,929 | 22,450 |
| web.archive.org | 0 | 2,678 | 2,159 | 0 | 2,159 | no | 59,886,953 | 249 | 100,473 |
| www.congress.gov | 0 | 78 | 14 | 0 | 14 | no | 30,654,231 | 368,127 | 9,651,232 |
| www.fdic.gov | 5,040 | 17,116 | 17,112 | 0 | 17,112 | YES — sitemap cap 5000/host | 1,264,687,069 | 68,733 | 92,282 |
| www.federalregister.gov | 319 | 773 | 319 | 0 | 319 | no | 1,672,988 | 4,337 | 8,331 |
| www.federalreserve.gov | 0 | 17 | 15 | 0 | 15 | no | 1,326,205 | 82,878 | 146,236 |
| www.ffiec.gov | 0 | 14 | 0 | 0 | 0 | no | 0 | — | — |
| www.fincen.gov | 2,885 | 4,869 | 4,181 | 0 | 4,181 | no | 877,439,615 | 34,837 | 819,515 |
| www.gao.gov | 0 | 7,729 | 7,673 | 54 | 7,619 | no | 6,715,034,845 | 93,970 | 5,030,953 |
| www.govinfo.gov | 501 | 18,329 | 18,310 | 0 | 18,310 | no | 16,422,047,517 | 45,655 | 1,024,101 |
| www.justice.gov | 5,003 | 5,788 | 5,780 | 4,367 | 1,413 | YES — sitemap cap 5000/host | 192,215,459 | 2,520 | 101,524 |
| www.ncua.gov | 0 | 6 | 6 | 0 | 6 | no | 1,140,127 | 73,871 | 591,447 |
| www.occ.gov | 5,069 | 15,516 | 15,511 | 0 | 15,511 | YES — sitemap cap 5000/host | 3,248,045,762 | 60,433 | 858,809 |
| www.sec.gov | 5,000 | 25,008 | 24,960 | 166 | 24,794 | YES — sitemap cap 5000/host | 12,124,930,860 | 56,093 | 742,873 |
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
