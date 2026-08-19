#!/usr/bin/env python3
"""Yield report between two graph-build checkpoints.

Answers "graph build N → source acquisition → graph build N+1: which
conclusions changed?" — separating novel-node yield from corroboration
yield, per source family:

  - new entities / people / relationships (grouped by source family)
  - existing relationships newly corroborated (a new source family, or
    more documents from a known family)
  - existing nodes receiving new relationships (independent chain
    extension: DOJ adding B→C to SEC's A→B)
  - previously disconnected components connected
  - contradiction and cross-family deltas (negative results are data)

Usage:
  python3 graph_diff.py OLD_CHECKPOINT.json [NEW_CHECKPOINT.json]

With one argument, the newest checkpoint in
ownership-reconstruction/baselines/ (by as_of) is the "new" side.
"""
from __future__ import annotations

import glob
import json
import os
import sys
from collections import Counter, defaultdict

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "ownership-reconstruction")


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def newest_checkpoint():
    paths = glob.glob(os.path.join(ROOT, "baselines", "checkpoint-*.json"))
    if not paths:
        sys.exit("no checkpoints in ownership-reconstruction/baselines/")
    return max(paths, key=lambda p: load(p).get("as_of", ""))


def components_of(rel_keys):
    """Undirected components over relationship endpoint names."""
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for key in rel_keys:
        s, _, t = key.split("|", 2)
        parent[find(s)] = find(t)
    comps = defaultdict(set)
    for x in parent:
        comps[find(x)].add(x)
    return list(comps.values())


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    old = load(sys.argv[1])
    new_path = sys.argv[2] if len(sys.argv) > 2 else newest_checkpoint()
    new = load(new_path)
    print(f"OLD {old['edges_sha256'][:12]} (as of {old['as_of'][:10]})  ->  "
          f"NEW {new['edges_sha256'][:12]} (as of {new['as_of'][:10]})\n")

    old_rels = {r["key"]: r for r in old["relationships"]}
    new_rels = {r["key"]: r for r in new["relationships"]}
    old_ents, new_ents = set(old["entity_names"]), set(new["entity_names"])
    old_ppl, new_ppl = set(old["person_names"]), set(new["person_names"])
    old_nodes = old_ents | old_ppl

    print("## Counts")
    for k in ("entities", "people", "edges", "relationships", "components"):
        print(f"  {k:14} {old['counts'][k]:6} -> {new['counts'][k]:6} "
              f"({new['counts'][k]-old['counts'][k]:+d})")

    added_rels = [new_rels[k] for k in new_rels.keys() - old_rels.keys()]
    fam_of_new = Counter()
    ext_nodes = set()
    for r in added_rels:
        fam_of_new[",".join(r["families"])] += 1
        s, _, t = r["key"].split("|", 2)
        for n in (s, t):
            if n in old_nodes:
                ext_nodes.add(n)

    print(f"\n## Novel yield")
    print(f"  new entities: {len(new_ents - old_ents)} | "
          f"new people: {len(new_ppl - old_ppl)} | "
          f"new relationships: {len(added_rels)}")
    print("  new relationships by source family:")
    for fams, n in fam_of_new.most_common():
        print(f"    {fams}: {n}")
    print(f"  existing nodes receiving NEW relationships "
          f"(independent chain extension): {len(ext_nodes)}")
    for n in sorted(ext_nodes)[:15]:
        print(f"    - {n}")

    print(f"\n## Corroboration yield")
    new_family = []
    more_docs = []
    for k in new_rels.keys() & old_rels.keys():
        o, n = old_rels[k], new_rels[k]
        gained = set(n["families"]) - set(o["families"])
        if gained:
            new_family.append((k, sorted(gained)))
        elif n["n_docs"] > o["n_docs"]:
            more_docs.append((k, n["n_docs"] - o["n_docs"]))
    print(f"  relationships gaining a NEW source family "
          f"(cross-agency corroboration): {len(new_family)}")
    for k, fams in new_family[:15]:
        print(f"    - {k}  (+{', '.join(fams)})")
    print(f"  relationships gaining more documents from known families: "
          f"{len(more_docs)}")

    old_comps = components_of(old_rels)
    joined = 0
    node_to_old_comp = {}
    for i, comp in enumerate(old_comps):
        for n in comp:
            node_to_old_comp[n] = i
    for comp in components_of(new_rels):
        touched = {node_to_old_comp[n] for n in comp if n in node_to_old_comp}
        if len(touched) > 1:
            joined += len(touched) - 1
    print(f"\n## Structure")
    print(f"  previously disconnected components connected: {joined}")

    print(f"\n## Conclusion deltas (negative results are data)")
    print(f"  cross-family relationships: "
          f"{old['cross_family_relationships']} -> "
          f"{new['cross_family_relationships']}")
    print(f"  cross-family multi-hop chains: {old['cross_family_chains']} "
          f"-> {new['cross_family_chains']}")
    oc = {c['object'] for c in old['competing_control_nodes']}
    nc = {c['object'] for c in new['competing_control_nodes']}
    print(f"  competing-control nodes: {len(oc)} -> {len(nc)}"
          + (f"  NEW: {sorted(nc - oc)}" if nc - oc else "")
          + (f"  RESOLVED: {sorted(oc - nc)}" if oc - nc else ""))


if __name__ == "__main__":
    main()
