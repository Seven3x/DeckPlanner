from __future__ import annotations

import contextlib
import contextvars
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import slay2_ai.effects as effects_module
import slay2_ai.planner as planner_module
import slay2_ai.triggers as triggers_module
from slay2_ai.card_defs import CardDefinition, build_demo_cards
from slay2_ai.demo import base_state
from slay2_ai.evaluator import evaluate_state
from slay2_ai.game_state import GameState
from slay2_ai.planner import PlayCardAction, legal_actions, search_best_sequence, simulate_play

from ..logging import GuiLogBus
from ..models import (
    GuiStateSnapshot,
    SearchBranchViewModel,
    SearchResultSnapshot,
    SearchStepDetailViewModel,
    StateMetricsViewModel,
    format_effect_for_display,
)
from .json_state_adapter import JSON_STATE_SCHEMA_V1, JsonStateAdapter, JsonStateParseError


_ACTIVE_RECORDER: contextvars.ContextVar["RuntimeLogRecorder | None"] = contextvars.ContextVar(
    "slay2_gui_runtime_recorder",
    default=None,
)
_HOOKS_INSTALLED = False


def _action_to_text(action: PlayCardAction) -> str:
    parts = [action.card_id]
    if action.discard_choices:
        parts.append(f"discard={list(action.discard_choices)}")
    if action.exhaust_choices:
        parts.append(f"exhaust={list(action.exhaust_choices)}")
    return " | ".join(parts)


def _action_meta(action: PlayCardAction) -> list[str]:
    return [
        f"card_id={action.card_id}",
        f"discard_choices={list(action.discard_choices) if action.discard_choices else []}",
        f"exhaust_choices={list(action.exhaust_choices) if action.exhaust_choices else []}",
    ]


def _format_event_payload(payload: dict) -> str:
    if not payload:
        return "-"
    keys = [
        "card_id",
        "card_type",
        "target",
        "amount",
        "count",
        "raw_damage",
        "blocked_amount",
        "actual_hp_loss",
        "new_block",
        "label",
    ]
    parts: list[str] = []
    for key in keys:
        if key in payload:
            parts.append(f"{key}={payload[key]}")
    if "cards" in payload:
        parts.append(f"cards={list(payload['cards'])}")
    return ", ".join(parts) if parts else str(payload)


def _effect_source(ctx: dict) -> str:
    if ctx.get("event") == "pending":
        label = ctx.get("label", "")
        return f"pending({label})" if label else "pending"
    if "card_id" in ctx:
        if ctx.get("is_replay"):
            return f"replay:{ctx['card_id']}"
        return f"card:{ctx['card_id']}"
    event = ctx.get("event")
    if isinstance(event, str) and event.startswith("on_"):
        return f"trigger:{event}"
    return "effect"


def _counter_delta(label: str, before: dict[str, int], after: dict[str, int]) -> list[str]:
    lines: list[str] = []
    keys = sorted(set(before) | set(after))
    for key in keys:
        b = before.get(key, 0)
        a = after.get(key, 0)
        if a == b:
            continue
        lines.append(f"{label}.{key}: {b} -> {a} (Δ{a - b:+d})")
    return lines


def _card_count_delta(label: str, before: list[str], after: list[str]) -> list[str]:
    before_counter = Counter(before)
    after_counter = Counter(after)
    lines: list[str] = []
    for card_id in sorted(set(before_counter) | set(after_counter)):
        b = before_counter.get(card_id, 0)
        a = after_counter.get(card_id, 0)
        if a == b:
            continue
        lines.append(f"{label}.{card_id}: {b} -> {a} (Δ{a - b:+d})")
    return lines


def _state_metrics(state: GameState) -> StateMetricsViewModel:
    return StateMetricsViewModel(
        player_hp=state.player_hp,
        player_max_hp=state.player_max_hp,
        player_block=state.block,
        player_energy=state.energy,
        enemy_hp=state.enemy_state.hp,
        enemy_max_hp=state.enemy_state.max_hp,
        enemy_block=state.enemy_state.block,
        enemy_intent_damage=state.enemy_state.intent_damage,
        hand_count=len(state.hand),
        draw_count=len(state.draw_pile),
        discard_count=len(state.discard_pile),
        exhaust_count=len(state.exhaust_pile),
        pending_count=len(state.pending_effects),
        trigger_count=len(state.triggers),
    )


