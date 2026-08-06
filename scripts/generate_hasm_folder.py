#!/usr/bin/env python3
"""Generate a HASM model folder from example JSON input files.

Expected output structure:
my.hasm/
  |- hasm.db
  |- PERSON/{UUID}/main.md
  |- PERSON/{UUID}/assets/
  |- EXPERIENCE/{UUID}/main.md
  |- EXPERIENCE/{UUID}/assets/
  |- FACT/{UUID}/main.md
  |- FACT/{UUID}/assets/
  `- LINK/{UUID}/main.md
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from pathlib import Path
from typing import Any

from common_logger import get_logger
from validate_hasm_examples import validate_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a my.hasm folder from JSON files.")
    parser.add_argument(
        "--input-dir",
        default="data/persons",
        help="Directory containing input JSON files (default: data/persons)",
    )
    parser.add_argument(
        "--output",
        default="output/my.hasm",
        help="Output HASM folder path (default: output/my.hasm)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete output path first if it already exists",
    )
    return parser.parse_args()


def _ensure_empty_dir(path: Path, force: bool) -> None:
    if path.exists():
        if not force:
            raise FileExistsError(
                f"Output path already exists: {path}. Use --force to overwrite."
            )
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _json_array(values: list[Any]) -> str:
    return json.dumps(values, ensure_ascii=False)


def _write_markdown(root: Path, rel_path: str, title: str, body_lines: list[str]) -> None:
    file_path = root / rel_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join([f"# {title}", "", *body_lines, ""])
    file_path.write_text(content, encoding="utf-8")


def _write_entity_folders(root: Path, entity: str, entity_id: str, markdown_path: str, title: str, body_lines: list[str]) -> None:
    base_dir = root / entity / entity_id
    (base_dir / "assets").mkdir(parents=True, exist_ok=True)
    _write_markdown(root, markdown_path, title, body_lines)


def _merge_unique(
    items: list[dict[str, Any]],
    key: str,
    src_file: Path,
    seen: dict[str, dict[str, Any]],
    logger: Any,
) -> None:
    for item in items:
        item_id = item.get(key)
        if not isinstance(item_id, str):
            raise ValueError(f"Missing or invalid '{key}' in {src_file.name}")
        if item_id in seen:
            if seen[item_id] != item:
                raise ValueError(
                    f"Conflicting duplicate {key} '{item_id}' between files."
                )
            logger.debug("Skipping identical duplicate %s=%s", key, item_id)
            continue
        seen[item_id] = item


def _init_db(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS person (
            person_id TEXT PRIMARY KEY,
            person_name TEXT NOT NULL,
            person_description_path TEXT NOT NULL,
            birthday TEXT NOT NULL,
            die TEXT NOT NULL,
            link_ids TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS experience (
            experience_id TEXT PRIMARY KEY,
            person_id TEXT NOT NULL,
            experience_name TEXT NOT NULL,
            experience_description_path TEXT NOT NULL,
            parent_experience_ids TEXT NOT NULL,
            link_ids TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS fact (
            fact_id TEXT PRIMARY KEY,
            fact_name TEXT NOT NULL,
            fact_description_path TEXT NOT NULL,
            experience_ids TEXT NOT NULL,
            person_ids TEXT NOT NULL,
            link_ids TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS link (
            link_id TEXT PRIMARY KEY,
            link_name TEXT NOT NULL,
            link_type TEXT NOT NULL,
            link_description_path TEXT NOT NULL,
            related_ids TEXT NOT NULL
        );
        """
    )
    return connection


