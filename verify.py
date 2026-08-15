#!/usr/bin/env python3

import argparse
import hashlib
import json
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
    parser.add_argument("--manifest", default="manifest.jsonl")
    args = parser.parse_args()

    failures = 0
    checked = 0

    with open(args.manifest, "r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, 1):
            record = json.loads(line)

            expected = record.get("sha256")
            object_path = record.get("object_path")

            # Failed retrieval records contain no object.
            if not expected or not object_path:
                continue

            checked += 1
            path = Path(object_path)

            if not path.exists():
                failures += 1
                print(
                    f"FAIL line {line_number}: "
                    f"missing {object_path}"
                )
                continue

            actual = digest(path)

            if actual != expected:
                failures += 1
                print(
                    f"FAIL line {line_number}: "
                    f"{object_path}\n"
                    f"  expected {expected}\n"
                    f"  actual   {actual}"
                )

    print(f"\nChecked: {checked}")
    print(f"Failures: {failures}")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
