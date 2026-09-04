#!/usr/bin/env python3
"""Validate HASM example JSON files.

Checks:
- Required top-level structure
- Required fields for person/experiences/facts/links
- UUID and ISO-8601 date formatting
- Path conventions for *_description_path
- Referential integrity (including FACT experience_ids)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from common_logger import get_logger

UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


@dataclass
class ValidationError:
    file: Path
    message: str


def is_uuid(value: Any) -> bool:
    return isinstance(value, str) and UUID_RE.match(value) is not None


def is_iso_datetime(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        datetime.fromisoformat(value)
        return True
    except ValueError:
        return False


def is_iso_datetime_or_blank(value: Any) -> bool:
    # Blank string is allowed for living persons (no death date yet).
    if value == "":
        return True
    return is_iso_datetime(value)


def expect_fields(obj: dict[str, Any], required: list[str], label: str, errors: list[ValidationError], file: Path) -> None:
    for key in required:
        if key not in obj:
            errors.append(ValidationError(file, f"{label}: missing required field '{key}'"))


def expect_description_path(path_value: Any, entity: str, entity_id: Any, file: Path, errors: list[ValidationError]) -> None:
    if not isinstance(path_value, str):
        errors.append(ValidationError(file, f"{entity}: description path must be string"))
        return
    if not isinstance(entity_id, str):
        return
    expected = f"{entity}/{entity_id}/main.md"
    if path_value != expected:
        errors.append(
            ValidationError(
                file,
                f"{entity}: description path must be '{expected}' but got '{path_value}'",
            )
        )


def validate_file(path: Path) -> list[ValidationError]:
    errors: list[ValidationError] = []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        # Error path: malformed JSON or unreadable file.
        return [ValidationError(path, f"invalid JSON: {exc}")]

    if not isinstance(data, dict):
        return [ValidationError(path, "top-level JSON must be an object")]

    top_required = ["person", "experiences", "facts", "links"]
    expect_fields(data, top_required, "top-level", errors, path)
    if errors:
        return errors

    person = data["person"]
    experiences = data["experiences"]
    facts = data["facts"]
    links = data["links"]

    if not isinstance(person, dict):
        errors.append(ValidationError(path, "person must be an object"))
        return errors
    if not isinstance(experiences, list):
        errors.append(ValidationError(path, "experiences must be a list"))
        return errors
    if not isinstance(facts, list):
        errors.append(ValidationError(path, "facts must be a list"))
        return errors
    if not isinstance(links, list):
        errors.append(ValidationError(path, "links must be a list"))
        return errors

    person_required = [
        "person_id",
        "person_name",
        "person_description_path",
        "birthday",
        "die",
        "link_ids",
    ]
    expect_fields(person, person_required, "person", errors, path)

    person_id = person.get("person_id")
    if not is_uuid(person_id):
        errors.append(ValidationError(path, "person.person_id must be UUID"))
    if not is_iso_datetime_or_blank(person.get("birthday")):
        errors.append(ValidationError(path, "person.birthday must be ISO-8601 datetime or blank"))
    if not is_iso_datetime_or_blank(person.get("die")):
        errors.append(ValidationError(path, "person.die must be ISO-8601 datetime or blank (living person)"))
    expect_description_path(
        person.get("person_description_path"), "PERSON", person_id, path, errors
    )

    exp_ids: set[str] = set()
    for i, exp in enumerate(experiences):
        if not isinstance(exp, dict):
            errors.append(ValidationError(path, f"experiences[{i}] must be an object"))
            continue
        req = [
            "experience_id",
            "person_id",
            "experience_name",
            "experience_description_path",
            "parent_experience_ids",
            "link_ids",
        ]
        expect_fields(exp, req, f"experiences[{i}]", errors, path)

        experience_id = exp.get("experience_id")
        if not is_uuid(experience_id):
            errors.append(ValidationError(path, f"experiences[{i}].experience_id must be UUID"))
        else:
            exp_ids.add(experience_id)

        if exp.get("person_id") != person_id:
            errors.append(
                ValidationError(
                    path,
                    f"experiences[{i}].person_id must match person.person_id",
                )
            )

        expect_description_path(
            exp.get("experience_description_path"),
            "EXPERIENCE",
            experience_id,
            path,
            errors,
        )

    fact_ids: set[str] = set()
    for i, fact in enumerate(facts):
        if not isinstance(fact, dict):
            errors.append(ValidationError(path, f"facts[{i}] must be an object"))
            continue
        req = [
            "fact_id",
            "fact_name",
            "occurred_at",
            "fact_description_path",
            "experience_ids",
            "person_ids",
            "link_ids",
        ]
        expect_fields(fact, req, f"facts[{i}]", errors, path)

        fact_id = fact.get("fact_id")
        if not is_uuid(fact_id):
            errors.append(ValidationError(path, f"facts[{i}].fact_id must be UUID"))
        else:
            fact_ids.add(fact_id)

        if not is_iso_datetime(fact.get("occurred_at")):
            errors.append(ValidationError(path, f"facts[{i}].occurred_at must be ISO-8601 datetime"))

        expect_description_path(
            fact.get("fact_description_path"), "FACT", fact_id, path, errors
        )

        experience_ids = fact.get("experience_ids")
        if not isinstance(experience_ids, list):
            errors.append(ValidationError(path, f"facts[{i}].experience_ids must be a list"))
        else:
            for eid in experience_ids:
                if eid not in exp_ids:
                    errors.append(
                        ValidationError(
                            path,
                            f"facts[{i}].experience_ids contains unknown experience_id '{eid}'",
                        )
                    )

    link_ids: set[str] = set()
    for i, link in enumerate(links):
        if not isinstance(link, dict):
            errors.append(ValidationError(path, f"links[{i}] must be an object"))
            continue
        req = [
            "link_id",
            "link_name",
            "link_type",
            "link_description_path",
            "related_ids",
        ]
        expect_fields(link, req, f"links[{i}]", errors, path)

        link_id = link.get("link_id")
        if not is_uuid(link_id):
            errors.append(ValidationError(path, f"links[{i}].link_id must be UUID"))
        else:
            link_ids.add(link_id)

        expect_description_path(
            link.get("link_description_path"), "LINK", link_id, path, errors
        )

    # Validate link references in person/experience/fact sections.
    def validate_link_id_array(label: str, values: Any) -> None:
        if not isinstance(values, list):
            errors.append(ValidationError(path, f"{label} must be a list"))
            return
        for lid in values:
            if lid not in link_ids:
                errors.append(ValidationError(path, f"{label} contains unknown link_id '{lid}'"))

    validate_link_id_array("person.link_ids", person.get("link_ids"))
    for i, exp in enumerate(experiences):
        if isinstance(exp, dict):
            validate_link_id_array(f"experiences[{i}].link_ids", exp.get("link_ids"))
    for i, fact in enumerate(facts):
        if isinstance(fact, dict):
            validate_link_id_array(f"facts[{i}].link_ids", fact.get("link_ids"))

    # LINK.related_ids can reference person, experience, fact, or link ids.
    # Cross-file references are allowed, so unknown local ids are accepted
    # if they are valid UUIDs.
    known_related_ids = {person_id} | exp_ids | fact_ids | link_ids
    for i, link in enumerate(links):
        if not isinstance(link, dict):
            continue
        related_ids = link.get("related_ids")
        if not isinstance(related_ids, list):
            errors.append(ValidationError(path, f"links[{i}].related_ids must be a list"))
            continue
        for rid in related_ids:
            if rid not in known_related_ids and not is_uuid(rid):
                errors.append(
                    ValidationError(
                        path,
                        f"links[{i}].related_ids contains invalid id '{rid}'",
                    )
                )

    return errors


def find_json_files(target_dir: Path) -> list[Path]:
    return sorted(target_dir.glob("*.json"))


def main() -> int:
    logger = get_logger("hasm-example-validator")
    parser = argparse.ArgumentParser(description="Validate HASM example JSON files.")
    parser.add_argument(
        "--dir",
        default="data/persons",
        help="Directory containing person JSON files (default: data/persons)",
    )
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent.parent
    target_dir = (base_dir / args.dir).resolve()
    logger.info("Starting validation: target_dir=%s", target_dir)

    if not target_dir.exists() or not target_dir.is_dir():
        # Error path: input directory does not exist.
        logger.error("Directory not found: %s", target_dir)
        return 2

    json_files = find_json_files(target_dir)
    if not json_files:
        # Error path: directory exists but contains no JSON files.
        logger.error("No JSON files found in %s", target_dir)
        return 2

    all_errors: list[ValidationError] = []
    for file_path in json_files:
        file_errors = validate_file(file_path)
        if not file_errors:
            logger.info("OK   %s", file_path.name)
        all_errors.extend(file_errors)

    if all_errors:
        # Error path: one or more files violated model constraints.
        logger.error("Validation errors:")
        for err in all_errors:
            logger.error("- %s: %s", err.file.name, err.message)
        logger.error("FAILED: %d error(s) found.", len(all_errors))
        return 1

    logger.info("SUCCESS: validated %d file(s).", len(json_files))
    return 0


if __name__ == "__main__":
    sys.exit(main())
