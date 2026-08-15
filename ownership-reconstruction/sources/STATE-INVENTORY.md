# 50-state + DC corporate-registry source inventory (Tier 3)

Initial inventory pass, 2026-08-15. Confidence flags: **CONFIRMED**
(verified against the source), **REPORTED** (believed from prior
knowledge — verify before onboarding), **UNKNOWN** (research needed).
Never bypass CAPTCHA/login/paywall; onboard bulk/API sources first —
they give the greatest preservation return per request.

## Highest-yield first targets (known/reported free bulk or open data)

| Jurisdiction | Channel | What it exposes | Confidence |
|--------------|---------|-----------------|------------|
| Colorado | Socrata open data (business entities dataset, CSV) | Entities, registered agents, addresses, status, history | REPORTED |
| New York | Socrata open data (active corporations since 1800) | Entities, DOS process addresses | REPORTED |
| Oregon | Socrata open data (active businesses) | Entities, registered agents, officers field varies | REPORTED |
| Hawaii | Socrata open data (DCCA business registrations) | Entities, officers/agents | REPORTED |
| Connecticut | Socrata open data (business registrations) | Entities, principals | REPORTED |
| Iowa | Socrata open data (active entities) | Entities, agents | REPORTED |
| Washington | Open data / SOS downloads | Corporations + charities | REPORTED |
| Florida | Sunbiz public SFTP bulk files + document images | Full filing corpus incl. officers, annual reports, historical | REPORTED |
| Ohio | SOS bulk business data download | Entities, filings history | REPORTED |
| North Carolina | SOS full database download (free) | Entities, officials | REPORTED |
| Texas | Comptroller franchise-tax active entities (open CSV) | Entity names, addresses, status (officers via SOSDirect, paid) | REPORTED |
| Minnesota | SOS data services | Entities (terms to verify) | UNKNOWN |
| Georgia | SOS corporations data download | Entities, officers | UNKNOWN |
| Virginia | SCC data extracts | Entities (fee status to verify) | UNKNOWN |

## Known constrained jurisdictions

| Jurisdiction | Constraint |
|--------------|-----------|
| Delaware | Bulk data commercial/paid; free search minimal — highest shell-formation volume, worst public visibility. Record as ACCESS_LIMITED; rely on side channels (SEC, court, property) for DE entities |
| Wyoming | Database download exists but fee-based (verify current terms) |
| Nevada | API/bulk fee-based (verify) |
| California | SOS bulk data historically fee-based; check open-data portal |
| Texas (officers) | SOSDirect paid |

## Remaining jurisdictions

AL, AK, AZ, AR, DC, ID, IL, IN, KS, KY, LA, ME, MD, MA, MI, MS, MO,
MT, NE, NH, NJ, NM, ND, OK, PA, RI, SC, SD, TN, UT, VT, WV, WI:
**UNKNOWN — research pass needed.** For each, determine: available
now? bulk download? public API? public search? historical filings?
document downloads? officers/directors/members/managers/registered
agents exposed? formation docs? annual reports? amendments? mergers?
dissolutions? former names?

## Onboarding order

1. Verify + onboard the Socrata open-data states (one generic
   snapshot connector covers all of them: dataset CSV export →
   stream → hash → release).
2. Florida Sunbiz bulk (largest filing-image corpus freely available).
3. Ohio / North Carolina full downloads.
4. Research pass over UNKNOWN jurisdictions, updating this file with
   CONFIRMED findings and per-state `state-<XX>.md` notes.