def main() -> int:
    args = parse_args()
    logger = get_logger("hasm-example-generator")

    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    input_dir = (repo_root / args.input_dir).resolve()
    output_root = (repo_root / args.output).resolve()
    logger.info("Generation config: input_dir=%s output=%s force=%s", input_dir, output_root, args.force)

    if not input_dir.exists() or not input_dir.is_dir():
        # Error path: source directory is missing or invalid.
        logger.error("Input directory not found: %s", input_dir)
        return 2

    json_files = sorted(input_dir.glob("*.json"))
    if not json_files:
        # Error path: no seed files to process.
        logger.error("No JSON files found in: %s", input_dir)
        return 2

    logger.info("Validating %d file(s) before generation", len(json_files))
    all_validation_errors = []
    for json_file in json_files:
        file_errors = validate_file(json_file)
        if file_errors:
            all_validation_errors.extend(file_errors)
        else:
            logger.info("Validation passed: %s", json_file.name)

    if all_validation_errors:
        # Error path: stop generation when model validation fails.
        logger.error("Validation failed with %d error(s)", len(all_validation_errors))
        for err in all_validation_errors:
            logger.error("%s: %s", err.file.name, err.message)
        return 1

    try:
        _ensure_empty_dir(output_root, force=args.force)
    except FileExistsError as exc:
        # Error path: output exists and user did not request overwrite.
        logger.error(str(exc))
        return 2

    for entity in ["PERSON", "EXPERIENCE", "FACT", "LINK"]:
        (output_root / entity).mkdir(parents=True, exist_ok=True)

    people_by_id: dict[str, dict[str, Any]] = {}
    experiences_by_id: dict[str, dict[str, Any]] = {}
    facts_by_id: dict[str, dict[str, Any]] = {}
    links_by_id: dict[str, dict[str, Any]] = {}

    for json_file in json_files:
        try:
            payload = _load_json(json_file)
        except Exception:
            # Error path: unexpected I/O or JSON parse failure.
            logger.exception("Failed to load JSON file: %s", json_file)
            return 1

        person = payload.get("person")
        experiences = payload.get("experiences", [])
        facts = payload.get("facts", [])
        links = payload.get("links", [])

        if not isinstance(person, dict):
            # Error path: file-level structure is malformed.
            logger.error("Invalid person object in %s", json_file.name)
            return 1

        try:
            _merge_unique([person], "person_id", json_file, people_by_id, logger)
            _merge_unique(experiences, "experience_id", json_file, experiences_by_id, logger)
            _merge_unique(facts, "fact_id", json_file, facts_by_id, logger)
            _merge_unique(links, "link_id", json_file, links_by_id, logger)
        except ValueError as exc:
            # Error path: duplicate/conflicting identifiers across files.
            logger.error("%s", exc)
            return 1

    db_path = output_root / "hasm.db"
    try:
        conn = _init_db(db_path)
    except Exception:
        # Error path: SQLite initialization failure.
        logger.exception("Failed to initialize database: %s", db_path)
        return 1

    try:
        for person in people_by_id.values():
            person_id = person["person_id"]
            _write_entity_folders(
                root=output_root,
                entity="PERSON",
                entity_id=person_id,
                markdown_path=person["person_description_path"],
                title=person["person_name"],
                body_lines=[
                    f"- person_id: {person_id}",
                    f"- birthday: {person['birthday']}",
                    f"- die: {person['die']}",
                ],
            )
            conn.execute(
                """
                INSERT INTO person (person_id, person_name, person_description_path, birthday, die, link_ids)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    person_id,
                    person["person_name"],
                    person["person_description_path"],
                    person["birthday"],
                    person["die"],
                    _json_array(person["link_ids"]),
                ),
            )

        for experience in experiences_by_id.values():
            experience_id = experience["experience_id"]
            _write_entity_folders(
                root=output_root,
                entity="EXPERIENCE",
                entity_id=experience_id,
                markdown_path=experience["experience_description_path"],
                title=experience["experience_name"],
                body_lines=[
                    f"- experience_id: {experience_id}",
                    f"- person_id: {experience['person_id']}",
                ],
            )
            conn.execute(
                """
                INSERT INTO experience (experience_id, person_id, experience_name, experience_description_path, parent_experience_ids, link_ids)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    experience_id,
                    experience["person_id"],
                    experience["experience_name"],
                    experience["experience_description_path"],
                    _json_array(experience["parent_experience_ids"]),
                    _json_array(experience["link_ids"]),
                ),
            )

        for fact in facts_by_id.values():
            fact_id = fact["fact_id"]
            _write_entity_folders(
                root=output_root,
                entity="FACT",
                entity_id=fact_id,
                markdown_path=fact["fact_description_path"],
                title=fact["fact_name"],
                body_lines=[
                    f"- fact_id: {fact_id}",
                    f"- fact_name: {fact['fact_name']}",
                ],
            )
            conn.execute(
                """
                INSERT INTO fact (fact_id, fact_name, fact_description_path, experience_ids, person_ids, link_ids)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    fact_id,
                    fact["fact_name"],
                    fact["fact_description_path"],
                    _json_array(fact["experience_ids"]),
                    _json_array(fact["person_ids"]),
                    _json_array(fact["link_ids"]),
                ),
            )

        for link in links_by_id.values():
            link_id = link["link_id"]
            _write_entity_folders(
                root=output_root,
                entity="LINK",
                entity_id=link_id,
                markdown_path=link["link_description_path"],
                title=link["link_name"],
                body_lines=[
                    f"- link_id: {link_id}",
                    f"- link_type: {link['link_type']}",
                ],
            )
            conn.execute(
                """
                INSERT INTO link (link_id, link_name, link_type, link_description_path, related_ids)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    link_id,
                    link["link_name"],
                    link["link_type"],
                    link["link_description_path"],
                    _json_array(link["related_ids"]),
                ),
            )

        conn.commit()
        logger.info("Database write complete: %s", db_path)
    except Exception:
        # Error path: write transaction failed.
        logger.exception("Generation failed while writing HASM artifacts")
        return 1
    finally:
        conn.close()

    logger.info("Generated HASM folder at: %s", output_root)
    logger.info(
        "Entities: PERSON=%d EXPERIENCE=%d FACT=%d LINK=%d",
        len(people_by_id),
        len(experiences_by_id),
        len(facts_by_id),
        len(links_by_id),
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
