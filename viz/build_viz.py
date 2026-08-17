#!/usr/bin/env python3
"""Regenerate viz/ownership-graph.html from the graph tables.

Reads ownership-reconstruction/*/pass2-observations.jsonl and
content-pass-2/raw-observations.jsonl (for the quoted evidence
sentences), injects the data into viz/graph-template.html, and writes
viz/ownership-graph.html — a self-contained interactive page (no
external resources). Deterministic given the input tables.

Usage: python3 viz/build_viz.py
"""
from __future__ import annotations

import collections
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GR = os.path.join(REPO, "ownership-reconstruction")
VIZ = os.path.dirname(os.path.abspath(__file__))
SUFFIX = "pass2-observations"


def load(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def main():
    ents = load(os.path.join(GR, "entities", f"{SUFFIX}.jsonl"))
    ppl = load(os.path.join(GR, "people", f"{SUFFIX}.jsonl"))
    edges = load(os.path.join(GR, "edges", f"{SUFFIX}.jsonl"))
    names = load(os.path.join(GR, "names", f"{SUFFIX}.jsonl"))
    unres = load(os.path.join(GR, "unresolved", f"{SUFFIX}.jsonl"))
    obs = {o["observation_id"]: o for o in
           load(os.path.join(REPO, "content-pass-2", "raw-observations.jsonl"))}

    deg = collections.Counter()
    for e in edges:
        deg[e["subject_id"]] += 1
        deg[e["object_id"]] += 1
    aliases = collections.defaultdict(list)
    for n in names:
        aliases[n["entity_id"]].append({"name": n["name"], "type": n["name_type"]})

    nodes = []
    for r in ents:
        if deg[r["entity_id"]]:
            nodes.append({"id": r["entity_id"], "name": r["legal_name"],
                          "kind": "entity", "deg": deg[r["entity_id"]],
                          "aliases": aliases[r["entity_id"]]})
    for r in ppl:
        if deg[r["person_id"]]:
            nodes.append({"id": r["person_id"], "name": r["normalized_name"],
                          "kind": "person", "deg": deg[r["person_id"]],
                          "aliases": [{"name": v, "type": "AKA"}
                                      for v in (r.get("name_variants") or [])]})

    elist = []
    for e in edges:
        o = obs.get(e["source_id"], {})
        elist.append({"s": e["subject_id"], "t": e["object_id"],
                      "a": e["assertion"], "pct": e.get("ownership_percent"),
                      "posture": e.get("evidentiary_posture"),
                      "conf": e.get("confidence"), "url": e["source_url"],
                      "quote": " ".join((o.get("raw_text") or "").split())[:260]})

    ledger = []
    for r in ents:
        if aliases[r["entity_id"]] and not deg[r["entity_id"]]:
            for a in aliases[r["entity_id"]]:
                ledger.append({"name": r["legal_name"], "alias": a["name"],
                               "type": a["type"]})
    for r in ppl:
        if not deg[r["person_id"]] and r.get("name_variants"):
            for v in r["name_variants"]:
                ledger.append({"name": r["normalized_name"], "alias": v,
                               "type": "AKA"})

    data = {
        "nodes": nodes,
        "edges": elist,
        "ledger": sorted(ledger, key=lambda r: r["name"].lower()),
        "stats": {"entities": len(ents), "people": len(ppl),
                  "edges": len(edges), "names": len(names),
                  "unresolved": len(unres)},
        "unreasons": collections.Counter(
            u["reason"].split(";")[0] for u in unres).most_common(),
    }

    tpl = open(os.path.join(VIZ, "graph-template.html"), encoding="utf-8").read()
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True).replace("</", "<\\/")
    out = os.path.join(VIZ, "ownership-graph.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(tpl.replace("__DATA__", payload))
    print(f"wrote {out}: {len(nodes)} nodes, {len(elist)} edges, "
          f"{len(ledger)} ledger rows")


if __name__ == "__main__":
    main()
