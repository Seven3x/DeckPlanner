from __future__ import annotations

from dataclasses import dataclass, field
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
from slay2_ai.game_state import GameState
from slay2_ai.planner import PlanResult


def _format_counter_map(data: dict[str, int]) -> list[str]:
    if not data:
        return []
    return [f"{k}: {v}" for k, v in sorted(data.items())]


def _callable_name(fn: Callable | None) -> str:
    if fn is None:
        return "-"
    module = getattr(fn, "__module__", "")
    qualname = getattr(fn, "__qualname__", getattr(fn, "__name__", type(fn).__name__))
    return f"{module}.{qualname}" if module else qualname


def format_effect_for_display(effect: object) -> str:
    if isinstance(effect, DealDamage):
        return f"DealDamage(amount={effect.amount}, target={effect.target})"
    if isinstance(effect, GainBlock):
        return f"GainBlock(amount={effect.amount})"
    if isinstance(effect, DrawCards):
        return f"DrawCards(amount={effect.amount})"
    if isinstance(effect, GainEnergy):
        return f"GainEnergy(amount={effect.amount})"
    if isinstance(effect, ApplyBuff):
        return f"ApplyBuff(key={effect.key}, amount={effect.amount}, target={effect.target})"
    if isinstance(effect, ApplyDebuff):
        return f"ApplyDebuff(key={effect.key}, amount={effect.amount}, target={effect.target})"
    if isinstance(effect, SetNextAttackBonus):
        return f"SetNextAttackBonus(amount={effect.amount})"
    if isinstance(effect, SetReplayNextCard):
        return f"SetReplayNextCard(charges={effect.charges})"
    if isinstance(effect, DiscardCards):
        return f"DiscardCards(amount={effect.amount})"
    if isinstance(effect, ExhaustFromHand):
        return f"ExhaustFromHand(amount={effect.amount})"
    if isinstance(effect, ScheduleEffect):
        inner = format_effect_for_display(effect.effect)
        label = effect.label or "<no_label>"
        return f"ScheduleEffect(delay={effect.delay_turns}, label={label}, effect={inner})"
    if isinstance(effect, AddTriggerEffect):
        inner = format_effect_for_display(effect.trigger.effect)
        return (
            "AddTriggerEffect("
            f"event={effect.trigger.event}, uses={effect.trigger.remaining_uses}, "
            f"expire_turn={effect.trigger.expire_turn}, effect={inner})"
        )
    if isinstance(effect, Conditional):
        true_text = "; ".join(format_effect_for_display(e) for e in effect.if_true) or "-"
        false_text = "; ".join(format_effect_for_display(e) for e in effect.if_false) or "-"
        return f"Conditional(if_true=[{true_text}], if_false=[{false_text}])"
    return type(effect).__name__


def _card_effect_summary(card: CardDefinition) -> str:
    if card.description:
        return card.description
    return "; ".join(format_effect_for_display(effect) for effect in card.effects) or "-"


@dataclass(frozen=True)
class CardViewModel:
    instance_key: str
    card_id: str
    name: str
    cost: int
    card_type: str
    tags_text: str
    effect_text: str
    zone: str

    def header_text(self) -> str:
        return f"{self.name} [{self.card_type}]"

    def detail_text(self) -> str:
        lines = [
            f"ID: {self.card_id}",
            f"Name: {self.name}",
            f"Cost: {self.cost}",
            f"Type: {self.card_type}",
            f"Tags: {self.tags_text}",
            f"Zone: {self.zone}",
            "",
            "Effect:",
            self.effect_text,
        ]
        return "\n".join(lines)


@dataclass(frozen=True)
class TriggerViewModel:
    label: str
    event: str
    remaining_uses: str
    expire_turn: str
    effect_text: str
    condition_text: str

    def detail_text(self) -> str:
        lines = [
            f"Label: {self.label}",
            f"Event: {self.event}",
            f"Remaining Uses: {self.remaining_uses}",
            f"Expire Turn: {self.expire_turn}",
            f"Condition: {self.condition_text}",
            "",
            "Effect:",
            self.effect_text,
        ]
        return "\n".join(lines)


@dataclass(frozen=True)
class PendingEffectViewModel:
    execute_turn: int
    label: str
    effect_text: str

    def detail_text(self) -> str:
        lines = [
            f"Execute Turn: {self.execute_turn}",
            f"Label: {self.label}",
            "",
            "Effect:",
            self.effect_text,
        ]
        return "\n".join(lines)


@dataclass(frozen=True)
class SearchStepDetailViewModel:
    step_index: int
    action_text: str
    before_summary: str
    after_summary: str
    score_before: float
    score_after: float
    event_logs: list[str] = field(default_factory=list)
    effect_logs: list[str] = field(default_factory=list)
    pending_changes: list[str] = field(default_factory=list)
    trigger_changes: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def list_text(self) -> str:
        return f"{self.step_index + 1}. {self.action_text}"

    def summary_text(self) -> str:
        return f"{self.list_text()} | score {self.score_before:.2f} -> {self.score_after:.2f}"

    def detail_text(self) -> str:
        lines = [
            f"Step: {self.step_index + 1}",
            f"Action: {self.action_text}",
            f"Score: {self.score_before:.2f} -> {self.score_after:.2f}",
            "",
            "Before:",
            self.before_summary,
            "",
            "After:",
            self.after_summary,
            "",
            "Events:",
        ]
        lines.extend(self.event_logs or ["<none>"])
        lines.extend(["", "Effects:"])
        lines.extend(self.effect_logs or ["<none>"])
        lines.extend(["", "Pending Changes:"])
        lines.extend(self.pending_changes or ["<none>"])
        lines.extend(["", "Trigger Changes:"])
        lines.extend(self.trigger_changes or ["<none>"])
        if self.notes:
            lines.extend(["", "Notes:"])
            lines.extend(self.notes)
        return "\n".join(lines)


