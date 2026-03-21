from __future__ import annotations

from .card_defs import build_demo_cards
from .effects import ApplyBuff
from .evaluator import evaluate_state
from .game_state import EnemyState, GameState
from .planner import (
    PlayCardAction,
    advance_one_full_turn,
    legal_actions,
    search_best_sequence,
    simulate_play,
)
from .triggers import Trigger


def base_state(
    hand: list[str],
    draw_pile: list[str] | None = None,
    enemy_hp: int = 52,
    intent_damage: int = 10,
    energy: int = 3,
) -> GameState:
    return GameState(
        player_hp=42,
        player_max_hp=60,
        energy=energy,
        block=0,
        buffs={},
        debuffs={},
        hand=list(hand),
        draw_pile=list(draw_pile or []),
        discard_pile=[],
        exhaust_pile=[],
        turn_index=1,
        cards_played_this_turn=[],
        attack_count_this_turn=0,
        skill_count_this_turn=0,
        pending_effects=[],
        triggers=[],
        enemy_state=EnemyState(hp=enemy_hp, max_hp=enemy_hp, block=0, intent_damage=intent_damage),
        rng_seed=7,
    )


def check_replay_semantics(cards: dict) -> None:
    state = base_state(hand=["echo_spell", "strike"], enemy_hp=30, intent_damage=0, energy=2)

    after_echo = simulate_play(state, PlayCardAction("echo_spell"), cards)
    assert after_echo.energy == 1, "echo_spell 应只消耗自己费用"
    assert after_echo.buffs.get("replay_next_card", 0) == 1, "echo_spell 不应重放自己"

    after_strike = simulate_play(after_echo, PlayCardAction("strike"), cards)
    # strike 基础6，replay再6，总共12
    assert after_strike.enemy_state.hp == 18, "下一张牌应被重放一次（6+6）"
    assert after_strike.energy == 0, "replay 不应重复支付费用"
    assert len(after_strike.cards_played_this_turn) == 2, "replay 不应计入正常出牌次数"

    print("[OK] replay_next_card: 当前牌不自耗，下一张牌重放且不重复计费/计次")


def check_trigger_expiry(cards: dict) -> None:
    state = base_state(hand=["prepared_stance"], enemy_hp=40, intent_damage=0, energy=1)
    after_setup = simulate_play(state, PlayCardAction("prepared_stance"), cards)
    assert len(after_setup.triggers) == 1, "应挂上本回合触发器"

    next_turn = advance_one_full_turn(after_setup, draw_n=0)
    assert len(next_turn.triggers) == 0, "本回合 trigger 必须在回合边界失效"

    print("[OK] trigger 过期: 本回合未触发会在下回合清理")


def check_event_wiring(cards: dict) -> None:
    state = base_state(hand=["defend"], draw_pile=["strike", "jab"], enemy_hp=50, intent_damage=9, energy=1)
    state.triggers.extend(
        [
            Trigger("on_draw", ApplyBuff("draw_event_count", 1), remaining_uses=None, label="count_draw"),
            Trigger("on_block_gained", ApplyBuff("block_event_count", 1), remaining_uses=None, label="count_block"),
            Trigger("on_damage_taken", ApplyBuff("damage_event_count", 1), remaining_uses=None, label="count_damage"),
        ]
    )

    after_block = simulate_play(state, PlayCardAction("defend"), cards)
    rolled = advance_one_full_turn(after_block, draw_n=2)

    assert rolled.buffs.get("block_event_count", 0) == 1, "应只触发一次 on_block_gained"
    assert rolled.buffs.get("damage_event_count", 0) == 1, "应在实际掉血时触发 on_damage_taken"
    assert rolled.buffs.get("draw_event_count", 0) == 1, "同一次抽牌不应重复触发 on_draw"

    print("[OK] 事件打通: on_draw/on_block_gained/on_damage_taken 触发次数正确")


def check_cross_turn_planning(cards: dict) -> None:
    state = base_state(
        hand=["bank_energy", "jab"],
        draw_pile=["desperate_blow", "strike", "defend"],
        enemy_hp=60,
        intent_damage=0,
        energy=1,
    )

    after_bank = simulate_play(state, PlayCardAction("bank_energy"), cards)
    immediate_score = evaluate_state(after_bank)
    rolled_score = evaluate_state(advance_one_full_turn(after_bank, draw_n=0))
    assert rolled_score > immediate_score, "推进完整回合后应体现 delayed value"

    result = search_best_sequence(state=state, cards=cards, max_depth=2, beam_width=4)
    print("[INFO] bank_energy 立即评分:", f"{immediate_score:.2f}")
    print("[INFO] bank_energy 过回合后评分:", f"{rolled_score:.2f}")
    print("[INFO] 跨回合搜索序列:", " -> ".join(result.sequence) if result.sequence else "<pass>")
    print("[INFO] 跨回合搜索评分:", f"{result.score:.2f}")


def check_discard_choices(cards: dict) -> None:
    state = base_state(
        hand=["burn_memory", "desperate_blow", "jab"],
        draw_pile=["strike", "defend", "insight"],
        enemy_hp=45,
        intent_damage=0,
        energy=2,
    )

    actions = [a for a in legal_actions(state, cards) if a.card_id == "burn_memory"]
    action_signatures = {(a.discard_choices, a.exhaust_choices) for a in actions}
    assert (("desperate_blow",), ()) in action_signatures, "应支持选择丢弃 desperate_blow"
    assert (("jab",), ()) in action_signatures, "应支持选择丢弃 jab"

    drop_desperate = simulate_play(
        state,
        PlayCardAction("burn_memory", discard_choices=("desperate_blow",)),
        cards,
    )
    drop_jab = simulate_play(
        state,
        PlayCardAction("burn_memory", discard_choices=("jab",)),
        cards,
    )

    after_drop_desperate = simulate_play(drop_desperate, PlayCardAction("jab"), cards)
    score_drop_desperate = evaluate_state(advance_one_full_turn(after_drop_desperate, draw_n=2))
    score_drop_jab = evaluate_state(advance_one_full_turn(drop_jab, draw_n=2))

    assert not (score_drop_desperate == score_drop_jab), "不同弃牌选择应产生不同结果"

    print(
        "[INFO] 弃牌选择评分: 丢desperate_blow后打jab=",
        f"{score_drop_desperate:.2f}",
        ", 丢jab(无后续攻击)=",
        f"{score_drop_jab:.2f}",
        sep="",
    )


def run_planner_demo(cards: dict) -> None:
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

    result = search_best_sequence(state=state, cards=cards, max_depth=5, beam_width=6)
    print("\n=== Planner Result ===")
    print("Best sequence:", " -> ".join(result.sequence) if result.sequence else "<pass>")
    print("Final score:", f"{result.score:.2f}")
    print("\n=== Trace ===")
    for line in result.trace:
        print(line)


def main() -> None:
    cards = build_demo_cards()

    check_replay_semantics(cards)
    check_trigger_expiry(cards)
    check_event_wiring(cards)
    check_cross_turn_planning(cards)
    check_discard_choices(cards)
    run_planner_demo(cards)


if __name__ == "__main__":
    main()