def _state_summary(state: GameState) -> str:
    return f"T={state.turn_index}; {_state_metrics(state).summary_text()}"


def _describe_key_changes(before: GameState, after: GameState) -> list[str]:
    lines: list[str] = []

    scalar_rows = [
        ("player_hp", before.player_hp, after.player_hp),
        ("player_energy", before.energy, after.energy),
        ("player_block", before.block, after.block),
        ("enemy_hp", before.enemy_state.hp, after.enemy_state.hp),
        ("enemy_block", before.enemy_state.block, after.enemy_state.block),
        ("enemy_intent_damage", before.enemy_state.intent_damage, after.enemy_state.intent_damage),
        ("turn_index", before.turn_index, after.turn_index),
        ("attack_count_this_turn", before.attack_count_this_turn, after.attack_count_this_turn),
        ("skill_count_this_turn", before.skill_count_this_turn, after.skill_count_this_turn),
    ]
    for label, before_value, after_value in scalar_rows:
        if before_value != after_value:
            lines.append(f"{label}: {before_value} -> {after_value} (Δ{after_value - before_value:+d})")

    count_rows = [
        ("hand_count", len(before.hand), len(after.hand)),
        ("draw_count", len(before.draw_pile), len(after.draw_pile)),
        ("discard_count", len(before.discard_pile), len(after.discard_pile)),
        ("exhaust_count", len(before.exhaust_pile), len(after.exhaust_pile)),
        ("pending_count", len(before.pending_effects), len(after.pending_effects)),
        ("trigger_count", len(before.triggers), len(after.triggers)),
    ]
    for label, before_value, after_value in count_rows:
        if before_value != after_value:
            lines.append(f"{label}: {before_value} -> {after_value} (Δ{after_value - before_value:+d})")

    lines.extend(_counter_delta("player_buff", before.buffs, after.buffs))
    lines.extend(_counter_delta("player_debuff", before.debuffs, after.debuffs))
    lines.extend(_counter_delta("enemy_buff", before.enemy_state.buffs, after.enemy_state.buffs))
    lines.extend(_counter_delta("enemy_debuff", before.enemy_state.debuffs, after.enemy_state.debuffs))

    lines.extend(_card_count_delta("hand", before.hand, after.hand))
    lines.extend(_card_count_delta("draw", before.draw_pile, after.draw_pile))
    lines.extend(_card_count_delta("discard", before.discard_pile, after.discard_pile))
    lines.extend(_card_count_delta("exhaust", before.exhaust_pile, after.exhaust_pile))

    return lines


def _pending_signature(state: GameState) -> set[tuple]:
    return {
        (
            row.execute_turn,
            row.label,
            format_effect_for_display(row.effect),
        )
        for row in state.pending_effects
    }


def _trigger_signature(state: GameState) -> set[tuple]:
    return {
        (
            row.event,
            row.label,
            row.remaining_uses,
            row.expire_turn,
            format_effect_for_display(row.effect),
        )
        for row in state.triggers
    }


def _describe_pending_delta(before: GameState, after: GameState) -> list[str]:
    before_sig = _pending_signature(before)
    after_sig = _pending_signature(after)
    lines: list[str] = []

    for row in sorted(after_sig - before_sig):
        execute_turn, label, effect_text = row
        lines.append(f"+ T{execute_turn} {label or '<no_label>'}: {effect_text}")
    for row in sorted(before_sig - after_sig):
        execute_turn, label, effect_text = row
        lines.append(f"- T{execute_turn} {label or '<no_label>'}: {effect_text}")
    return lines


def _describe_trigger_delta(before: GameState, after: GameState) -> list[str]:
    before_sig = _trigger_signature(before)
    after_sig = _trigger_signature(after)
    lines: list[str] = []

    for row in sorted(after_sig - before_sig):
        event, label, uses, expire, effect_text = row
        lines.append(
            f"+ {label or '<no_label>'} ({event}, uses={uses}, expire={expire}) -> {effect_text}"
        )
    for row in sorted(before_sig - after_sig):
        event, label, uses, expire, effect_text = row
        lines.append(
            f"- {label or '<no_label>'} ({event}, uses={uses}, expire={expire}) -> {effect_text}"
        )
    return lines


def _log_snippets(event_logs: list[str], effect_logs: list[str], max_items: int = 10) -> list[str]:
    rows = [f"EVENT {line}" for line in event_logs] + [f"EFFECT {line}" for line in effect_logs]
    return rows[:max_items]


