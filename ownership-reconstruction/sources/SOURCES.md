# Ownership-reconstruction source catalog

Ten ingestion families plus web-archive evidence. Every family writes
the same universal edge format (see [../SCHEMA.md](../SCHEMA.md)), and
every ingested document is archived (hashed bytes + manifest) before
extraction so each edge's `source_sha256` points at preserved
evidence.

Standing policy for all sources: public access only; no
authentication; no bypassing access controls or paywalls; official
bulk-data products preferred over scraping search interfaces; sources
whose terms prohibit collection are reference-only. Documents are
preserved whole — extraction never substitutes for the document.

## 1. State corporate registries + historical filings (priority #1)

Not just current entity-search results: formation documents, annual
reports, amendments, mergers, dissolutions, reinstatements, and
foreign registrations. **Every historical role is retained** (closed
with `valid_to`), never overwritten by current state. Per GAO, most
states collect some officer/director/manager/member information, but
it varies by jurisdiction and is not equivalent to beneficial
ownership — which is why registry roles stay distinct from
`BENEFICIAL_OWNER` in the schema. Renames feed the `names/` history
table.

Per-state onboarding checklist: official bulk/API availability; which
roles the state discloses; terms permitting archival; historical
depth of amendments/annual reports. Track findings as
`sources/state-<XX>.md`. All jurisdictions currently `RESEARCH`.

## 2. UCC filings

Debtor / secured-party relationships expose commercial links invisible
in corporate registration — a shell with no public footprint connects
to a lender, affiliate, address, or individual through a financing
statement. Own ingestion family per state UCC system (many are
searchable through the same Secretary of State infrastructure; assess
bulk availability alongside family 1). Edges: `DEBTOR`,
`SECURED_PARTY`, plus address nodes from filing addresses.

## 3. Real estate

County recorder / register-of-deeds records, assessor parcels,
transfer deeds, mortgages/deeds of trust, and state-level transfer
records. An LLC buying property yields addresses, dates,
counterparties, signatories, and mailing addresses that can resolve an
otherwise opaque entity. Edges: `PROPERTY_OWNER`, `SIGNATORY`,
`SHARED_ADDRESS`. Highly fragmented (3,000+ counties) — onboard
opportunistically, bulk-first. FinCEN's Residential Real Estate
reporting regime's public rules/guidance/data artifacts are preserved
separately under `policy-history/` (distinct regime from CTA/BOSS).

## 4. SEC EDGAR — exhibits, not just XBRL

Ownership disclosures (Schedules 13D/13G), insider filings (Forms
3/4/5), Form D, subsidiaries exhibits (Ex-21), merger agreements,
credit agreements, and organizational charts connect enormous numbers
of legal entities. SEC publishes nightly bulk `submissions.zip` and
`companyfacts.zip` — purpose-built archival side channels: snapshot
the bulk files, archive them hashed, extract edges from the archived
copy. sec.gov is already on the crawler allowlist. Edges:
`BENEFICIAL_OWNER` (13D/G are genuinely DIRECT), `OFFICER`,
`DIRECTOR`, `PARENT`, `SUBSIDIARY`.

## 5. Federal procurement (SAM / USAspending)

Legal names, UEIs, historical names, addresses, parent/recipient
relationships, awards, agencies. **Preserve snapshots** (monthly
extracts archived and hashed), never query the live API on demand —
`ACME HOLDINGS LLC → UEI → recipient → award → agency` becomes a
reproducible evidence path only if the snapshot is preserved. Edges:
`CONTRACT_RECIPIENT`, `PARENT`; name history from historical-name
fields.

## 6. IRS nonprofit data (Form 990 series)

Officers, directors, trustees, key/highly-compensated employees,
related organizations (Schedule R), and transactions with related
entities. IRS publishes the actual e-file corpus in bulk XML (current
and historical downloads). Foundations/charities bridge people and
entities that otherwise appear disconnected. Edges: `OFFICER`,
`DIRECTOR`, `TRUSTEE`, `RELATED_ORGANIZATION`.

## 7. Courts + bankruptcy

Opinions and pleadings from free official sources (govinfo — already
allowlisted), DOJ exhibits, state court records, and bankruptcy
documents available through lawful public channels. Bankruptcy
schedules and adversary proceedings are particularly revealing about
counterparties and affiliated entities. PACER's paywall is respected —
no fee-bypass; RECAP/CourtListener are reference-only pointers to
primary documents. **Preserve the documents, not merely extracted
names.**

## 8. Regulatory licensing

FINRA/SEC investment-adviser data (Form ADV discloses control
persons), NMLS where publicly available, state insurance regulators,
state professional/business licenses, FCC, FERC, transportation
regulators, healthcare provider/entity datasets. Licensing regimes
frequently require identifying control persons that incorporation
records don't. Edges: `OFFICER`, `DIRECTOR`, `BENEFICIAL_OWNER` where
the regime directly reports it.

## 9. Enforcement + sanctions

DOJ, SEC, CFTC, FTC, CFPB, OFAC, FinCEN enforcement actions, state
AGs, banking regulators. Enforcement documents frequently contain the
exact sentence a graph needs — "X, which was owned and controlled by
Y" — and that is ingested as a `BENEFICIAL_OWNER` edge with
`evidence_class: DIRECT` backed by the archived document, never
inferred from address matching. OFAC list files additionally provide
structured ownership rationales.

## 10. Congressional + GAO material

Crawled aggressively (broader than the FinCEN-centric seed set): GAO
reports (including the June 2026 report establishing that FinCEN
collected BOI from early 2024 and that six federal agencies were
searching the system), committee exhibits, hearing records, and
investigation releases — congressional publication can transform
otherwise inaccessible information into an independently public
government record. Hosts already allowlisted; congress.gov and
gao.gov exposed no sitemap to discovery, so seed their listing pages
directly and expand.

## Web archives (`CORPORATE-PUBLIC` / `WEB-ARCHIVE`)

Corporate websites historically carried management biographies,
portfolio-company lists, office addresses, privacy-policy legal
entities, and acquisition announcements that later disappear. Archive
current corporate pages as `CORPORATE-PUBLIC` and historical snapshots
(e.g. Wayback Machine captures) as `WEB-ARCHIVE` — **never treated as
equivalent to government evidence**: edges extracted from them are at
most `OFFICIAL_INFERENCE`/`RESEARCH_INFERENCE` with the snapshot URL
and hash preserved.

## Reference-only (never ground truth)

| Source | Why |
|--------|-----|
| CourtListener / RECAP | Unofficial mirror; pointer to primary documents |
| OpenCorporates and similar aggregators | Use to find primary records, never as evidence |
| Journalism | `PRESS-REPORT`; at most `RESEARCH_INFERENCE` |
