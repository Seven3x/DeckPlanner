from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .effects import (
    AddTriggerEffect,
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
from .triggers import Trigger

CardType = Literal["attack", "skill", "power"]


@dataclass
class CardDefinition:
    card_id: str
    name: str
    cost: int
    card_type: CardType
    effects: list
    exhaust: bool = False
    tags: set[str] = field(default_factory=set)
    description: str = ""


def _combo_condition(state, ctx: dict) -> bool:
    return ctx.get("attack_count_before", 0) >= 1


def _low_hp_condition(state, ctx: dict) -> bool:
    return state.player_hp * 2 <= state.player_max_hp


def build_demo_cards() -> dict[str, CardDefinition]:
    cards = {
        "strike": CardDefinition(
            card_id="strike",
            name="Strike",
            cost=1,
            card_type="attack",
            effects=[DealDamage(6)],
            description="造成6点伤害。",
        ),
        "defend": CardDefinition(
            card_id="defend",
            name="Defend",
            cost=1,
            card_type="skill",
            effects=[GainBlock(5)],
            description="获得5点格挡。",
        ),
        "insight": CardDefinition(
            card_id="insight",
            name="Insight",
            cost=1,
            card_type="skill",
            effects=[DrawCards(2)],
            description="抽2张牌。",
        ),
        "jab": CardDefinition(
            card_id="jab",
            name="Jab",
            cost=0,
            card_type="attack",
            effects=[DealDamage(4)],
            description="0费，造成4点伤害。",
        ),
        "bank_energy": CardDefinition(
            card_id="bank_energy",
            name="Bank Energy",
            cost=1,
            card_type="skill",
            effects=[ScheduleEffect(GainEnergy(2), delay_turns=1, label="next_turn_energy")],
            description="下回合获得2点能量。",
        ),
        "sharpen": CardDefinition(
            card_id="sharpen",
            name="Sharpen",
            cost=1,
            card_type="skill",
            effects=[SetNextAttackBonus(5)],
            description="下一张攻击牌额外+5伤害。",
        ),
        "echo_spell": CardDefinition(
            card_id="echo_spell",
            name="Echo Spell",
            cost=1,
            card_type="skill",
            effects=[SetReplayNextCard(1)],
            description="下一张打出的牌效果重放一次。",
        ),
        "combo_slash": CardDefinition(
            card_id="combo_slash",
            name="Combo Slash",
            cost=1,
            card_type="attack",
            effects=[
                DealDamage(4),
                Conditional(
                    condition=_combo_condition,
                    if_true=[DealDamage(4)],
                    if_false=[],
                ),
            ],
            description="造成4点伤害。若此前已打出攻击牌，再造成4点。",
        ),
        "burn_memory": CardDefinition(
            card_id="burn_memory",
            name="Burn Memory",
            cost=1,
            card_type="skill",
            effects=[DiscardCards(1), DrawCards(2)],
            description="弃1抽2。",
        ),
        "desperate_blow": CardDefinition(
            card_id="desperate_blow",
            name="Desperate Blow",
            cost=2,
            card_type="attack",
            effects=[
                Conditional(
                    condition=_low_hp_condition,
                    if_true=[DealDamage(16)],
                    if_false=[DealDamage(8)],
                )
            ],
            description="若生命低于50%，造成16伤害，否则8伤害。",
        ),
        "prepared_stance": CardDefinition(
            card_id="prepared_stance",
            name="Prepared Stance",
            cost=1,
            card_type="skill",
            effects=[
                AddTriggerEffect(
                    trigger=Trigger(
                        event="on_attack_played",
                        effect=GainBlock(3),
                        remaining_uses=1,
                        expire_turn=None,
                        label="attack_once_gain_block",
                    ),
                    expire_on_current_turn=True,
                )
            ],
            description="本回合下次打出攻击牌时，获得3格挡。",
        ),
        "purge_tactics": CardDefinition(
            card_id="purge_tactics",
            name="Purge Tactics",
            cost=0,
            card_type="skill",
            effects=[DrawCards(1), ExhaustFromHand(1)],
            exhaust=True,
            description="抽1，再消耗1张手牌。本牌打出后消耗。",
        ),
    }
    return cards
