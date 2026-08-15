#!/bin/sh
# Enumerate sitemaps + Federal Register; update inventory and candidates.
set -eu
cd "$(dirname "$0")/.."
python3 discover.py
