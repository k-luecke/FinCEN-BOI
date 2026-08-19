# Coverage report

Generated 2026-08-19T16:59:16.317077+00:00 from committed inventory + manifest.

**Reading this table:** a host at the sitemap cap (5000 URLs/host) is bounded by *discovery budget*, not by the end of its collection — those rows are a first slice. Archive size is never a proxy for share-of-BOI preserved: the CTA-filed database is confidential and not publicly downloadable.

**Non-content**: captures the challenge detector classified as bot challenges / interstitials / application shells — bytes we hold that are *not* the requested record (see RECOVERY-REPORT.md for lawful alternate-route recovery).

| Host | Discovered | Attempted | Archived | Non-content | With content | Ceiling hit? | Bytes | Median obj | p95 obj |
|------|-----------:|----------:|---------:|------------:|-------------:|--------------|------:|-----------:|--------:|
| bsaaml.ffiec.gov | 0 | 3 | 0 | 0 | 0 | no | 0 | — | — |
| bsaefiling.fincen.gov | 0 | 16 | 8 | 0 | 8 | no | 11,642,555 | 1,352,619 | 3,118,512 |
| congress.gov | 0 | 3 | 0 | 0 | 0 | no | 0 | — | — |
| fincen.gov | 0 | 9 | 6 | 0 | 6 | no | 199,724 | 32,778 | 35,808 |
| gao.gov | 0 | 2 | 2 | 0 | 2 | no | 224,036 | 112,018 | 130,688 |
| home.treasury.gov | 5,000 | 8,792 | 8,745 | 0 | 8,745 | YES — sitemap cap 5000/host | 2,886,103,562 | 113,586 | 598,957 |
| judiciary.house.gov | 0 | 994 | 988 | 0 | 988 | no | 632,521,243 | 184,343 | 1,200,637 |
| justice.gov | 0 | 2 | 2 | 0 | 2 | no | 635,168 | 317,584 | 528,113 |
| ncua.gov | 9,407 | 5,551 | 5,549 | 0 | 5,549 | YES — sitemap cap 5000/host | 585,912,541 | 58,000 | 188,975 |
| occ.gov | 0 | 5 | 5 | 0 | 5 | no | 836,766 | 78,416 | 461,953 |
| oig.treasury.gov | 72 | 226 | 226 | 0 | 226 | no | 163,729,203 | 117,012 | 2,980,022 |
| oversight.house.gov | 5,000 | 17,101 | 16,961 | 0 | 16,961 | YES — sitemap cap 5000/host | 1,169,364,468 | 60,377 | 67,998 |
| treasury.gov | 0 | 3 | 2 | 0 | 2 | no | 303,046 | 151,523 | 178,677 |
| vault.fbi.gov | 5,014 | 9,561 | 9,559 | 0 | 9,559 | YES — sitemap cap 5000/host | 325,876,432 | 21,936 | 22,453 |
| web.archive.org | 0 | 643 | 466 | 0 | 466 | no | 18,266,463 | 255 | 101,096 |
| www.congress.gov | 0 | 78 | 14 | 0 | 14 | no | 30,654,231 | 368,127 | 9,651,232 |
| www.fdic.gov | 5,000 | 17,076 | 17,073 | 0 | 17,073 | YES — sitemap cap 5000/host | 1,261,747,300 | 68,731 | 92,227 |
| www.federalregister.gov | 317 | 769 | 317 | 0 | 317 | no | 1,663,986 | 4,337 | 8,339 |
| www.federalreserve.gov | 0 | 17 | 15 | 0 | 15 | no | 1,326,205 | 82,878 | 146,236 |
| www.ffiec.gov | 0 | 14 | 0 | 0 | 0 | no | 0 | — | — |
| www.fincen.gov | 2,870 | 4,854 | 4,166 | 0 | 4,166 | no | 876,938,921 | 34,857 | 823,397 |
| www.gao.gov | 0 | 7,729 | 7,673 | 54 | 7,619 | no | 6,715,032,376 | 93,970 | 5,030,953 |
| www.govinfo.gov | 499 | 18,327 | 18,308 | 0 | 18,308 | no | 16,421,476,400 | 45,654 | 1,024,423 |
| www.justice.gov | 5,000 | 5,785 | 5,777 | 4,367 | 1,410 | YES — sitemap cap 5000/host | 191,920,903 | 2,520 | 101,504 |
| www.ncua.gov | 0 | 6 | 6 | 0 | 6 | no | 1,139,755 | 73,871 | 591,447 |
| www.occ.gov | 5,010 | 15,457 | 15,453 | 0 | 15,453 | YES — sitemap cap 5000/host | 3,225,744,300 | 60,405 | 857,400 |
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
