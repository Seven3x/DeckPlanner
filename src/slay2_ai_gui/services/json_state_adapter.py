from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from slay2_ai.card_defs import CardDefinition
from slay2_ai.effects import (
    AddTriggerEffect,
    ApplyBuff,
    ApplyDebuff,
    Conditional,
    DealDamage,
    DiscardCards,
    DrawCards,
    ExhaustFromHand,
    GainBlock,
    GainEnergy,
    ScheduleEffect,
    SetNextAttackBonus,
    SetReplayNextCard,
)
from slay2_ai.game_state import EnemyState, GameState, PendingEffect
from slay2_ai.triggers import SUPPORTED_EVENTS, Trigger


JSON_STATE_SCHEMA_V1 = "slay2_gui_state.v1"


class JsonStateParseError(ValueError):
    pass


@dataclass(frozen=True)
class JsonStateParseResult:
    state: GameState
    warnings: list[str]
    schema_version: str


class JsonStateAdapter:
    """Parse JSON payload into GameState with minimal assumptions.

    Supported schema version:
    - slay2_gui_state.v1
    """

    def __init__(self, cards: dict[str, CardDefinition]) -> None:
        self._cards = cards
        self._warnings: list[str] = []

    def parse(self, payload: dict) -> JsonStateParseResult:
        self._warnings = []
        if not isinstance(payload, dict):
            raise JsonStateParseError("JSON 根节点需为对象(dict)。")

        schema_version = payload.get("schema_version", JSON_STATE_SCHEMA_V1)
        if not isinstance(schema_version, str):
            raise JsonStateParseError("schema_version 必须是字符串。")
        if schema_version != JSON_STATE_SCHEMA_V1:
            self._warnings.append(
                f"schema_version={schema_version} 与当前适配器({JSON_STATE_SCHEMA_V1})不一致，按兼容模式解析。"
            )

        player = self._required_mapping(payload, "player", "root")
        enemy = self._required_mapping(payload, "enemy", "root")
        zones = self._required_mapping(payload, "zones", "root")
        turn = self._optional_mapping(payload, "turn", "root")

        hand = self._card_list(zones, "hand", "root.zones")
        draw_pile = self._card_list(zones, "draw_pile", "root.zones")
        discard_pile = self._card_list(zones, "discard_pile", "root.zones")
        exhaust_pile = self._card_list(zones, "exhaust_pile", "root.zones")
        self._validate_card_ids(hand + draw_pile + discard_pile + exhaust_pile)

        pending_rows = self._optional_list(payload, "pending_effects", "root")
        pending_effects = [
            self._parse_pending(row, f"root.pending_effects[{idx}]")
            for idx, row in enumerate(pending_rows)
        ]

        trigger_rows = self._optional_list(payload, "triggers", "root")
        triggers = [self._parse_trigger(row, f"root.triggers[{idx}]") for idx, row in enumerate(trigger_rows)]

        state = GameState(
            player_hp=self._required_int(player, "hp", "root.player"),
            player_max_hp=self._required_int(player, "max_hp", "root.player"),
            energy=self._required_int(player, "energy", "root.player"),
            block=self._required_int(player, "block", "root.player"),
            buffs=self._counter_map(player, "buffs", "root.player"),
            debuffs=self._counter_map(player, "debuffs", "root.player"),
            hand=hand,
            draw_pile=draw_pile,
            discard_pile=discard_pile,
            exhaust_pile=exhaust_pile,
            turn_index=self._optional_int(turn, "turn_index", "root.turn", default=1),
            cards_played_this_turn=self._string_list(
                turn.get("cards_played_this_turn", []), "root.turn.cards_played_this_turn"
            ),
            attack_count_this_turn=self._optional_int(
                turn, "attack_count_this_turn", "root.turn", default=0
            ),
            skill_count_this_turn=self._optional_int(
                turn, "skill_count_this_turn", "root.turn", default=0
            ),
            pending_effects=pending_effects,
            triggers=triggers,
            enemy_state=EnemyState(
                hp=self._required_int(enemy, "hp", "root.enemy"),
                max_hp=self._required_int(enemy, "max_hp", "root.enemy"),
                block=self._required_int(enemy, "block", "root.enemy"),
                intent_damage=self._required_int(enemy, "intent_damage", "root.enemy"),
                buffs=self._counter_map(enemy, "buffs", "root.enemy"),
                debuffs=self._counter_map(enemy, "debuffs", "root.enemy"),
            ),
            rng_seed=self._optional_int(turn, "rng_seed", "root.turn", default=0),
        )
        return JsonStateParseResult(
            state=state,
            warnings=list(self._warnings),
            schema_version=schema_version,
        )

    def _parse_pending(self, raw_row: object, path: str) -> PendingEffect:
        row = self._as_mapping(raw_row, path)
        effect_row = self._required_mapping(row, "effect", path)
        return PendingEffect(
            execute_turn=self._required_int(row, "execute_turn", path),
            label=self._optional_str(row, "label", path, default=""),
            effect=self._parse_effect(effect_row, f"{path}.effect"),
        )

    def _parse_trigger(self, raw_row: object, path: str) -> Trigger:
        row = self._as_mapping(raw_row, path)
        event = self._required_str(row, "event", path)
        if event not in SUPPORTED_EVENTS:
            raise JsonStateParseError(f"{path}.event 不受支持: {event}")

        effect_row = self._required_mapping(row, "effect", path)
        condition = self._parse_trigger_condition(row.get("condition"), f"{path}.condition")

        remaining = row.get("remaining_uses", 1)
        if remaining is not None:
            remaining = self._as_int(remaining, f"{path}.remaining_uses")

        expire_turn = row.get("expire_turn")
        if expire_turn is not None:
            expire_turn = self._as_int(expire_turn, f"{path}.expire_turn")

        return Trigger(
            event=event,
            effect=self._parse_effect(effect_row, f"{path}.effect"),
            condition=condition,
            remaining_uses=remaining,
            expire_turn=expire_turn,
            label=self._optional_str(row, "label", path, default=""),
        )

    def _parse_effect(self, row: dict, path: str) -> object:
        effect_type = self._required_str(row, "type", path)

        if effect_type == "DealDamage":
            return DealDamage(
                amount=self._required_int(row, "amount", path),
                target=self._optional_str(row, "target", path, default="enemy"),
            )
        if effect_type == "GainBlock":
            return GainBlock(amount=self._required_int(row, "amount", path))
        if effect_type == "DrawCards":
            return DrawCards(amount=self._required_int(row, "amount", path))
        if effect_type == "GainEnergy":
            return GainEnergy(amount=self._required_int(row, "amount", path))
        if effect_type == "ApplyBuff":
            return ApplyBuff(
                key=self._required_str(row, "key", path),
                amount=self._required_int(row, "amount", path),
                target=self._optional_str(row, "target", path, default="player"),
            )
        if effect_type == "ApplyDebuff":
            return ApplyDebuff(
                key=self._required_str(row, "key", path),
                amount=self._required_int(row, "amount", path),
                target=self._optional_str(row, "target", path, default="enemy"),
            )
        if effect_type == "SetNextAttackBonus":
            return SetNextAttackBonus(amount=self._required_int(row, "amount", path))
        if effect_type == "SetReplayNextCard":
            return SetReplayNextCard(charges=self._optional_int(row, "charges", path, default=1))
        if effect_type == "DiscardCards":
            return DiscardCards(amount=self._required_int(row, "amount", path))
        if effect_type == "ExhaustFromHand":
            return ExhaustFromHand(amount=self._required_int(row, "amount", path))
        if effect_type == "ScheduleEffect":
            inner = self._required_mapping(row, "effect", path)
            return ScheduleEffect(
                effect=self._parse_effect(inner, f"{path}.effect"),
                delay_turns=self._required_int(row, "delay_turns", path),
                label=self._optional_str(row, "label", path, default=""),
            )
        if effect_type == "Conditional":
            condition = self._parse_conditional_condition(row.get("condition"), f"{path}.condition")
            if_true_rows = self._optional_list(row, "if_true", path)
            if_false_rows = self._optional_list(row, "if_false", path)
            return Conditional(
                condition=condition,
                if_true=[
                    self._parse_effect(self._as_mapping(item, f"{path}.if_true[{idx}]"), f"{path}.if_true[{idx}]")
                    for idx, item in enumerate(if_true_rows)
                ],
                if_false=[
                    self._parse_effect(
                        self._as_mapping(item, f"{path}.if_false[{idx}]"),
                        f"{path}.if_false[{idx}]",
                    )
                    for idx, item in enumerate(if_false_rows)
                ],
            )
        if effect_type == "AddTriggerEffect":
            trigger_spec = self._required_mapping(row, "trigger", path)
            return AddTriggerEffect(
                trigger=self._parse_trigger(trigger_spec, f"{path}.trigger"),
                expire_on_current_turn=self._optional_bool(
                    row, "expire_on_current_turn", path, default=False
                ),
            )

        raise JsonStateParseError(f"{path}.type 暂不支持: {effect_type}")

    def _parse_trigger_condition(
        self,
        raw_condition: object,
        path: str,
    ) -> Callable[[GameState, dict], bool] | None:
        if raw_condition is None:
            return None
        if isinstance(raw_condition, str):
            if raw_condition == "always":
                return None
            self._warnings.append(f"{path} 使用了未支持字符串条件 {raw_condition}，按 always 处理。")
            return None

        if not isinstance(raw_condition, dict):
            self._warnings.append(f"{path} 条件格式非法，按 always 处理。")
            return None

        condition_type = raw_condition.get("type")
        if condition_type == "always":
            return None

        if condition_type == "player_hp_ratio_lte":
            ratio = self._as_float(raw_condition.get("value"), f"{path}.value")

            def hp_ratio_lte(state: GameState, ctx: dict) -> bool:
                del ctx
                return state.player_hp / max(1, state.player_max_hp) <= ratio

            hp_ratio_lte.__name__ = f"json_player_hp_ratio_lte_{ratio}"
            return hp_ratio_lte

        if condition_type == "attack_count_before_gte":
            threshold = self._as_int(raw_condition.get("value"), f"{path}.value")

            def attack_count_before_gte(state: GameState, ctx: dict) -> bool:
                del state
                return int(ctx.get("attack_count_before", 0)) >= threshold

            attack_count_before_gte.__name__ = f"json_attack_count_before_gte_{threshold}"
            return attack_count_before_gte

        self._warnings.append(f"{path} 条件类型 {condition_type} 未支持，按 always 处理。")
        return None

    def _parse_conditional_condition(
        self,
        raw_condition: object,
        path: str,
    ) -> Callable[[GameState, dict], bool]:
        parsed = self._parse_trigger_condition(raw_condition, path)
        if parsed is not None:
            return parsed

        # Conditional 无法使用 None condition，这里给一个保守默认值并留 warning。
        self._warnings.append(f"{path} 未提供可执行条件，Conditional 默认走 if_false 分支。")

        def always_false(state: GameState, ctx: dict) -> bool:
            del state, ctx
            return False

        always_false.__name__ = "json_always_false"
        return always_false

    def _counter_map(self, src: dict, key: str, path: str) -> dict[str, int]:
        raw = src.get(key, {})
        if raw is None:
            return {}
        if not isinstance(raw, dict):
            raise JsonStateParseError(f"{path}.{key} 必须是对象。")
        result: dict[str, int] = {}
        for raw_key, raw_value in raw.items():
            if not isinstance(raw_key, str):
                raise JsonStateParseError(f"{path}.{key} 的键必须是字符串。")
            result[raw_key] = self._as_int(raw_value, f"{path}.{key}.{raw_key}")
        return result

    def _card_list(self, src: dict, key: str, path: str) -> list[str]:
        return self._string_list(src.get(key, []), f"{path}.{key}")

    def _validate_card_ids(self, card_ids: list[str]) -> None:
        unknown = sorted({card_id for card_id in card_ids if card_id not in self._cards})
        if unknown:
            raise JsonStateParseError(f"JSON 中存在未知 card_id: {unknown}")

    def _required_mapping(self, src: dict, key: str, path: str) -> dict:
        if key not in src:
            raise JsonStateParseError(f"{path}.{key} 缺失。")
        return self._as_mapping(src[key], f"{path}.{key}")

    def _optional_mapping(self, src: dict, key: str, path: str) -> dict:
        raw = src.get(key, {})
        if raw is None:
            return {}
        return self._as_mapping(raw, f"{path}.{key}")

    def _required_int(self, src: dict, key: str, path: str) -> int:
        if key not in src:
            raise JsonStateParseError(f"{path}.{key} 缺失。")
        return self._as_int(src[key], f"{path}.{key}")

    def _optional_int(self, src: dict, key: str, path: str, default: int) -> int:
        if key not in src:
            return default
        return self._as_int(src[key], f"{path}.{key}")

    def _required_str(self, src: dict, key: str, path: str) -> str:
        if key not in src:
            raise JsonStateParseError(f"{path}.{key} 缺失。")
        value = src[key]
        if not isinstance(value, str):
            raise JsonStateParseError(f"{path}.{key} 必须是字符串。")
        return value

    def _optional_str(self, src: dict, key: str, path: str, default: str) -> str:
        if key not in src:
            return default
        value = src[key]
        if not isinstance(value, str):
            raise JsonStateParseError(f"{path}.{key} 必须是字符串。")
        return value

    def _optional_bool(self, src: dict, key: str, path: str, default: bool) -> bool:
        if key not in src:
            return default
        value = src[key]
        if not isinstance(value, bool):
            raise JsonStateParseError(f"{path}.{key} 必须是布尔值。")
        return value

    def _optional_list(self, src: dict, key: str, path: str) -> list:
        raw = src.get(key, [])
        if raw is None:
            return []
        if not isinstance(raw, list):
            raise JsonStateParseError(f"{path}.{key} 必须是数组。")
        return raw

    def _string_list(self, raw: object, path: str) -> list[str]:
        if raw is None:
            return []
        if not isinstance(raw, list):
            raise JsonStateParseError(f"{path} 必须是字符串数组。")
        rows: list[str] = []
        for idx, value in enumerate(raw):
            if not isinstance(value, str):
                raise JsonStateParseError(f"{path}[{idx}] 必须是字符串。")
            rows.append(value)
        return rows

    def _as_mapping(self, raw: object, path: str) -> dict:
        if not isinstance(raw, dict):
            raise JsonStateParseError(f"{path} 必须是对象。")
        return raw

    def _as_int(self, raw: object, path: str) -> int:
        if isinstance(raw, bool) or not isinstance(raw, int):
            raise JsonStateParseError(f"{path} 必须是整数。")
        return raw

    def _as_float(self, raw: object, path: str) -> float:
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise JsonStateParseError(f"{path} 必须是数值。")
        return float(raw)
