# High-value gaps

Sources we want, cannot currently acquire (or have not yet onboarded),
and the reason. Restrictions are recorded, never evaded.

## Enumeration gaps (no sitemap exposed to discovery)

Zero URLs were discovered by sitemap on these allowlisted hosts —
either no standard sitemap, robots blocked from CI, or non-standard
locations. Their listing pages are seeded directly; deeper coverage
needs per-host enumeration work:

| Host | Note |
|------|------|
| www.congress.gov | No sitemap found. congress.gov offers an official API (api.congress.gov, free key) — proper connector work, not yet built |
| www.gao.gov | No sitemap found; `reports-testimonies` and `topics` listing pages seeded |
| www.ffiec.gov / bsaaml.ffiec.gov | No sitemap found; manual seed of key pages (BSA/AML manual) in place |
| www.ncua.gov, www.federalreserve.gov | No sitemap found; supervision pages seeded |
| bsaefiling.fincen.gov | No sitemap; main page seeded |
| judiciary.house.gov | No sitemap found; homepage seeded |

## Access-restricted / paywalled (recorded, not evaded)

| Source | Status |
|--------|--------|
| PACER (federal court dockets incl. bankruptcy schedules) | Paywalled. Use free official channels (govinfo opinions) and RECAP references only |
| State registry search portals with CAPTCHAs or anti-bulk terms | Recorded per state as onboarding proceeds; bulk-data states preferred |
| Wayback Machine / web.archive.org | Not on the allowlist yet; WEB-ARCHIVE evidence channel designed but no connector |

## Not-yet-onboarded ingestion families (designed, no connector built)

State corporate registries (all jurisdictions at `RESEARCH`), UCC
systems, county real-estate records, SAM/USAspending snapshots, IRS
990 bulk XML, FEC bulk data, regulatory licensing datasets,
enforcement-document harvesting beyond seeded pages. SEC EDGAR is the
exception — its bulk snapshot connector is live.

## Confidential by law (never targets)

The CTA-filed BOI database (31 U.S.C. § 5336(c)) and SAR/BSA records —
including leak mirrors of either. These are boundaries, not gaps to
close.

## Watch items

- The June 2026 GAO report on BOI collection/sharing and six-agency
  access: locate the report landing page + PDF on gao.gov and seed
  them explicitly (gao.gov's lack of sitemap means discovery will not
  find it automatically).
- FinCEN deletion implementation notices: as published, seed same-day
  (see deletion-record/README.md).
