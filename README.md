# hasm_example_generator

Standalone seed-data repository for generating and evaluating HASM model examples.

## Project Status

This repository is public for visibility and personal development. It is currently
maintained as a solo project, and contributions are not being accepted at this
time. Please do not open pull requests or issues proposing changes until this
notice is updated.

## Purpose

This repository is versioned independently from the main HASM application.
It stores curated JSON input files that can be converted into HASM model storage artifacts.

## Dataset Scope

Current dataset includes 3 Japanese historical figures:

- Oda Nobunaga
- Toyotomi Hideyoshi
- Tokugawa Ieyasu

Each JSON file contains all major HASM entities needed for import:

- `person` (PERSON)
- `experiences` (EXPERIENCE)
- `facts` (FACT)
- `links` (LINK)

## Folder Structure

```text
hasm_example_generator/
  |- .gitignore
  |- README.md
  `- data/
      `- persons/
          |- oda_nobunaga.json
          |- toyotomi_hideyoshi.json
          `- tokugawa_ieyasu.json
```

## JSON Conventions

- IDs are UUID strings.
- FACT entries include both `fact_id` and `fact_name`.
- FACT entries use `experience_ids` to point to existing EXPERIENCE IDs.
- Path fields (`*_description_path`) follow HASM storage model conventions:
  - `PERSON/{person_id}/main.md`
  - `EXPERIENCE/{experience_id}/main.md`
  - `FACT/{fact_id}/main.md`
  - `LINK/{link_id}/main.md`
- Date values use ISO-8601 strings.

## Next Steps

- Add a script to transform these JSON files into an actual `my.hasm/` folder.
- Add validation to ensure referential integrity across IDs.

## Validation Script

Run the Python validator from repository root:

```bash
python scripts/validate_hasm_examples.py
```

Optional directory override:

```bash
python scripts/validate_hasm_examples.py --dir data/persons
```

Validation checks include:

- Required PERSON/EXPERIENCE/FACT/LINK fields
- UUID and ISO-8601 datetime formats
- Description path conventions
- FACT `experience_ids` referential integrity
- Link reference integrity across entities (local or external UUID references)

## Generate HASM Folder

Generate HASM folder layout from JSON data:

```bash
python scripts/generate_hasm_folder.py --output output/my.hasm --force
```

This creates:

- `output/my.hasm/hasm.db`
- `output/my.hasm/PERSON/{UUID}/main.md` and `assets/`
- `output/my.hasm/EXPERIENCE/{UUID}/main.md` and `assets/`
- `output/my.hasm/FACT/{UUID}/main.md` and `assets/`
- `output/my.hasm/LINK/{UUID}/main.md` and `assets/`

## License

This project is released under the [MIT License](LICENSE).

## Project Policies

- Contribution status: see [CONTRIBUTING.md](CONTRIBUTING.md).
- Security reports: see [SECURITY.md](SECURITY.md).
- Support expectations: see [SUPPORT.md](SUPPORT.md).

## Logger Integration (Submodule)

These Python scripts try to use shared logger code from `hasm_logger` first.

Expected submodule path:

- `scripts/hasm_logger/src/python/hasm_logger/logger.py`

If not found, scripts automatically fall back to built-in Python logging.

Optional override:

```bash
set HASM_LOGGER_PYTHON_PATH=D:\path\to\hasm_logger\src\python
```
