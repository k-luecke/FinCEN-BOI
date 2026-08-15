# Policy history

Preserves the public record establishing what the federal beneficial
ownership dataset **was** — because proving the dataset existed, what
it contained, and how it ended is nearly as important as reconstructing
its contents.

## The evidence chain

Each link below is an archival target: primary government sources are
crawled into the archive (hashed, manifested); non-government coverage
is referenced per [PROVENANCE.md](../PROVENANCE.md).

1. **Statutory basis / what was collected** — Corporate Transparency
   Act, 31 U.S.C. § 5336: reporting companies, beneficial owners,
   company applicants; confidentiality of reported BOI
   (§ 5336(c)); retention direction that FinCEN maintain reported
   information for **not fewer than five years** after a reporting
   company terminates.
2. **Who was required to file / fields collected** — the September
   2022 BOI Reporting Rule; FinCEN's BOI FAQs and Small Entity
   Compliance Guide (seeded since the first crawl); the BOI report
   form and instructions.
3. **Access framework** — the December 2023 BOI Access Rule and
   agency access agreements.
4. **Scale and use** — FinCEN statistics and testimony on filing
   volumes; GAO's June 2026 report documenting that FinCEN had
   collected and shared BOI and given six law-enforcement agencies
   access (locate, verify, archive).
5. **Contraction** — the March 2025 interim final rule limiting
   reporting to foreign reporting companies.
6. **Termination and deletion** — the **August 11, 2026 final rule**
   (effective **August 14, 2026**) permanently exempting U.S.
   companies and U.S. persons, under which FinCEN states it will
   **delete previously reported BOI of persons it reasonably believes
   are U.S. persons** from the database, while foreign reporting
   companies continue reporting for foreign individuals. Primary
   sources: FinCEN news release, Treasury press release (both now
   seeded), and the Federal Register final-rule text (captured by the
   Federal Register enumeration in discovery).
7. **Responses** — Congressional letters, hearings, oversight
   requests, and any litigation over the deletion (archive court
   records via public official sources as they appear).

The apparent tension between the statutory five-year retention
direction and the announced deletion of previously collected
U.S.-person BOI is **documented, not adjudicated, here**: this
directory's job is to preserve the rulemaking record, the statutory
text, the deletion provisions and their legal theory, implementation
dates, and responses — so the question can be examined later against
complete primary evidence, whatever the answer turns out to be.

## Related but separate regime

FinCEN's **Residential Real Estate** reporting regime (beneficial
owners of transferee entities/trusts in covered transfers;
certifications retained five years by reporting persons) is a distinct
regime from CTA/BOSS. Its guidance and rulemaking record are preserved
as their own thread here and must not be conflated with the CTA
dataset's history.

## Mechanics

Government sources for every link above live in `seeds.txt` (the
policy-history section) and flow through the normal crawl → hash →
manifest pipeline; the daily scheduled crawl picks up new seeds
automatically. The change ledger then tracks these pages over time —
if guidance quietly changes or vanishes, the ledger records it.
