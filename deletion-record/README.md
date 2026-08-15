# Deletion record

A dated ledger of evidence about the deletion of previously collected
U.S.-person beneficial ownership information from the federal
database. Primary sources are archived (hashed bytes in the object
store, entries in `manifest.jsonl`); press coverage is referenced, not
mirrored, per [PROVENANCE.md](../PROVENANCE.md).

## Ledger

| Date (UTC) | Event | Primary source | Status |
|------------|-------|----------------|--------|
| 2026-08-11 | FinCEN announces final rule permanently ending BOI reporting for U.S. companies/persons; states it will delete previously reported BOI of individuals it reasonably believes are U.S. persons (e.g. linked to a U.S. passport or driver's license) | FinCEN news release; Treasury press release (both seeded for archival) | Seeded 2026-08-15 |
| 2026-08-14 | Final rule effective | Federal Register final-rule document (via FR enumeration) | Pending capture in next crawl |
| — | Deletion implementation: schedule, method, scope, completion | To be identified as FinCEN publishes | Open |
| — | GAO June 2026 report on BOI collection/sharing and six-agency law-enforcement access | GAO report (gao.gov allowlisted) | To locate and seed |
| — | Congressional responses, oversight letters, litigation | As they appear on seeded congressional/judicial sources | Open |

Press coverage (reference-only, `PRESS-REPORT`): Reuters and trade
press reported the deletion provision in the week of 2026-08-11.

## Maintenance

- Add a row for every deletion-related event, with its primary source
  seeded in `seeds.txt` the same day.
- After each crawl, update Status with the manifest `sha256` of the
  captured document, so every ledger row points at preserved bytes.
- The change ledger (`ledger.jsonl`) is itself part of this record: it
  will show when BOI-related pages are modified or removed
  (`MODIFIED` / `REMOVED` with previous and current hashes).
