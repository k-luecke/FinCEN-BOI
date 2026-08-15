# Ownership reconstruction

Reconstructs, **from public records only**, the pieces of the
company → natural-person ownership/control graph that those records
independently disclose.

## What this is not

The beneficial ownership information that companies filed with FinCEN
under the Corporate Transparency Act is confidential by statute
(31 U.S.C. § 5336(c)) and was never publicly accessible. This dataset
does not contain it, does not attempt to obtain it, and cannot recreate
it. What it can do is preserve the *independently public* evidence of
the same underlying relationships — state registry filings, SEC
disclosures, court records, and other sources that lawfully disclose
who controls or owns what — before, during, and after the federal
dataset's deletion.

## Layout

```
ownership-reconstruction/
├── entities/        # legal entities, one JSONL record each
├── people/          # natural persons as named in sources
├── addresses/       # normalized addresses — first-class graph nodes
├── names/           # entity name history (LEGAL/FORMER/DBA/...)
├── edges/           # universal evidence edges (one shape, all sources)
├── sources/         # source catalog and per-source onboarding notes
└── unresolved/      # ambiguous matches awaiting resolution
```

The result is a **temporally versioned, source-addressable
corporate-control graph**: conflicting assertions are all retained
with their dates and sources (a registry saying X manages, an SEC
exhibit saying Y owns 100%, a court filing saying Z controls — three
edges, never collapsed), and analysis happens over preserved evidence
rather than over ingestion-time judgment calls.

Records are JSONL, validated by `ownership_schema.py` at the repo root:

```sh
python3 ownership_schema.py --root ownership-reconstruction
```

## Ground rules

1. **Evidence over inference.** Every relationship carries
   `source_url`, `retrieved_at`, and (whenever the source is archived)
   the `sha256` of the exact bytes, so each edge in the graph is
   traceable to a preserved document.
2. **Assertions are what the source says.** A registered agent is a
   `REGISTERED_AGENT`. An LLC manager is a `MANAGER`. Co-located
   companies get `SHARED_ADDRESS` — which must touch an address node
   and never implies common ownership. `BENEFICIAL_OWNER` is reserved
   for sources that themselves state ownership/control, and the
   validator rejects it at any evidence class other than `DIRECT`.
   Promoting control roles to ownership is how a corporate graph
   becomes confidently wrong — the schema makes it a validation error
   instead.
3. **Public, lawful sources only.** No authentication, no bypassing
   access controls or paywalls, official bulk-data products preferred
   over scraping search interfaces. Sources that prohibit bulk
   collection are cataloged as reference-only.
4. **Ambiguity is recorded, not resolved by guessing.** Same-name
   collisions and uncertain matches go to `unresolved/`, not into the
   graph.

See [SCHEMA.md](SCHEMA.md) for record formats and
[sources/SOURCES.md](sources/SOURCES.md) for the source catalog.