@dataclass
class RuntimeLogRecorder:
    event_logs: list[str]
    effect_logs: list[str]

    def __init__(self) -> None:
        self.event_logs = []
        self.effect_logs = []

    def record_event(self, event: str, payload: dict) -> None:
        self.event_logs.append(f"Event[{event}] {_format_event_payload(payload)}")

    def record_effect(self, effect: object, ctx: dict) -> None:
        source = _effect_source(ctx)
        self.effect_logs.append(f"{source} -> {format_effect_for_display(effect)}")


def _install_runtime_hooks() -> None:
    global _HOOKS_INSTALLED
    if _HOOKS_INSTALLED:
        return

    original_emit_event = triggers_module.emit_event

    def emit_event_with_recorder(state: GameState, event: str, payload: dict | None = None) -> None:
        recorder = _ACTIVE_RECORDER.get()
        if recorder is not None:
            recorder.record_event(event, dict(payload or {}))
        original_emit_event(state, event, payload)

    triggers_module.emit_event = emit_event_with_recorder
    planner_module.emit_event = emit_event_with_recorder

    effect_classes = [
        effects_module.DealDamage,
        effects_module.GainBlock,
        effects_module.DrawCards,
        effects_module.GainEnergy,
        effects_module.ApplyBuff,
        effects_module.ApplyDebuff,
        effects_module.AddTriggerEffect,
        effects_module.ScheduleEffect,
        effects_module.SetNextAttackBonus,
        effects_module.SetReplayNextCard,
        effects_module.DiscardCards,
        effects_module.ExhaustFromHand,
        effects_module.Conditional,
    ]

    for effect_cls in effect_classes:
        original_apply = effect_cls.apply

        def wrapped_apply(self, state: GameState, ctx: dict, _orig: Callable = original_apply):
            recorder = _ACTIVE_RECORDER.get()
            if recorder is not None:
                recorder.record_effect(self, ctx)
            return _orig(self, state, ctx)

        effect_cls.apply = wrapped_apply

    _HOOKS_INSTALLED = True


@contextlib.contextmanager
def _record_runtime(recorder: RuntimeLogRecorder):
    token = _ACTIVE_RECORDER.set(recorder)
    try:
        yield
    finally:
        _ACTIVE_RECORDER.reset(token)


