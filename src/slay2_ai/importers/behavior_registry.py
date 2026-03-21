from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ..effects import (
    ApplyBuff,
    ApplyDebuff,
    Conditional,
    DealDamage,
    DrawCards,
    Effect,
    GainBlock,
    GainEnergy,
    ScheduleEffect,
    SetNextAttackBonus,
    SetReplayNextCard,
)
from ..game_state import GameState


ConditionFn = Callable[[GameState, dict], bool]

SUPPORTED_BEHAVIOR_KEYS = {
    "deal_damage",
    "gain_block",
    "draw_cards",
    "gain_energy",
    "apply_buff",
    "apply_debuff",
    "set_next_attack_bonus",
    "replay_next_card",
    "schedule_effect",
    "conditional",
    "text_only",
    "unimplemented",
}


class UnsupportedBehaviorError(ValueError):
    pass


@dataclass(frozen=True)
class BehaviorBuildResult:
    effects: list[Effect]
    executable: bool
    status: str
    note: str = ""


ALIASES = {
    "damage": "deal_damage",
    "block": "gain_block",
    "draw": "draw_cards",
    "energy": "gain_energy",
    "buff": "apply_buff",
    "debuff": "apply_debuff",
    "next_attack_bonus": "set_next_attack_bonus",
    "replay": "replay_next_card",
    "delayed": "schedule_effect",
    "if_else": "conditional",
}


def normalize_behavior_key(raw_key: Any) -> str:
    if raw_key is None:
        return "text_only"
    if not isinstance(raw_key, str):
        raise UnsupportedBehaviorError("behavior_key must be a string")

    key = raw_key.strip().lower()
    key = ALIASES.get(key, key)
    if key not in SUPPORTED_BEHAVIOR_KEYS:
        raise UnsupportedBehaviorError(f"Unsupported behavior_key '{raw_key}'")
    return key


def build_behavior(behavior_key: Any, params: Any) -> BehaviorBuildResult:
    key = normalize_behavior_key(behavior_key)
    row = params or {}
    if not isinstance(row, dict):
        raise UnsupportedBehaviorError("params must be an object")

    if key == "deal_damage":
        return BehaviorBuildResult(
            effects=[DealDamage(amount=_required_int(row, "amount"), target=_optional_str(row, "target", "enemy"))],
            executable=True,
            status="mapped",
        )

    if key == "gain_block":
        return BehaviorBuildResult(
            effects=[GainBlock(amount=_required_int(row, "amount"))],
            executable=True,
            status="mapped",
        )

    if key == "draw_cards":
        return BehaviorBuildResult(
            effects=[DrawCards(amount=_required_int(row, "amount"))],
            executable=True,
            status="mapped",
        )

    if key == "gain_energy":
        return BehaviorBuildResult(
            effects=[GainEnergy(amount=_required_int(row, "amount"))],
            executable=True,
            status="mapped",
        )

    if key == "apply_buff":
        return BehaviorBuildResult(
            effects=[
                ApplyBuff(
                    key=_required_str(row, "key"),
                    amount=_required_int(row, "amount"),
                    target=_optional_str(row, "target", "player"),
                )
            ],
            executable=True,
            status="mapped",
        )

    if key == "apply_debuff":
        return BehaviorBuildResult(
            effects=[
                ApplyDebuff(
                    key=_required_str(row, "key"),
                    amount=_required_int(row, "amount"),
                    target=_optional_str(row, "target", "enemy"),
                )
            ],
            executable=True,
            status="mapped",
        )

    if key == "set_next_attack_bonus":
        return BehaviorBuildResult(
            effects=[SetNextAttackBonus(amount=_required_int(row, "amount"))],
            executable=True,
            status="mapped",
        )

    if key == "replay_next_card":
        return BehaviorBuildResult(
            effects=[SetReplayNextCard(charges=_optional_int(row, "charges", 1))],
            executable=True,
            status="mapped",
        )

    if key == "schedule_effect":
        delay_turns = _required_int(row, "delay_turns")
        label = _optional_str(row, "label", "")
        nested_effect = _required_dict(row, "effect")
        nested = _build_nested_single_effect(nested_effect)
        return BehaviorBuildResult(
            effects=[ScheduleEffect(effect=nested, delay_turns=delay_turns, label=label)],
            executable=True,
            status="mapped",
        )

    if key == "conditional":
        condition_spec = _required_dict(row, "condition")
        condition_fn = _build_condition(condition_spec)

        if_true = _build_branch_effects(_required_list(row, "if_true"), "if_true")
        if_false = _build_branch_effects(_required_list(row, "if_false"), "if_false")

        return BehaviorBuildResult(
            effects=[Conditional(condition=condition_fn, if_true=if_true, if_false=if_false)],
            executable=True,
            status="mapped",
        )

    if key == "text_only":
        note = _optional_str(row, "reason", "behavior intentionally text-only")
        return BehaviorBuildResult(effects=[], executable=False, status="text_only", note=note)

    if key == "unimplemented":
        note = _optional_str(row, "reason", "behavior not implemented")
        return BehaviorBuildResult(effects=[], executable=False, status="unimplemented", note=note)

    raise UnsupportedBehaviorError(f"Unsupported behavior_key '{key}'")


