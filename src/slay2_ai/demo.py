from __future__ import annotations

from .card_defs import build_demo_cards
from .game_state import EnemyState, GameState
from .planner import search_best_sequence


def build_demo_state() -> GameState:
    # 手牌故意覆盖复杂机制：下回合收益、下一攻击增益、重放、联动攻击
    opening_hand = [
        "echo_spell",
        "sharpen",
        "combo_slash",
        "bank_energy",
        "jab",
    ]
    draw_pile = [
        "strike",
        "defend",
        "insight",
        "prepared_stance",
        "burn_memory",
        "desperate_blow",
        "purge_tactics",
    ]

    return GameState(
        player_hp=42,
        player_max_hp=60,
        energy=3,
        block=0,
        buffs={},
        debuffs={},
        hand=opening_hand,
        draw_pile=draw_pile,
        discard_pile=[],
        exhaust_pile=[],
        turn_index=1,
        cards_played_this_turn=[],
        attack_count_this_turn=0,
        skill_count_this_turn=0,
        pending_effects=[],
        triggers=[],
        enemy_state=EnemyState(hp=52, max_hp=52, block=0, intent_damage=10),
        rng_seed=7,
    )


def print_result(result) -> None:
    print("=== Planner Result ===")
    print("Best sequence:", " -> ".join(result.sequence) if result.sequence else "<pass>")
    print("Final score:", f"{result.score:.2f}")
    print("\n=== Trace ===")
    for line in result.trace:
        print(line)

    fs = result.final_state
    print("\n=== Final State Snapshot ===")
    print(
        f"Player HP={fs.player_hp}, Energy={fs.energy}, Block={fs.block}, "
        f"Enemy HP={fs.enemy_state.hp}, Pending={len(fs.pending_effects)}, "
        f"NextAtkBonus={fs.buffs.get('next_attack_bonus', 0)}, "
        f"ReplayCharges={fs.buffs.get('replay_next_card', 0)}"
    )


def main() -> None:
    cards = build_demo_cards()
    state = build_demo_state()

    result = search_best_sequence(
        state=state,
        cards=cards,
        max_depth=5,
        beam_width=6,
    )
    print_result(result)


if __name__ == "__main__":
    main()
