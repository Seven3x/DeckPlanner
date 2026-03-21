from __future__ import annotations

from dataclasses import dataclass

from slay2_ai.game_state import GameState
from slay2_ai.planner import PlanResult


def _format_counter_map(data: dict[str, int]) -> str:
    if not data:
        return "-"
    return ", ".join(f"{k}:{v}" for k, v in sorted(data.items()))


@dataclass(frozen=True)
class GuiStateSnapshot:
    turn_index: int
    player_hp: int
    player_max_hp: int
    energy: int
    block: int
    player_buffs_text: str
    player_debuffs_text: str
    enemy_hp: int
    enemy_max_hp: int
    enemy_block: int
    enemy_intent_damage: int
    enemy_buffs_text: str
    enemy_debuffs_text: str
    hand: list[str]
    draw_pile: list[str]
    discard_pile: list[str]
    exhaust_pile: list[str]
    pending_effects: list[str]
    triggers: list[str]

    @classmethod
    def from_game_state(cls, state: GameState) -> "GuiStateSnapshot":
        pending_rows = [
            f"T{pending.execute_turn} | {pending.label or '<no_label>'} | {type(pending.effect).__name__}"
            for pending in state.pending_effects
        ]
        trigger_rows = [
            (
                f"{trigger.event} | {trigger.label or '<no_label>'} | "
                f"uses={trigger.remaining_uses} | expire={trigger.expire_turn}"
            )
            for trigger in state.triggers
        ]

        return cls(
            turn_index=state.turn_index,
            player_hp=state.player_hp,
            player_max_hp=state.player_max_hp,
            energy=state.energy,
            block=state.block,
            player_buffs_text=_format_counter_map(state.buffs),
            player_debuffs_text=_format_counter_map(state.debuffs),
            enemy_hp=state.enemy_state.hp,
            enemy_max_hp=state.enemy_state.max_hp,
            enemy_block=state.enemy_state.block,
            enemy_intent_damage=state.enemy_state.intent_damage,
            enemy_buffs_text=_format_counter_map(state.enemy_state.buffs),
            enemy_debuffs_text=_format_counter_map(state.enemy_state.debuffs),
            hand=list(state.hand),
            draw_pile=list(state.draw_pile),
            discard_pile=list(state.discard_pile),
            exhaust_pile=list(state.exhaust_pile),
            pending_effects=pending_rows,
            triggers=trigger_rows,
        )


@dataclass(frozen=True)
class SearchResultSnapshot:
    sequence: list[str]
    score: float
    trace: list[str]

    @classmethod
    def from_plan_result(cls, result: PlanResult) -> "SearchResultSnapshot":
        return cls(sequence=list(result.sequence), score=result.score, trace=list(result.trace))

    def summary_text(self) -> str:
        sequence_text = " -> ".join(self.sequence) if self.sequence else "<pass>"
        return f"Score={self.score:.2f}; Sequence={sequence_text}"
