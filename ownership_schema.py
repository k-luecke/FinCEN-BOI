#!/usr/bin/env python3
"""
Schema and validator for the ownership-reconstruction dataset.

The dataset reconstructs, from public records only, pieces of the
company -> natural-person ownership/control graph that those records
independently disclose. It does NOT contain CTA-filed beneficial
ownership information, which is confidential and not publicly
available.

Three record types, stored as JSONL under ownership-reconstruction/:

    entities/*.jsonl        legal entities
    people/*.jsonl          natural persons (as named in sources)
    relationships/*.jsonl   evidence-backed entity<->person links

Core rules this validator enforces:

1. Role vocabulary is closed. A relationship's role is what the source
   document actually establishes — MEMBER, MANAGER, DIRECTOR,
   REGISTERED_AGENT, etc. are never promoted to
   BENEFICIAL_OWNER_REPORTED. That role is reserved for sources that
   themselves directly report the person as a beneficial owner, and
   requires evidence_level DIRECT.
2. Every relationship carries provenance: source_url and retrieved_at
   are mandatory; sha256 should reference an object in the archive.
3. Referential integrity: relationships may only reference entity_ids
   and person_ids that exist in the dataset.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROLES = {
    "BENEFICIAL_OWNER_REPORTED",
    "MEMBER",
    "MANAGER",
    "DIRECTOR",
    "OFFICER",
    "ORGANIZER",
    "INCORPORATOR",
    "REGISTERED_AGENT",
    "SIGNATORY",
    "TRUSTEE",
    "UNKNOWN_CONTROL_ROLE",
}

EVIDENCE_LEVELS = {
    # The source document itself states the relationship.
    "DIRECT",
    # Inferred from an official record that implies but does not state
    # it (e.g. the same person signs as manager across filings).
    "OFFICIAL_INFERENCE",
    # Inferred from secondary research; weakest tier.
    "RESEARCH_INFERENCE",
}

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")

ENTITY_REQUIRED = ("entity_id", "legal_name", "jurisdiction")
PERSON_REQUIRED = ("person_id", "normalized_name")
RELATIONSHIP_REQUIRED = (
    "entity_id",
    "person_id",
    "role",
    "evidence_level",
    "source_url",
    "retrieved_at",
)


class Problems:
    def __init__(self) -> None:
        self.count = 0

    def report(self, where: str, message: str) -> None:
        self.count += 1
        print(f"FAIL {where}: {message}")


def check_required(record: dict, fields, where: str, problems: Problems):
    for field in fields:
        value = record.get(field)

        if value is None or (isinstance(value, str) and not value.strip()):
            problems.report(where, f"missing required field '{field}'")


def check_date(record: dict, field: str, where: str, problems: Problems):
    value = record.get(field)

    if value is not None and not DATE_RE.match(str(value)):
        problems.report(
            where, f"field '{field}' is not ISO-dated: {value!r}"
        )


def validate_entity(record: dict, where: str, problems: Problems):
    check_required(record, ENTITY_REQUIRED, where, problems)
    check_date(record, "formation_date", where, problems)


def validate_person(record: dict, where: str, problems: Problems):
    check_required(record, PERSON_REQUIRED, where, problems)

    variants = record.get("name_variants")

    if variants is not None and not isinstance(variants, list):
        problems.report(where, "name_variants must be a list")


def validate_relationship(
    record: dict,
    where: str,
    problems: Problems,
    entity_ids: set[str],
    person_ids: set[str],
):
    check_required(record, RELATIONSHIP_REQUIRED, where, problems)

    role = record.get("role")

    if role is not None and role not in ROLES:
        problems.report(where, f"unknown role {role!r}")

    level = record.get("evidence_level")

    if level is not None and level not in EVIDENCE_LEVELS:
        problems.report(where, f"unknown evidence_level {level!r}")

    if role == "BENEFICIAL_OWNER_REPORTED" and level != "DIRECT":
        problems.report(
            where,
            "BENEFICIAL_OWNER_REPORTED requires evidence_level DIRECT: "
            "a source must itself report the person as a beneficial "
            "owner; control roles are never promoted",
        )

    percent = record.get("ownership_percent")

    if percent is not None:
        if not isinstance(percent, (int, float)) or not 0 <= percent <= 100:
            problems.report(
                where, f"ownership_percent out of range: {percent!r}"
            )

    for field in ("start_date", "end_date", "source_date"):
        check_date(record, field, where, problems)

    entity_id = record.get("entity_id")

    if entity_id and entity_ids and entity_id not in entity_ids:
        problems.report(where, f"unknown entity_id {entity_id!r}")

    person_id = record.get("person_id")

    if person_id and person_ids and person_id not in person_ids:
        problems.report(where, f"unknown person_id {person_id!r}")


def iter_jsonl(directory: Path):
    for path in sorted(directory.glob("*.jsonl")):
        with path.open("r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, 1):
                line = line.strip()

                if not line:
                    continue

                where = f"{path}:{line_number}"

                try:
                    yield where, json.loads(line)
                except json.JSONDecodeError as exc:
                    yield where, exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        default="ownership-reconstruction",
        help="Dataset root containing entities/, people/, relationships/",
    )
    args = parser.parse_args()

    root = Path(args.root)
    problems = Problems()

    entity_ids: set[str] = set()
    person_ids: set[str] = set()

    counts = {"entities": 0, "people": 0, "relationships": 0}

    for where, record in iter_jsonl(root / "entities"):
        if isinstance(record, Exception):
            problems.report(where, f"malformed JSON: {record}")
            continue

        counts["entities"] += 1
        validate_entity(record, where, problems)

        if record.get("entity_id"):
            if record["entity_id"] in entity_ids:
                problems.report(
                    where, f"duplicate entity_id {record['entity_id']!r}"
                )
            entity_ids.add(record["entity_id"])

    for where, record in iter_jsonl(root / "people"):
        if isinstance(record, Exception):
            problems.report(where, f"malformed JSON: {record}")
            continue

        counts["people"] += 1
        validate_person(record, where, problems)

        if record.get("person_id"):
            if record["person_id"] in person_ids:
                problems.report(
                    where, f"duplicate person_id {record['person_id']!r}"
                )
            person_ids.add(record["person_id"])

    for where, record in iter_jsonl(root / "relationships"):
        if isinstance(record, Exception):
            problems.report(where, f"malformed JSON: {record}")
            continue

        counts["relationships"] += 1
        validate_relationship(
            record, where, problems, entity_ids, person_ids
        )

    print(
        f"Validated {counts['entities']} entities, "
        f"{counts['people']} people, "
        f"{counts['relationships']} relationships"
    )
    print(f"Problems: {problems.count}")

    return 1 if problems.count else 0


if __name__ == "__main__":
    sys.exit(main())
