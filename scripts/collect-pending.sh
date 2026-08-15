#!/bin/sh
# Consume up to LIMIT pending queue URLs, verify, and update state.
# Safe to re-run; state derives from append-only logs.
set -eu
cd "$(dirname "$0")/.."
LIMIT="${LIMIT:-2000}"
DELAY="${DELAY:-1.0}"
python3 queue.py --queue-out queue.jsonl --pending-out pending-seeds.txt --limit "$LIMIT"
[ -s pending-seeds.txt ] || { echo "No pending work."; exit 0; }
python3 archive.py --seeds pending-seeds.txt --delay "$DELAY" --out archive --manifest run-manifest.jsonl
python3 verify.py --manifest run-manifest.jsonl
cat run-manifest.jsonl >> manifest.jsonl && rm -f run-manifest.jsonl
python3 ledger.py --manifest manifest.jsonl --out ledger.jsonl
python3 queue.py --queue-out queue.jsonl --limit 0
python3 metrics.py
echo "Done. Objects in ./archive — move to durable storage (release/backup) to complete DURABLY_ARCHIVED."
