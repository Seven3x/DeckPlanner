# DeckPlanner

A Python prototype for card-game decision planning based on **state simulation**, **event-driven effects**, and **search over action sequences**.

## Goal

DeckPlanner is a local research project for building a card-game decision engine inspired by *Slay the Spire*-style combat.

The project does **not** assign a fixed score to each card. Instead, it models:

- game state transitions
- atomic card effects
- triggers and delayed effects
- turn-level action planning
- heuristic evaluation of resulting states

The main goal is to answer:

> Given the current state `s`, what is the best action sequence this turn?

---

## Design Principles

### 1. State-first, not static card scoring
Card value is state-dependent.  
We evaluate actions in context rather than giving every card a permanent score.

### 2. Effects as composable atomic operations
Complex cards should be represented as combinations of reusable effect primitives, such as:

- `DealDamage`
- `GainBlock`
- `DrawCards`
- `GainEnergy`
- `ApplyBuff`
- `ApplyDebuff`
- `AddTrigger`
- `ScheduleEffect`
- `Conditional`
- `ReplayCardEffect`

### 3. Event-driven architecture
The engine should support effects that respond to events like:

- `on_turn_start`
- `on_turn_end`
- `on_card_played`
- `on_attack_played`
- `on_skill_played`
- `on_damage_taken`
- `on_block_gained`
- `on_draw`
- `on_discard`
- `on_exhaust`

### 4. Explicit delayed / cross-turn effects
Delayed effects must be stored in state and executed later.  
They should **not** be flattened into an immediate heuristic bonus.

### 5. Searchable action space
The planner searches over playable card sequences within the current turn using:

- DFS
- optional beam search
- optional rollout later

---

## Project Status

Current target is an **MVP** that supports:

- one player
- one enemy
- hand / draw pile / discard pile / exhaust pile
- basic card play
- start/end of turn flow
- delayed effects
- single-use triggers
- simple heuristic evaluator
- turn-level sequence planner

---

## Planned Structure

```text
DeckPlanner/
├── README.md
├── game_state.py
├── card_defs.py
├── effects.py
├── triggers.py
├── evaluator.py
├── planner.py
├── demo.py
└── tests/
    ├── test_effects.py
    └── test_planner.py