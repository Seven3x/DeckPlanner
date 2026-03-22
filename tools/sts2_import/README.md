# STS2 Import Tools

This folder provides an offline import pipeline for Slay the Spire 2 card data.

## Directory purpose

- `normalize_cards.py`: Convert raw card data into normalized schema (`cards.json` or `cards.<version>.json`).
- `raw_catalog_builder.py`: Merge a versioned raw directory into a single raw catalog payload.
- `behavior_registry.py`: Shared behavior key validation for the normalizer.
- `import_status_report.py`: Generate import coverage/status metrics for a normalized file.
- `sample_raw_loader.py`: Runtime smoke-check that loads normalized cards into `slay2_ai`.

## Raw data layouts

### Single file mode (legacy-compatible)

- Place one JSON file under `data/sts2/raw/`.
- Payload can be either:
  - JSON array of cards, or
  - JSON object with `cards: []`.

Reference sample: `data/sts2/raw/cards_sample.json`.

### Versioned directory mode (new)

Use this structure:

- `data/sts2/raw/<version>/`
  - `source_manifest.json`
  - `ironclad_cards.json`
  - `silent_cards.json`
  - `neutral_cards.json`
  - `status_cards.json`
  - `curse_cards.json`

Example directory:

- `data/sts2/raw/sample_full_catalog_v1/`

`source_manifest.json` can explicitly list files and `source_kind`.
If manifest omits `files`, the builder auto-scans `*.json` (excluding manifest).

## Build merged raw catalog

```bash
python tools/sts2_import/raw_catalog_builder.py \
  --input-dir data/sts2/raw/sample_full_catalog_v1
```

Optional output override:

```bash
python tools/sts2_import/raw_catalog_builder.py \
  --input-dir data/sts2/raw/sample_full_catalog_v1 \
  --output /tmp/sts2_catalog_merged.json
```

Builder behavior:

- Merges multiple raw files from one version directory.
- Deduplicates repeated `id` rows when payload is identical.
- Raises an error for conflicting duplicate `id` payloads.
- Adds source metadata per card (`version`, `source_file`, `source_kind`, `import_timestamp`).

## Run normalization

### Single file -> `cards.json`

```bash
python tools/sts2_import/normalize_cards.py \
  --input data/sts2/raw/cards_sample.json \
  --output data/sts2/normalized/cards.json
```

### Versioned directory -> `cards.<version>.json`

```bash
python tools/sts2_import/normalize_cards.py \
  --input-dir data/sts2/raw/sample_full_catalog_v1
```

Equivalent explicit version/output:

```bash
python tools/sts2_import/normalize_cards.py \
  --input-dir data/sts2/raw/sample_full_catalog_v1 \
  --version sample_full_catalog_v1 \
  --output data/sts2/normalized/cards.sample_full_catalog_v1.json
```

Notes:

- `--input` and `--input-dir` are mutually exclusive.
- Normalizer keeps behavior validation and schema-structure validation.
- Output includes `card_count`.

## Generate import status report

```bash
python tools/sts2_import/import_status_report.py \
  --input data/sts2/normalized/cards.sample_full_catalog_v1.json
```

This prints:

- total cards
- executable cards
- mapped cards
- text_only cards
- unimplemented cards
- behavior key counts
- character counts
- type counts
- rarity counts

It also writes markdown by default:

- `docs/sts2_import_status_<version>.md`

## Load normalized cards into slay2_ai

Default file (`cards.json`):

```bash
python tools/sts2_import/sample_raw_loader.py
```

Versioned file (`cards.<version>.json`):

```bash
python tools/sts2_import/sample_raw_loader.py --version sample_full_catalog_v1
```

## Integration note

Runtime adapter lives in `src/slay2_ai/importers/` and remains isolated from GUI main logic.

Current definition of "full import": catalog ingestion completeness (all cards represented in normalized data), not full executable behavior coverage.
