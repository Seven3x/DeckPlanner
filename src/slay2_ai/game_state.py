from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional, TYPE_CHECKING
import copy
import random

if TYPE_CHECKING:
    from .effects import Effect


ConditionFn = Callable[["GameState", dict], bool]


@dataclass
class EnemyState:
    hp: int
    max_hp: int
    block: int = 0
    intent_damage: int = 0
    buffs: dict[str, int] = field(default_factory=dict)
    debuffs: dict[str, int] = field(default_factory=dict)


@dataclass
class Trigger:
    event: str
    effect: "Effect"
    condition: Optional[ConditionFn] = None
    remaining_uses: Optional[int] = 1
    expire_turn: Optional[int] = None
    label: str = ""


@dataclass
class PendingEffect:
    execute_turn: int
    effect: "Effect"
    label: str = ""


@dataclass
class GameState:
    player_hp: int
    player_max_hp: int
    energy: int
    block: int
    buffs: dict[str, int]
    debuffs: dict[str, int]
    hand: list[str]
    draw_pile: list[str]
    discard_pile: list[str]
    exhaust_pile: list[str]
    turn_index: int
    cards_played_this_turn: list[str]
    attack_count_this_turn: int
    skill_count_this_turn: int
    pending_effects: list[PendingEffect]
    triggers: list[Trigger]
    enemy_state: EnemyState
    rng_seed: int = 0

    def clone(self) -> "GameState":
        return copy.deepcopy(self)

    def _effect_sig(self, effect: "Effect") -> str:
        return f"{effect.__class__.__name__}:{repr(effect)}"

    def state_signature(self) -> tuple:
        return (
            self.turn_index,
            self.player_hp,
            self.player_max_hp,
            self.energy,
            self.block,
            tuple(sorted(self.buffs.items())),
            tuple(sorted(self.debuffs.items())),
            tuple(self.hand),
            tuple(self.draw_pile),
            tuple(self.discard_pile),
            tuple(self.exhaust_pile),
            tuple(self.cards_played_this_turn),
            self.attack_count_this_turn,
            self.skill_count_this_turn,
            tuple(
                sorted(
                    (
                        p.execute_turn,
                        p.label,
                        self._effect_sig(p.effect),
                    )
                    for p in self.pending_effects
                )
            ),
            tuple(
                sorted(
                    (
                        t.event,
                        t.label,
                        t.remaining_uses,
                        t.expire_turn,
                        self._effect_sig(t.effect),
                    )
                    for t in self.triggers
                )
            ),
            self.enemy_state.hp,
            self.enemy_state.max_hp,
            self.enemy_state.block,
            self.enemy_state.intent_damage,
            tuple(sorted(self.enemy_state.buffs.items())),
            tuple(sorted(self.enemy_state.debuffs.items())),
            self.rng_seed,
        )

    def draw_cards(self, n: int) -> list[str]:
        from .triggers import emit_event

        drawn_cards: list[str] = []
        for _ in range(n):
            if not self.draw_pile:
                if not self.discard_pile:
                    break
                self.draw_pile = list(self.discard_pile)
                self.discard_pile.clear()
                rnd = random.Random(self.rng_seed)
                rnd.shuffle(self.draw_pile)
                self.rng_seed += 1

            card_id = self.draw_pile.pop()
            self.hand.append(card_id)
            drawn_cards.append(card_id)

        if drawn_cards:
            emit_event(self, "on_draw", {"cards": list(drawn_cards), "count": len(drawn_cards)})

        return drawn_cards

    def add_pending(self, delay_turns: int, effect: "Effect", label: str = "") -> None:
        self.pending_effects.append(
            PendingEffect(execute_turn=self.turn_index + delay_turns, effect=effect, label=label)
        )

    def remove_expired_markers(self) -> None:
        for key in ("next_attack_bonus", "replay_next_card"):
            if self.buffs.get(key, 0) < 0:
                self.buffs[key] = 0