@dataclass(frozen=True)
class SearchBranchViewModel:
    branch_label: str
    score: float
    actions: list[str] = field(default_factory=list)
    step_summaries: list[str] = field(default_factory=list)
    step_details: list[SearchStepDetailViewModel] = field(default_factory=list)

    def list_text(self) -> str:
        action_preview = " -> ".join(self.actions[:3]) if self.actions else "<pass>"
        if len(self.actions) > 3:
            action_preview = f"{action_preview} -> ..."
        return f"{self.branch_label} | score={self.score:.2f} | {action_preview}"


@dataclass(frozen=True)
class GuiStateSnapshot:
    turn_index: int
    player_hp: int
    player_max_hp: int
    energy: int
    block: int
    player_buffs: list[str]
    player_debuffs: list[str]
    enemy_hp: int
    enemy_max_hp: int
    enemy_block: int
    enemy_intent_damage: int
    enemy_buffs: list[str]
    enemy_debuffs: list[str]
    hand_cards: list[CardViewModel]
    draw_pile_cards: list[CardViewModel]
    discard_pile_cards: list[CardViewModel]
    exhaust_pile_cards: list[CardViewModel]
    pending_effects: list[PendingEffectViewModel]
    triggers: list[TriggerViewModel]

    @classmethod
    def from_game_state(
        cls,
        state: GameState,
        card_defs: dict[str, CardDefinition],
    ) -> "GuiStateSnapshot":
        def build_card_vm(card_id: str, zone: str, index: int) -> CardViewModel:
            card = card_defs.get(card_id)
            if card is None:
                return CardViewModel(
                    instance_key=f"{zone}:{index}:{card_id}",
                    card_id=card_id,
                    name=card_id,
                    cost=-1,
                    card_type="unknown",
                    tags_text="-",
                    effect_text="未找到卡牌定义。",
                    zone=zone,
                )

            tags_text = ", ".join(sorted(card.tags)) if card.tags else "-"
            return CardViewModel(
                instance_key=f"{zone}:{index}:{card_id}",
                card_id=card.card_id,
                name=card.name,
                cost=card.cost,
                card_type=card.card_type,
                tags_text=tags_text,
                effect_text=_card_effect_summary(card),
                zone=zone,
            )

        pending_rows = [
            PendingEffectViewModel(
                execute_turn=pending.execute_turn,
                label=pending.label or "<no_label>",
                effect_text=format_effect_for_display(pending.effect),
            )
            for pending in sorted(state.pending_effects, key=lambda x: (x.execute_turn, x.label))
        ]
        trigger_rows = [
            TriggerViewModel(
                label=trigger.label or "<no_label>",
                event=trigger.event,
                remaining_uses=(
                    "unlimited" if trigger.remaining_uses is None else str(trigger.remaining_uses)
                ),
                expire_turn="none" if trigger.expire_turn is None else str(trigger.expire_turn),
                effect_text=format_effect_for_display(trigger.effect),
                condition_text=_callable_name(trigger.condition),
            )
            for trigger in state.triggers
        ]

        return cls(
            turn_index=state.turn_index,
            player_hp=state.player_hp,
            player_max_hp=state.player_max_hp,
            energy=state.energy,
            block=state.block,
            player_buffs=_format_counter_map(state.buffs),
            player_debuffs=_format_counter_map(state.debuffs),
            enemy_hp=state.enemy_state.hp,
            enemy_max_hp=state.enemy_state.max_hp,
            enemy_block=state.enemy_state.block,
            enemy_intent_damage=state.enemy_state.intent_damage,
            enemy_buffs=_format_counter_map(state.enemy_state.buffs),
            enemy_debuffs=_format_counter_map(state.enemy_state.debuffs),
            hand_cards=[build_card_vm(card_id, "hand", i) for i, card_id in enumerate(state.hand)],
            draw_pile_cards=[
                build_card_vm(card_id, "draw_pile", i) for i, card_id in enumerate(state.draw_pile)
            ],
            discard_pile_cards=[
                build_card_vm(card_id, "discard_pile", i) for i, card_id in enumerate(state.discard_pile)
            ],
            exhaust_pile_cards=[
                build_card_vm(card_id, "exhaust_pile", i) for i, card_id in enumerate(state.exhaust_pile)
            ],
            pending_effects=pending_rows,
            triggers=trigger_rows,
        )


@dataclass(frozen=True)
class SearchResultSnapshot:
    sequence: list[str]
    score: float
    trace: list[str]
    recommended_steps: list[str]
    recommended_step_details: list[SearchStepDetailViewModel]
    candidate_branches: list[SearchBranchViewModel]

    @classmethod
    def from_plan_result(
        cls,
        result: PlanResult,
        recommended_step_details: list[SearchStepDetailViewModel] | None = None,
        candidate_branches: list[SearchBranchViewModel] | None = None,
    ) -> "SearchResultSnapshot":
        recommended_steps = [line for line in result.trace if line.startswith("Play=")]
        if not recommended_steps and result.sequence:
            recommended_steps = [f"Play={step}" for step in result.sequence]
        step_details = list(recommended_step_details or [])
        if step_details:
            recommended_steps = [row.summary_text() for row in step_details]
        return cls(
            sequence=list(result.sequence),
            score=result.score,
            trace=list(result.trace),
            recommended_steps=recommended_steps,
            recommended_step_details=step_details,
            candidate_branches=list(candidate_branches or []),
        )

    def summary_text(self) -> str:
        sequence_text = " -> ".join(self.sequence) if self.sequence else "<pass>"
        return f"Score={self.score:.2f}; Sequence={sequence_text}"
