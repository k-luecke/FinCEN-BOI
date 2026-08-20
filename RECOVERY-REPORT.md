# Recovery report — challenge-aware lawful recovery

Generated 2026-08-20T12:36:29.784633+00:00 from committed recovery state. No CAPTCHA solving, proxy/identity rotation, fingerprint spoofing, or rate-limit circumvention is used anywhere in this pipeline: challenged endpoints are routed around through lawful public representations, or recorded as unresolved.

## 1. Challenge / non-content responses

- **6277** challenge/non-content observations across the corpus (latest observation per URL).
- Requested-URL coverage states: UNRESOLVED_CHALLENGE: 4440, NON_CONTENT_TECHNICAL_RESPONSE: 1120, RECOVERED_OFFICIAL_MIRROR: 317, RECOVERED_WEB_ARCHIVE: 282, ACCESS_RESTRICTED: 118

## 2. Hosts generating them

| Host | States |
|------|--------|
| bsaaml.ffiec.gov | ACCESS_RESTRICTED: 3 |
| bsaefiling.fincen.gov | NON_CONTENT_TECHNICAL_RESPONSE: 8 |
| congress.gov | ACCESS_RESTRICTED: 3 |
| fincen.gov | NON_CONTENT_TECHNICAL_RESPONSE: 3 |
| home.treasury.gov | ACCESS_RESTRICTED: 27, NON_CONTENT_TECHNICAL_RESPONSE: 7 |
| judiciary.house.gov | ACCESS_RESTRICTED: 1, NON_CONTENT_TECHNICAL_RESPONSE: 1 |
| ncua.gov | NON_CONTENT_TECHNICAL_RESPONSE: 2 |
| treasury.gov | NON_CONTENT_TECHNICAL_RESPONSE: 1 |
| vault.fbi.gov | NON_CONTENT_TECHNICAL_RESPONSE: 2 |
| www.congress.gov | ACCESS_RESTRICTED: 59 |
| www.fdic.gov | NON_CONTENT_TECHNICAL_RESPONSE: 1 |
| www.federalregister.gov | RECOVERED_OFFICIAL_MIRROR: 317, UNRESOLVED_CHALLENGE: 135 |
| www.ffiec.gov | ACCESS_RESTRICTED: 14 |
| www.fincen.gov | NON_CONTENT_TECHNICAL_RESPONSE: 8, ACCESS_RESTRICTED: 5 |
| www.gao.gov | UNRESOLVED_CHALLENGE: 54, NON_CONTENT_TECHNICAL_RESPONSE: 1, ACCESS_RESTRICTED: 1 |
| www.govinfo.gov | NON_CONTENT_TECHNICAL_RESPONSE: 1054 |
| www.justice.gov | UNRESOLVED_CHALLENGE: 4085, RECOVERED_WEB_ARCHIVE: 282, ACCESS_RESTRICTED: 4, NON_CONTENT_TECHNICAL_RESPONSE: 3 |
| www.ncua.gov | NON_CONTENT_TECHNICAL_RESPONSE: 1 |
| www.occ.gov | NON_CONTENT_TECHNICAL_RESPONSE: 1 |
| www.sec.gov | UNRESOLVED_CHALLENGE: 166, NON_CONTENT_TECHNICAL_RESPONSE: 2, ACCESS_RESTRICTED: 1 |
| www.treasury.gov | NON_CONTENT_TECHNICAL_RESPONSE: 25 |

## 3. Document identities

- 6277 identities built; 5930 resolved via API metadata or URL-slug derivation.
- Document-identity coverage: UNRESOLVED_CHALLENGE: 4440, NON_CONTENT_TECHNICAL_RESPONSE: 1120, RECOVERED_OFFICIAL_MIRROR: 317, RECOVERED_WEB_ARCHIVE: 282, ACCESS_RESTRICTED: 118

## 4–7. Recovery outcomes

- Same-agency recoveries (`SAME_DOCUMENT`): 0
- Official government mirrors (`OFFICIAL_MIRROR`): 317
- Public web archive (`ARCHIVED_VERSION`): 282
- Derived representations (API metadata records): 317
- Still unresolved: **5678** (by tier: {0: 159, 1: 2304, 2: 3215})

## 8. Highest-value challenged collections

