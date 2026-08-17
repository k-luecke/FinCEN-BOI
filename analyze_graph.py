#!/usr/bin/env python3
"""Network-level queries over the ownership-reconstruction graph.

Three analyses, all deterministic, all preserving falsifiability back to
source evidence (every reported claim carries its edge's posture and
source document):

1. Multi-hop ownership/control chains — directed paths through
   BENEFICIAL_OWNER / PARENT / UNKNOWN_CONTROL_ROLE edges, each hop
   annotated with assertion, posture, and source.
2. Controller centrality weighted by evidentiary posture — findings and
   designations outweigh allegations; weights are analysis-time
   parameters (documented below), never stored in the graph.
3. Competing-control detection — nodes over which distinct sources
   assert different owners/controllers. Same-observation co-owners
   (split name lists) are concurrent, not competing; assertions from
   distinct documents are surfaced with dates and postures so temporal
   succession vs. genuine contradiction is a reviewer's call over cited
   evidence.

Writes ownership-reconstruction/ANALYSIS.md.

Usage: python3 analyze_graph.py
"""
from __future__ import annotations

import json
import os
from collections import defaultdict

REPO = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(REPO, "ownership-reconstruction")
SUFFIX = "pass2-observations"

# Posture weights — analysis-time only (SCHEMA: weighting is an
# analysis-time act over preserved evidence). A finding or designation is
# the issuing agency's own conclusion; allegations are claims in filings.
POSTURE_WEIGHT = {
    "ADJUDICATED_FACT": 1.0,
    "GOVERNMENT_FINDING": 1.0,
    "ADMINISTRATIVE_DESIGNATION": 1.0,
    "SELF_REPORTED": 0.9,
    "GOVERNMENT_ALLEGATION": 0.6,
    "COURT_ALLEGATION": 0.6,
    "CONGRESSIONAL_ASSERTION": 0.5,
    "THIRD_PARTY_ASSERTION": 0.4,
    "OTHER_DIRECT_ASSERTION": 0.4,
}
CONTROL_ASSERTIONS = {"BENEFICIAL_OWNER", "PARENT", "UNKNOWN_CONTROL_ROLE"}


