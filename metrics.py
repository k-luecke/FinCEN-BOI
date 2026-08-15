#!/usr/bin/env python3
"""
Live machine-readable collection metrics -> metrics.json.

Computed from the append-only logs (manifest, inventory, queue,
ledger) plus the ownership-reconstruction dataset. Always safe to
re-run; atomic write.

durably_archived_urls counts archived URLs only when --release-verified
is passed — i.e. the caller has just confirmed the durable release
asset exists. A manifest pointing at bytes that died with a CI runner
is not preservation, and these metrics refuse to pretend otherwise.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

from archive import normalized_host


def iter_jsonl(path: Path):
    if not path.exists():
        return

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def count_jsonl_dir(directory: Path) -> int:
    total = 0

    for path in directory.glob("*.jsonl"):
        with path.open("r", encoding="utf-8") as f:
            total += sum(1 for line in f if line.strip())

    return total


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="manifest.jsonl")
    parser.add_argument("--inventory", default="url-inventory.jsonl")
    parser.add_argument("--queue", default="queue.jsonl")
    parser.add_argument("--ledger", default="ledger.jsonl")
    parser.add_argument("--graph-root", default="ownership-reconstruction")
    parser.add_argument("--recovery-metrics",
                        default="recovery/metrics.json")
    parser.add_argument("--out", default="metrics.json")
    parser.add_argument(
        "--release-verified",
        action="store_true",
        help=(
            "Caller has verified the durable release assets exist for "
            "all archived batches; counts archived URLs as durable"
        ),
    )
    args = parser.parse_args()

    archived_urls: set[str] = set()
    attempted_urls: set[str] = set()
    unique_objects: dict[str, int] = {}
    raw_observations = 0
    by_host: Counter = Counter()
    by_provenance: Counter = Counter()

    for record in iter_jsonl(Path(args.manifest)):
        raw_observations += 1
        url = record.get("url", "")
        attempted_urls.add(url)
        by_host[normalized_host(url)] += 1
        by_provenance[record.get("provenance") or "UNCLASSIFIED"] += 1

        if record.get("sha256"):
            archived_urls.add(url)
            unique_objects.setdefault(
                record["sha256"], record.get("content_length") or 0
            )

    queue_counts: Counter = Counter()

    for row in iter_jsonl(Path(args.queue)):
        queue_counts[row.get("state", "?")] += 1

    ledger_counts: Counter = Counter()

    for row in iter_jsonl(Path(args.ledger)):
        ledger_counts[row.get("change_type", "?")] += 1

    discovered = sum(1 for _ in iter_jsonl(Path(args.inventory)))
    graph = Path(args.graph_root)

    # Challenge-aware coverage: a URL whose latest capture is a bot
    # challenge / interstitial / app shell is NOT archived content.
    recovery_path = Path(args.recovery_metrics)
    recovery: dict = {}

    if recovery_path.exists():
        try:
            recovery_full = json.loads(
                recovery_path.read_text(encoding="utf-8")
            )
            recovery = {
                "challenge_observations": recovery_full.get(
                    "challenge_observations", 0
                ),
                "requested_url_coverage": recovery_full.get(
                    "requested_url_coverage", {}
                ),
                "document_identity_coverage": recovery_full.get(
                    "document_identity_coverage", {}
                ),
                "recovery_links_by_relationship": recovery_full.get(
                    "recovery_links_by_relationship", {}
                ),
                "unresolved": recovery_full.get("unresolved", 0),
            }
        except (json.JSONDecodeError, OSError):
            recovery = {}

    non_content = (
        recovery.get("requested_url_coverage", {}) or {}
    )
    non_content_total = sum(
        count for state, count in non_content.items()
        if state in ("UNRESOLVED_CHALLENGE",
                     "NON_CONTENT_TECHNICAL_RESPONSE")
    )

    metrics = {
        "generated_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
        "discovered_urls": discovered,
        "queued_urls": queue_counts.get("DISCOVERED", 0),
        "attempted_urls": len(attempted_urls),
        "archived_urls": len(archived_urls),
        "archived_content_urls": len(archived_urls) - non_content_total,
        "non_content_technical_responses": non_content_total,
        "archived_note": (
            "archived_urls counts every URL with stored bytes; "
            "archived_content_urls excludes captures the challenge "
            "detector classified as bot challenges/interstitials/app "
            "shells (see recovery/)"
        ),
        "recovery": recovery,
        "durably_archived_urls": (
            len(archived_urls) if args.release_verified else 0
        ),
        "durability_note": (
            "release assets verified this run"
            if args.release_verified
            else "not verified this run — see releases for durable copies"
        ),
        "unique_objects": len(unique_objects),
        "total_bytes": sum(unique_objects.values()),
        "verified_objects": len(unique_objects),
        "verification_note": (
            "objects are hash-verified at capture (verify.py) before "
            "manifests merge; periodic re-verification via "
            "verify-archive workflow"
        ),
        "modified_urls": ledger_counts.get("MODIFIED", 0),
        "not_found_urls": queue_counts.get("NOT_FOUND", 0),
        "temporary_errors": queue_counts.get("TEMPORARY_ERROR", 0),
        "access_restricted": queue_counts.get("ACCESS_RESTRICTED", 0),
        "rate_limited": queue_counts.get("RATE_LIMITED", 0),
        "robots_disallowed": queue_counts.get("ROBOTS_DISALLOWED", 0),
        "manual_review": queue_counts.get("MANUAL_REVIEW", 0),
        "ownership_bearing_documents": 0,
        "raw_observations": raw_observations,
        "validated_graph_edges": count_jsonl_dir(graph / "edges"),
        "unresolved_entities": count_jsonl_dir(graph / "unresolved"),
        "graph_entities": count_jsonl_dir(graph / "entities"),
        "graph_people": count_jsonl_dir(graph / "people"),
        "by_host": dict(by_host.most_common()),
        "by_provenance": dict(by_provenance.most_common()),
        "queue_states": dict(queue_counts),
        "ledger_change_types": dict(ledger_counts),
    }

    out = Path(args.out)
    tmp = out.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, out)

    print(
        f"metrics: {metrics['archived_urls']} archived urls, "
        f"{metrics['unique_objects']} objects, "
        f"{metrics['total_bytes']} bytes, "
        f"durable={metrics['durably_archived_urls']}"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
