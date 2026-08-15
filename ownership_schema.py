#!/usr/bin/env python3
"""
Schema and validator for the ownership-reconstruction dataset:
a temporally versioned, source-addressable corporate-control graph
built from lawful public records only.

The dataset does NOT contain CTA-filed beneficial ownership
information, which is confidential and not publicly available. It
records what public sources independently disclose.

Node types (JSONL under ownership-reconstruction/):

    entities/*.jsonl    legal entities
    people/*.jsonl      natural persons as named in sources
    addresses/*.jsonl   normalized addresses — first-class graph nodes
    names/*.jsonl       entity name history (LEGAL/FORMER/DBA/...)

Edge type:

    edges/*.jsonl       universal evidence edges: subject, assertion,
                        object, validity window, provenance, evidence
                        class, confidence

Core rules enforced here:

1. Closed assertion vocabulary. An edge asserts exactly what its
   source establishes. BENEFICIAL_OWNER is reserved for sources that
   themselves state ownership/control (a registry BO field, an SEC
   ownership filing, an enforcement document saying "owned and
   controlled by") and requires evidence_class DIRECT. Managers,
   registered agents, shared addresses, etc. are never promoted.
2. SHARED_ADDRESS never implies common ownership; it must connect at
   least one address node and is weighting input, not a conclusion.
3. Conflicting edges are never collapsed: if one source says X
   manages, another says Y owns, and a third says Z controls, all
   three edges are retained with their dates and sources. The
   validator checks records, not consistency of the world.
4. Every edge carries provenance: source_url and retrieved_at are
   mandatory; source_sha256 should reference archived bytes.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ASSERTIONS = {
    # ownership / reported control
    "BENEFICIAL_OWNER",
    # corporate roles as sources state them
    "MEMBER",
    "MANAGER",
    "OFFICER",
    "DIRECTOR",
    "ORGANIZER",
    "INCORPORATOR",
    "TRUSTEE",
    "SIGNATORY",
    "REGISTERED_AGENT",
    "UNKNOWN_CONTROL_ROLE",
    # inter-entity structure
    "PARENT",
    "SUBSIDIARY",
    "RELATED_ORGANIZATION",
    # commercial / asset relationships
    "SECURED_PARTY",
    "DEBTOR",
    "PROPERTY_OWNER",
    "CONTRACT_RECIPIENT",
    # co-location (weighting input, never ownership)
    "SHARED_ADDRESS",
}

EVIDENCE_CLASSES = {
    # The source document itself states the relationship.
    "DIRECT",
    # Implied by official records without being stated.
    "OFFICIAL_INFERENCE",
    # Secondary research; weakest tier.
    "RESEARCH_INFERENCE",
}

NAME_TYPES = {"LEGAL", "FORMER", "DBA", "FOREIGN_REGISTRATION"}

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")

ENTITY_REQUIRED = ("entity_id", "legal_name", "jurisdiction")
PERSON_REQUIRED = ("person_id", "normalized_name")
ADDRESS_REQUIRED = ("address_id", "normalized")
NAME_REQUIRED = ("entity_id", "name", "name_type", "source_url")
EDGE_REQUIRED = (
    "subject_id",
    "assertion",
    "object_id",
    "evidence_class",
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


def validate_address(record: dict, where: str, problems: Problems):
    check_required(record, ADDRESS_REQUIRED, where, problems)


def validate_name(
    record: dict,
    where: str,
    problems: Problems,
    entity_ids: set[str],
):
    check_required(record, NAME_REQUIRED, where, problems)

    name_type = record.get("name_type")

    if name_type is not None and name_type not in NAME_TYPES:
        problems.report(where, f"unknown name_type {name_type!r}")

    for field in ("valid_from", "valid_to"):
        check_date(record, field, where, problems)

    entity_id = record.get("entity_id")

    if entity_id and entity_ids and entity_id not in entity_ids:
        problems.report(where, f"unknown entity_id {entity_id!r}")


def validate_edge(
    record: dict,
    where: str,
    problems: Problems,
    node_ids: set[str],
    address_ids: set[str],
):
    check_required(record, EDGE_REQUIRED, where, problems)

    assertion = record.get("assertion")

    if assertion is not None and assertion not in ASSERTIONS:
        problems.report(where, f"unknown assertion {assertion!r}")

    evidence_class = record.get("evidence_class")

    if evidence_class is not None and evidence_class not in EVIDENCE_CLASSES:
        problems.report(
            where, f"unknown evidence_class {evidence_class!r}"
        )

    if assertion == "BENEFICIAL_OWNER" and evidence_class != "DIRECT":
        problems.report(
            where,
            "BENEFICIAL_OWNER requires evidence_class DIRECT: the "
            "source must itself state ownership/control; other roles "
            "and co-location are never promoted",
        )

    subject_id = record.get("subject_id")
    object_id = record.get("object_id")

    if assertion == "SHARED_ADDRESS" and address_ids:
        if (
            subject_id not in address_ids
            and object_id not in address_ids
        ):
            problems.report(
                where,
                "SHARED_ADDRESS must connect at least one address "
                "node; co-location is weighting input, not ownership",
            )

    confidence = record.get("confidence")

    if confidence is not None:
        if (
            not isinstance(confidence, (int, float))
            or not 0 <= confidence <= 1
        ):
            problems.report(
                where, f"confidence out of range [0,1]: {confidence!r}"
            )

    percent = record.get("ownership_percent")

    if percent is not None:
        if not isinstance(percent, (int, float)) or not 0 <= percent <= 100:
            problems.report(
                where, f"ownership_percent out of range: {percent!r}"
            )

    for field in ("valid_from", "valid_to", "source_date"):
        check_date(record, field, where, problems)

    for field, value in (("subject_id", subject_id), ("object_id", object_id)):
        if value and node_ids and value not in node_ids:
            problems.report(where, f"unknown {field} {value!r}")


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


def collect(
    root: Path,
    subdir: str,
    id_field: str,
    validator,
    problems: Problems,
) -> tuple[int, set[str]]:
    ids: set[str] = set()
    count = 0

    for where, record in iter_jsonl(root / subdir):
        if isinstance(record, Exception):
            problems.report(where, f"malformed JSON: {record}")
            continue

        count += 1
        validator(record, where, problems)

        record_id = record.get(id_field)

        if record_id:
            if record_id in ids:
                problems.report(
                    where, f"duplicate {id_field} {record_id!r}"
                )
            ids.add(record_id)

    return count, ids


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        default="ownership-reconstruction",
        help="Dataset root",
    )
    args = parser.parse_args()

    root = Path(args.root)
    problems = Problems()

    n_entities, entity_ids = collect(
        root, "entities", "entity_id", validate_entity, problems
    )
    n_people, person_ids = collect(
        root, "people", "person_id", validate_person, problems
    )
    n_addresses, address_ids = collect(
        root, "addresses", "address_id", validate_address, problems
    )

    node_ids = entity_ids | person_ids | address_ids

    n_names = 0

    for where, record in iter_jsonl(root / "names"):
        if isinstance(record, Exception):
            problems.report(where, f"malformed JSON: {record}")
            continue

        n_names += 1
        validate_name(record, where, problems, entity_ids)

    n_edges = 0

    for where, record in iter_jsonl(root / "edges"):
        if isinstance(record, Exception):
            problems.report(where, f"malformed JSON: {record}")
            continue

        n_edges += 1
        validate_edge(record, where, problems, node_ids, address_ids)

    print(
        f"Validated {n_entities} entities, {n_people} people, "
        f"{n_addresses} addresses, {n_names} name records, "
        f"{n_edges} edges"
    )
    print(f"Problems: {problems.count}")

    return 1 if problems.count else 0


if __name__ == "__main__":
    sys.exit(main())
