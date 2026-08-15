# FinCEN-BOI public-record archive

A deliberately boring, provenance-first archival crawler for **publicly
accessible** FinCEN / Treasury / Federal Register / DOJ / Congressional
records.

What it does:

- Fetches only explicitly seeded URLs on a fixed allowlist of public
  government (and related public-record) hosts.
- Preserves the exact bytes served, content-addressed by SHA-256.
- Appends one retrieval record per fetch to `manifest.jsonl` (URL, final
  URL, timestamp, HTTP status, content type, length, hash, provenance).
- Rate-limits conservatively (default 2 s between requests).

What it deliberately does **not** do:

- No authentication, ever.
- No bypassing of robots or access controls.
- No link discovery or fetching of arbitrary external hosts — redirects
  that escape the allowlist are rejected.
- No mirroring of leaked confidential SAR/BSA documents. Public
  reporting *about* such material is classified separately — see
  [PROVENANCE.md](PROVENANCE.md).

## Usage

Run the crawler over the seed list:

```sh
python3 archive.py --seeds seeds.txt
```

Options:

| Flag             | Default          | Meaning                          |
|------------------|------------------|----------------------------------|
| `--out`          | `archive`        | Object-store root directory      |
| `--manifest`     | `manifest.jsonl` | Append-only retrieval ledger     |
| `--delay`        | `2.0`            | Seconds between requests         |
| `--max-bytes`    | 100 MB           | Per-object size cap              |
| `--follow-links` | off              | Crawl same-allowlist HTML links  |
| `--max-pages`    | `20000`          | Fetch cap when following links   |
| `--max-depth`    | `32`             | Link depth cap from any seed     |

With `--follow-links`, the crawler extracts `<a href>` links from every
fetched HTML page and crawls, breadth-first to closure, any that stay
on the host allowlist. Followed links honor `robots.txt` (explicit
seeds are archival requests and are always fetched); disallowed URLs
get a `robots_disallowed` manifest record instead of a fetch. Each
record carries `parent_url` and `depth`, so the manifest doubles as a
link graph.

Verify archive integrity (re-hash every stored object against the
manifest):

```sh
python3 verify.py --manifest manifest.jsonl
```

Exits non-zero if any object is missing or its bytes no longer match the
recorded SHA-256.

Rebuild the per-URL change ledger from the manifest:

```sh
python3 ledger.py --manifest manifest.jsonl --out ledger.jsonl
```

Each URL that has ever been crawled gets one entry with
`previous_sha256`, `current_sha256`, `first_seen`, `last_seen`, the
latest HTTP status, and a
`change_type` of `ADDED | MODIFIED | REMOVED | UNCHANGED | UNAVAILABLE`.
Because the manifest is append-only, the ledger is a pure function of it
and can always be rebuilt.

## Scheduled crawls

`.github/workflows/archive.yml` re-runs the seed set daily (and on
manual dispatch). Each run:

1. Crawls `seeds.txt` into a fresh per-run manifest and object store.
2. Fails loudly if *every* fetch failed (runner/network problem, not
   evidence that all records vanished), so the ledger isn't poisoned
   with false `REMOVED` entries.
3. Verifies the run's objects against their hashes.
4. Appends the run manifest to the committed `manifest.jsonl` and
   rebuilds `ledger.jsonl`.
5. Publishes the fetched bytes as GitHub Release assets
   (`objects-run-<id>`, no retention expiry; tar paths match
   `object_path` in the manifest) and commits the updated manifest and
   ledger. Bytes stay out of git history.

Manual dispatch accepts `seeds_file`, `delay`, `follow_links`, and
`max_pages` inputs, so a one-off bulk crawl (e.g. of
`discovered-seeds.txt`, following links to closure) runs through the
same pipeline without touching the daily schedule.

If a public record disappears, the repo holds cryptographic evidence
that these exact bytes were served from that government URL at that
timestamp — plus the later observation that the URL changed or vanished.

## Discovery

`discover.py` builds a historical inventory of what public FinCEN
material actually exists, instead of hand-writing more seeds:

```sh
python3 discover.py
```

Two modes, both restricted to the crawler's existing host allowlist:

- **Sitemap enumeration** — reads `robots.txt` for `Sitemap:` entries
  (falling back to `/sitemap.xml`) on every allowlisted host (canonical
  variants; override with `--hosts`), recurses sitemap indexes, and
  collects page URLs. Per-host caps (`--max-sitemaps`,
  `--max-urls-per-host`) keep giant hosts (congress.gov, sec.gov,
  justice.gov) bounded — truncation is logged loudly, and repeated runs
  keep growing the inventory. Congressional hosts get `CONGRESS`
  provenance in candidate seeds; everything else `GOV-PUBLIC`.
- **Federal Register enumeration** — walks the public documents API for
  every Federal Register document published by FinCEN, collecting both
  HTML and govinfo.gov PDF URLs plus document metadata.

Discovery fetches only metadata (robots, sitemap XML, API JSON), never
record content, and produces:

- `url-inventory.jsonl` — one record per URL ever discovered, with
  `first_discovered` / `last_confirmed` timestamps, host, and discovery
  method. URLs are never dropped: a page that vanishes from a sitemap
  keeps its record, its `last_confirmed` just stops advancing — so the
  inventory doubles as a disappearance signal.
- `discovered-seeds.txt` — seed-format candidates not already in
  `seeds.txt`, ready for review. Archiving them stays an explicit step:
  `python3 archive.py --seeds discovered-seeds.txt`.

`.github/workflows/discover.yml` re-runs discovery weekly and commits
the updated inventory and candidate list.

## SAR material

SAR filings themselves are confidential under 31 U.S.C. § 5318(g) and
are never gathered. [SAR-SOURCES.md](SAR-SOURCES.md) catalogs the
split: official public SAR material (statistics, forms, examiner
guidance, oversight reports) is mirrored via `seeds.txt`; non-government
or unofficial sources — including FinCEN Files journalism and leak
mirrors — are referenced by citation only and are outside the crawler's
allowlist.

## Layout

```
archive/
└── objects/
    └── sha256/
        ├── 00/
        ├── 01/
        ...
        └── ff/
manifest.jsonl
seeds.txt
```

Storage is content-addressed: if two URLs serve the same bytes, one
object is stored with two retrieval records. If a URL's content changes,
both versions are preserved under their respective hashes, so the
manifest doubles as a change ledger over time.

The binary object store (`archive/`) is **not** committed to git — a
comprehensive archive grows to many gigabytes. Code, seeds, provenance
vocabulary, and hash manifests are what live in this repository.

## Seed format

One entry per line in `seeds.txt`:

```
URL|PROVENANCE|SOURCE
```

Only the URL is mandatory; provenance defaults to `UNCLASSIFIED`. The
provenance vocabulary is defined in [PROVENANCE.md](PROVENANCE.md).

## Roadmap

1. ~~Scheduled re-crawls of the seed set producing a change ledger.~~
   Done — see `.github/workflows/archive.yml` and `ledger.py`.
2. ~~Discovery: enumerate FinCEN sitemaps, the Federal Register's
   FinCEN collection, and a historical URL inventory.~~ Done — see
   `discover.py` and `.github/workflows/discover.yml`.
3. ~~Offload object stores to durable bulk storage.~~ Done — each crawl
   run publishes its objects as GitHub Release assets.
4. ~~Same-domain link extraction.~~ Done — `--follow-links` crawls
   allowlisted HTML links breadth-first to closure.
5. ~~Extend sitemap discovery to the other allowlisted hosts.~~ Done —
   all canonical allowlisted hosts are enumerated by default.