class CoreGameService:
    """Thin adapter between Qt GUI and slay2_ai core logic."""

    def __init__(self, log_bus: GuiLogBus) -> None:
        self._log_bus = log_bus
        self._cards: dict[str, CardDefinition] = build_demo_cards()
        self._json_adapter = JsonStateAdapter(self._cards)
        self._state: GameState | None = None
        self._last_search: SearchResultSnapshot | None = None
        _install_runtime_hooks()

    def _replace_state(
        self,
        state: GameState,
        source: str,
        reset_search: bool = True,
        warnings: list[str] | None = None,
    ) -> None:
        self._state = state
        if reset_search:
            self._last_search = None
            self._log_bus.publish("search", "搜索结果已重置。")

        self._log_bus.publish("event", f"状态入口: {source}")
        self._log_bus.publish("event", _state_summary(state))

        for warning in warnings or []:
            self._log_bus.publish("error", f"JSON 警告: {warning}")

    def _ensure_state(self) -> GameState:
        if self._state is None:
            self.run_demo()
        assert self._state is not None
        return self._state

    def run_demo(self) -> None:
        state = base_state(
            hand=["echo_spell", "sharpen", "combo_slash", "bank_energy", "jab"],
            draw_pile=[
                "strike",
                "defend",
                "insight",
                "prepared_stance",
                "burn_memory",
                "desperate_blow",
                "purge_tactics",
            ],
            enemy_hp=52,
            intent_damage=10,
            energy=3,
        )
        self._replace_state(state, source="demo")

    def get_state_snapshot(self) -> GuiStateSnapshot | None:
        if self._state is None:
            return None
        return GuiStateSnapshot.from_game_state(self._state, self._cards)

    def get_search_snapshot(self) -> SearchResultSnapshot | None:
        return self._last_search

    def list_manual_play_options(self) -> list[tuple[str, str]]:
        state = self._state
        if state is None:
            return []

        actions = legal_actions(state, self._cards)
        options: list[tuple[str, str]] = []
        seen: set[str] = set()
        variant_counter: dict[str, int] = {}
        for action in actions:
            variant_counter[action.card_id] = variant_counter.get(action.card_id, 0) + 1

        for card_id in state.hand:
            if card_id in seen:
                continue
            seen.add(card_id)
            card = self._cards.get(card_id)
            card_name = card.name if card else card_id
            variants = variant_counter.get(card_id, 0)
            if variants > 1:
                suffix = f" (分支{variants})"
            elif variants == 1:
                suffix = ""
            else:
                suffix = " (当前不可执行)"
            options.append((card_id, f"{card_name} [{card_id}]{suffix}"))
        return options

    def search_best_sequence(self, max_depth: int = 5, beam_width: int = 6) -> SearchResultSnapshot | None:
        state = self._ensure_state()

        self._log_bus.publish(
            "search",
            f"开始搜索: depth={max_depth}, beam={beam_width}, 当前评分={evaluate_state(state):.2f}",
        )

        result = search_best_sequence(
            state=state,
            cards=self._cards,
            max_depth=max_depth,
            beam_width=beam_width,
        )

        recommended_step_details, _ = self._build_step_details_for_sequence(state, result.sequence)
        candidate_branches = self._build_candidate_branches(
            max_depth=max_depth,
            beam_width=beam_width,
            limit=max(3, beam_width),
        )

        self._last_search = SearchResultSnapshot.from_plan_result(
            result=result,
            recommended_step_details=recommended_step_details,
            candidate_branches=candidate_branches,
        )

        self._log_bus.publish("search", self._last_search.summary_text())
        for line in self._last_search.trace[:24]:
            self._log_bus.publish("search", line)
        if len(self._last_search.trace) > 24:
            self._log_bus.publish("search", "trace 已截断显示（仅前24行）。")

        return self._last_search

    def _find_action_by_label(self, state: GameState, action_label: str) -> PlayCardAction | None:
        for action in legal_actions(state, self._cards):
            if _action_to_text(action) == action_label:
                return action
        return None

    def _run_action_with_runtime_logs(
        self,
        state: GameState,
        action: PlayCardAction,
    ) -> tuple[GameState, RuntimeLogRecorder]:
        recorder = RuntimeLogRecorder()
        with _record_runtime(recorder):
            after_state = simulate_play(state, action, self._cards)
        return after_state, recorder

    def _build_step_details_for_sequence(
        self,
        start_state: GameState,
        action_labels: list[str],
    ) -> tuple[list[SearchStepDetailViewModel], GameState]:
        details: list[SearchStepDetailViewModel] = []
        rolling_state = start_state.clone()

        for idx, action_label in enumerate(action_labels):
            action = self._find_action_by_label(rolling_state, action_label)
            if action is None:
                details.append(
                    SearchStepDetailViewModel(
                        step_index=idx,
                        action_text=action_label,
                        before_summary=_state_summary(rolling_state),
                        after_summary=_state_summary(rolling_state),
                        score_before=evaluate_state(rolling_state),
                        score_after=evaluate_state(rolling_state),
                        notes=["当前状态无法复原该动作，详情基于已知序列标签。"],
                    )
                )
                break

            before_state = rolling_state.clone()
            after_state, recorder = self._run_action_with_runtime_logs(rolling_state, action)
            details.append(
                SearchStepDetailViewModel(
                    step_index=idx,
                    action_text=action_label,
                    before_summary=_state_summary(before_state),
                    after_summary=_state_summary(after_state),
                    score_before=evaluate_state(before_state),
                    score_after=evaluate_state(after_state),
                    action_meta=_action_meta(action),
                    key_changes=_describe_key_changes(before_state, after_state),
                    event_logs=list(recorder.event_logs),
                    effect_logs=list(recorder.effect_logs),
                    pending_changes=_describe_pending_delta(before_state, after_state),
                    trigger_changes=_describe_trigger_delta(before_state, after_state),
                    related_log_snippets=_log_snippets(recorder.event_logs, recorder.effect_logs),
                )
            )
            rolling_state = after_state

        return details, rolling_state

    def _build_candidate_branches(
        self,
        max_depth: int,
        beam_width: int,
        limit: int,
    ) -> list[SearchBranchViewModel]:
        state = self._ensure_state()
        actions = legal_actions(state, self._cards)
        if not actions:
            return []

        branches: list[SearchBranchViewModel] = []
        total = len(actions)
        for index, first_action in enumerate(actions):
            label = _action_to_text(first_action)
            self._log_bus.publish("search", f"评估候选起手 {index + 1}/{total}: {label}")

            first_state = simulate_play(state, first_action, self._cards)
            tail_result = search_best_sequence(
                state=first_state,
                cards=self._cards,
                max_depth=max(0, max_depth - 1),
                beam_width=beam_width,
            )
            sequence = [label] + list(tail_result.sequence)
            step_details, final_state = self._build_step_details_for_sequence(state, sequence)

            branches.append(
                SearchBranchViewModel(
                    branch_label=f"候选 {index + 1}",
                    score=tail_result.score,
                    actions=sequence,
                    step_summaries=[row.summary_text() for row in step_details],
                    step_details=step_details,
                    final_state_summary=_state_summary(final_state),
                    final_metrics=_state_metrics(final_state),
                )
            )

        branches.sort(key=lambda row: row.score, reverse=True)
        return branches[:limit]

    def execute_manual_action(self, card_id: str) -> bool:
        state = self._ensure_state()
        actions = [action for action in legal_actions(state, self._cards) if action.card_id == card_id]
        if not actions:
            self._log_bus.publish("event", f"卡牌 {card_id} 当前不可执行。")
            return False

        selected = actions[0]
        if len(actions) > 1:
            self._log_bus.publish(
                "event",
                f"卡牌 {card_id} 存在 {len(actions)} 个合法分支，当前阶段自动采用第一种。",
            )

        before_state = state.clone()
        next_state, recorder = self._run_action_with_runtime_logs(state, selected)
        detail = SearchStepDetailViewModel(
            step_index=0,
            action_text=_action_to_text(selected),
            before_summary=_state_summary(before_state),
            after_summary=_state_summary(next_state),
            score_before=evaluate_state(before_state),
            score_after=evaluate_state(next_state),
            action_meta=_action_meta(selected),
            key_changes=_describe_key_changes(before_state, next_state),
            event_logs=list(recorder.event_logs),
            effect_logs=list(recorder.effect_logs),
            pending_changes=_describe_pending_delta(before_state, next_state),
            trigger_changes=_describe_trigger_delta(before_state, next_state),
            related_log_snippets=_log_snippets(recorder.event_logs, recorder.effect_logs),
        )

        self._replace_state(
            next_state,
            source=f"manual_action:{_action_to_text(selected)}",
            reset_search=True,
        )

        self._log_bus.publish("event", f"手动打牌: {_action_to_text(selected)}")
        self._log_bus.publish("event", f"评分变化: {detail.score_before:.2f} -> {detail.score_after:.2f}")
        for row in detail.key_changes:
            self._log_bus.publish("event", f"关键变化: {row}")
        for row in detail.event_logs:
            self._log_bus.publish("event", row)
        for row in detail.effect_logs:
            self._log_bus.publish("effect", row)
        for row in detail.pending_changes:
            self._log_bus.publish("effect", f"Pending {row}")
        for row in detail.trigger_changes:
            self._log_bus.publish("effect", f"Trigger {row}")
        if not detail.effect_logs:
            self._log_bus.publish("effect", "本次动作没有效果执行日志。")

        return True

    def refresh_state(self) -> None:
        if self._state is None:
            self._log_bus.publish("event", "当前没有运行中的状态，可先点击“运行 demo”或“加载 JSON”。")
            return
        self._log_bus.publish("event", f"状态已刷新。{_state_summary(self._state)}")

    def load_json_file(self, file_path: str) -> bool:
        path = Path(file_path)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            parse_result = self._json_adapter.parse(data)
        except JsonStateParseError as exc:
            self._log_bus.publish("error", f"JSON 解析失败: {exc}")
            return False
        except Exception as exc:  # noqa: BLE001
            self._log_bus.publish_exception(exc, context="加载 JSON 失败")
            return False

        self._replace_state(
            parse_result.state,
            source=f"json:{path.name}",
            reset_search=True,
            warnings=parse_result.warnings,
        )
        self._log_bus.publish(
            "event",
            f"JSON 状态已载入: {path.name} (schema={parse_result.schema_version or JSON_STATE_SCHEMA_V1})",
        )
        self._log_bus.publish(
            "event",
            "当前 JSON 触发器 condition 支持: always / player_hp_ratio_lte / attack_count_before_gte。"
            "未支持条件会按 always（trigger）或 if_false（Conditional）兼容处理。",
        )
        return True
