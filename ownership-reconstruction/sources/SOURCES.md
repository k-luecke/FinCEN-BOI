# Ownership-reconstruction source catalog

Sources that publicly and lawfully disclose entity↔person
ownership/control relationships. Policy for every source:

- Public access only — no authentication, no bypassing access controls
  or paywalls.
- Prefer **official bulk-data products and APIs** over scraping search
  interfaces; a source whose terms prohibit bulk collection is
  cataloged reference-only.
- Every ingested document is archived (hashed bytes + manifest) before
  extraction, so each relationship's `sha256` points at preserved
  evidence.

## 1. State corporate registries

The highest-value layer. Per GAO's 2026 review, most states collect
*some* ownership/control information — officers, directors, LLC
managers or members — but requirements vary substantially by state and
those people are **not necessarily CTA beneficial owners**. That is
why the schema keeps registry roles (`MANAGER`, `MEMBER`, `OFFICER`,
`REGISTERED_AGENT`, …) distinct from `BENEFICIAL_OWNER_REPORTED`.

Per-state onboarding checklist (work through before ingesting):

1. Does the state publish an official bulk download or API?
2. What roles does the state actually collect and disclose?
3. Do the terms of use permit archival/bulk retrieval?
4. Historical depth — are amendments/annual reports retrievable?

| State onboarding status | Meaning |
|-------------------------|---------|
| `RESEARCH`              | Not yet assessed (initial state for all 50 states + DC + territories) |
| `BULK`                  | Official bulk data available — ingest via bulk product |
| `API`                   | Official API — ingest via API within its terms |
| `PORTAL-ONLY`           | Search portal only — assess terms before any collection |
| `REFERENCE-ONLY`        | Terms prohibit collection — cite, do not ingest |

All jurisdictions currently `RESEARCH`. Track per-state findings as
`sources/state-<XX>.md` files as they are assessed.

## 2. Federal datasets

| Source | What it discloses | Access | Status |
|--------|-------------------|--------|--------|
| SEC EDGAR (sec.gov — allowlisted) | Officers/directors, 5%+ ownership (Schedules 13D/13G), insider ownership (Forms 3/4/5), subsidiaries (Ex-21) | Official full-text + bulk data | Ready to onboard |
| Federal Register / GovInfo (allowlisted) | Rulemakings; ownership disclosures embedded in notices | Already being archived | Active |
| Court records via GovInfo (allowlisted) | Opinions and public filings that establish ownership/control | Free official mirror of opinions | Ready to onboard |
| FEC bulk data (fec.gov) | Committee officers/treasurers, corporate connections | Official bulk downloads | RESEARCH — host not yet allowlisted |
| IRS Form 990 series (irs.gov) | Nonprofit officers/directors/key employees | Official bulk e-file data | RESEARCH — host not yet allowlisted |
| SAM.gov entity registrations | Federal contractor entity data | Official API/extracts | RESEARCH — host not yet allowlisted |
| USAspending | Contract/grant recipient ownership fields (highly-compensated officers) | Official API/bulk | RESEARCH — host not yet allowlisted |
| OFAC sanctions lists (treasury.gov — allowlisted) | Designated persons and their entities, with ownership rationale | Official data files | Ready to onboard |
| Bankruptcy filings | Statements of financial affairs disclose ownership | PACER is paywalled — use free official sources and RECAP references only | RESEARCH |
| County property/business records | Deeds, fictitious-name filings | Varies wildly | RESEARCH |

Hosts get added to the crawler allowlist when their connector is
built, not before.

## 3. Reference-only (never ingested as ground truth)

| Source | Why reference-only |
|--------|--------------------|
| CourtListener / RECAP | Unofficial mirror; cite as `SECONDARY`, prefer official copies |
| OpenCorporates and similar aggregators | Secondary aggregation; use to *find* primary records, never as evidence themselves |
| Journalism (ICIJ, etc.) | `PRESS-REPORT`/`RESEARCH_INFERENCE` at most — see PROVENANCE.md |

## 4. Related but separate: Residential Real Estate regime

FinCEN's Residential Real Estate reporting regime (transferee
entity/trust beneficial-ownership reporting on covered transfers, with
reporting persons retaining certifications for five years) is a
**different reporting regime from CTA/BOSS**. Its public guidance and
rulemaking record are preserved under `policy-history/`, not mingled
into this dataset.
