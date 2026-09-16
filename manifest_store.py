#!/usr/bin/env python3
"""Size-capped shards for the append-only retrieval ledger.

GitHub rejects any blob over 100 MB. The committed ledger outgrew that
limit (manifest.jsonl sat 3 bytes under the cap), so scheduled crawls
could fetch and verify objects, then fail at `git push` while appending
one more line.

The ledger now lives under manifest/part-NNNNN.jsonl. Readers that still
pass --manifest manifest.jsonl transparently concatenate those shards.
A single run-manifest.jsonl file is unchanged: it is not the committed
ledger and stays a regular file.

This module is dependency-free so commit_state.sh and recovery.yml can
call it before ledger/queue/metrics rebuilds.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

GITHUB_MAX_FILE_BYTES = 100 * 1024 * 1024
# Leave headroom for one day's crawl plus a push-race retry append.
SHARD_MAX_BYTES = 80 * 1024 * 1024
GUARD_BYTES = 90 * 1024 * 1024
SHARD_DIRNAME = "manifest"
SHARD_GLOB = "part-*.jsonl"
DEFAULT_LEDGER = Path("manifest.jsonl")


def shard_dir_for(path: Path) -> Path | None:
    """Directory of part-*.jsonl shards for a committed-ledger path."""

    path = Path(path)
    if path.is_dir():
        return path
    if path.name == DEFAULT_LEDGER.name:
        return path.parent / SHARD_DIRNAME
    return None


def resolve_files(path: Path | str) -> list[Path]:
    """Ordered JSONL files that constitute this manifest.

    Shards win when present so a leftover monolith is ignored after
    migration. A path that is not the committed ledger (run-manifest
    files, tests) is always the file itself.
    """

    path = Path(path)
    directory = shard_dir_for(path)
    if directory is not None and directory.is_dir():
        shards = sorted(directory.glob(SHARD_GLOB))
        if shards:
            return shards
    if path.is_file():
        return [path]
    return []


def iter_jsonl_records(path: Path | str):
    """Yield parsed records from a run file or the sharded committed ledger."""

    files = resolve_files(path)
    if not files:
        return

    line_number = 0
    for file in files:
        with file.open("r", encoding="utf-8") as handle:
            for raw in handle:
                line_number += 1
                line = raw.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as exc:
                    print(
                        f"WARN: skipping malformed manifest line "
                        f"{line_number} in {file}: {exc}",
                        file=sys.stderr,
                    )


def iter_jsonl_lines(path: Path | str):
    """Yield raw (stripped) non-empty lines, in shard order."""

    for file in resolve_files(path):
        with file.open("r", encoding="utf-8") as handle:
            for raw in handle:
                line = raw.strip()
                if line:
                    yield line


def _next_shard_path(directory: Path) -> Path:
    existing = sorted(directory.glob(SHARD_GLOB))
    if not existing:
        return directory / "part-00001.jsonl"
    latest = existing[-1]
    number = int(latest.stem.split("-")[1])
    return directory / f"part-{number + 1:05d}.jsonl"


def split_file(
    src: Path,
    dest_dir: Path,
    max_bytes: int = SHARD_MAX_BYTES,
) -> list[Path]:
    """Split a JSONL file on line boundaries into size-capped shards."""

    dest_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    current_handle = None
    current_size = 0

    def roll() -> None:
        nonlocal current_handle, current_size
        if current_handle is not None:
            current_handle.close()
        path = dest_dir / f"part-{len(written) + 1:05d}.jsonl"
        current_handle = path.open("w", encoding="utf-8")
        written.append(path)
        current_size = 0

    roll()
    with src.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw if raw.endswith("\n") else raw + "\n"
            nbytes = len(line.encode("utf-8"))
            if current_size and current_size + nbytes > max_bytes:
                roll()
            assert current_handle is not None
            current_handle.write(line)
            current_size += nbytes
    if current_handle is not None:
        current_handle.close()
    return written


def ensure_shards(
    dest: Path = DEFAULT_LEDGER,
    max_bytes: int = SHARD_MAX_BYTES,
) -> Path:
    """Make sure the committed ledger is a shard directory.

    If the historical monolith still exists and is over max_bytes, split
    it and remove the monolith so git no longer tracks a 100 MB blob.
    """

    dest = Path(dest)
    directory = shard_dir_for(dest)
    if directory is None:
        raise ValueError(f"{dest} is not a committed-ledger path")
    directory.mkdir(parents=True, exist_ok=True)
    shards = sorted(directory.glob(SHARD_GLOB))
    if shards:
        return directory
    if dest.is_file():
        if dest.stat().st_size > max_bytes:
            split_file(dest, directory, max_bytes=max_bytes)
            dest.unlink()
        else:
            target = directory / "part-00001.jsonl"
            target.write_bytes(dest.read_bytes())
            dest.unlink()
    elif not shards:
        (directory / "part-00001.jsonl").touch()
    return directory


def append(
    run_manifest: Path | str,
    dest: Path | str = DEFAULT_LEDGER,
    max_bytes: int = SHARD_MAX_BYTES,
) -> Path:
    """Append a run's JSONL records onto the latest shard, rotating if needed."""

    run_manifest = Path(run_manifest)
    dest = Path(dest)
    incoming = run_manifest.read_bytes()
    if incoming and not incoming.endswith(b"\n"):
        incoming += b"\n"
    if len(incoming) >= GITHUB_MAX_FILE_BYTES:
        raise SystemExit(
            f"{run_manifest} is {len(incoming)} bytes; a single shard "
            f"cannot exceed GitHub's {GITHUB_MAX_FILE_BYTES} byte limit"
        )

    directory = ensure_shards(dest, max_bytes=max_bytes)
    shards = sorted(directory.glob(SHARD_GLOB))
    current = shards[-1] if shards else directory / "part-00001.jsonl"
    current_size = current.stat().st_size if current.exists() else 0
    if current_size and current_size + len(incoming) > max_bytes:
        current = _next_shard_path(directory)
        current_size = 0
    with current.open("ab") as handle:
        handle.write(incoming)
    if current.stat().st_size >= GITHUB_MAX_FILE_BYTES:
        raise SystemExit(
            f"{current} is {current.stat().st_size} bytes, over GitHub's "
            f"{GITHUB_MAX_FILE_BYTES} byte limit"
        )
    print(
        f"Appended {run_manifest} -> {current} "
        f"({current.stat().st_size} bytes)"
    )
    return current


