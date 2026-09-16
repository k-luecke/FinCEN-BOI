# Committed retrieval ledger

The append-only crawl ledger is stored here as `part-NNNNN.jsonl`
shards. GitHub rejects any single blob over 100 MB; a monolithic
`manifest.jsonl` at the repo root hit that cap and blocked scheduled
workflow pushes after objects were already verified and released.

Readers still accept `--manifest manifest.jsonl`. `manifest_store.py`
concatenates these parts in order. New retrievals append to the latest
part and open a new one before any shard would exceed 80 MB.

Do not recreate a root `manifest.jsonl`.
