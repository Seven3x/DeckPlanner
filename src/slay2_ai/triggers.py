from __future__ import annotations

from .game_state import GameState, Trigger


SUPPORTED_EVENTS = {
    "on_turn_start",
    "on_turn_end",
    "on_card_played",
    "on_attack_played",
    "on_skill_played",
    "on_damage_taken",
    "on_block_gained",
    "on_draw",
    "on_discard",
    "on_exhaust",
}


def add_trigger(state: GameState, trigger: Trigger) -> None:
    if trigger.event not in SUPPORTED_EVENTS:
        raise ValueError(f"Unsupported event: {trigger.event}")
    state.triggers.append(trigger)


def cleanup_triggers(state: GameState) -> None:
    kept: list[Trigger] = []
    for trigger in state.triggers:
        if trigger.expire_turn is not None and state.turn_index > trigger.expire_turn:
            continue
        if trigger.remaining_uses is not None and trigger.remaining_uses <= 0:
            continue
        kept.append(trigger)
    state.triggers = kept


def emit_event(state: GameState, event: str, payload: dict | None = None) -> None:
    payload = payload or {}
    payload["event"] = event
    cleanup_triggers(state)

    for trigger in list(state.triggers):
        if trigger.event != event:
            continue
        if trigger.condition and not trigger.condition(state, payload):
            continue

        trigger.effect.apply(state, payload)
        if trigger.remaining_uses is not None:
            trigger.remaining_uses -= 1

    cleanup_triggers(state)