Ranked by preservation tier of pending items — Tier 0 (FinCEN/BOI/CTA core) first, then Tier 1 (enforcement, oversight), then general agency content.

## 9. DOJ

- DOJ URL states: UNRESOLVED_CHALLENGE: 4085, RECOVERED_WEB_ARCHIVE: 282, ACCESS_RESTRICTED: 4, NON_CONTENT_TECHNICAL_RESPONSE: 3

## 10. Federal Register

- FR URL states: RECOVERED_OFFICIAL_MIRROR: 317, UNRESOLVED_CHALLENGE: 135
- Each recovered FR document links its page identity to the official GovInfo bytes (`FR_API_RECORD --REPRESENTS--> GOVINFO_DOCUMENT`); both identities preserved.

## 11. Congress / GAO

- Congress: ACCESS_RESTRICTED: 62
- GAO: UNRESOLVED_CHALLENGE: 54, NON_CONTENT_TECHNICAL_RESPONSE: 1, ACCESS_RESTRICTED: 1

## 12. Challenge fingerprints observed

- `UNKNOWN_RESPONSE|detection_mode:metadata_only|expected_document_got_html` × 1043
- `ACCESS_INTERSTITIAL|redirect_to_interstitial_endpoint` × 452
- `ERROR_RESPONSE|http_status:403` × 112
- `BOT_CHALLENGE|detection_mode:metadata_only|expected_document_body_missing|host_challenge_pattern|small_html_success:2410` × 93
- `BOT_CHALLENGE|detection_mode:metadata_only|expected_document_body_missing|host_challenge_pattern|small_html_success:2419` × 78
- `BOT_CHALLENGE|detection_mode:metadata_only|expected_document_body_missing|host_challenge_pattern|small_html_success:2443` × 66
- `BOT_CHALLENGE|detection_mode:metadata_only|expected_document_body_missing|host_challenge_pattern|small_html_success:2586` × 62
- `BOT_CHALLENGE|detection_mode:metadata_only|expected_document_body_missing|host_challenge_pattern|small_html_success:2454` × 62
- `BOT_CHALLENGE|detection_mode:metadata_only|expected_document_body_missing|host_challenge_pattern|small_html_success:2421` × 59
- `BOT_CHALLENGE|detection_mode:metadata_only|expected_document_body_missing|host_challenge_pattern|small_html_success:2564` × 58
- `BOT_CHALLENGE|detection_mode:metadata_only|expected_document_body_missing|host_challenge_pattern|small_html_success:2432` × 55
- `BOT_CHALLENGE|detection_mode:metadata_only|expected_document_body_missing|host_challenge_pattern|small_html_success:2509` × 49
- `BOT_CHALLENGE|detection_mode:metadata_only|expected_document_body_missing|host_challenge_pattern|small_html_success:2498` × 49
- `BOT_CHALLENGE|detection_mode:metadata_only|expected_document_body_missing|host_challenge_pattern|small_html_success:2487` × 49
- `BOT_CHALLENGE|detection_mode:metadata_only|expected_document_body_missing|host_challenge_pattern|small_html_success:2476` × 47

## 13. Most effective alternate routes

- `federal_register_api_inventory_crossref`: 317 links
- `federal_register_api`: 317 links
- `wayback_cdx`: 282 links

## 14. Access-limited gaps

- 118 URLs are access-restricted (401/403 without challenge markup). These are recorded as gaps and never evaded.

## 15. Retry posture

- Challenged endpoints: no immediate retry; small ordinary probe per run; direct retries wait a 7-day cadence and only resume when a probe shows the challenge lifted.
- 429: Retry-After honored once, then the host is stopped for the run. 5xx/network: bounded exponential backoff. 403: classified, never evaded. CAPTCHA: never automated.

## Provenance rules

- Every recovered object keeps original publisher vs retrieval host distinct (e.g. publisher DOJ, retrieval host web.archive.org, relationship ARCHIVED_VERSION).
- Original challenge observations are preserved in `recovery/challenge-observations.jsonl` and the manifest; recovery never rewrites URL history.
- Byte-identical official copies are EXACT_DUPLICATE; differing bytes with matching identity are SAME_DOCUMENT_DIFFERENT_REPRESENTATION; both provenance records are kept.
