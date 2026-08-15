# Ownership-reconstruction schema

Three JSONL record types. `ownership_schema.py --root
ownership-reconstruction` validates all of them, including referential
integrity from relationships to entities and people.

## entity (`entities/*.jsonl`)

| Field            | Required | Notes                                        |
|------------------|----------|----------------------------------------------|
| `entity_id`      | yes      | Stable id, e.g. `us-de:7286832` (jurisdiction:registry number) |
| `legal_name`     | yes      | As registered                                |
| `jurisdiction`   | yes      | e.g. `US-DE`, `US-WY`                        |
| `entity_number`  | no       | Registry filing number                       |
| `formation_date` | no       | ISO date                                     |
| `entity_type`    | no       | LLC, corporation, LP, trust, …               |
| `status`         | no       | active, dissolved, …                         |
| `source_url`     | no       | Where this entity record was established     |
| `retrieved_at`   | no       | ISO timestamp                                |
| `sha256`         | no       | Hash of the archived source object           |

## person (`people/*.jsonl`)

| Field             | Required | Notes                                   |
|-------------------|----------|-----------------------------------------|
| `person_id`       | yes      | Stable id                               |
| `normalized_name` | yes      | Canonical form                          |
| `name_variants`   | no       | List of spellings seen in sources       |
| `source_url`      | no       |                                         |
| `retrieved_at`    | no       |                                         |
| `sha256`          | no       |                                         |

Persons are *names as evidenced in sources*, not resolved identities.
Two different "John Smith"s stay two `person_id`s until evidence merges
them; uncertain merges live in `unresolved/`.

## relationship (`relationships/*.jsonl`)

| Field               | Required | Notes                                |
|---------------------|----------|--------------------------------------|
| `entity_id`         | yes      | Must exist in entities/              |
| `person_id`         | yes      | Must exist in people/                |
| `role`              | yes      | Closed vocabulary below              |
| `ownership_percent` | no       | 0–100                                |
| `start_date`        | no       | ISO date                             |
| `end_date`          | no       | ISO date                             |
| `source_url`        | yes      | The disclosing public record         |
| `source_document`   | no       | Document title/identifier            |
| `source_date`       | no       | Date of the source document          |
| `retrieved_at`      | yes      | When the source was retrieved        |
| `sha256`            | no       | Hash of the archived source object   |
| `evidence_level`    | yes      | `DIRECT`, `OFFICIAL_INFERENCE`, `RESEARCH_INFERENCE` |

### Roles

```
BENEFICIAL_OWNER_REPORTED   source directly reports beneficial ownership
MEMBER                      LLC member
MANAGER                     LLC manager
DIRECTOR
OFFICER
ORGANIZER
INCORPORATOR
REGISTERED_AGENT
SIGNATORY
TRUSTEE
UNKNOWN_CONTROL_ROLE        control shown, capacity unclear
```

**Rule enforced by the validator:** `BENEFICIAL_OWNER_REPORTED`
requires `evidence_level: DIRECT`. Managers, registered agents,
organizers, and other control roles are never promoted to beneficial
owner — that distinction is exactly what most state registries do not
capture (officers/directors/managers are not necessarily CTA
beneficial owners), so it lives in the schema rather than in judgment
calls at ingestion time.

### Evidence levels

- `DIRECT` — the source document itself states the relationship.
- `OFFICIAL_INFERENCE` — implied by official records without being
  stated (e.g. the same person executes filings across years).
- `RESEARCH_INFERENCE` — secondary research; weakest tier, never
  sufficient for `BENEFICIAL_OWNER_REPORTED`.

### Example (synthetic)

```json
{"entity_id": "us-xx:0000000", "person_id": "p:example-1",
 "role": "MANAGER", "ownership_percent": null,
 "start_date": "2024-03-01", "end_date": null,
 "source_url": "https://example.gov/filing/0000000",
 "source_document": "Annual Report 2024", "source_date": "2024-03-01",
 "retrieved_at": "2026-08-15T00:00:00+00:00",
 "sha256": null, "evidence_level": "DIRECT"}
```
