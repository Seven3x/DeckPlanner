from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .game_state import GameState, Trigger


ConditionFn = Callable[[GameState, dict], bool]


class Effect:
    def apply(self, state: GameState, ctx: dict) -> None:
        raise NotImplementedError


@dataclass
class DealDamage(Effect):
    amount: int
    target: str = "enemy"

    def apply(self, state: GameState, ctx: dict) -> None:
        dmg = self.amount
        if ctx.get("is_attack"):
            bonus = state.buffs.get("next_attack_bonus", 0)
            if bonus > 0:
                dmg += bonus
                state.buffs["next_attack_bonus"] = 0

            strength = state.buffs.get("strength", 0)
            if strength:
                dmg += strength

        if self.target == "enemy":
            enemy = state.enemy_state
            actual = max(0, dmg - enemy.block)
            enemy.block = max(0, enemy.block - dmg)
            enemy.hp = max(0, enemy.hp - actual)
        elif self.target == "player":
            actual = max(0, dmg - state.block)
            state.block = max(0, state.block - dmg)
            state.player_hp = max(0, state.player_hp - actual)
        else:
            raise ValueError(f"Unknown target {self.target}")


@dataclass
class GainBlock(Effect):
    amount: int

    def apply(self, state: GameState, ctx: dict) -> None:
        state.block += self.amount


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

    def apply(self, state: GameState, ctx: dict) -> None:
        from .triggers import add_trigger

        add_trigger(state, self.trigger)


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

        for _ in range(min(self.amount, len(state.hand))):
            card_id = state.hand.pop(0)
            state.discard_pile.append(card_id)
            emit_event(state, "on_discard", {"card_id": card_id})


@dataclass
class ExhaustFromHand(Effect):
    amount: int

    def apply(self, state: GameState, ctx: dict) -> None:
        from .triggers import emit_event

        for _ in range(min(self.amount, len(state.hand))):
            card_id = state.hand.pop(0)
            state.exhaust_pile.append(card_id)
            emit_event(state, "on_exhaust", {"card_id": card_id})


@dataclass
class Conditional(Effect):
    condition: ConditionFn
    if_true: list[Effect] = field(default_factory=list)
    if_false: list[Effect] = field(default_factory=list)

    def apply(self, state: GameState, ctx: dict) -> None:
        branch = self.if_true if self.condition(state, ctx) else self.if_false
        for effect in branch:
            effect.apply(state, ctx)
