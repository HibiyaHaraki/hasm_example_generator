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

Current dataset includes 3 Japanese historical figures and 1 real profile:

- Oda Nobunaga
- Toyotomi Hideyoshi
- Tokugawa Ieyasu
- Haraki Hibiya (generated from `scripts/generate_haraki_hibiya.py`, sourced from hibiya-app's `Record_data.js`)

Each JSON file contains all major HASM entities needed for import:

- `person` (PERSON)
- `experiences` (EXPERIENCE)
- `facts` (FACT)
- `links` (LINK)

To regenerate the Haraki Hibiya dataset after `Record_data.js` changes, update the
`RECORDS` list in `scripts/generate_haraki_hibiya.py` and re-run it:

```bash
python scripts/generate_haraki_hibiya.py
```

To regenerate Hololive JP PERSON seed files:

```bash
python scripts/generate_hololive_jp.py
```

To enrich those files with YouTube video FACT entries and detected collaboration
LINK entries, set a YouTube Data API key in your local shell first:

```bash
set YOUTUBE_API_KEY=<your local YouTube Data API key>
python scripts/generate_hololive_jp.py --max-videos 0
```

Use `--include-dev-is` to also include hololive DEV_IS members. Use
`--max-videos N` for a smaller API-cost test run.

### YouTube Fetching Setup

The YouTube API key must stay local. Do not commit it to this repository. The
repository ignores `.env`, `.env.*`, and `*.local.env` files, but the scripts use
the `YOUTUBE_API_KEY` environment variable directly and do not require a local
file.

1. Create or select a Google Cloud project.
2. Enable the YouTube Data API v3 for that project.
3. Create an API key in Google Cloud Console.
4. Restrict the key where possible, for example by API restriction to YouTube
  Data API v3.
5. Set the key only in your local terminal before running generation.

For Command Prompt:

```bat
set YOUTUBE_API_KEY=<your local YouTube Data API key>
set HOLOLIVE_MAX_VIDEOS=10
generate_all.bat
```

For PowerShell:

```powershell
$env:YOUTUBE_API_KEY = "<your local YouTube Data API key>"
$env:HOLOLIVE_MAX_VIDEOS = "10"
.\generate_all.bat
```

Use `HOLOLIVE_MAX_VIDEOS=10` for an initial test run. Use `0` to fetch all
available uploads, which can consume significant YouTube API quota.

To run the full local generation flow at once on Windows:

```bat
generate_all.bat
```

The batch file runs Haraki Hibiya JSON generation, Hololive JP JSON generation,
JSON validation, and HASM output generation. Optional environment variables:

- `YOUTUBE_API_KEY`: enrich Hololive FACT/LINK data from YouTube.
- `HOLOLIVE_MAX_VIDEOS`: maximum videos per Hololive channel; default is `0` for all.
- `HOLOLIVE_INCLUDE_DEV_IS=1`: also include hololive DEV_IS members.
- `PYTHON`: Python executable name or path; default is `python`.

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
- FACT entries include `fact_id`, `fact_name`, and `occurred_at` (matches the HASM `fact.occurred_at` column used to order FACT commits along the visualizer Z-axis).
- FACT entries use `experience_ids` to point to existing EXPERIENCE IDs.
- Path fields (`*_description_path`) follow HASM storage model conventions:
  - `PERSON/{person_id}/main.md`
  - `EXPERIENCE/{experience_id}/main.md`
  - `FACT/{fact_id}/main.md`
  - `LINK/{link_id}/main.md`
- Date values use ISO-8601 strings. `person.birthday`/`person.die` may be blank (`""`) for a living person with no death date.

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
python scripts/generate_hasm_folder.py --output output --force
```

This creates one independent HASM model per JSON file, except Hololive JP
source files are combined into one model:

- `output/{person-folder}/hasm.db`
- `output/{person-folder}/PERSON/{UUID}/main.md` and `assets/`
- `output/{person-folder}/EXPERIENCE/{UUID}/main.md` and `assets/`
- `output/{person-folder}/FACT/{UUID}/main.md` and `assets/`
- `output/{person-folder}/LINK/{UUID}/main.md` and `assets/`
- `output/Hololive_JP/hasm.db` contains every `hololive_jp_*.json` PERSON,
  EXPERIENCE, FACT, and LINK row in one database.

Non-Hololive models contain only the person and related entities from their
source JSON file.

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
