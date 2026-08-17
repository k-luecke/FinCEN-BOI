# Recovery report — challenge-aware lawful recovery

Generated 2026-08-17T00:28:00.836178+00:00 from committed recovery state. No CAPTCHA solving, proxy/identity rotation, fingerprint spoofing, or rate-limit circumvention is used anywhere in this pipeline: challenged endpoints are routed around through lawful public representations, or recorded as unresolved.

## 1. Challenge / non-content responses

- **4648** challenge/non-content observations across the corpus (latest observation per URL).
- Requested-URL coverage states: UNRESOLVED_CHALLENGE: 4193, RECOVERED_OFFICIAL_MIRROR: 317, RECOVERED_WEB_ARCHIVE: 126, NON_CONTENT_TECHNICAL_RESPONSE: 8, ACCESS_RESTRICTED: 4

## 2. Hosts generating them

| Host | States |
|------|--------|
| bsaaml.ffiec.gov | ACCESS_RESTRICTED: 1 |
| bsaefiling.fincen.gov | NON_CONTENT_TECHNICAL_RESPONSE: 1 |
| www.congress.gov | ACCESS_RESTRICTED: 1 |
| www.federalregister.gov | RECOVERED_OFFICIAL_MIRROR: 317, UNRESOLVED_CHALLENGE: 2 |
| www.ffiec.gov | ACCESS_RESTRICTED: 1 |
| www.fincen.gov | NON_CONTENT_TECHNICAL_RESPONSE: 1 |
| www.gao.gov | NON_CONTENT_TECHNICAL_RESPONSE: 1 |
| www.govinfo.gov | NON_CONTENT_TECHNICAL_RESPONSE: 1 |
| www.justice.gov | UNRESOLVED_CHALLENGE: 4191, RECOVERED_WEB_ARCHIVE: 126 |
| www.sec.gov | NON_CONTENT_TECHNICAL_RESPONSE: 4, ACCESS_RESTRICTED: 1 |

## 3. Document identities

- 4648 identities built; 4625 resolved via API metadata or URL-slug derivation.
- Document-identity coverage: UNRESOLVED_CHALLENGE: 4193, RECOVERED_OFFICIAL_MIRROR: 317, RECOVERED_WEB_ARCHIVE: 126, NON_CONTENT_TECHNICAL_RESPONSE: 8, ACCESS_RESTRICTED: 4

## 4–7. Recovery outcomes

- Same-agency recoveries (`SAME_DOCUMENT`): 0
- Official government mirrors (`OFFICIAL_MIRROR`): 317
- Public web archive (`ARCHIVED_VERSION`): 126
- Derived representations (API metadata records): 317
- Still unresolved: **4205** (by tier: {0: 4, 1: 2418, 2: 1783})

## 8. Highest-value challenged collections

Ranked by preservation tier of pending items — Tier 0 (FinCEN/BOI/CTA core) first, then Tier 1 (enforcement, oversight), then general agency content.

## 9. DOJ

- DOJ URL states: UNRESOLVED_CHALLENGE: 4191, RECOVERED_WEB_ARCHIVE: 126

## 10. Federal Register

- FR URL states: RECOVERED_OFFICIAL_MIRROR: 317, UNRESOLVED_CHALLENGE: 2
- Each recovered FR document links its page identity to the official GovInfo bytes (`FR_API_RECORD --REPRESENTS--> GOVINFO_DOCUMENT`); both identities preserved.

## 11. Congress / GAO

- Congress: ACCESS_RESTRICTED: 1
- GAO: NON_CONTENT_TECHNICAL_RESPONSE: 1

## 12. Challenge fingerprints observed

- `ACCESS_INTERSTITIAL|redirect_to_interstitial_endpoint` × 319
- `BOT_CHALLENGE|detection_mode:metadata_only|expected_document_body_missing|host_challenge_pattern|small_html_success:2409` × 91
- `BOT_CHALLENGE|detection_mode:metadata_only|expected_document_body_missing|host_challenge_pattern|small_html_success:2417` × 85
- `BOT_CHALLENGE|detection_mode:metadata_only|expected_document_body_missing|host_challenge_pattern|small_html_success:2433` × 77
- `BOT_CHALLENGE|detection_mode:metadata_only|expected_document_body_missing|host_challenge_pattern|small_html_success:2477` × 70
- `BOT_CHALLENGE|detection_mode:metadata_only|expected_document_body_missing|host_challenge_pattern|small_html_success:2444` × 68
- `BOT_CHALLENGE|detection_mode:metadata_only|expected_document_body_missing|host_challenge_pattern|small_html_success:2422` × 63
- `BOT_CHALLENGE|detection_mode:metadata_only|expected_document_body_missing|host_challenge_pattern|small_html_success:2455` × 62
- `BOT_CHALLENGE|detection_mode:metadata_only|expected_document_body_missing|host_challenge_pattern|small_html_success:2488` × 59
- `BOT_CHALLENGE|detection_mode:metadata_only|expected_document_body_missing|host_challenge_pattern|small_html_success:2400` × 59
- `BOT_CHALLENGE|detection_mode:metadata_only|expected_document_body_missing|host_challenge_pattern|small_html_success:2576` × 57
- `BOT_CHALLENGE|detection_mode:metadata_only|expected_document_body_missing|host_challenge_pattern|small_html_success:2466` × 57
- `BOT_CHALLENGE|detection_mode:metadata_only|expected_document_body_missing|host_challenge_pattern|small_html_success:2411` × 51
- `BOT_CHALLENGE|detection_mode:metadata_only|expected_document_body_missing|host_challenge_pattern|small_html_success:2431` × 51
- `BOT_CHALLENGE|detection_mode:metadata_only|expected_document_body_missing|host_challenge_pattern|small_html_success:2510` × 50

## 13. Most effective alternate routes

- `federal_register_api_inventory_crossref`: 317 links
- `federal_register_api`: 317 links
- `wayback_cdx`: 126 links

## 14. Access-limited gaps

- 4 URLs are access-restricted (401/403 without challenge markup). These are recorded as gaps and never evaded.

## 15. Retry posture

- Challenged endpoints: no immediate retry; small ordinary probe per run; direct retries wait a 7-day cadence and only resume when a probe shows the challenge lifted.
- 429: Retry-After honored once, then the host is stopped for the run. 5xx/network: bounded exponential backoff. 403: classified, never evaded. CAPTCHA: never automated.

## Provenance rules

- Every recovered object keeps original publisher vs retrieval host distinct (e.g. publisher DOJ, retrieval host web.archive.org, relationship ARCHIVED_VERSION).
- Original challenge observations are preserved in `recovery/challenge-observations.jsonl` and the manifest; recovery never rewrites URL history.
- Byte-identical official copies are EXACT_DUPLICATE; differing bytes with matching identity are SAME_DOCUMENT_DIFFERENT_REPRESENTATION; both provenance records are kept.
