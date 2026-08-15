"""Step 7 — textual near-duplicate detection (bottom-k shingle sketches).

Exact duplicates are already collapsed by SHA-256 content addressing.
This pass finds *textual* near-duplicates across different objects
(same report as HTML and PDF, amended versions, mirrored press releases)
using 5-word shingles, a bottom-64 sketch, LSH banding for candidate
pairs, and union-find grouping at estimated Jaccard >= 0.85.

Nothing is deleted; groups are advisory (near_duplicate_group_id).

Usage: python3 -m content_pass_1.dedup
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from collections import defaultdict

from .common import OUT_ROOT, PASS_VERSION, log, read_jsonl, text_disk_path

SKETCH_K = 64
BANDS = 16          # 16 bands x 4 rows over the sorted sketch
JACCARD_THRESHOLD = 0.85
MIN_CHARS = 500     # tiny pages group trivially; skip them

WORD = re.compile(r"[a-z0-9]{2,}")


def sketch_text(text: str):
    words = WORD.findall(text.lower())
    if len(words) < 20:
        return None
    hashes = set()
    for i in range(len(words) - 4):
        sh = " ".join(words[i:i + 5])
        hashes.add(int.from_bytes(
            hashlib.blake2b(sh.encode(), digest_size=8).digest(), "big"))
    return sorted(hashes)[:SKETCH_K]


class UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        while self.parent.setdefault(x, x) != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def main():
    inv = {r["sha256"]: r for r in
           read_jsonl(os.path.join(OUT_ROOT, "corpus-inventory.jsonl"))}
    sketches = {}
    for sha in inv:
        tp = text_disk_path(sha)
        if not os.path.isfile(tp) or os.path.getsize(tp) < MIN_CHARS:
            continue
        with open(tp, encoding="utf-8") as fh:
            sk = sketch_text(fh.read())
        if sk and len(sk) == SKETCH_K:
            sketches[sha] = sk
    log(f"dedup: {len(sketches)} sketchable documents")

    buckets = defaultdict(list)
    rows = SKETCH_K // BANDS
    for sha, sk in sketches.items():
        for b in range(BANDS):
            key = (b, tuple(sk[b * rows:(b + 1) * rows]))
            buckets[key].append(sha)

    uf = UnionFind()
    checked = set()
    for key, members in buckets.items():
        if len(members) < 2 or len(members) > 200:
            continue
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                a, b = members[i], members[j]
                pair = (a, b) if a < b else (b, a)
                if pair in checked:
                    continue
                checked.add(pair)
                sa, sb = set(sketches[a]), set(sketches[b])
                jac = len(sa & sb) / len(sa | sb)
                if jac >= JACCARD_THRESHOLD:
                    uf.union(a, b)

    groups = defaultdict(list)
    for sha in sketches:
        root = uf.find(sha)
        groups[root].append(sha)

    out = []
    gid = 0
    for root, members in sorted(groups.items()):
        if len(members) < 2:
            continue
        gid += 1
        out.append({
            "near_duplicate_group_id": f"ndg-{gid:05d}",
            "member_count": len(members),
            "members": [{
                "sha256": s,
                "url": inv[s].get("url"),
                "host": inv[s].get("host"),
                "sniffed_mime": inv[s].get("sniffed_mime"),
            } for s in sorted(members)],
            "method": f"bottom-{SKETCH_K} 5-shingle sketch, jaccard>={JACCARD_THRESHOLD}",
            "pass_version": PASS_VERSION,
        })
    path = os.path.join(OUT_ROOT, "near-duplicate-groups.jsonl")
    with open(path, "w", encoding="utf-8") as fh:
        for rec in out:
            fh.write(json.dumps(rec, sort_keys=True, ensure_ascii=False) + "\n")
    log(f"dedup: {gid} near-duplicate groups covering "
        f"{sum(r['member_count'] for r in out)} documents")


if __name__ == "__main__":
    main()
