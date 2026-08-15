#!/bin/sh
# Re-hash every locally stored object against its content address,
# and check the committed manifest where objects are present.
set -eu
cd "$(dirname "$0")/.."
python3 verify_objects.py --root "${ROOT:-archive}"
