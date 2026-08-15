# Ownership-reconstruction schema

A temporally versioned, source-addressable corporate-control graph.
Four node tables and one universal edge table, all JSONL, validated by
`ownership_schema.py --root ownership-reconstruction`.

## Nodes

### entity (`entities/*.jsonl`)

| Field            | Required | Notes                                          |
|------------------|----------|------------------------------------------------|
| `entity_id`      | yes      | Stable id, e.g. `us-de:7286832`                |
| `legal_name`     | yes      | Current registered name (history in `names/`)  |
| `jurisdiction`   | yes      | e.g. `US-DE`                                   |
| `entity_number`  | no       | Registry filing number                         |
| `formation_date` | no       | ISO date                                       |
| `entity_type`    | no       | LLC, corporation, LP, trust, …                 |
| `status`         | no       | active, dissolved, …                           |

### person (`people/*.jsonl`)

| Field             | Required | Notes                              |
|-------------------|----------|------------------------------------|
| `person_id`       | yes      | e.g. `p:<uuid>`                    |
| `normalized_name` | yes      |                                    |
| `name_variants`   | no       | List of spellings seen in sources  |

Persons are names-as-evidenced, not resolved identities; uncertain
merges live in `unresolved/`.

### address (`addresses/*.jsonl`)

Addresses are **first-class graph nodes** — much shell structure
surfaces as `person → entity A → address → entity B`.

| Field        | Required | Notes                                        |
|--------------|----------|----------------------------------------------|
| `address_id` | yes      | e.g. `a:<hash of normalized form>`           |
| `normalized` | yes      | Canonical single-line form                   |
| `raw`        | no       | List of raw strings seen in sources          |
| `notes`      | no       | e.g. "registered-agent office", "residential"|

**Weighting rule (documented, applied at analysis time):** shared
addresses are evidence *input*, never an ownership conclusion. A
registered-agent office hosting 30,000 LLCs is nearly meaningless;
two obscure companies sharing a residential mailing address is much
stronger. Encode strength in the edge's `confidence`, and never infer
common ownership from co-location alone.

### name history (`names/*.jsonl`)

Former names are never normalized away — otherwise
`ABC Holdings LLC → XYZ Capital LLC` looks like two unrelated
companies.

| Field          | Required | Notes                                     |
|----------------|----------|-------------------------------------------|
| `entity_id`    | yes      | Must exist in `entities/`                 |
| `name`         | yes      |                                           |
| `name_type`    | yes      | `LEGAL` \| `FORMER` \| `DBA` \| `FOREIGN_REGISTRATION` |
| `jurisdiction` | no       |                                           |
| `valid_from`   | no       | ISO date                                  |
| `valid_to`     | no       | ISO date                                  |
| `source_url`   | yes      |                                           |
| `source_id`    | no       |                                           |
| `retrieved_at` | no       |                                           |
| `sha256`       | no       |                                           |

## Edges (`edges/*.jsonl`) — the universal evidence-edge format

Every ingestion connector — state registries, UCC, real estate, EDGAR,
procurement, IRS 990, courts, licensing, enforcement — writes this one
shape.

| Field            | Required | Notes                                     |
|------------------|----------|-------------------------------------------|
| `subject_id`     | yes      | Any node id (entity, person, address)     |
| `assertion`      | yes      | Closed vocabulary below                   |
| `object_id`      | yes      | Any node id                               |
| `ownership_percent` | no    | 0–100, when the source states it          |
| `valid_from`     | no       | ISO date                                  |
| `valid_to`       | no       | ISO date                                  |
| `source_id`      | no       | Connector-local source identifier         |
| `source_url`     | yes      | The disclosing public record              |
| `source_date`    | no       | Date of the source document               |
| `retrieved_at`   | yes      | When the source was retrieved             |
| `source_sha256`  | no       | Hash of the archived source object        |
| `source_locator` | no       | Page/line/exhibit within the source       |
| `evidence_class` | yes      | `DIRECT` \| `OFFICIAL_INFERENCE` \| `RESEARCH_INFERENCE` |
| `confidence`     | no       | 0–1                                       |

### Assertion vocabulary

```
BENEFICIAL_OWNER       source itself states ownership/control (DIRECT only)
MEMBER                 LLC member
MANAGER                LLC manager
OFFICER
DIRECTOR
ORGANIZER
INCORPORATOR
TRUSTEE
SIGNATORY
REGISTERED_AGENT
UNKNOWN_CONTROL_ROLE   control shown, capacity unclear
PARENT                 entity->entity
SUBSIDIARY             entity->entity
RELATED_ORGANIZATION   e.g. IRS 990 Schedule R
SECURED_PARTY          UCC financing statements
DEBTOR                 UCC financing statements
PROPERTY_OWNER         deeds, assessor records
CONTRACT_RECIPIENT     SAM/USAspending awards
SHARED_ADDRESS         co-location; must touch an address node
```

### Rules enforced by the validator

1. **`BENEFICIAL_OWNER` requires `evidence_class: DIRECT`.** The
   source must itself state ownership/control — a registry BO field,
   an SEC ownership filing, an enforcement document's "X, which was
   owned and controlled by Y". Roles, structure, and co-location are
   never promoted.
2. **`SHARED_ADDRESS` must connect at least one address node** —
   co-location is weighting input, not a conclusion.
3. **Referential integrity**: subject/object must exist among entity,
   person, and address nodes; name records must reference a known
   entity.
4. **Provenance is mandatory** on every edge (`source_url`,
   `retrieved_at`); `source_sha256` should point at archived bytes.
5. Ranges: `confidence` in [0,1], `ownership_percent` in [0,100],
   dates ISO.

### Conflicting edges are never collapsed

If a Tennessee filing says X is manager, an SEC exhibit says Y owns
100%, and a 2024 court filing says Z exercises control, the graph
holds **all three edges** with their dates and sources. Resolution is
an analysis-time act over preserved evidence, never an ingestion-time
overwrite. Likewise, a role that ends is closed with `valid_to`, never
deleted — every historical role is retained.

### Example (synthetic)

```json
{"subject_id": "p:example-1", "assertion": "MANAGER",
 "object_id": "us-xx:0000000", "valid_from": "2024-03-01",
 "source_url": "https://example.gov/filing/1",
 "source_date": "2024-03-01",
 "retrieved_at": "2026-08-15T00:00:00+00:00",
 "source_sha256": null, "source_locator": "p.2",
 "evidence_class": "DIRECT", "confidence": 0.95}
```
