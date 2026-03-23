# STS2 Behavior Coverage Evaluation

## Dataset

- Source directory: `data/sts2/raw/ea_01`
- Normalized output: `data/sts2/normalized/cards.ea_01.json`
- Status report: `docs/sts2_import_status_ea_01.md`
- Unimplemented analysis: `docs/sts2_unimplemented_analysis_ea_01.md`

## Coverage Summary

| Metric | Initial | Final |
| --- | ---: | ---: |
| total_cards | 577 | 577 |
| executable_cards | 39 | 85 |
| mapped_cards | 39 | 85 |
| unimplemented_cards | 538 | 492 |

## Newly Supported Patterns

- exact `Deal X damage. Apply Y Vulnerable.`
- exact `Deal X damage. Apply Y Weak.`
- exact `Deal X damage. Apply Y Weak. Apply Y Vulnerable.`
- exact `Apply X Weak. Apply Y Vulnerable.`
- exact `Gain X Block. Draw Y cards.`
- exact `Draw X cards. Discard Y cards.`
- exact `Deal X damage. Draw Y cards.`
- exact `Deal X damage. Draw 1 card. Discard 1 card.`
- exact `Gain X Block. Deal Y damage.`
- exact `Deal X damage twice.`
- exact `Deal X damage N times.` where `N` resolves to a small fixed integer
- exact placeholder-form `Gain {Energy:energyIcons()}.`
- exact `Gain energy, then draw`
- exact `Gain block, next turn gain block`
- exact `Gain block, next turn gain energy`
- exact `Exhaust 1 card, then draw`
- exact `Gain block, apply weak`
- exact one-line `Gain Strength.` and `Gain Dexterity.`

## New Behavior Categories

- `sequence`
  - used as a conservative multi-effect wrapper built from already supported primitives
- `discard_cards`
  - enables safe playable draw/discard cards
- `exhaust_from_hand`
  - enables safe playable exhaust-then-draw cards
- `apply_buff`
  - now used for exact one-line `strength` and `dexterity`

## Small Engine Extensions

- runtime loader now maps `exhaust` keyword tags into `CardDefinition.exhaust`
- `GainBlock` now reads player `dexterity` so exact `Gain Dexterity.` cards have meaningful planner impact

## Deliberately Kept Unimplemented

- AoE attacks against `ALL enemies`
- random-target attacks/debuffs
- persistent triggered powers
- orb/channel/focus cards
- summon/Osty cards
- forge/star/doom systems
- temporary `this turn` stat modifiers
- delayed card-return / card-identity mechanics
- in-hand passive curse/status effects as executable actions

## Risk Notes

- `sequence` only composes already-supported primitive effects; it does not guess new mechanics
- repeat damage mapping is capped to small fixed repeat counts to avoid unsafe `X`-style expansion
- placeholder-form `Gain {...}.` is only mapped to energy when the placeholder name itself clearly indicates energy
- buff mapping is intentionally limited to `strength` and `dexterity`; broader buff support was not generalized

## Recommendation

- If the next phase should continue executable coverage, the most leveraged decision is whether to introduce an AoE abstraction or keep planner semantics strictly single-enemy.
- After that, the next clean frontier is deterministic triggered powers with no random targeting.
- Resource-system cards should remain deferred until you choose a subsystem priority order.
