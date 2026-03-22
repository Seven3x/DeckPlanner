# STS2 External Database Input

This directory is reserved for external STS2 one-card-per-file database dumps.

Suggested layout:

- `data/sts2/external/sts2_database/<version>/`
  - `Silent/`
  - `Ironclad/`
  - `Neutral/`
  - `Status/`
  - `Curse/`
  - each card as one `*.json` file

The importer scans recursively and does not require a fixed nesting depth.

Run importer:

```bash
python tools/sts2_import/import_sts2_database.py \
  --input-dir data/sts2/external/sts2_database/0.98.2 \
  --version 0.98.2
```

Default output:

- `data/sts2/normalized/cards.<version>.json`

You can override output:

```bash
python tools/sts2_import/import_sts2_database.py \
  --input-dir data/sts2/external/sts2_database/0.98.2 \
  --version 0.98.2 \
  --output data/sts2/normalized/cards.sts2_db_0.98.2.json
```

Import notes:

- `unimplemented` is expected for complex cards and does not mean import failure.
- Runtime planner only executes cards mapped to supported behaviors.
- Original source file path is kept in `card.source.original_file`.
