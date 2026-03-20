from __future__ import annotations

from .game_state import GameState


def evaluate_state(state: GameState) -> float:
    enemy = state.enemy_state

    # 1) 生存价值
    hp_ratio = state.player_hp / max(1, state.player_max_hp)
    survivability = hp_ratio * 40.0

    incoming = max(0, enemy.intent_damage - state.block)
    survivability -= incoming * 1.8
    if state.player_hp <= incoming:
        survivability -= 40.0

    survivability += min(state.block, enemy.intent_damage) * 0.9

    # 2) 输出价值
    damage_done = enemy.max_hp - enemy.hp
    offense = damage_done * 1.4
    if enemy.hp <= 0:
        offense += 100.0
    elif enemy.hp <= 12:
        offense += 8.0

    # 3) 资源价值
    resources = 0.0
    resources += state.energy * 1.2
    resources += len(state.hand) * 0.7
    resources += min(6, len(state.draw_pile)) * 0.2
    if state.energy == 0 and len(state.hand) > 0:
        resources += 1.0

    # 4) 引擎价值
    engine = 0.0
    engine += len(state.pending_effects) * 2.0
    engine += len(state.triggers) * 1.8
    engine += state.buffs.get("next_attack_bonus", 0) * 0.6
    engine += state.buffs.get("replay_next_card", 0) * 3.0
    engine += state.attack_count_this_turn * 0.4

    return survivability + offense + resources + engine
