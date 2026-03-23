# STS2 Behavior Coverage Agent Status

## Current Input

- Input catalog: `data/sts2/raw/ea_01`
- Output catalog: `data/sts2/normalized/cards.ea_01.json`
- Status report: `docs/sts2_import_status_ea_01.md`
- Unimplemented analysis: `docs/sts2_unimplemented_analysis_ea_01.md`

## Baseline

- Initial executable cards: `39`
- Initial unimplemented cards: `538`
- Goal: raise behavior coverage conservatively using low-risk text patterns without breaking loader or planner safety.

## Iterations

### Iteration 1

- Executable / unimplemented: `39 / 538`
- Focus:
  - inspect high-frequency unimplemented templates
  - identify low-risk compound patterns
- Findings:
  - best first targets were fixed multi-hit, damage + debuff, block + draw, draw + discard, damage + draw, and energy + draw
  - runtime already had enough primitive effects to support a generic sequence wrapper
- Verification:
  - baseline importer/report/loader passed

### Iteration 2

- Executable / unimplemented: `42 / 535`
- Added patterns:
  - fixed multi-hit damage via repeated `deal_damage`
- Rule changes:
  - introduced `sequence` behavior support in runtime and schema
  - loader now respects `exhaust` from normalized tags
- Findings:
  - growth was smaller than expected because sentence normalization left `..` separators that blocked most compound regexes
- Verification:
  - importer/report/loader/planner smoke checks passed

### Iteration 3

- Executable / unimplemented: `69 / 508`
- Added patterns:
  - `damage + weak`
  - `damage + vulnerable`
  - `damage + weak + vulnerable`
  - `block + draw`
  - `draw + discard`
  - `damage + draw`
  - `block + damage`
  - `damage + draw + discard`
  - `weak + vulnerable`
  - fixed multi-hit damage with extracted repeat counts
- Rule changes:
  - fixed importer English text normalization so multi-line sentences could be matched reliably
- Verification:
  - importer/report/loader/planner smoke checks passed

### Iteration 4

- Executable / unimplemented: `83 / 494`
- Added patterns:
  - placeholder-form `gain_energy`
  - `gain_energy + draw`
  - `block + next_turn_block`
  - `block + next_turn_energy`
  - `exhaust_from_hand + draw`
  - `block + weak`
- Rule changes:
  - added `discard_cards` and `exhaust_from_hand` behavior keys
  - reused `schedule_effect` for safe next-turn effects
- Verification:
  - importer/report/loader smoke checks passed
  - targeted planner validation passed for scheduled effects and hand-choice effects

### Iteration 5

- Executable / unimplemented: `85 / 492`
- Added patterns:
  - exact one-line `gain strength`
  - exact one-line `gain dexterity`
- Rule changes:
  - `GainBlock` now applies player `dexterity` as a minimal local engine extension
- Verification:
  - importer/report/loader smoke checks passed
  - targeted buff interaction validation passed

## Newly Supported Behavior Categories

- single-effect buffs: `apply_buff` for `strength` and `dexterity`
- compound action cards through `sequence`
- repeated fixed-hit attacks
- draw/discard hand-manipulation cards
- scheduled next-turn block or energy
- executable exhaust cards through tag-aware runtime loading

## Remaining Blockers

- AoE target semantics are still single-enemy in the current engine
- random-target semantics remain unmodeled
- triggered and persistent power behavior still dominates the remainder
- resource systems such as orbs, summon/Osty, forge, stars, doom remain outside current safe coverage
- several temporary or turn-scoped buffs need explicit lifecycle semantics before mapping

## Stop Reason

- Coverage improved materially from `39` to `85`
- Remaining unmapped volume is now mostly trigger/AoE/random/resource/conditional complexity rather than missed simple templates
- Further safe gains require user decisions on target semantics and subsystem abstractions
