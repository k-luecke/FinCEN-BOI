# Collection report

**As of 2026-08-15T04:15Z.** Regenerate the numbers any time with
`python3 metrics.py` (reads only committed state) — this file records
status at the last operator checkpoint.

## Plain truth first

- **Durably archived so far: 0 URLs, 0 bytes.** No `objects-run-*`
  release exists yet and `manifest.jsonl` is not yet on `main`.
  "Workflows configured" is not "data collected", and this report does
  not conflate them.
- **The first real acquisition run is executing now**: the bulk
  chunked crawl (run 31863450182) over the 38,749-URL discovered
  queue — host-aligned chunks, max 4 parallel, 1s per-host delay.
  Each chunk verifies its objects and uploads them as a workflow
  artifact at chunk completion; the aggregate job then publishes the
  merged object store as a durable release, **verifies the release
  asset exists**, and commits `manifest.jsonl`, `ledger.jsonl`,
  `queue.jsonl`, and `metrics.json`.
- An EDGAR bulk snapshot run (submissions.zip + companyfacts.zip,
  streamed and hashed) is dispatched alongside it — the first P2
  ownership-source bytes.

## What was attempted before this and what happened

| Run | Outcome |
|-----|---------|
| Crawl run 1 (3,497 URLs, artifact-era workflow) | Cancelled deliberately — its final push would have failed (pre-rebase-fix) |
| Crawl run 2 (queued duplicate) | Cancelled deliberately |
| Crawl run 3 (closure, follow-links) | **Failed at 4,332 pages**: unquoted space in a followed link crashed the crawler; fixed (sanitize + resilient fetch, PR #9); its fetched bytes were lost with the runner — precisely the failure mode the durability checks now guard against |
| Crawl run 4 | Cancelled deliberately — redundant with the bulk crawl after the seed list expanded |
| Discovery runs 1–2 | **Succeeded**: 38,758-URL inventory committed |

## Discovery coverage (committed)

38,758 URLs across 11 hosts. Seven hosts truncated at their 5,000-URL
per-host caps (home.treasury.gov, oversight.house.gov, vault.fbi.gov,
www.fdic.gov, www.justice.gov, www.occ.gov, www.sec.gov) — deeper
enumeration continues on the daily discovery schedule. fincen.gov
fully enumerated (2,870 URLs). Federal Register FinCEN collection: 317
documents (HTML + govinfo PDF each). Hosts yielding zero sitemap URLs
are recorded in [HIGH-VALUE-GAPS.md](HIGH-VALUE-GAPS.md).

## Lifecycle now enforced

`FETCHED` (bytes on a runner) → `VERIFIED` (verify.py re-hash passes)
→ `DURABLY_ARCHIVED` (release asset confirmed to exist via API after
upload). Collection workflows fail — visibly — if a run with work
archives zero objects or if the release asset count is zero.
`metrics.json` refuses to count `durably_archived_urls` unless the
release check ran.