def oversized_paths(
    root: Path = Path("."),
    limit: int = GUARD_BYTES,
) -> list[tuple[Path, int]]:
    """Tracked-looking JSONL files that would fail a GitHub push."""

    hits: list[tuple[Path, int]] = []
    candidates = [root / DEFAULT_LEDGER]
    directory = root / SHARD_DIRNAME
    if directory.is_dir():
        candidates.extend(sorted(directory.glob(SHARD_GLOB)))
    for extra in ("ledger.jsonl", "queue.jsonl", "url-inventory.jsonl"):
        candidates.append(root / extra)
    seen: set[Path] = set()
    for path in candidates:
        path = path.resolve()
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        size = path.stat().st_size
        if size >= limit:
            hits.append((path, size))
    return hits


def guard(root: Path = Path("."), limit: int = GUARD_BYTES) -> int:
    hits = oversized_paths(root, limit=limit)
    if not hits:
        print(f"Size guard passed (limit {limit} bytes).")
        return 0
    for path, size in hits:
        print(f"OVERSIZE {size} bytes: {path}", file=sys.stderr)
    print(
        "GitHub will reject files at 100 MB. Rotate shards or compact "
        "derived JSONL before committing.",
        file=sys.stderr,
    )
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    split_p = sub.add_parser("split", help="split a monolith into shards")
    split_p.add_argument("src", nargs="?", default=str(DEFAULT_LEDGER))
    split_p.add_argument("--max-bytes", type=int, default=SHARD_MAX_BYTES)

    append_p = sub.add_parser("append", help="append a run manifest")
    append_p.add_argument("run_manifest")
    append_p.add_argument("--dest", default=str(DEFAULT_LEDGER))
    append_p.add_argument("--max-bytes", type=int, default=SHARD_MAX_BYTES)

    files_p = sub.add_parser("files", help="print resolved shard paths")
    files_p.add_argument("path", nargs="?", default=str(DEFAULT_LEDGER))

    guard_p = sub.add_parser("guard", help="fail if JSONL files approach 100 MB")
    guard_p.add_argument("--root", default=".")
    guard_p.add_argument("--limit", type=int, default=GUARD_BYTES)

    args = parser.parse_args(argv)

    if args.cmd == "split":
        src = Path(args.src)
        directory = ensure_shards(src, max_bytes=args.max_bytes)
        for path in sorted(directory.glob(SHARD_GLOB)):
            print(f"{path} {path.stat().st_size}")
        return 0
    if args.cmd == "append":
        append(args.run_manifest, dest=args.dest, max_bytes=args.max_bytes)
        return 0
    if args.cmd == "files":
        for path in resolve_files(args.path):
            print(path)
        return 0
    if args.cmd == "guard":
        return guard(Path(args.root), limit=args.limit)
    return 1


if __name__ == "__main__":
    sys.exit(main())
