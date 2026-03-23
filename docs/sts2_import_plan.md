# STS2 Import Plan

## Import goals

- Build a maintainable STS2 card import pipeline without copying game source code.
- Keep import path offline and local-file based.
- Normalize raw data into a stable schema for planner and GUI consumption.
- Support full card catalog ingestion (catalog completeness) even when behavior execution is partial.
- Keep explicit `text_only` / `unimplemented` fallback for non-executable cards.

## Directory layout

- `tools/sts2_import/`
  - `normalize_cards.py`
  - `raw_catalog_builder.py`
  - `import_sts2_database.py`
  - `behavior_registry.py`
  - `import_status_report.py`
  - `sample_raw_loader.py`
  - `README.md`
- `data/sts2/raw/`
  - `cards_sample.json` (legacy single-file sample)
  - `<version>/` (versioned multi-file raw catalog)
    - `source_manifest.json`
    - multiple raw JSON files
- `data/sts2/normalized/`
  - `cards.json` (legacy default output)
  - `cards.<version>.json` (versioned normalized output)
  - schema files (`cards.schema.json`, `cards.schema.example.json`)
- `src/slay2_ai/importers/`
  - runtime behavior mapper and normalized loader

## Canonical schema

Each normalized card uses these fields:

- `id`: stable unique card id
- `name`: display name
- `character`: pool owner / character key
- `cost`: integer cost or special string (`X`, `variable`)
- `type`: `attack` / `skill` / `power` / `status` / `curse` / `other`
- `rarity`: `basic` / `common` / `uncommon` / `rare` / `special`
- `tags`: list of text tags
- `text`: card text for display
- `behavior_key`: runtime behavior mapping key
- `params`: behavior parameter object
- `source`: import provenance object (including version/source file metadata)

## Raw -> normalized flow

Two import paths are supported:

1. Native raw catalog path (`raw_catalog_builder.py` + `normalize_cards.py`)
2. External single-card database path (`import_sts2_database.py`)

The native path remains responsible for repository-owned raw catalogs.
The external path is dedicated to full-catalog ingestion from third-party single-card JSON exports.

### Single file mode

1. Put raw JSON under `data/sts2/raw/`.
2. Run `tools/sts2_import/normalize_cards.py --input ...`.
3. Script validates required fields, behavior params, and normalized schema structure.
4. Script writes normalized payload to `data/sts2/normalized/cards.json` (or custom output).

### Versioned directory mode

1. Create `data/sts2/raw/<version>/` with `source_manifest.json` and multiple raw JSON files.
2. Optional pre-merge check: run `tools/sts2_import/raw_catalog_builder.py --input-dir ...`.
3. Run `tools/sts2_import/normalize_cards.py --input-dir data/sts2/raw/<version>`.
4. Script merges files, deduplicates repeated `id`, validates behavior/schema, and writes:
   - `data/sts2/normalized/cards.<version>.json`

Validation includes:

- required card fields
- duplicate `id` checks (including conflicting duplicates across files)
- cost type checks (`int` or supported special token)
- behavior key validity
- nested behavior validation for `schedule_effect` and `conditional`
- normalized payload schema-structure checks (`card_count`, required fields, enum fields)

### External single-card database mode

1. Put external files under a recursive directory tree, e.g.:
   - `data/sts2/external/sts2_database/<version>/.../*.json`
2. Run:
   - `python tools/sts2_import/import_sts2_database.py --input-dir ... --version <version>`
3. Importer recursively scans all `*.json`, imports only recognized payload shape, and skips invalid/non-matching files with skip details.
4. Script writes:
   - `data/sts2/normalized/cards.<version>.json`

External importer mapping rules:

- Conservatively maps only very safe behaviors (`deal_damage`, `gain_block`, `draw_cards`, `gain_energy`) when text is clearly single-effect.
- Also allows very low-risk single-target debuff mapping for exact one-line `Apply X Weak / Vulnerable / Poison.` cards.
- Complex/power/triggered/ambiguous cards default to `unimplemented`.
- Keeps rich provenance in `source`, including original file path and raw text/variables/upgrades metadata.

Repository note:

- In the current repository snapshot, the reserved external directory may be empty.
- The actual one-card dataset used for ingestion convergence lives under `data/sts2/raw/ea_01/` and is compatible with the external importer because each file already uses the same single-card payload shape.

## behavior_key design

Mapped behaviors:

- `deal_damage`
- `gain_block`
- `draw_cards`
- `gain_energy`
- `apply_buff`
- `apply_debuff`
- `set_next_attack_bonus`
- `replay_next_card`
- `schedule_effect`
- `conditional`

Fallback behaviors:

- `text_only`
- `unimplemented`

## Runtime integration with slay2_ai

- Runtime loader: `src/slay2_ai/importers/sts2_loader.py`
- Behavior mapper: `src/slay2_ai/importers/behavior_registry.py`
- Output: `dict[str, CardDefinition]`

Integration rules:

- Mapped behavior keys become real `Effect` objects.
- `text_only` / `unimplemented` cards are loaded with:
  - `executable=False`
  - empty `effects`
  - explicit tags and source markers
- Planner skips non-executable cards to prevent false simulation.
- Loader now supports both:
  - `cards.json`
  - `cards.<version>.json` (by `version` argument)

## Import status reporting

`tools/sts2_import/import_status_report.py` outputs coverage metrics:

- total cards
- executable cards
- mapped cards
- text_only cards
- unimplemented cards
- behavior key counts
- character counts
- type counts
- rarity counts

It can also write markdown report:

- `docs/sts2_import_status_<version>.md`

## Supported now

- Offline local-file import only
- Single-file and versioned-directory raw ingestion
- Multi-file merge + duplicate detection/dedup
- Normalized schema + behavior validation
- Runtime mapping for common action cards
- Conditional and delayed effect mapping
- Explicit non-executable placeholders
- Coverage/report generation for import progress

## Not yet supported

- Full executable behavior for every STS2 card mechanic
- Exhaustive condition language
- Complex bespoke mechanics requiring custom engine state
- Auto-upgrade handling (`+` versions) and localization packs

## Current definition of "full card import"

Catalog completeness: all cards are represented in normalized data with stable IDs and metadata.
This does not imply all cards are executable in planner/runtime yet.

## Next extension path

1. Add richer condition registry and trigger construction.
2. Add card upgrade variants and localization metadata.
3. Add regression tests for importer + planner compatibility.
4. Add GUI-side catalog switching entry point with version selection.
