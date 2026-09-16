#!/usr/bin/env python3
"""Tests for size-capped manifest shards."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import manifest_store


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


class ManifestStoreTest(unittest.TestCase):
    def test_resolve_single_run_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "run-manifest.jsonl"
            write_jsonl(path, [{"url": "https://example.gov/a"}])
            self.assertEqual(manifest_store.resolve_files(path), [path])
            records = list(manifest_store.iter_jsonl_records(path))
            self.assertEqual(records[0]["url"], "https://example.gov/a")

    def test_shards_win_over_monolith(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            monolith = root / "manifest.jsonl"
            write_jsonl(monolith, [{"url": "https://example.gov/old"}])
            shard_dir = root / "manifest"
            shard_dir.mkdir()
            write_jsonl(
                shard_dir / "part-00001.jsonl",
                [{"url": "https://example.gov/one"}],
            )
            write_jsonl(
                shard_dir / "part-00002.jsonl",
                [{"url": "https://example.gov/two"}],
            )
            urls = [
                row["url"]
                for row in manifest_store.iter_jsonl_records(monolith)
            ]
            self.assertEqual(
                urls,
                ["https://example.gov/one", "https://example.gov/two"],
            )

    def test_append_rotates_at_max_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dest = root / "manifest.jsonl"
            run1 = root / "run-1.jsonl"
            run2 = root / "run-2.jsonl"
            write_jsonl(run1, [{"url": "https://example.gov/1", "n": 1}])
            write_jsonl(run2, [{"url": "https://example.gov/2", "n": 2}])
            manifest_store.append(run1, dest=dest, max_bytes=50)
            manifest_store.append(run2, dest=dest, max_bytes=50)
            shards = sorted((root / "manifest").glob("part-*.jsonl"))
            self.assertGreaterEqual(len(shards), 2)
            self.assertFalse(dest.exists())
            urls = [
                row["url"] for row in manifest_store.iter_jsonl_records(dest)
            ]
            self.assertEqual(
                urls,
                ["https://example.gov/1", "https://example.gov/2"],
            )
            for shard in shards:
                self.assertLess(shard.stat().st_size, 100 * 1024 * 1024)

    def test_split_oversized_monolith(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dest = root / "manifest.jsonl"
            rows = [
                {"url": f"https://example.gov/{i}", "pad": "x" * 50}
                for i in range(40)
            ]
            write_jsonl(dest, rows)
            self.assertGreater(dest.stat().st_size, 80)
            manifest_store.ensure_shards(dest, max_bytes=400)
            self.assertFalse(dest.exists())
            shards = sorted((root / "manifest").glob("part-*.jsonl"))
            self.assertGreaterEqual(len(shards), 2)
            recovered = list(manifest_store.iter_jsonl_records(dest))
            self.assertEqual(len(recovered), 40)
            self.assertEqual(recovered[0]["url"], rows[0]["url"])
            self.assertEqual(recovered[-1]["url"], rows[-1]["url"])

    def test_guard_catches_monolith(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "manifest.jsonl"
            path.write_bytes(b"x" * 1000)
            self.assertEqual(manifest_store.guard(root, limit=500), 1)
            self.assertEqual(manifest_store.guard(root, limit=5000), 0)


if __name__ == "__main__":
    unittest.main()
