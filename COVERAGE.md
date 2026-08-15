# Coverage report

Generated 2026-08-15T13:25:15.448769+00:00 from committed inventory + manifest.

**Reading this table:** a host at the sitemap cap (5000 URLs/host) is bounded by *discovery budget*, not by the end of its collection — those rows are a first slice. Archive size is never a proxy for share-of-BOI preserved: the CTA-filed database is confidential and not publicly downloadable.

| Host | Discovered | Attempted | Archived | Ceiling hit? | Bytes | Median obj | p95 obj |
|------|-----------:|----------:|---------:|--------------|------:|-----------:|--------:|
| bsaaml.ffiec.gov | 0 | 1 | 0 | no | 0 | — | — |
| bsaefiling.fincen.gov | 0 | 1 | 0 | no | 0 | — | — |
| home.treasury.gov | 5,000 | 5,001 | 5,001 | YES — sitemap cap 5000/host | 604,445,437 | 110,296 | 173,731 |
| judiciary.house.gov | 0 | 1 | 1 | no | 55,008 | 55,008 | 55,008 |
| oig.treasury.gov | 72 | 72 | 72 | no | 2,383,761 | 30,142 | 43,747 |
| oversight.house.gov | 5,000 | 5,000 | 4,930 | YES — sitemap cap 5000/host | 301,022,999 | 59,544 | 64,620 |
| vault.fbi.gov | 5,000 | 5,001 | 5,001 | YES — sitemap cap 5000/host | 108,329,755 | 21,960 | 22,731 |
| www.congress.gov | 0 | 1 | 0 | no | 0 | — | — |
| www.fdic.gov | 5,000 | 5,001 | 5,000 | YES — sitemap cap 5000/host | 363,689,157 | 69,259 | 91,350 |
| www.federalregister.gov | 317 | 319 | 0 | no | 0 | — | — |
| www.federalreserve.gov | 0 | 1 | 0 | no | 0 | — | — |
| www.ffiec.gov | 0 | 1 | 0 | no | 0 | — | — |
| www.fincen.gov | 2,870 | 2,874 | 2,871 | no | 103,969,173 | 32,760 | 55,160 |
| www.gao.gov | 0 | 3 | 3 | no | 257,069 | 122,070 | 131,693 |
| www.govinfo.gov | 499 | 499 | 498 | no | 134,425,797 | 192,504 | 546,057 |
| www.justice.gov | 5,000 | 5,001 | 5,001 | YES — sitemap cap 5000/host | 79,527,411 | 2,494 | 98,703 |
| www.ncua.gov | 0 | 1 | 1 | no | 65,845 | 65,845 | 65,845 |
| www.occ.gov | 5,003 | 5,001 | 5,000 | YES — sitemap cap 5000/host | 1,416,445,434 | 67,868 | 1,164,314 |
| www.sec.gov | 5,000 | 5,002 | 4,986 | YES — sitemap cap 5000/host | 6,337,854,210 | 132,658 | 1,618,682 |

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
