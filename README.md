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

| Flag          | Default          | Meaning                          |
|---------------|------------------|----------------------------------|
| `--out`       | `archive`        | Object-store root directory      |
| `--manifest`  | `manifest.jsonl` | Append-only retrieval ledger     |
| `--delay`     | `2.0`            | Seconds between requests         |
| `--max-bytes` | 100 MB           | Per-object size cap              |

Verify archive integrity (re-hash every stored object against the
manifest):

```sh
python3 verify.py --manifest manifest.jsonl
```

Exits non-zero if any object is missing or its bytes no longer match the
recorded SHA-256.

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

1. Scheduled re-crawls of the seed set producing a change ledger
   (`ADDED | MODIFIED | REMOVED | UNCHANGED` per URL, with previous and
   current SHA-256, first/last seen).
2. Discovery: enumerate FinCEN sitemaps, same-domain public links, the
   Federal Register's FinCEN collection, and a historical URL inventory —
   systematically determining what public FinCEN material exists, rather
   than hand-writing more seeds.
