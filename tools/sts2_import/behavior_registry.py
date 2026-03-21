from __future__ import annotations

from typing import Any

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


class BehaviorValidationError(ValueError):
    pass


def normalize_behavior_key(raw_key: Any) -> str:
    if raw_key is None:
        return "text_only"
    if not isinstance(raw_key, str):
        raise BehaviorValidationError("behavior_key must be a string when provided")

    key = raw_key.strip().lower()
    key = ALIASES.get(key, key)
    if key not in SUPPORTED_BEHAVIOR_KEYS:
        raise BehaviorValidationError(f"unsupported behavior_key '{raw_key}'")
    return key


def validate_behavior_spec(behavior_key: str, params: Any, path: str = "card") -> list[str]:
    errors: list[str] = []
    if params is None:
        params = {}
    if not isinstance(params, dict):
        return [f"{path}.params must be an object"]

    def require_int(key: str) -> None:
        value = params.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            errors.append(f"{path}.params.{key} must be an integer")

    if behavior_key == "deal_damage":
        require_int("amount")
    elif behavior_key == "gain_block":
        require_int("amount")
    elif behavior_key == "draw_cards":
        require_int("amount")
    elif behavior_key == "gain_energy":
        require_int("amount")
    elif behavior_key == "apply_buff":
        if not isinstance(params.get("key"), str):
            errors.append(f"{path}.params.key must be a string")
        require_int("amount")
    elif behavior_key == "apply_debuff":
        if not isinstance(params.get("key"), str):
            errors.append(f"{path}.params.key must be a string")
        require_int("amount")
    elif behavior_key == "set_next_attack_bonus":
        require_int("amount")
    elif behavior_key == "replay_next_card":
        charges = params.get("charges", 1)
        if isinstance(charges, bool) or not isinstance(charges, int):
            errors.append(f"{path}.params.charges must be an integer")
    elif behavior_key == "schedule_effect":
        delay_turns = params.get("delay_turns")
        if isinstance(delay_turns, bool) or not isinstance(delay_turns, int):
            errors.append(f"{path}.params.delay_turns must be an integer")
        nested = params.get("effect")
        if not isinstance(nested, dict):
            errors.append(f"{path}.params.effect must be an object")
        else:
            errors.extend(_validate_nested_behavior(nested, f"{path}.params.effect"))
    elif behavior_key == "conditional":
        condition = params.get("condition")
        if not isinstance(condition, dict):
            errors.append(f"{path}.params.condition must be an object")
        else:
            condition_type = condition.get("type")
            if not isinstance(condition_type, str):
                errors.append(f"{path}.params.condition.type must be a string")

        for branch_name in ("if_true", "if_false"):
            branch = params.get(branch_name)
            if not isinstance(branch, list):
                errors.append(f"{path}.params.{branch_name} must be a list")
                continue
            for idx, item in enumerate(branch):
                if not isinstance(item, dict):
                    errors.append(f"{path}.params.{branch_name}[{idx}] must be an object")
                    continue
                errors.extend(
                    _validate_nested_behavior(item, f"{path}.params.{branch_name}[{idx}]")
                )
    elif behavior_key in {"text_only", "unimplemented"}:
        pass

    return errors


def _validate_nested_behavior(raw_spec: dict[str, Any], path: str) -> list[str]:
    errors: list[str] = []
    try:
        behavior_key = normalize_behavior_key(raw_spec.get("behavior_key"))
    except BehaviorValidationError as exc:
        return [f"{path}.behavior_key invalid: {exc}"]

    params = raw_spec.get("params", {})
    errors.extend(validate_behavior_spec(behavior_key, params, path=path))
    return errors
