# Provenance vocabulary

Every retrieval record in `manifest.jsonl` and every seed in `seeds.txt`
carries one of the following provenance classifications.

## GOV-PUBLIC

Intentionally published government record.

## FOIA

Government record publicly released under FOIA.

## CONGRESS

Congressional publication, exhibit, report, letter, hearing record, or
committee release.

## COURT

Public judicial record.

## PRESS-DATA

Dataset intentionally made publicly available by a journalistic
organization.

## PRESS-REPORT

Published journalism.

## LEAK-REFERENCE

Citation/metadata describing leaked confidential material. The
confidential source material itself is not mirrored.

## SECONDARY

Other public secondary research.

## UNCLASSIFIED

Awaiting review.

---

## Policy notes

- This archive preserves **public records**. It only fetches explicitly
  seeded URLs on an allowlist of public hosts, never authenticates, and
  never attempts to bypass access controls.
- For FinCEN Files / SAR-related material, use `PRESS-DATA`,
  `PRESS-REPORT`, and `LEAK-REFERENCE` for public reporting and
  intentionally released derivative datasets. Mirrors of raw leaked SARs
  are **not** crawled merely because somebody has made them
  internet-accessible — the archive distinguishes government-public
  records and public reporting from confidential BSA records, and does
  not act as a redistribution mechanism for the latter.
