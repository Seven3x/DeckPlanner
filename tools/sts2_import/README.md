# STS2 Import Tools

This folder provides an offline import pipeline for Slay the Spire 2 card data.

## Directory purpose

- `normalize_cards.py`: Convert local raw card data into normalized schema.
- `behavior_registry.py`: Shared behavior key validation for the normalizer.
- `sample_raw_loader.py`: Minimal verification script that loads normalized cards into `slay2_ai`.

## Prepare raw data

1. Put local raw data in `data/sts2/raw/`.
2. Raw format can be JSON list or JSON object with `cards: []`.
3. Each raw card should contain at least:
   - `name`, `character`, `cost`, `type`, `rarity`, `text`
4. Optional fields:
   - `id`, `tags`, `behavior_key`, `params`, `source`

Reference sample: `data/sts2/raw/cards_sample.json`.

## Run normalization

```bash
python tools/sts2_import/normalize_cards.py \
  --input data/sts2/raw/cards_sample.json \
  --output data/sts2/normalized/cards.json
```

Output file:

- `data/sts2/normalized/cards.json`

Schema reference:

- `data/sts2/normalized/cards.schema.json`
- `data/sts2/normalized/cards.schema.example.json`

## Load normalized cards into slay2_ai

Run the loader check script:

```bash
python tools/sts2_import/sample_raw_loader.py
```

The script will:

1. Load `data/sts2/normalized/cards.json`.
2. Build `CardDefinition` catalog with behavior mapping.
3. Print summary counts:
   - total cards
   - executable cards
   - mapped cards
   - text-only cards
   - unimplemented cards
4. Validate that `text_only` cards are not treated as legal planner actions.

## Integration note

Runtime adapter lives in `src/slay2_ai/importers/` and is intentionally isolated from GUI main logic.
