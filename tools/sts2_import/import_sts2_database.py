from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from normalize_cards import SCHEMA_VERSION, _validate_output_payload


MAPPED_BEHAVIOR_KEYS = {
    "deal_damage",
    "gain_block",
    "draw_cards",
    "gain_energy",
    "lose_hp",
    "discard_cards",
    "exhaust_from_hand",
    "channel_orb",
    "apply_debuff",
    "apply_buff",
    "sequence",
    "add_trigger",
    "schedule_effect",
    "passive_in_hand_trigger",
}

SAFE_BUFF_KEYS = {
    "strength": "strength",
    "dexterity": "dexterity",
    "focus": "focus",
    "orb slots": "orb_slots",
}

TYPE_MAP = {
    "attack": "attack",
    "skill": "skill",
    "power": "power",
    "status": "status",
    "curse": "curse",
}

RARITY_MAP = {
    "basic": "basic",
    "starter": "basic",
    "common": "common",
    "uncommon": "uncommon",
    "rare": "rare",
    "special": "special",
    "status": "special",
    "curse": "special",
    "ancient": "special",
}

SAFE_DEBUFF_KEYS = {
    "weak": "weak",
    "vulnerable": "vulnerable",
    "poison": "poison",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import external STS2 single-card database JSON files into normalized schema"
    )
    parser.add_argument(
        "--input-dir",
        required=True,
        help="Directory tree containing one-card-per-file JSON payloads",
    )
    parser.add_argument(
        "--version",
        default=None,
        help="Import version label used for output naming and source metadata",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output path for normalized cards JSON (default: data/sts2/normalized/cards.<version>.json)",
    )
    return parser.parse_args()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _relative_path(path: Path, base: Path) -> str:
    try:
        return str(path.resolve().relative_to(base.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def _resolve_input_dir(path_value: str, repo_root: Path) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = repo_root / path
    return path.resolve()


def _resolve_output_path(path_value: str | None, repo_root: Path, version: str) -> Path:
    if path_value:
        path = Path(path_value)
        if not path.is_absolute():
            path = repo_root / path
        return path.resolve()
    return (repo_root / "data" / "sts2" / "normalized" / f"cards.{version}.json").resolve()


def _normalize_cost(raw_cost: Any) -> int | str:
    if isinstance(raw_cost, bool):
        raise ValueError("card.cost must not be boolean")
    if isinstance(raw_cost, int):
        if raw_cost < 0:
            # Normalized schema disallows negative integer cost values.
            # Preserve source intent as a string token so cards stay in catalog
            # and remain non-executable at runtime.
            return str(raw_cost)
        return raw_cost
    if isinstance(raw_cost, str):
        token = raw_cost.strip()
        if not token:
            raise ValueError("card.cost string must not be empty")
        if token.isdigit():
            return int(token)
        if token.upper() == "X":
            return "X"
        if token.lower() in {"variable", "var"}:
            return "variable"
        return token
    raise ValueError("card.cost must be int or string")


def _normalize_type(raw_type: Any) -> str:
    if not isinstance(raw_type, str):
        return "other"
    return TYPE_MAP.get(raw_type.strip().lower(), "other")


def _normalize_rarity(raw_rarity: Any) -> str:
    if not isinstance(raw_rarity, str):
        return "special"
    return RARITY_MAP.get(raw_rarity.strip().lower(), "special")


def _pick_text(card: dict[str, Any]) -> str:
    for key in ("text_default_eng", "text_default_chs", "text_raw_eng", "text_raw_chs"):
        value = card.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise ValueError("card text missing: expected one of text_default_eng/text_default_chs/text_raw_eng/text_raw_chs")


def _remove_markup(text: str) -> str:
    return re.sub(r"\[(?:/?)[a-zA-Z_]+\]", "", text)


def _normalize_for_matching(text: str) -> str:
    stripped = _remove_markup(text).replace("\r\n", "\n").replace("\r", "\n").strip()
    stripped = re.sub(r"\.\s*\.", ". ", stripped)
    return re.sub(r"\s+", " ", stripped)


def _normalized_english_text(card: dict[str, Any]) -> str:
    for key in ("text_raw_eng", "text_default_eng"):
        value = card.get(key)
        if isinstance(value, str) and value.strip():
            text = value.strip()
            text = text.replace("\r\n", "\n").replace("\r", "\n")
            text = _remove_markup(text)
            text = text.replace("\n", ". ")
            text = re.sub(r"\.\s*\.", ". ", text)
            return re.sub(r"\s+", " ", text).strip()
    return ""


def _parse_amount_token(token: str, variables: dict[str, Any]) -> int | None:
    token = token.strip()
    if token.isdigit():
        return int(token)

    energy_icon = re.match(r"^\{[A-Za-z0-9_]+:energyIcons\((?P<amount>\d+)\)\}$", token)
    if energy_icon:
        return int(energy_icon.group("amount"))

    placeholder = re.match(r"^\{(?P<name>[A-Za-z0-9_]+)(?::[^}]*)?\}$", token)
    if not placeholder:
        return None

    var_name = placeholder.group("name")
    value = variables.get(var_name)
    if value is None:
        value = _resolve_variable_fallback(var_name, variables)
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, str):
        matched = re.match(r"^\s*(\d+)", value)
        if matched:
            return int(matched.group(1))
    return None


def _resolve_variable_fallback(var_name: str, variables: dict[str, Any]) -> Any:
    direct_candidates = [
        var_name.replace("Calculated", ""),
        var_name.replace("Calculation", ""),
        "Damage" if "damage" in var_name.lower() else None,
        "Block" if "block" in var_name.lower() else None,
        "Cards" if "card" in var_name.lower() else None,
        "Energy" if "energy" in var_name.lower() else None,
    ]
    for candidate in direct_candidates:
        if candidate and candidate in variables:
            return variables[candidate]

    lowered_name = var_name.lower()
    ranked_keys = sorted(
        (
            key
            for key in variables
            if isinstance(key, str) and key.lower() != "keywords"
        ),
        key=lambda key: (
            0 if lowered_name in key.lower() or key.lower() in lowered_name else 1,
            key,
        ),
    )
    for key in ranked_keys:
        value = variables.get(key)
        if isinstance(value, (int, str)) and not isinstance(value, bool):
            return value
    return None


def _sequence(*effects: tuple[str, dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    return "sequence", {"effects": [{"behavior_key": key, "params": params} for key, params in effects]}


def _parse_repeat_token(token: str, variables: dict[str, Any]) -> int | None:
    amount = _parse_amount_token(token, variables)
    if amount is None or amount <= 1 or amount > 5:
        return None
    return amount


def _parse_placeholder_name(token: str) -> str | None:
    matched = re.match(r"^\{(?P<name>[A-Za-z0-9_]+):[^}]+\}$", token.strip())
    if not matched:
        return None
    return matched.group("name")


def _normalize_tags(card: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    variables = card.get("variables")
    if isinstance(variables, dict):
        keywords = variables.get("keywords")
        if isinstance(keywords, list):
            for keyword in keywords:
                if isinstance(keyword, str) and keyword.strip():
                    tags.append(keyword.strip().lower())

    target_type = card.get("targetType")
    if isinstance(target_type, str) and target_type.strip():
        tags.append(f"target:{target_type.strip().lower()}")

    upgrades = card.get("upgrades")
    if isinstance(upgrades, dict):
        for key in ("addKeywords", "removedKeywords"):
            values = upgrades.get(key)
            if isinstance(values, list):
                for value in values:
                    if isinstance(value, str) and value.strip():
                        tags.append(value.strip().lower())

    deduped: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        if tag not in seen:
            deduped.append(tag)
            seen.add(tag)
    return deduped


def _infer_behavior(card: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    variables = card.get("variables")
    if not isinstance(variables, dict):
        variables = {}

    candidate_text = _normalized_english_text(card)

    if not candidate_text:
        return "unimplemented", {}

    text = _normalize_for_matching(candidate_text)
    patterns: list[tuple[re.Pattern[str], str]] = [
        (re.compile(r"^Deal (?P<amount>(?:\d+|X|\{[^{}]+\})) damage\.$", re.IGNORECASE), "deal_damage"),
        (re.compile(r"^Gain (?P<amount>(?:\d+|X|\{[^{}]+\})) Block\.$", re.IGNORECASE), "gain_block"),
        (re.compile(r"^Draw (?P<amount>(?:\d+|X|\{[^{}]+\})) cards?\.$", re.IGNORECASE), "draw_cards"),
        (
            re.compile(
                r"^Draw (?P<amount>(?:\d+|X|\{[^{}]+\})) \{[^{}]+\}\.$",
                re.IGNORECASE,
            ),
            "draw_cards",
        ),
        (re.compile(r"^Gain (?P<amount>(?:\d+|X|\{[^{}]+\})) Energy\.$", re.IGNORECASE), "gain_energy"),
    ]

    for pattern, behavior_key in patterns:
        matched = pattern.match(text)
        if not matched:
            continue
        amount = _parse_amount_token(matched.group("amount"), variables)
        if amount is None:
            return "unimplemented", {}
        return behavior_key, {"amount": amount}

    energy_placeholder_match = re.match(r"^Gain (?P<amount>\{[^{}]+\})\.$", text, re.IGNORECASE)
    if energy_placeholder_match:
        placeholder_name = _parse_placeholder_name(energy_placeholder_match.group("amount"))
        amount = _parse_amount_token(energy_placeholder_match.group("amount"), variables)
        if amount is not None and placeholder_name and "energy" in placeholder_name.lower():
            return "gain_energy", {"amount": amount}

    buff_match = re.match(
        r"^Gain (?P<amount>(?:\d+|\{[^{}]+\})) (?P<buff>Strength|Dexterity|Focus|Orb Slots)\.$",
        text,
        re.IGNORECASE,
    )
    if buff_match:
        amount = _parse_amount_token(buff_match.group("amount"), variables)
        buff_key = SAFE_BUFF_KEYS.get(buff_match.group("buff").strip().lower())
        if amount is not None and buff_key:
            return "apply_buff", {"key": buff_key, "amount": amount, "target": "player"}

    channel_match = re.match(
        r"^Channel (?P<amount>(?:\d+|\{[^{}]+\})) (?P<orb>Lightning|Frost)\.$",
        text,
        re.IGNORECASE,
    )
    if channel_match:
        amount = _parse_amount_token(channel_match.group("amount"), variables)
        if amount is not None:
            return "channel_orb", {"orb_type": channel_match.group("orb").strip().lower(), "amount": amount}

    debuff_match = re.match(
        r"^Apply (?P<amount>(?:\d+|\{[^{}]+\})) (?P<debuff>[A-Za-z]+)\.$",
        text,
        re.IGNORECASE,
    )
    if debuff_match:
        amount = _parse_amount_token(debuff_match.group("amount"), variables)
        debuff_key = SAFE_DEBUFF_KEYS.get(debuff_match.group("debuff").strip().lower())
        if amount is not None and debuff_key:
            return "apply_debuff", {"key": debuff_key, "amount": amount, "target": "enemy"}

    sequence_patterns: list[tuple[re.Pattern[str], Any]] = [
        (
            re.compile(
                r"^Lose (?P<hp>(?:\d+|\{[^{}]+\})) HP\. Gain (?P<block>(?:\d+|\{[^{}]+\})) Block\.$",
                re.IGNORECASE,
            ),
            lambda m: _sequence(
                ("lose_hp", {"amount": _parse_amount_token(m.group("hp"), variables), "target": "player"}),
                ("gain_block", {"amount": _parse_amount_token(m.group("block"), variables)}),
            ),
        ),
        (
            re.compile(
                r"^Lose (?P<hp>(?:\d+|\{[^{}]+\})) HP\. Gain (?P<energy>\{[^{}]+\})\.$",
                re.IGNORECASE,
            ),
            lambda m: _sequence(
                ("lose_hp", {"amount": _parse_amount_token(m.group("hp"), variables), "target": "player"}),
                ("gain_energy", {"amount": _parse_amount_token(m.group("energy"), variables)}),
            ),
        ),
        (
            re.compile(
                r"^Lose (?P<hp>(?:\d+|\{[^{}]+\})) HP\. Deal (?P<damage>(?:\d+|\{[^{}]+\})) damage\.$",
                re.IGNORECASE,
            ),
            lambda m: _sequence(
                ("lose_hp", {"amount": _parse_amount_token(m.group("hp"), variables), "target": "player"}),
                ("deal_damage", {"amount": _parse_amount_token(m.group("damage"), variables)}),
            ),
        ),
        (
            re.compile(
                r"^Lose (?P<hp>(?:\d+|\{[^{}]+\})) HP\. Gain (?P<energy>\{[^{}]+\})\. Draw (?P<draw>(?:\d+|\{[^{}]+\})) cards?\.$",
                re.IGNORECASE,
            ),
            lambda m: _sequence(
                ("lose_hp", {"amount": _parse_amount_token(m.group("hp"), variables), "target": "player"}),
                ("gain_energy", {"amount": _parse_amount_token(m.group("energy"), variables)}),
                ("draw_cards", {"amount": _parse_amount_token(m.group("draw"), variables)}),
            ),
        ),
        (
            re.compile(
                r"^Gain (?P<block>(?:\d+|\{[^{}]+\})) Block\. Draw (?P<draw>(?:\d+|\{[^{}]+\})) (?:card|cards|\{[^{}]+\})\.$",
                re.IGNORECASE,
            ),
            lambda m: _sequence(
                ("gain_block", {"amount": _parse_amount_token(m.group("block"), variables)}),
                ("draw_cards", {"amount": _parse_amount_token(m.group("draw"), variables)}),
            ),
        ),
        (
            re.compile(
                r"^Draw (?P<draw>(?:\d+|\{[^{}]+\})) (?:card|cards|\{[^{}]+\})\. Discard (?P<discard>(?:\d+|\{[^{}]+\})) (?:card|cards|\{[^{}]+\})\.$",
                re.IGNORECASE,
            ),
            lambda m: _sequence(
                ("draw_cards", {"amount": _parse_amount_token(m.group("draw"), variables)}),
                ("discard_cards", {"amount": _parse_amount_token(m.group("discard"), variables)}),
            ),
        ),
        (
            re.compile(
                r"^Gain (?P<energy>(?:\d+|\{[^{}]+\}))(?: Energy)?\. Draw (?P<draw>(?:\d+|\{[^{}]+\})) (?:card|cards|\{[^{}]+\})\.$",
                re.IGNORECASE,
            ),
            lambda m: _sequence(
                ("gain_energy", {"amount": _parse_amount_token(m.group("energy"), variables)}),
                ("draw_cards", {"amount": _parse_amount_token(m.group("draw"), variables)}),
            ),
        ),
        (
            re.compile(
                r"^Deal (?P<damage>(?:\d+|\{[^{}]+\})) damage\. Draw (?P<draw>(?:\d+|\{[^{}]+\})) (?:card|cards|\{[^{}]+\})\.$",
                re.IGNORECASE,
            ),
            lambda m: _sequence(
                ("deal_damage", {"amount": _parse_amount_token(m.group("damage"), variables)}),
                ("draw_cards", {"amount": _parse_amount_token(m.group("draw"), variables)}),
            ),
        ),
        (
            re.compile(
                r"^Deal (?P<damage>(?:\d+|\{[^{}]+\})) damage\. Apply (?P<amount>(?:\d+|\{[^{}]+\})) (?P<debuff>Weak|Vulnerable|Poison)\.$",
                re.IGNORECASE,
            ),
            lambda m: _sequence(
                ("deal_damage", {"amount": _parse_amount_token(m.group("damage"), variables)}),
                (
                    "apply_debuff",
                    {
                        "key": SAFE_DEBUFF_KEYS[m.group("debuff").strip().lower()],
                        "amount": _parse_amount_token(m.group("amount"), variables),
                        "target": "enemy",
                    },
                ),
            ),
        ),
        (
            re.compile(
                r"^Apply (?P<weak>(?:\d+|\{[^{}]+\})) Weak\. Apply (?P<vuln>(?:\d+|\{[^{}]+\})) Vulnerable\.$",
                re.IGNORECASE,
            ),
            lambda m: _sequence(
                ("apply_debuff", {"key": "weak", "amount": _parse_amount_token(m.group("weak"), variables), "target": "enemy"}),
                ("apply_debuff", {"key": "vulnerable", "amount": _parse_amount_token(m.group("vuln"), variables), "target": "enemy"}),
            ),
        ),
        (
            re.compile(
                r"^Deal (?P<damage>(?:\d+|\{[^{}]+\})) damage\. Apply (?P<weak>(?:\d+|\{[^{}]+\})) Weak\. Apply (?P<vuln>(?:\d+|\{[^{}]+\})) Vulnerable\.$",
                re.IGNORECASE,
            ),
            lambda m: _sequence(
                ("deal_damage", {"amount": _parse_amount_token(m.group("damage"), variables)}),
                ("apply_debuff", {"key": "weak", "amount": _parse_amount_token(m.group("weak"), variables), "target": "enemy"}),
                ("apply_debuff", {"key": "vulnerable", "amount": _parse_amount_token(m.group("vuln"), variables), "target": "enemy"}),
            ),
        ),
        (
            re.compile(
                r"^Gain (?P<block>(?:\d+|\{[^{}]+\})) Block\. Deal (?P<damage>(?:\d+|\{[^{}]+\})) damage\.$",
                re.IGNORECASE,
            ),
            lambda m: _sequence(
                ("gain_block", {"amount": _parse_amount_token(m.group("block"), variables)}),
                ("deal_damage", {"amount": _parse_amount_token(m.group("damage"), variables)}),
            ),
        ),
        (
            re.compile(
                r"^Deal (?P<damage>(?:\d+|\{[^{}]+\})) damage\. Draw 1 card\. Discard 1 card\.$",
                re.IGNORECASE,
            ),
            lambda m: _sequence(
                ("deal_damage", {"amount": _parse_amount_token(m.group("damage"), variables)}),
                ("draw_cards", {"amount": 1}),
                ("discard_cards", {"amount": 1}),
            ),
        ),
        (
            re.compile(
                r"^Gain (?P<block>(?:\d+|\{[^{}]+\})) Block\. Apply (?P<weak>(?:\d+|\{[^{}]+\})) Weak\.$",
                re.IGNORECASE,
            ),
            lambda m: _sequence(
                ("gain_block", {"amount": _parse_amount_token(m.group("block"), variables)}),
                ("apply_debuff", {"key": "weak", "amount": _parse_amount_token(m.group("weak"), variables), "target": "enemy"}),
            ),
        ),
        (
            re.compile(
                r"^Exhaust (?P<count>(?:\d+|\{[^{}]+\})) card\. Draw (?P<draw>(?:\d+|\{[^{}]+\})) cards?\.$",
                re.IGNORECASE,
            ),
            lambda m: _sequence(
                ("exhaust_from_hand", {"amount": _parse_amount_token(m.group("count"), variables)}),
                ("draw_cards", {"amount": _parse_amount_token(m.group("draw"), variables)}),
            ),
        ),
        (
            re.compile(
                r"^Gain (?P<block>(?:\d+|\{[^{}]+\})) Block\. Next turn, gain (?P<next>(?:\d+|\{[^{}]+\})) Block\.$",
                re.IGNORECASE,
            ),
            lambda m: _sequence(
                ("gain_block", {"amount": _parse_amount_token(m.group("block"), variables)}),
                (
                    "schedule_effect",
                    {
                        "delay_turns": 1,
                        "label": "next_turn_block",
                        "effect": {
                            "behavior_key": "gain_block",
                            "params": {"amount": _parse_amount_token(m.group("next"), variables)},
                        },
                    },
                ),
            ),
        ),
        (
            re.compile(
                r"^Gain (?P<block>(?:\d+|\{[^{}]+\})) Block\. Next turn, gain (?P<next>\{[^{}]+\})\.$",
                re.IGNORECASE,
            ),
            lambda m: _sequence(
                ("gain_block", {"amount": _parse_amount_token(m.group("block"), variables)}),
                (
                    "schedule_effect",
                    {
                        "delay_turns": 1,
                        "label": "next_turn_energy",
                        "effect": {
                            "behavior_key": "gain_energy",
                            "params": {"amount": _parse_amount_token(m.group("next"), variables)},
                        },
                    },
                ),
            ),
        ),
        (
            re.compile(
                r"^Next turn, gain (?P<next>\{[^{}]+\})\.$",
                re.IGNORECASE,
            ),
            lambda m: (
                "schedule_effect",
                {
                    "delay_turns": 1,
                    "label": "next_turn_energy",
                    "effect": {
                        "behavior_key": "gain_energy",
                        "params": {"amount": _parse_amount_token(m.group("next"), variables)},
                    },
                },
            ),
        ),
        (
            re.compile(
                r"^Exhaust (?P<count>(?:\d+|\{[^{}]+\})) card\. Next turn, gain (?P<next>\{[^{}]+\})\.$",
                re.IGNORECASE,
            ),
            lambda m: _sequence(
                ("exhaust_from_hand", {"amount": _parse_amount_token(m.group("count"), variables)}),
                (
                    "schedule_effect",
                    {
                        "delay_turns": 1,
                        "label": "next_turn_energy",
                        "effect": {
                            "behavior_key": "gain_energy",
                            "params": {"amount": _parse_amount_token(m.group("next"), variables)},
                        },
                    },
                ),
            ),
        ),
        (
            re.compile(
                r"^Deal (?P<damage>(?:\d+|\{[^{}]+\})) damage\. Next turn, gain (?P<next>\{[^{}]+\})\.$",
                re.IGNORECASE,
            ),
            lambda m: _sequence(
                ("deal_damage", {"amount": _parse_amount_token(m.group("damage"), variables)}),
                (
                    "schedule_effect",
                    {
                        "delay_turns": 1,
                        "label": "next_turn_energy",
                        "effect": {
                            "behavior_key": "gain_energy",
                            "params": {"amount": _parse_amount_token(m.group("next"), variables)},
                        },
                    },
                ),
            ),
        ),
        (
            re.compile(
                r"^Deal (?P<damage>(?:\d+|\{[^{}]+\})) damage\. Next turn, draw (?P<draw>(?:\d+|\{[^{}]+\})) (?:card|cards|\{[^{}]+\})\.$",
                re.IGNORECASE,
            ),
            lambda m: _sequence(
                ("deal_damage", {"amount": _parse_amount_token(m.group("damage"), variables)}),
                (
                    "schedule_effect",
                    {
                        "delay_turns": 1,
                        "label": "next_turn_draw",
                        "effect": {
                            "behavior_key": "draw_cards",
                            "params": {"amount": _parse_amount_token(m.group("draw"), variables)},
                        },
                    },
                ),
            ),
        ),
        (
            re.compile(
                r"^Gain (?P<block>(?:\d+|\{[^{}]+\})) Block\. Next turn, draw (?P<draw>(?:\d+|\{[^{}]+\})) (?:card|cards|\{[^{}]+\}) and gain (?P<energy>\{[^{}]+\})\.$",
                re.IGNORECASE,
            ),
            lambda m: _sequence(
                ("gain_block", {"amount": _parse_amount_token(m.group("block"), variables)}),
                (
                    "schedule_effect",
                    {
                        "delay_turns": 1,
                        "label": "next_turn_draw_and_energy",
                        "effect": {
                            "behavior_key": "sequence",
                            "params": {
                                "effects": [
                                    {
                                        "behavior_key": "draw_cards",
                                        "params": {"amount": _parse_amount_token(m.group("draw"), variables)},
                                    },
                                    {
                                        "behavior_key": "gain_energy",
                                        "params": {"amount": _parse_amount_token(m.group("energy"), variables)},
                                    },
                                ]
                            },
                        },
                    },
                ),
            ),
        ),
        (
            re.compile(
                r"^Deal (?P<damage>(?:\d+|\{[^{}]+\})) damage to ALL enemies\.$",
                re.IGNORECASE,
            ),
            lambda m: ("deal_damage", {"amount": _parse_amount_token(m.group("damage"), variables), "target": "enemy"}),
        ),
        (
            re.compile(
                r"^Deal (?P<damage>(?:\d+|\{[^{}]+\})) damage to ALL enemies twice\.$",
                re.IGNORECASE,
            ),
            lambda m: _sequence(
                ("deal_damage", {"amount": _parse_amount_token(m.group("damage"), variables), "target": "enemy"}),
                ("deal_damage", {"amount": _parse_amount_token(m.group("damage"), variables), "target": "enemy"}),
            ),
        ),
        (
            re.compile(
                r"^Deal (?P<damage>(?:\d+|\{[^{}]+\})) damage (?P<repeat>(?:\d+|\{[^{}]+\})) times to ALL enemies\.$",
                re.IGNORECASE,
            ),
            lambda m: _sequence(
                *(("deal_damage", {"amount": _parse_amount_token(m.group("damage"), variables), "target": "enemy"}) for _ in range(_parse_repeat_token(m.group("repeat"), variables) or 0))
            ),
        ),
        (
            re.compile(
                r"^Deal (?P<damage>(?:\d+|\{[^{}]+\})) damage to a random enemy twice\.$",
                re.IGNORECASE,
            ),
            lambda m: _sequence(
                ("deal_damage", {"amount": _parse_amount_token(m.group("damage"), variables), "target": "enemy"}),
                ("deal_damage", {"amount": _parse_amount_token(m.group("damage"), variables), "target": "enemy"}),
            ),
        ),
        (
            re.compile(
                r"^Deal (?P<damage>(?:\d+|\{[^{}]+\})) damage to a random enemy (?P<repeat>(?:\d+|\{[^{}]+\})) times\.$",
                re.IGNORECASE,
            ),
            lambda m: _sequence(
                *(("deal_damage", {"amount": _parse_amount_token(m.group("damage"), variables), "target": "enemy"}) for _ in range(_parse_repeat_token(m.group("repeat"), variables) or 0))
            ),
        ),
        (
            re.compile(
                r"^Deal (?P<damage>(?:\d+|\{[^{}]+\})) damage and apply (?P<amount>(?:\d+|\{[^{}]+\})) Vulnerable to ALL enemies\.$",
                re.IGNORECASE,
            ),
            lambda m: _sequence(
                ("deal_damage", {"amount": _parse_amount_token(m.group("damage"), variables), "target": "enemy"}),
                ("apply_debuff", {"key": "vulnerable", "amount": _parse_amount_token(m.group("amount"), variables), "target": "enemy"}),
            ),
        ),
        (
            re.compile(
                r"^Apply (?P<amount>(?:\d+|\{[^{}]+\})) Poison to a random enemy (?P<repeat>(?:\d+|\{[^{}]+\})) times\.$",
                re.IGNORECASE,
            ),
            lambda m: _sequence(
                *(("apply_debuff", {"key": "poison", "amount": _parse_amount_token(m.group("amount"), variables), "target": "enemy"}) for _ in range(_parse_repeat_token(m.group("repeat"), variables) or 0))
            ),
        ),
        (
            re.compile(
                r"^Deal (?P<damage>(?:\d+|\{[^{}]+\})) damage\. Channel (?P<amount>(?:\d+|\{[^{}]+\})) (?P<orb>Lightning|Frost)\.$",
                re.IGNORECASE,
            ),
            lambda m: _sequence(
                ("deal_damage", {"amount": _parse_amount_token(m.group("damage"), variables)}),
                ("channel_orb", {"orb_type": m.group("orb").strip().lower(), "amount": _parse_amount_token(m.group("amount"), variables)}),
            ),
        ),
        (
            re.compile(
                r"^Channel (?P<amount>(?:\d+|\{[^{}]+\})) Frost\. Draw (?P<draw>(?:\d+|\{[^{}]+\})) (?:card|cards|\{[^{}]+\})\.$",
                re.IGNORECASE,
            ),
            lambda m: _sequence(
                ("channel_orb", {"orb_type": "frost", "amount": _parse_amount_token(m.group("amount"), variables)}),
                ("draw_cards", {"amount": _parse_amount_token(m.group("draw"), variables)}),
            ),
        ),
        (
            re.compile(
                r"^Gain (?P<amount>(?:\d+|\{[^{}]+\})) Dexterity this turn\.$",
                re.IGNORECASE,
            ),
            lambda m: _sequence(
                ("apply_buff", {"key": "dexterity", "amount": _parse_amount_token(m.group("amount"), variables), "target": "player"}),
                ("schedule_effect", {"delay_turns": 1, "label": "expire_dexterity_this_turn", "effect": {"behavior_key": "apply_buff", "params": {"key": "dexterity", "amount": -(_parse_amount_token(m.group("amount"), variables) or 0), "target": "player"}}}),
            ),
        ),
        (
            re.compile(
                r"^Gain (?P<amount>(?:\d+|\{[^{}]+\})) Strength this turn\.$",
                re.IGNORECASE,
            ),
            lambda m: _sequence(
                ("apply_buff", {"key": "strength", "amount": _parse_amount_token(m.group("amount"), variables), "target": "player"}),
                ("schedule_effect", {"delay_turns": 1, "label": "expire_strength_this_turn", "effect": {"behavior_key": "apply_buff", "params": {"key": "strength", "amount": -(_parse_amount_token(m.group("amount"), variables) or 0), "target": "player"}}}),
            ),
        ),
        (
            re.compile(
                r"^Enemy loses (?P<amount>(?:\d+|\{[^{}]+\})) Strength this turn\.$",
                re.IGNORECASE,
            ),
            lambda m: _sequence(
                ("apply_buff", {"key": "strength", "amount": -(_parse_amount_token(m.group("amount"), variables) or 0), "target": "enemy"}),
                ("schedule_effect", {"delay_turns": 1, "label": "expire_enemy_strength_loss_this_turn", "effect": {"behavior_key": "apply_buff", "params": {"key": "strength", "amount": _parse_amount_token(m.group("amount"), variables), "target": "enemy"}}}),
            ),
        ),
        (
            re.compile(
                r"^Whenever you play a card, gain (?P<amount>(?:\d+|\{[^{}]+\})) Block\.$",
                re.IGNORECASE,
            ),
            lambda m: (
                "add_trigger",
                {
                    "event": "on_card_played",
                    "label": "whenever_play_card_gain_block",
                    "effect": {
                        "behavior_key": "gain_block",
                        "params": {"amount": _parse_amount_token(m.group("amount"), variables)},
                    },
                },
            ),
        ),
        (
            re.compile(
                r"^Whenever you play an Attack this turn, gain (?P<amount>(?:\d+|\{[^{}]+\})) Block\.$",
                re.IGNORECASE,
            ),
            lambda m: (
                "add_trigger",
                {
                    "event": "on_attack_played",
                    "label": "this_turn_attack_gain_block",
                    "expire_on_current_turn": True,
                    "effect": {
                        "behavior_key": "gain_block",
                        "params": {"amount": _parse_amount_token(m.group("amount"), variables)},
                    },
                },
            ),
        ),
        (
            re.compile(
                r"^Whenever you play a Power, Channel (?P<amount>(?:\d+|\{[^{}]+\})) Lightning\.$",
                re.IGNORECASE,
            ),
            lambda m: (
                "add_trigger",
                {
                    "event": "on_power_played",
                    "label": "on_power_played_channel_lightning",
                    "effect": {
                        "behavior_key": "channel_orb",
                        "params": {"orb_type": "lightning", "amount": _parse_amount_token(m.group("amount"), variables)},
                    },
                },
            ),
        ),
        (
            re.compile(
                r"^Whenever you play a Power, gain (?P<amount>\{[^{}]+\})\.$",
                re.IGNORECASE,
            ),
            lambda m: (
                "add_trigger",
                {
                    "event": "on_power_played",
                    "label": "on_power_played_gain_energy",
                    "effect": {
                        "behavior_key": "gain_energy",
                        "params": {"amount": _parse_amount_token(m.group("amount"), variables)},
                    },
                },
            ),
        ),
        (
            re.compile(
                r"^Whenever you play a Colorless card, gain (?P<amount>(?:\d+|\{[^{}]+\})) Strength\.$",
                re.IGNORECASE,
            ),
            lambda m: (
                "add_trigger",
                {
                    "event": "on_card_played",
                    "label": "on_colorless_play_gain_strength",
                    "condition": {"type": "event_card_character_is", "value": "colorless"},
                    "effect": {
                        "behavior_key": "apply_buff",
                        "params": {"key": "strength", "amount": _parse_amount_token(m.group("amount"), variables), "target": "player"},
                    },
                },
            ),
        ),
        (
            re.compile(
                r"^Whenever you play an Ethereal card, gain (?P<amount>(?:\d+|\{[^{}]+\})) Block\.$",
                re.IGNORECASE,
            ),
            lambda m: (
                "add_trigger",
                {
                    "event": "on_card_played",
                    "label": "on_ethereal_play_gain_block",
                    "condition": {"type": "event_card_has_tag", "value": "ethereal"},
                    "effect": {
                        "behavior_key": "gain_block",
                        "params": {"amount": _parse_amount_token(m.group("amount"), variables)},
                    },
                },
            ),
        ),
        (
            re.compile(
                r"^Whenever you apply Vulnerable, draw (?P<amount>(?:\d+|\{[^{}]+\})) (?:card|cards|\{[^{}]+\})\.$",
                re.IGNORECASE,
            ),
            lambda m: (
                "add_trigger",
                {
                    "event": "on_debuff_applied",
                    "label": "on_apply_vulnerable_draw",
                    "condition": {"type": "event_debuff_key_is", "value": "vulnerable"},
                    "effect": {
                        "behavior_key": "draw_cards",
                        "params": {"amount": _parse_amount_token(m.group("amount"), variables)},
                    },
                },
            ),
        ),
        (
            re.compile(
                r"^Whenever you apply a debuff to an enemy, they take (?P<amount>(?:\d+|\{[^{}]+\})) damage\.$",
                re.IGNORECASE,
            ),
            lambda m: (
                "add_trigger",
                {
                    "event": "on_debuff_applied",
                    "label": "on_apply_debuff_deal_damage",
                    "effect": {
                        "behavior_key": "deal_damage",
                        "params": {"amount": _parse_amount_token(m.group("amount"), variables), "target": "enemy"},
                    },
                },
            ),
        ),
        (
            re.compile(
                r"^Whenever you gain Block, deal (?P<amount>(?:\d+|\{[^{}]+\})) damage to a random enemy\.$",
                re.IGNORECASE,
            ),
            lambda m: (
                "add_trigger",
                {
                    "event": "on_block_gained",
                    "label": "on_gain_block_deal_damage",
                    "effect": {
                        "behavior_key": "deal_damage",
                        "params": {"amount": _parse_amount_token(m.group("amount"), variables), "target": "enemy"},
                    },
                },
            ),
        ),
        (
            re.compile(
                r"^This turn, whenever you play an Attack, gain (?P<amount>(?:\d+|\{[^{}]+\})) Strength this turn\.$",
                re.IGNORECASE,
            ),
            lambda m: (
                "add_trigger",
                {
                    "event": "on_attack_played",
                    "label": "this_turn_play_attack_gain_temp_strength",
                    "expire_on_current_turn": True,
                    "effect": {
                        "behavior_key": "sequence",
                        "params": {
                            "effects": [
                                {
                                    "behavior_key": "apply_buff",
                                    "params": {"key": "strength", "amount": _parse_amount_token(m.group("amount"), variables), "target": "player"},
                                },
                                {
                                    "behavior_key": "schedule_effect",
                                    "params": {
                                        "delay_turns": 1,
                                        "label": "expire_attack_trigger_strength",
                                        "effect": {
                                            "behavior_key": "apply_buff",
                                            "params": {"key": "strength", "amount": -(_parse_amount_token(m.group("amount"), variables) or 0), "target": "player"},
                                        },
                                    },
                                },
                            ]
                        },
                    },
                },
            ),
        ),
        (
            re.compile(
                r"^Whenever you play a card this turn, gain (?P<amount>(?:\d+|\{[^{}]+\})) Strength this turn\.$",
                re.IGNORECASE,
            ),
            lambda m: (
                "add_trigger",
                {
                    "event": "on_card_played",
                    "label": "this_turn_play_card_gain_temp_strength",
                    "expire_on_current_turn": True,
                    "effect": {
                        "behavior_key": "sequence",
                        "params": {
                            "effects": [
                                {
                                    "behavior_key": "apply_buff",
                                    "params": {"key": "strength", "amount": _parse_amount_token(m.group("amount"), variables), "target": "player"},
                                },
                                {
                                    "behavior_key": "schedule_effect",
                                    "params": {
                                        "delay_turns": 1,
                                        "label": "expire_monologue_strength",
                                        "effect": {
                                            "behavior_key": "apply_buff",
                                            "params": {"key": "strength", "amount": -(_parse_amount_token(m.group("amount"), variables) or 0), "target": "player"},
                                        },
                                    },
                                },
                            ]
                        },
                    },
                },
            ),
        ),
        (
            re.compile(
                r"^Whenever you play a card that costs (?P<cost>\{[^{}]+\}) or more, gain (?P<amount>(?:\d+|\{[^{}]+\})) Block\.$",
                re.IGNORECASE,
            ),
            lambda m: (
                "add_trigger",
                {
                    "event": "on_card_played",
                    "label": "on_play_cost_gte_gain_block",
                    "condition": {"type": "event_card_cost_gte", "value": _parse_amount_token(m.group("cost"), variables)},
                    "effect": {
                        "behavior_key": "gain_block",
                        "params": {"amount": _parse_amount_token(m.group("amount"), variables)},
                    },
                },
            ),
        ),
    ]

    for pattern, builder in sequence_patterns:
        matched = pattern.match(text)
        if not matched:
            continue
        behavior_key, params = builder(matched)
        if _behavior_params_resolved(behavior_key, params):
            return behavior_key, params

    repeat_match = re.match(
        r"^Deal (?P<damage>(?:\d+|\{[^{}]+\})) damage (?P<repeat>(?:\d+|\{[^{}]+\})) (?:times|\{[^{}]+\})\.$",
        text,
        re.IGNORECASE,
    )
    if repeat_match:
        damage = _parse_amount_token(repeat_match.group("damage"), variables)
        repeat = _parse_repeat_token(repeat_match.group("repeat"), variables)
        if damage is not None and repeat is not None:
            return _sequence(*(("deal_damage", {"amount": damage}) for _ in range(repeat)))

    twice_match = re.match(
        r"^Deal (?P<damage>(?:\d+|\{[^{}]+\})) damage twice\.$",
        text,
        re.IGNORECASE,
    )
    if twice_match:
        damage = _parse_amount_token(twice_match.group("damage"), variables)
        if damage is not None:
            return _sequence(("deal_damage", {"amount": damage}), ("deal_damage", {"amount": damage}))

    passive_in_hand_match = re.match(
        r"^At the end of your turn, if this is in your Hand, (?P<verb>take|lose) (?P<amount>(?:\d+|\{[^{}]+\})) (?P<kind>damage|HP)\.$",
        text,
        re.IGNORECASE,
    )
    if passive_in_hand_match:
        amount = _parse_amount_token(passive_in_hand_match.group("amount"), variables)
        if amount is not None:
            return (
                "passive_in_hand_trigger",
                {
                    "event": "on_turn_end",
                    "label": "passive_in_hand_end_turn_hp_loss",
                    "effect": {
                        "behavior_key": "lose_hp",
                        "params": {"amount": amount, "target": "player"},
                    },
                    "reason": "passive in-hand end-turn HP loss is modeled separately from executable card play",
                },
            )

    return "unimplemented", {}


def _sequence_params_valid(params: dict[str, Any]) -> bool:
    effects = params.get("effects")
    if not isinstance(effects, list) or not effects:
        return False
    for effect in effects:
        if not isinstance(effect, dict):
            return False
        nested = effect.get("params")
        if not isinstance(nested, dict):
            return False
        for value in nested.values():
            if value is None:
                return False
    return True


def _add_trigger_params_valid(params: dict[str, Any]) -> bool:
    event = params.get("event")
    effect = params.get("effect")
    if not isinstance(event, str) or not event.strip():
        return False
    if not isinstance(effect, dict):
        return False
    nested_params = effect.get("params")
    if not isinstance(nested_params, dict):
        return False
    for value in nested_params.values():
        if value is None:
            return False
    return True


def _behavior_params_resolved(behavior_key: str, params: dict[str, Any]) -> bool:
    if behavior_key == "sequence":
        return _sequence_params_valid(params)
    if behavior_key == "add_trigger":
        return _add_trigger_params_valid(params)
    if behavior_key == "passive_in_hand_trigger":
        return _add_trigger_params_valid({"event": params.get("event"), "effect": params.get("effect")})
    for value in params.values():
        if value is None:
            return False
    return True


def _is_single_card_payload(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    card = payload.get("card")
    return isinstance(card, dict)


def _normalize_single_card(
    *,
    payload: dict[str, Any],
    file_path: Path,
    input_dir: Path,
    repo_root: Path,
    import_version: str,
) -> dict[str, Any]:
    card = payload["card"]

    card_id = card.get("key")
    if not isinstance(card_id, str) or not card_id.strip():
        raise ValueError("card.key must be a non-empty string")

    name_eng = card.get("name_eng")
    name_chs = card.get("name_chs")
    if isinstance(name_eng, str) and name_eng.strip():
        name = name_eng.strip()
    elif isinstance(name_chs, str) and name_chs.strip():
        name = name_chs.strip()
    else:
        raise ValueError("card name missing: expected name_eng or name_chs")

    category = card.get("category")
    if not isinstance(category, str) or not category.strip():
        raise ValueError("card.category must be a non-empty string")

    normalized = {
        "id": card_id.strip(),
        "name": name,
        "character": category.strip().lower(),
        "cost": _normalize_cost(card.get("cost")),
        "type": _normalize_type(card.get("type")),
        "rarity": _normalize_rarity(card.get("rarity")),
        "tags": _normalize_tags(card),
        "text": _pick_text(card),
        "behavior_key": "unimplemented",
        "params": {},
        "source": {
            "source_kind": "sts2_database",
            "game_version": payload.get("game_version"),
            "database_version": payload.get("database_version"),
            "targetType": card.get("targetType"),
            "name_chs": card.get("name_chs"),
            "name_eng": card.get("name_eng"),
            "text_raw_chs": card.get("text_raw_chs"),
            "text_raw_eng": card.get("text_raw_eng"),
            "text_default_chs": card.get("text_default_chs"),
            "text_default_eng": card.get("text_default_eng"),
            "text_upgraded_chs": card.get("text_upgraded_chs"),
            "text_upgraded_eng": card.get("text_upgraded_eng"),
            "variables": card.get("variables"),
            "upgrades": card.get("upgrades"),
            "original_file": _relative_path(file_path, input_dir),
            "source_file": _relative_path(file_path, repo_root),
            "import_version": import_version,
            "version": import_version,
            "importer": "tools/sts2_import/import_sts2_database.py",
            "schema_version": SCHEMA_VERSION,
        },
    }

    behavior_key, params = _infer_behavior(card)
    normalized["behavior_key"] = behavior_key
    normalized["params"] = params
    return normalized


def _collect_json_files(input_dir: Path) -> list[Path]:
    return sorted(path for path in input_dir.rglob("*.json") if path.is_file())


def _ensure_unique_ids(cards: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for card in cards:
        card_id = card["id"]
        if card_id in seen:
            duplicates.add(card_id)
        seen.add(card_id)
    if duplicates:
        joined = ", ".join(sorted(duplicates))
        raise ValueError(f"Duplicate normalized card id(s) detected: {joined}")


def main() -> None:
    args = parse_args()
    repo_root = _repo_root()

    input_dir = _resolve_input_dir(args.input_dir, repo_root)
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")
    if not input_dir.is_dir():
        raise NotADirectoryError(f"Input path is not a directory: {input_dir}")

    resolved_version = (args.version.strip() if isinstance(args.version, str) and args.version.strip() else "")
    if not resolved_version:
        resolved_version = input_dir.name or "sts2_database"

    output_path = _resolve_output_path(args.output, repo_root, resolved_version)

    all_json_files = _collect_json_files(input_dir)
    normalized_cards: list[dict[str, Any]] = []
    skipped: list[tuple[str, str]] = []

    for file_path in all_json_files:
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception as exc:
            skipped.append((_relative_path(file_path, input_dir), f"invalid JSON: {exc}"))
            continue

        if not _is_single_card_payload(payload):
            skipped.append((_relative_path(file_path, input_dir), "not STS2 single-card database format"))
            continue

        try:
            normalized = _normalize_single_card(
                payload=payload,
                file_path=file_path,
                input_dir=input_dir,
                repo_root=repo_root,
                import_version=resolved_version,
            )
        except ValueError as exc:
            skipped.append((_relative_path(file_path, input_dir), str(exc)))
            continue

        normalized_cards.append(normalized)

    if not normalized_cards:
        raise ValueError("No valid STS2 single-card database entries were imported")

    _ensure_unique_ids(normalized_cards)

    payload = {
        "schema_version": SCHEMA_VERSION,
        "card_count": len(normalized_cards),
        "cards": normalized_cards,
    }
    schema_path = repo_root / "data" / "sts2" / "normalized" / "cards.schema.json"
    _validate_output_payload(payload, schema_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    executable_cards = sum(
        1
        for card in normalized_cards
        if card["behavior_key"] in MAPPED_BEHAVIOR_KEYS
        and card["behavior_key"] != "passive_in_hand_trigger"
        and isinstance(card["cost"], int)
    )
    passive_modeled_cards = sum(1 for card in normalized_cards if card["behavior_key"] == "passive_in_hand_trigger")
    unimplemented_cards = sum(1 for card in normalized_cards if card["behavior_key"] == "unimplemented")

    print(f"input_dir={_relative_path(input_dir, repo_root)}")
    print(f"output_file={_relative_path(output_path, repo_root)}")
    print(f"total_files_scanned={len(all_json_files)}")
    print(f"valid_cards_imported={len(normalized_cards)}")
    print(f"skipped_files={len(skipped)}")
    print(f"executable_cards={executable_cards}")
    print(f"passive_modeled_cards={passive_modeled_cards}")
    print(f"unimplemented_cards={unimplemented_cards}")

    if skipped:
        preview = skipped[:10]
        print("skipped_file_samples:")
        for rel_path, reason in preview:
            print(f"  - {rel_path}: {reason}")
        if len(skipped) > len(preview):
            print(f"  - ... {len(skipped) - len(preview)} more")


if __name__ == "__main__":
    main()
