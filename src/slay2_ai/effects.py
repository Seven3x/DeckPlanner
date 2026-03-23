from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .game_state import GameState
from .triggers import Trigger


ConditionFn = Callable[[GameState, dict], bool]


class Effect:
    def apply(self, state: GameState, ctx: dict) -> None:
        raise NotImplementedError


def _pop_with_choices(hand: list[str], choices_remaining: list[str]) -> str | None:
    while choices_remaining and choices_remaining[0] not in hand:
        choices_remaining.pop(0)

    if choices_remaining:
        chosen = choices_remaining.pop(0)
        hand.remove(chosen)
        return chosen

    if hand:
        return hand.pop(0)

    return None


@dataclass
class DealDamage(Effect):
    amount: int
    target: str = "enemy"

    def apply(self, state: GameState, ctx: dict) -> None:
        from .triggers import emit_event

        raw_damage = self.amount
        if ctx.get("is_attack"):
            bonus = state.buffs.get("next_attack_bonus", 0)
            if bonus > 0:
                raw_damage += bonus
                state.buffs["next_attack_bonus"] = 0

            strength = state.buffs.get("strength", 0)
            if strength:
                raw_damage += strength

        if self.target == "enemy":
            enemy = state.enemy_state
            blocked_amount = min(enemy.block, raw_damage)
            actual_hp_loss = max(0, raw_damage - enemy.block)
            enemy.block = max(0, enemy.block - raw_damage)
            enemy.hp = max(0, enemy.hp - actual_hp_loss)
        elif self.target == "player":
            blocked_amount = min(state.block, raw_damage)
            actual_hp_loss = max(0, raw_damage - state.block)
            state.block = max(0, state.block - raw_damage)
            state.player_hp = max(0, state.player_hp - actual_hp_loss)
        else:
            raise ValueError(f"Unknown target {self.target}")

        if actual_hp_loss > 0:
            emit_event(
                state,
                "on_damage_taken",
                {
                    "target": self.target,
                    "raw_damage": raw_damage,
                    "actual_hp_loss": actual_hp_loss,
                    "blocked_amount": blocked_amount,
                },
            )


@dataclass
class GainBlock(Effect):
    amount: int

    def apply(self, state: GameState, ctx: dict) -> None:
        from .triggers import emit_event

        dexterity = state.buffs.get("dexterity", 0)
        total_amount = self.amount + dexterity
        state.block += max(0, total_amount)
        emit_event(
            state,
            "on_block_gained",
            {
                "amount": max(0, total_amount),
                "new_block": state.block,
            },
        )


@dataclass
class DrawCards(Effect):
    amount: int

    def apply(self, state: GameState, ctx: dict) -> None:
        state.draw_cards(self.amount)


@dataclass
class GainEnergy(Effect):
    amount: int

    def apply(self, state: GameState, ctx: dict) -> None:
        state.energy += self.amount


@dataclass
class ApplyBuff(Effect):
    key: str
    amount: int
    target: str = "player"

    def apply(self, state: GameState, ctx: dict) -> None:
        container = state.buffs if self.target == "player" else state.enemy_state.buffs
        container[self.key] = container.get(self.key, 0) + self.amount


@dataclass
class ApplyDebuff(Effect):
    key: str
    amount: int
    target: str = "enemy"

    def apply(self, state: GameState, ctx: dict) -> None:
        container = state.debuffs if self.target == "player" else state.enemy_state.debuffs
        container[self.key] = container.get(self.key, 0) + self.amount


@dataclass
class AddTriggerEffect(Effect):
    trigger: Trigger
    expire_on_current_turn: bool = False

    def apply(self, state: GameState, ctx: dict) -> None:
        from .triggers import add_trigger

        trigger = Trigger(
            event=self.trigger.event,
            effect=self.trigger.effect,
            condition=self.trigger.condition,
            remaining_uses=self.trigger.remaining_uses,
            expire_turn=self.trigger.expire_turn,
            label=self.trigger.label,
        )
        if self.expire_on_current_turn and trigger.expire_turn is None:
            trigger.expire_turn = state.turn_index

        add_trigger(state, trigger)


@dataclass
class ScheduleEffect(Effect):
    effect: Effect
    delay_turns: int
    label: str = ""

    def apply(self, state: GameState, ctx: dict) -> None:
        state.add_pending(self.delay_turns, self.effect, label=self.label)


@dataclass
class SetNextAttackBonus(Effect):
    amount: int

    def apply(self, state: GameState, ctx: dict) -> None:
        state.buffs["next_attack_bonus"] = state.buffs.get("next_attack_bonus", 0) + self.amount


@dataclass
class SetReplayNextCard(Effect):
    charges: int = 1

    def apply(self, state: GameState, ctx: dict) -> None:
        state.buffs["replay_next_card"] = state.buffs.get("replay_next_card", 0) + self.charges


@dataclass
class DiscardCards(Effect):
    amount: int

    def apply(self, state: GameState, ctx: dict) -> None:
        from .triggers import emit_event

        choices_remaining = ctx.setdefault("discard_choices_remaining", [])
        for _ in range(min(self.amount, len(state.hand))):
            chosen = _pop_with_choices(state.hand, choices_remaining)
            if chosen is None:
                break
            state.discard_pile.append(chosen)
            emit_event(state, "on_discard", {"card_id": chosen})


@dataclass
class ExhaustFromHand(Effect):
    amount: int

    def apply(self, state: GameState, ctx: dict) -> None:
        from .triggers import emit_event

        choices_remaining = ctx.setdefault("exhaust_choices_remaining", [])
        for _ in range(min(self.amount, len(state.hand))):
            chosen = _pop_with_choices(state.hand, choices_remaining)
            if chosen is None:
                break
            state.exhaust_pile.append(chosen)
            emit_event(state, "on_exhaust", {"card_id": chosen})


@dataclass
class Conditional(Effect):
    condition: ConditionFn
    if_true: list[Effect] = field(default_factory=list)
    if_false: list[Effect] = field(default_factory=list)

    def apply(self, state: GameState, ctx: dict) -> None:
        branch = self.if_true if self.condition(state, ctx) else self.if_false
        for effect in branch:
            effect.apply(state, ctx)
