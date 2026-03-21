# STS2 Import Plan

## Import goals

- Build a maintainable STS2 card import pipeline without copying game source code.
- Keep import path offline and local-file based.
- Normalize raw data into a stable schema for planner and GUI consumption.
- Support partial behavior mapping first, with explicit `text_only` / `unimplemented` fallback.

## Directory layout

- `tools/sts2_import/`
  - `normalize_cards.py`
  - `behavior_registry.py`
  - `sample_raw_loader.py`
  - `README.md`
- `data/sts2/raw/`
  - local raw input examples
- `data/sts2/normalized/`
  - normalized output (`cards.json`)
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
- `source`: import provenance object

## Raw -> normalized flow

1. Put raw JSON under `data/sts2/raw/`.
2. Run `tools/sts2_import/normalize_cards.py`.
3. Script validates required fields and behavior params.
4. Script writes normalized payload to `data/sts2/normalized/cards.json`.

Validation includes:

- required card fields
- unique `id`
- cost type checks (`int` or supported special token)
- behavior key validity
- nested behavior validation for `schedule_effect` and `conditional`

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
- Planner now skips non-executable cards to prevent false simulation.

## Supported now

- Data normalization and schema validation
- Local-file import only (no network dependency)
- Runtime mapping for common action cards
- Conditional and delayed effect mapping
- Explicit non-executable placeholders

## Not yet supported

- Full STS2 card pool ingestion
- Exhaustive condition language
- Complex bespoke mechanics requiring custom engine state
- Auto-upgrade handling (`+` versions) and localization packs

## Next extension path

1. Add raw adapters for additional formats (YAML/CSV).
2. Add richer condition registry and trigger construction.
3. Add card upgrade variants and localization metadata.
4. Add GUI-side import entry point for switching catalogs.
5. Add regression tests for importer + planner compatibility.
