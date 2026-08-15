# Content Pass 1 derived artifacts — interim staging

The complete `derived/` tree from Content Pass 1 (extracted text for
33,518 documents, ZIP container indexes, per-host boilerplate models —
533 MB raw), packaged as a split zstd tarball so it is durable *now*
on this branch. Every candidate locator in `content-pass-1/` resolves
against these files.

```sh
cat derived-content-pass-1.tar.zst.part00 \
    derived-content-pass-1.tar.zst.part01 > derived-content-pass-1.tar.zst
sha256sum -c sha256sums.txt   # verify parts and the reassembled tarball
zstd -dc derived-content-pass-1.tar.zst | tar -x   # extracts derived/
```

Reassembled tarball SHA-256:
`d7eba7dae5a8f1ed26c00a1ad8e9d411b93012f0f75f53262c7b795ebd2b1fff`
(zstd -19 repack of the tree whose -10 packing was recorded as
`3c92d42a…` in the pass report; identical contents).

**This directory is interim.** The repository's durable-artifact home
for bulk data is GitHub Release assets published by Actions.
`.github/workflows/content-pass-1.yml` reproduces this exact tree from
the `objects-run-*` releases and publishes it as a
`derived-pass1-run-<id>` release — but `workflow_dispatch` only
registers once the workflow file reaches the default branch. After this
branch merges and that release exists, delete this directory; the
content is reproducible and the original archived source bytes remain
the primary archival asset.
