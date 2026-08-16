#!/bin/sh
# Merge this run's manifest records into the LATEST main state and
# push, with bounded retry on push races.
#
# Replaces rebase-based commit steps: two runs appending to
# manifest.jsonl from stale checkouts produce add/add or append/append
# rebase conflicts (this killed the first bulk-crawl aggregate's
# commit). Instead, at commit time we always start from origin/main's
# current state files, re-append this run's records, rebuild derived
# state, and push; on a push race we repeat against the newer main.
set -eu

RUN_MANIFEST="${1:?usage: commit_state.sh <run-manifest.jsonl> <commit-message>}"
MSG="${2:?commit message required}"

git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"

attempt=0
while :; do
  git fetch origin main
  git reset --soft FETCH_HEAD
  # Start every state file from the freshest committed version.
  for f in manifest.jsonl ledger.jsonl queue.jsonl metrics.json; do
    git checkout FETCH_HEAD -- "$f" 2>/dev/null || rm -f "$f"
  done

  cat "$RUN_MANIFEST" >> manifest.jsonl
  python3 ledger.py --manifest manifest.jsonl --out ledger.jsonl
  python3 queue.py --queue-out queue.jsonl --limit 0
  # METRICS_FLAGS may carry --release-verified when the caller has
  # confirmed durable release assets exist.
  python3 metrics.py ${METRICS_FLAGS:-}

  git add manifest.jsonl ledger.jsonl queue.jsonl metrics.json
  if git diff --cached --quiet; then
    echo "No state changes to commit."
    exit 0
  fi
  git commit -m "$MSG"

  if git push origin HEAD:main; then
    echo "State committed."
    exit 0
  fi

  attempt=$((attempt+1))
  if [ "$attempt" -ge 3 ]; then
    echo "Push failed after 3 attempts." >&2
    exit 1
  fi
  echo "Push race detected; retrying against newer main ($attempt/3)."
  sleep $((5 * attempt))
done
