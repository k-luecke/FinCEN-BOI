# Data lineage note (merge of main, 2026-08-17)

Parallel sessions evolved the Pass 2 tooling on `main` while this branch
was open. The merge resolved add/add conflicts by keeping `main`'s newer
full-corpus versions of: `content_pass_2/observe.py` (their parser line,
labeled observe/1.1.0, independently fixes the same capture-defect
classes this branch fixed in v1.3–1.4 and adds ALL-CAPS caption names,
OOO/OAO prefix entities, name-lists, and clause-connective stops),
`content_pass_2/recovery_queues.py` (adds citation-edge evidence),
`raw-observations.jsonl` + `observe-stats.json` (regenerated 2026-08-18
over the grown corpus), the regenerated `acquisition/` queues, and the
disk-managed multi-release `content-pass-1.yml`.

Downstream artifacts in this directory that were NOT conflicted —
`normalized-assertions.jsonl`, `validated-edges.jsonl`,
`validation-sample.jsonl`, `financial-flow-observations.jsonl`,
`metrics.json`, `PASS-2-REPORT.md` — still derive from THIS branch's
observe/1.4.0 run over the 2026-08-15 corpus (its raw observations are
preserved in git history at commit `62d157b`). Re-deriving them from the
full-corpus raw observations is the natural next step after merge.
