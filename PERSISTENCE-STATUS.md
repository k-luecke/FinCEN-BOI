# Persistence status

**As of 2026-08-15T04:15Z.** Plain answers, no aspiration.

**1. What is collecting right now?**
The bulk chunked crawl (Actions run 31863450182): the 38,749-URL
discovered queue in host-aligned chunks, max 4 parallel, 1s per-host
delay. An EDGAR bulk snapshot run (submissions.zip + companyfacts.zip)
is dispatched alongside it. The interactive session's own sandbox
cannot reach the target hosts (egress-restricted); all fetching
happens on Actions runners.

**2. How many URLs have actually been archived?**
Durably: **zero, so far.** Earlier runs were cancelled or crashed
before their durability steps (see COLLECTION-REPORT.md). The bulk
crawl's chunks upload verified objects as workflow artifacts as each
chunk completes, and the aggregate publishes the durable release.
Check the live number with: `python3 metrics.py && cat metrics.json`
after pulling main.

**3. How many bytes have actually been preserved?**
Durably, zero (see above). This file must be re-checked after the bulk
run completes — `metrics.json` on main will carry the verified totals.

**4. Where are those bytes durably stored?**
GitHub Release assets on this repository, tagged `objects-run-<id>`
(zstd tarballs, split under the 2 GB asset limit; tar paths match
`manifest.jsonl` `object_path` values). Interim: per-chunk workflow
artifacts (90-day retention) as recovery copies.

**5. When will discovery run next?**
Daily at 07:41 UTC (`discover.yml`), plus on manual dispatch.

**6. When will collection run next?**
Three standing schedules: `archive.yml` daily 06:17 UTC (recheck of
the curated high-value seed list — change detection on BOI pages);
`collect-pending.yml` daily 10:47 UTC (up to 4,000 pending/retry queue
URLs); `edgar-snapshot.yml` weekly Tuesday 08:29 UTC. Verification
audit: `verify-archive.yml` weekly Wednesday 11:11 UTC.

**7. What happens if a workflow times out?**
Nothing on `main` is corrupted: state commits happen only after
verification, and queue state derives from append-only logs. Work
completed by finished chunks survives as artifacts; unfinished URLs
simply remain pending, and the next `collect-pending` run recomputes
and consumes them. Chunk jobs carry a 350-minute timeout below the 6h
kill line.

**8. What happens to 429/5xx/network failures?**
In-run: bounded retries (3) with exponential backoff + jitter,
honoring Retry-After on 429. Across runs: recorded in the manifest,
classified by `queue.py` as RATE_LIMITED / TEMPORARY_ERROR, and
re-emitted as pending (after new URLs) until a URL has been attempted
5 times, after which it stays recorded as a gap. 404/410 and 401/403
are observations, never retried, never evaded.

**9. Which important sources remain inaccessible?**
See HIGH-VALUE-GAPS.md: PACER (paywalled), hosts without sitemaps
(congress.gov, gao.gov, FFIEC, NCUA, Federal Reserve — listing pages
seeded, APIs/connectors pending), state registries not yet onboarded,
and — permanently, by law — the CTA-filed BOI database and SAR/BSA
records.

**10. How do I verify tomorrow morning that collection continued
overnight?**
```sh
git pull
tail -3 collection-state/*.json 2>/dev/null; cat metrics.json
git log --oneline -10        # look for bot commits: crawl/discovery/queue
```
Then check Actions → recent runs are green, and Releases →
`objects-run-*` entries exist with assets. Green runs with zero new
objects fail by design, so green means bytes landed.

**11. What exact command resumes collection manually?**
Via Actions (works from anywhere):
`gh workflow run collect-pending.yml` (optionally
`-f limit=4000 -f delay=1.0`). On a local clone with network access:
`./scripts/collect-pending.sh`.

**12. What exact command verifies the archive?**
Latest durable release: `gh workflow run verify-archive.yml` (or watch
its Wednesday run). Locally against a downloaded/extracted release or
local store: `./scripts/verify-archive.sh` (re-hashes every object
against its content address); manifest-based:
`python3 verify.py --manifest manifest.jsonl`.