def load(sub, fname=None):
    path = os.path.join(ROOT, sub, fname or f"{SUFFIX}.jsonl")
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def main():
    ents = {r["entity_id"]: r for r in load("entities")}
    ppl = {r["person_id"]: r for r in load("people")}
    edges = [e for e in load("edges") if e["assertion"] in CONTROL_ASSERTIONS]

    def name(nid):
        r = ents.get(nid) or ppl.get(nid) or {}
        return r.get("legal_name") or r.get("normalized_name") or nid

    out = defaultdict(list)
    for e in edges:
        out[e["subject_id"]].append(e)

    def ew(e):
        return POSTURE_WEIGHT.get(e.get("evidentiary_posture"), 0.4) * (
            e.get("confidence") or 0.5)

    # Parallel evidence edges (same pair asserted in many filings) collapse
    # to one hop carrying its evidence count and the best-posture edge.
    pair_edges = defaultdict(list)
    for e in edges:
        pair_edges[(e["subject_id"], e["object_id"])].append(e)
    uniq_out = defaultdict(list)
    for (s, t), es in pair_edges.items():
        best = max(es, key=ew)
        uniq_out[s].append({"t": t, "best": best, "n_sources": len(
            {e.get("source_sha256") for e in es})})

    # ---- 1. multi-hop chains (distinct node paths) --------------------
    chains = []

    def dfs(nid, hops, seen):
        extended = False
        for h in sorted(uniq_out.get(nid, []), key=lambda h: h["t"]):
            if h["t"] in seen:
                continue
            dfs(h["t"], hops + [h], seen | {h["t"]})
            extended = True
        if not extended and len(hops) >= 2:
            chains.append(hops)

    roots = set(uniq_out) - {e["object_id"] for e in edges}
    for r in sorted(roots):
        dfs(r, [], {r})

    def chain_weight(ch):
        w = 1.0
        for h in ch:
            w *= ew(h["best"])
        return w

    chains.sort(key=lambda ch: (-len(ch), -chain_weight(ch)))

    # ---- 2. posture-weighted controller centrality --------------------
    def descendants(nid):
        seen, stack = set(), [nid]
        while stack:
            for h in uniq_out.get(stack.pop(), []):
                if h["t"] not in seen:
                    seen.add(h["t"])
                    stack.append(h["t"])
        return seen

    central = []
    for nid, hs in uniq_out.items():
        w = sum(ew(h["best"]) for h in hs)
        central.append({"id": nid, "name": name(nid),
                        "held": len(hs),
                        "evidence": sum(h["n_sources"] for h in hs),
                        "weighted": round(w, 2),
                        "reach": len(descendants(nid))})
    central.sort(key=lambda r: (-r["weighted"], -r["reach"], r["id"]))

    # ---- 3. competing-control detection -------------------------------
    competing = []
    by_object = defaultdict(list)
    for e in edges:
        if e["assertion"] in ("BENEFICIAL_OWNER", "UNKNOWN_CONTROL_ROLE"):
            by_object[e["object_id"]].append(e)
    for obj, es in sorted(by_object.items()):
        subjects = {e["subject_id"] for e in es}
        docs = {e.get("source_sha256") for e in es}
        if len(subjects) < 2:
            continue
        # co-owners asserted by one document are concurrent, not competing
        if len(docs) < 2:
            continue
        claims, seen_claims = [], set()
        for e in es:
            key = (e["subject_id"], e.get("source_sha256"))
            if key in seen_claims:
                continue
            seen_claims.add(key)
            claims.append({"subject": e["subject_id"],
                           "assertion": e["assertion"],
                           "pct": e.get("ownership_percent"),
                           "posture": e.get("evidentiary_posture"),
                           "date": e.get("source_date"),
                           "source_sha256": (e.get("source_sha256") or "")[:16],
                           "source_url": e.get("source_url")})
        claims.sort(key=lambda c: (c["date"] or "", c["subject"]))
        competing.append({"object": obj, "claims": claims})
    competing.sort(key=lambda r: -len(r["claims"]))

    # ---- report --------------------------------------------------------
    L = []
    L.append("# Graph analyses (pass2-observations)\n")
    L.append("Regenerate with `python3 analyze_graph.py`. Posture weights "
             "are analysis-time parameters (see script header); the graph "
             "itself stores evidence, not judgments.\n")
    dated = [e for e in edges if e.get("source_date")]
    vf = [e for e in edges if e.get("valid_from")]
    if dated:
        span = sorted(e["source_date"] for e in dated)
        L.append(f"\nTemporal coverage: {len(dated)}/{len(edges)} edges "
                 f"carry a document date ({span[0]} … {span[-1]}); "
                 f"{len(vf)} additionally carry a sentence-stated event "
                 f"date in `valid_from`.\n")

    L.append(f"\n## 1. Multi-hop ownership/control chains "
             f"({len(chains)} maximal distinct node paths of length ≥ 2)\n")
    for ch in chains[:20]:
        hops = [name(ch[0]["best"]["subject_id"])]
        for h in ch:
            e = h["best"]
            pct = f" {e['ownership_percent']}%" if e.get("ownership_percent") else ""
            multi = f"×{h['n_sources']}" if h["n_sources"] > 1 else ""
            hops.append(f"—[{e['assertion']}{pct}·{e.get('evidentiary_posture','?')[:14]}{multi}]→ "
                        f"{name(e['object_id'])}")
        L.append("- " + " ".join(hops))
        srcs = " · ".join(sorted({(h["best"].get('source_sha256') or '')[:12] for h in ch}))
        L.append(f"  <br>sources: `{srcs}`")

    L.append("\n## 2. Controller centrality (posture-weighted)\n")
    L.append("`held` = distinct owned/controlled parties; `evidence` = "
             "distinct supporting documents across those relationships.\n")
    L.append("| Controller | Held | Evidence docs | Weighted score | Reach |")
    L.append("|---|---|---|---|---|")
    for r in central[:20]:
        L.append(f"| {r['name']} | {r['held']} | {r['evidence']} | "
                 f"{r['weighted']} | {r['reach']} |")

    L.append(f"\n## 3. Competing control assertions across documents "
             f"({len(competing)} nodes)\n")
    L.append("Distinct sources assert different owners/controllers for the "
             "same node. Succession vs. contradiction is a review call — "
             "every claim below cites its document.\n")
    for r in competing[:20]:
        L.append(f"\n**{name(r['object'])}**")
        for c in r["claims"]:
            pct = f" ({c['pct']}%)" if c.get("pct") else ""
            dt = f", {c['date']}" if c.get("date") else ""
            L.append(f"- {name(c['subject'])}{pct} — {c['assertion']}, "
                     f"{c['posture']}{dt} · `{c['source_sha256']}`")

    with open(os.path.join(ROOT, "ANALYSIS.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print(f"chains>=2: {len(chains)} | centrality rows: {len(central)} | "
          f"competing-control nodes: {len(competing)}")
    print("wrote ownership-reconstruction/ANALYSIS.md")


if __name__ == "__main__":
    main()
