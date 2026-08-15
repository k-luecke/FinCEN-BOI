# SAR source catalog

Suspicious Activity Reports (SARs) are confidential Bank Secrecy Act
records. Under 31 U.S.C. § 5318(g)(2) and implementing regulations,
neither filing institutions nor the government may disclose a SAR or
information that would reveal its existence, and unauthorized disclosure
carries criminal penalties. There is therefore no lawful public corpus
of SAR filings to gather, and this project does not attempt to assemble
one.

What *can* be gathered splits cleanly along the rule established in
[PROVENANCE.md](PROVENANCE.md):

1. **Government-public SAR material is mirrored** — fetched by the
   crawler, hashed, and preserved byte-for-byte.
2. **Non-government or unofficial sources are referenced** — cataloged
   here with provenance labels so they can be found and cited, but
   never fetched or mirrored by the crawler.

---

## 1. Government-public SAR material (mirrored via `seeds.txt`)

| Material | Publisher | Provenance |
|----------|-----------|------------|
| SAR Stats — aggregate filing statistics and bulk data | FinCEN | `GOV-PUBLIC` |
| SAR filing information, forms, and electronic filing instructions | FinCEN / BSA E-Filing | `GOV-PUBLIC` |
| SAR-related advisories and guidance | FinCEN | `GOV-PUBLIC` |
| FFIEC BSA/AML Examination Manual (SAR sections) | FFIEC | `GOV-PUBLIC` |
| BSA/AML supervision pages of the federal banking regulators | OCC, FDIC, Federal Reserve, NCUA | `GOV-PUBLIC` |
| Oversight reports on SAR programs | GAO, Treasury OIG | `GOV-PUBLIC` |
| Enforcement actions and rulemakings that discuss SAR obligations | FinCEN, Federal Register | `GOV-PUBLIC` |
| Congressional hearing records and committee releases about SARs | House/Senate committees | `CONGRESS` |
| Judicial opinions and public court filings that quote or describe SARs | Federal courts (via govinfo.gov) | `COURT` |

These enter the archive through the normal seed → fetch → hash →
manifest pipeline.

## 2. Non-government / unofficial sources (referenced only — never mirrored)

Cataloged for citation. The crawler's allowlist does not include these
hosts, so they cannot be fetched even if seeded by mistake.

| Reference | URL | Provenance |
|-----------|-----|------------|
| ICIJ — FinCEN Files investigation hub | https://www.icij.org/investigations/fincen-files/ | `PRESS-REPORT` |
| ICIJ — FinCEN Files transactions dataset (intentionally published derivative data; not raw SARs) | https://www.icij.org/investigations/fincen-files/explore-the-fincen-files-data/ | `PRESS-DATA` |
| BuzzFeed News — FinCEN Files series | https://www.buzzfeednews.com/collection/fincenfiles | `PRESS-REPORT` |
| CourtListener / RECAP — free but unofficial mirror of federal court dockets | https://www.courtlistener.com/ | `SECONDARY` |

To add a reference, append a row with the correct provenance label. If
a source turns out to be an official government publication after all,
it graduates to `seeds.txt` and the allowlist instead.

## 3. Leaked raw SARs (`LEAK-REFERENCE` — cited, never gathered)

The FinCEN Files reporting was based on leaked SARs. The journalism
about them and the intentionally released derivative dataset are
covered by section 2. The underlying leaked SAR documents themselves
are confidential BSA records regardless of who has re-hosted them, and
this archive does not fetch, mirror, or redistribute them from any
source, official-looking or not. Where a leaked document must be
identified for research purposes, record a `LEAK-REFERENCE` entry:
a citation describing the document (e.g. the reporting that describes
it, filing institution, date range as published) — metadata about the
material, not the material.