def _build_nested_single_effect(raw_spec: dict[str, Any]) -> Effect:
    nested_key = raw_spec.get("behavior_key")
    nested_params = raw_spec.get("params", {})
    nested = build_behavior(nested_key, nested_params)

    if not nested.executable:
        raise UnsupportedBehaviorError(
            f"Nested behavior '{normalize_behavior_key(nested_key)}' is not executable"
        )
    if len(nested.effects) != 1:
        raise UnsupportedBehaviorError(
            "Nested behavior must map to exactly one Effect for schedule_effect"
        )
    return nested.effects[0]


def _build_branch_effects(raw_specs: list[Any], branch_name: str) -> list[Effect]:
    effects: list[Effect] = []
    for index, raw_item in enumerate(raw_specs):
        if not isinstance(raw_item, dict):
            raise UnsupportedBehaviorError(f"conditional.{branch_name}[{index}] must be an object")

        nested_key = raw_item.get("behavior_key")
        nested_params = raw_item.get("params", {})
        nested = build_behavior(nested_key, nested_params)

        if not nested.executable:
            resolved = normalize_behavior_key(nested_key)
            raise UnsupportedBehaviorError(
                f"conditional.{branch_name}[{index}] uses non-executable behavior '{resolved}'"
            )

        effects.extend(nested.effects)
    return effects


def _build_condition(raw_spec: dict[str, Any]) -> ConditionFn:
    condition_type = _required_str(raw_spec, "type").strip().lower()

    if condition_type == "always":
        def always_true(state: GameState, ctx: dict) -> bool:
            del state, ctx
            return True

        always_true.__name__ = "normalized_cond_always_true"
        return always_true

    if condition_type == "attack_count_before_gte":
        threshold = _required_int(raw_spec, "value")

        def attack_count_before_gte(state: GameState, ctx: dict) -> bool:
            del state
            return int(ctx.get("attack_count_before", 0)) >= threshold

        attack_count_before_gte.__name__ = f"normalized_cond_attack_count_before_gte_{threshold}"
        return attack_count_before_gte

    if condition_type == "player_hp_ratio_lte":
        ratio = _required_float(raw_spec, "value")

        def player_hp_ratio_lte(state: GameState, ctx: dict) -> bool:
            del ctx
            return state.player_hp / max(1, state.player_max_hp) <= ratio

        player_hp_ratio_lte.__name__ = f"normalized_cond_player_hp_ratio_lte_{ratio:g}"
        return player_hp_ratio_lte

    raise UnsupportedBehaviorError(f"Unsupported conditional condition type '{condition_type}'")


def _required_dict(row: dict[str, Any], key: str) -> dict[str, Any]:
    value = row.get(key)
    if not isinstance(value, dict):
        raise UnsupportedBehaviorError(f"params.{key} must be an object")
    return value


def _required_list(row: dict[str, Any], key: str) -> list[Any]:
    value = row.get(key)
    if not isinstance(value, list):
        raise UnsupportedBehaviorError(f"params.{key} must be a list")
    return value


def _required_str(row: dict[str, Any], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise UnsupportedBehaviorError(f"params.{key} must be a non-empty string")
    return value


def _optional_str(row: dict[str, Any], key: str, default: str) -> str:
    value = row.get(key, default)
    if not isinstance(value, str):
        raise UnsupportedBehaviorError(f"params.{key} must be a string")
    return value


def _required_int(row: dict[str, Any], key: str) -> int:
    value = row.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise UnsupportedBehaviorError(f"params.{key} must be an integer")
    return value


def _optional_int(row: dict[str, Any], key: str, default: int) -> int:
    value = row.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise UnsupportedBehaviorError(f"params.{key} must be an integer")
    return value


def _required_float(row: dict[str, Any], key: str) -> float:
    value = row.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise UnsupportedBehaviorError(f"params.{key} must be numeric")
    return float(value)
