#!/usr/bin/env python3
"""
Partition a seed list into host-aligned chunks for parallel crawling.

Chunking rule: a host's URLs are never split across chunks, so chunks
crawled in parallel never hit the same site — each chunk's rate limit
stays a true per-host rate limit. Hosts are bin-packed greedily
(largest first) into chunks of roughly --target URLs; a single host
larger than the target gets a chunk of its own.

Outputs one seed file per chunk (chunk-00.txt, chunk-01.txt, ...) into
--out-dir, and prints a GitHub Actions matrix JSON ({"chunk": [...]})
with --print-matrix.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path

from archive import normalized_host, parse_seed


def load_seed_lines(path: Path) -> "OrderedDict[str, list[str]]":
    """Seed lines grouped by host, in first-seen host order."""

    by_host: "OrderedDict[str, list[str]]" = OrderedDict()

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()

        if not line or line.startswith("#"):
            continue

        url, _provenance, _source = parse_seed(line)
        host = normalized_host(url)

        by_host.setdefault(host, []).append(line)

    return by_host


def pack_chunks(
    by_host: "OrderedDict[str, list[str]]",
    target: int,
) -> list[list[str]]:
    """Greedy first-fit-decreasing bin packing, hosts kept whole."""

    hosts = sorted(by_host.items(), key=lambda kv: len(kv[1]), reverse=True)

    chunks: list[list[str]] = []
    sizes: list[int] = []

    for _host, lines in hosts:
        placed = False

        for i, size in enumerate(sizes):
            if size + len(lines) <= target:
                chunks[i].extend(lines)
                sizes[i] += len(lines)
                placed = True
                break

        if not placed:
            chunks.append(list(lines))
            sizes.append(len(lines))

    return chunks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", default="discovered-seeds.txt")
    parser.add_argument("--out-dir", default="chunks")
    parser.add_argument(
        "--target",
        type=int,
        default=4000,
        help="Approximate URLs per chunk (hosts are never split)",
    )
    parser.add_argument(
        "--print-matrix",
        action="store_true",
        help='Print {"chunk": [...]} JSON for a GitHub Actions matrix',
    )
    args = parser.parse_args()

    by_host = load_seed_lines(Path(args.seeds))
    total = sum(len(lines) for lines in by_host.values())

    if not total:
        print("ERROR: no seeds to chunk", file=sys.stderr)
        return 1

    chunks = pack_chunks(by_host, args.target)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    names = []

    for index, lines in enumerate(chunks):
        name = f"chunk-{index:02d}"
        names.append(name)
        (out_dir / f"{name}.txt").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )
        print(
            f"{name}: {len(lines)} URLs",
            file=sys.stderr,
        )

    print(
        f"{total} seeds across {len(by_host)} hosts -> "
        f"{len(chunks)} chunks",
        file=sys.stderr,
    )

    if args.print_matrix:
        print(json.dumps({"chunk": names}))

    return 0


if __name__ == "__main__":
    sys.exit(main())
