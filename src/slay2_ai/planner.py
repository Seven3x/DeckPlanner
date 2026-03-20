from __future__ import annotations

from dataclasses import dataclass
from math import inf

from .card_defs import CardDefinition
from .evaluator import evaluate_state
from .game_state import GameState
from .triggers import emit_event


@dataclass
class PlanResult:
    sequence: list[str]
    score: float
    final_state: GameState
    trace: list[str]


def resolve_pending_effects(state: GameState) -> None:
    due = [p for p in state.pending_effects if p.execute_turn <= state.turn_index]
    state.pending_effects = [p for p in state.pending_effects if p.execute_turn > state.turn_index]
    for pending in due:
        pending.effect.apply(state, {"event": "pending", "label": pending.label})


def start_turn(state: GameState, base_energy: int = 3, draw_n: int = 5) -> None:
    state.turn_index += 1
    state.energy = base_energy
    state.block = 0
    state.cards_played_this_turn.clear()
    state.attack_count_this_turn = 0
    state.skill_count_this_turn = 0
    resolve_pending_effects(state)
    emit_event(state, "on_turn_start", {})
    drawn = state.draw_cards(draw_n)
    if drawn > 0:
        emit_event(state, "on_draw", {"count": drawn})


def end_turn(state: GameState) -> None:
    emit_event(state, "on_turn_end", {})
    state.discard_pile.extend(state.hand)
    state.hand.clear()


def legal_actions(state: GameState, cards: dict[str, CardDefinition]) -> list[str]:
    actions: list[str] = []
    for card_id in state.hand:
        card = cards[card_id]
        if card.cost <= state.energy:
            actions.append(card_id)
    return actions


def _play_card_once(state: GameState, card_id: str, cards: dict[str, CardDefinition], is_replay: bool) -> None:
    card = cards[card_id]

    attack_count_before = state.attack_count_this_turn

    if not is_replay:
        state.hand.remove(card_id)
        state.energy -= card.cost
        state.cards_played_this_turn.append(card_id)
        if card.card_type == "attack":
            state.attack_count_this_turn += 1
        elif card.card_type == "skill":
            state.skill_count_this_turn += 1

    ctx = {
        "card_id": card_id,
        "card_type": card.card_type,
        "is_attack": card.card_type == "attack",
        "is_skill": card.card_type == "skill",
        "is_replay": is_replay,
        "attack_count_before": attack_count_before,
    }

    emit_event(state, "on_card_played", ctx)
    if card.card_type == "attack":
        emit_event(state, "on_attack_played", ctx)
    elif card.card_type == "skill":
        emit_event(state, "on_skill_played", ctx)

    for effect in card.effects:
        effect.apply(state, ctx)

    if not is_replay:
        if card.exhaust:
            state.exhaust_pile.append(card_id)
            emit_event(state, "on_exhaust", {"card_id": card_id})
        else:
            state.discard_pile.append(card_id)


def simulate_play(state: GameState, card_id: str, cards: dict[str, CardDefinition]) -> GameState:
    nxt = state.clone()
    _play_card_once(nxt, card_id, cards, is_replay=False)

    replay_charges = nxt.buffs.get("replay_next_card", 0)
    if replay_charges > 0:
        nxt.buffs["replay_next_card"] = replay_charges - 1
        _play_card_once(nxt, card_id, cards, is_replay=True)

    nxt.remove_expired_markers()
    return nxt


def search_best_sequence(
    state: GameState,
    cards: dict[str, CardDefinition],
    max_depth: int = 4,
    beam_width: int | None = None,
) -> PlanResult:
    best_score = -inf
    best_sequence: list[str] = []
    best_state = state.clone()
    best_trace: list[str] = []
    visited_depth_score: dict[tuple, float] = {}

    def summarize(st: GameState) -> str:
        return (
            f"HP={st.player_hp} EN={st.energy} BLK={st.block} "
            f"EnemyHP={st.enemy_state.hp} Hand={len(st.hand)} "
            f"Pending={len(st.pending_effects)} Trig={len(st.triggers)}"
        )

    def dfs(cur: GameState, depth: int, seq: list[str], trace: list[str]) -> None:
        nonlocal best_score, best_sequence, best_state, best_trace

        score = evaluate_state(cur)
        sig = (depth, cur.state_signature())
        if visited_depth_score.get(sig, -inf) >= score:
            return
        visited_depth_score[sig] = score

        if score > best_score:
            best_score = score
            best_sequence = list(seq)
            best_state = cur.clone()
            best_trace = list(trace)

        if depth >= max_depth:
            return

        actions = legal_actions(cur, cards)
        if not actions:
            return

        next_states: list[tuple[str, GameState, float]] = []
        for action in actions:
            nxt = simulate_play(cur, action, cards)
            next_states.append((action, nxt, evaluate_state(nxt)))

        next_states.sort(key=lambda x: x[2], reverse=True)
        if beam_width is not None:
            next_states = next_states[:beam_width]

        for action, nxt, _ in next_states:
            step_summary = f"Play={action} -> {summarize(nxt)}"
            dfs(nxt, depth + 1, seq + [action], trace + [step_summary])

    dfs(state.clone(), 0, [], [f"Start -> {summarize(state)}"])
    return PlanResult(best_sequence, best_score, best_state, best_trace)
