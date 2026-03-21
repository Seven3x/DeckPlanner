from __future__ import annotations

import json
from pathlib import Path

from slay2_ai.card_defs import build_demo_cards
from slay2_ai.demo import base_state
from slay2_ai.evaluator import evaluate_state
from slay2_ai.game_state import GameState
from slay2_ai.planner import PlayCardAction, legal_actions, search_best_sequence, simulate_play

from ..logging import GuiLogBus
from ..models import GuiStateSnapshot, SearchResultSnapshot


def _action_to_text(action: PlayCardAction) -> str:
    parts = [action.card_id]
    if action.discard_choices:
        parts.append(f"discard={list(action.discard_choices)}")
    if action.exhaust_choices:
        parts.append(f"exhaust={list(action.exhaust_choices)}")
    return " | ".join(parts)


class CoreGameService:
    """Thin adapter between Qt GUI and slay2_ai core logic."""

    def __init__(self, log_bus: GuiLogBus) -> None:
        self._log_bus = log_bus
        self._cards = build_demo_cards()
        self._state: GameState | None = None
        self._last_search: SearchResultSnapshot | None = None

    def run_demo(self) -> None:
        self._state = base_state(
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
        self._last_search = None

        self._log_bus.publish("event", "Demo 场景已载入。")
        self._log_bus.publish("event", f"当前手牌: {self._state.hand}")
        self._log_bus.publish("event", f"初始评分: {evaluate_state(self._state):.2f}")

    def get_state_snapshot(self) -> GuiStateSnapshot | None:
        if self._state is None:
            return None
        return GuiStateSnapshot.from_game_state(self._state)

    def get_search_snapshot(self) -> SearchResultSnapshot | None:
        return self._last_search

    def search_best_sequence(self, max_depth: int = 5, beam_width: int = 6) -> SearchResultSnapshot | None:
        if self._state is None:
            self.run_demo()

        assert self._state is not None
        result = search_best_sequence(
            state=self._state,
            cards=self._cards,
            max_depth=max_depth,
            beam_width=beam_width,
        )

        self._last_search = SearchResultSnapshot.from_plan_result(result)
        self._log_bus.publish("search", self._last_search.summary_text())

        trace_preview = self._last_search.trace[:20]
        for line in trace_preview:
            self._log_bus.publish("search", line)
        if len(self._last_search.trace) > len(trace_preview):
            self._log_bus.publish("search", "...trace 已截断显示（仅前20行）。")

        return self._last_search

    def execute_first_legal_action(self) -> None:
        if self._state is None:
            self.run_demo()

        assert self._state is not None
        actions = legal_actions(self._state, self._cards)
        if not actions:
            self._log_bus.publish("event", "当前无可执行动作。")
            return

        selected = actions[0]
        previous_enemy_hp = self._state.enemy_state.hp
        previous_block = self._state.block

        self._state = simulate_play(self._state, selected, self._cards)
        self._last_search = None

        self._log_bus.publish("effect", f"手动执行动作(占位): {_action_to_text(selected)}")
        self._log_bus.publish(
            "effect",
            (
                "状态变化: "
                f"EnemyHP {previous_enemy_hp}->{self._state.enemy_state.hp}; "
                f"Block {previous_block}->{self._state.block}; "
                f"Energy={self._state.energy}"
            ),
        )

    def refresh_state(self) -> None:
        if self._state is None:
            self._log_bus.publish("event", "当前没有运行中的状态，先点击“运行 demo”。")
            return
        self._log_bus.publish("event", "状态已刷新。")

    def load_json_file(self, file_path: str) -> bool:
        """Stage-1 placeholder: validates JSON and reserves conversion hook."""
        path = Path(file_path)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            self._log_bus.publish_exception(exc, context="加载 JSON 失败")
            return False

        if not isinstance(data, dict):
            self._log_bus.publish("error", "JSON 根节点需为对象(dict)。")
            return False

        self._log_bus.publish("event", f"已读取 JSON 文件: {path.name}")
        self._log_bus.publish("event", "JSON -> GameState 映射接口已预留，当前阶段尚未实现自动装载。")
        return False
