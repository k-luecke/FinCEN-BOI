#!/usr/bin/env python3
"""
Re-verify a content-addressed object store against itself.

Object paths encode their own SHA-256 (objects/sha256/<aa>/<rest>), so
a downloaded release tarball can be verified with no manifest at hand:
every object file is re-hashed and compared to its path. Used by the
weekly verify-archive workflow after downloading release assets.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path


def digest(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="archive")
    args = parser.parse_args()

    base = Path(args.root) / "objects" / "sha256"

    if not base.is_dir():
        print(f"ERROR: no object store at {base}", file=sys.stderr)
        return 1

    checked = 0
    failures = 0

    for path in sorted(base.glob("*/*")):
        if not path.is_file():
            continue

        checked += 1
        expected = path.parent.name + path.name
        actual = digest(path)

        if actual != expected:
            failures += 1
            print(
                f"FAIL {path}\n  expected {expected}\n  actual   {actual}"
            )

    print(f"Checked: {checked}")
    print(f"Failures: {failures}")

    if checked == 0:
        print("ERROR: zero objects found — nothing was verified",
              file=sys.stderr)
        return 1

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
