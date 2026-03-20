from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from math import inf

from .card_defs import CardDefinition
from .effects import DealDamage, DiscardCards, ExhaustFromHand
from .evaluator import evaluate_state
from .game_state import GameState
from .triggers import cleanup_triggers, emit_event


@dataclass(frozen=True)
class PlayCardAction:
    card_id: str
    discard_choices: tuple[str, ...] = ()
    exhaust_choices: tuple[str, ...] = ()


@dataclass
class PlanResult:
    sequence: list[str]
    score: float
    final_state: GameState
    trace: list[str]


def _action_label(action: PlayCardAction) -> str:
    parts = [action.card_id]
    if action.discard_choices:
        parts.append(f"discard={list(action.discard_choices)}")
    if action.exhaust_choices:
        parts.append(f"exhaust={list(action.exhaust_choices)}")
    return " | ".join(parts)


def resolve_pending_effects(state: GameState) -> None:
    due = [p for p in state.pending_effects if p.execute_turn <= state.turn_index]
    state.pending_effects = [p for p in state.pending_effects if p.execute_turn > state.turn_index]
    for pending in due:
        pending.effect.apply(state, {"event": "pending", "label": pending.label})


def start_turn(state: GameState, base_energy: int = 3, draw_n: int = 5) -> None:
    state.turn_index += 1
    cleanup_triggers(state)
    state.energy = base_energy
    state.block = 0
    state.cards_played_this_turn.clear()
    state.attack_count_this_turn = 0
    state.skill_count_this_turn = 0
    resolve_pending_effects(state)
    emit_event(state, "on_turn_start", {})
    state.draw_cards(draw_n)


def end_turn(state: GameState) -> None:
    emit_event(state, "on_turn_end", {})
    state.discard_pile.extend(state.hand)
    state.hand.clear()
    cleanup_triggers(state)


def _required_choices(card: CardDefinition) -> tuple[int, int]:
    discard_n = 0
    exhaust_n = 0
    for effect in card.effects:
        if isinstance(effect, DiscardCards):
            discard_n += effect.amount
        elif isinstance(effect, ExhaustFromHand):
            exhaust_n += effect.amount
    return discard_n, exhaust_n


def _remove_cards_once(cards: list[str], to_remove: tuple[str, ...]) -> list[str]:
    remaining = list(cards)
    for card_id in to_remove:
        if card_id in remaining:
            remaining.remove(card_id)
    return remaining


def _distinct_choice_tuples(pool: list[str], count: int) -> list[tuple[str, ...]]:
    if count == 0:
        return [()]
    if len(pool) < count:
        return []

    choices = {
        tuple(pool[i] for i in idxs)
        for idxs in combinations(range(len(pool)), count)
    }
    return sorted(choices)


def legal_actions(state: GameState, cards: dict[str, CardDefinition]) -> list[PlayCardAction]:
    actions: list[PlayCardAction] = []

    for card_id in state.hand:
        card = cards[card_id]
        if card.cost > state.energy:
            continue

        post_play_hand = list(state.hand)
        post_play_hand.remove(card_id)

        discard_n, exhaust_n = _required_choices(card)
        discard_options = _distinct_choice_tuples(post_play_hand, discard_n)
        if not discard_options:
            continue

        for discard_choice in discard_options:
            hand_after_discard = _remove_cards_once(post_play_hand, discard_choice)
            exhaust_options = _distinct_choice_tuples(hand_after_discard, exhaust_n)
            if not exhaust_options:
                continue

            for exhaust_choice in exhaust_options:
                actions.append(
                    PlayCardAction(
                        card_id=card_id,
                        discard_choices=discard_choice,
                        exhaust_choices=exhaust_choice,
                    )
                )

    return actions


def _play_card_once(
    state: GameState,
    action: PlayCardAction,
    cards: dict[str, CardDefinition],
    is_replay: bool,
) -> None:
    card = cards[action.card_id]
    attack_count_before = state.attack_count_this_turn

    if not is_replay:
        state.hand.remove(action.card_id)
        state.energy -= card.cost
        state.cards_played_this_turn.append(action.card_id)
        if card.card_type == "attack":
            state.attack_count_this_turn += 1
        elif card.card_type == "skill":
            state.skill_count_this_turn += 1

    ctx = {
        "card_id": action.card_id,
        "card_type": card.card_type,
        "is_attack": card.card_type == "attack",
        "is_skill": card.card_type == "skill",
        "is_replay": is_replay,
        "attack_count_before": attack_count_before,
        "discard_choices_remaining": [] if is_replay else list(action.discard_choices),
        "exhaust_choices_remaining": [] if is_replay else list(action.exhaust_choices),
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
            state.exhaust_pile.append(action.card_id)
            emit_event(state, "on_exhaust", {"card_id": action.card_id})
        else:
            state.discard_pile.append(action.card_id)


def simulate_play(state: GameState, action: PlayCardAction, cards: dict[str, CardDefinition]) -> GameState:
    nxt = state.clone()

    pre_replay_charges = nxt.buffs.get("replay_next_card", 0)
    _play_card_once(nxt, action, cards, is_replay=False)

    # 仅消费“打牌前已有”的 replay charge；当前牌新生成的 charge 保留给后续牌。
    if pre_replay_charges > 0:
        current_total = nxt.buffs.get("replay_next_card", 0)
        nxt.buffs["replay_next_card"] = max(0, current_total - 1)
        _play_card_once(nxt, PlayCardAction(card_id=action.card_id), cards, is_replay=True)

    nxt.remove_expired_markers()
    return nxt


def advance_one_full_turn(state: GameState, draw_n: int = 5) -> GameState:
    nxt = state.clone()
    end_turn(nxt)

    # 简化敌方回合：按 intent_damage 对玩家造成伤害。
    incoming = max(0, nxt.enemy_state.intent_damage)
    if incoming > 0:
        DealDamage(incoming, target="player").apply(nxt, {"event": "enemy_turn", "is_attack": False})

    start_turn(nxt, base_energy=3, draw_n=draw_n)
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
            f"T={st.turn_index} HP={st.player_hp} EN={st.energy} BLK={st.block} "
            f"EnemyHP={st.enemy_state.hp} Hand={len(st.hand)} "
            f"Pending={len(st.pending_effects)} Trig={len(st.triggers)}"
        )

    def dfs(cur: GameState, depth: int, seq: list[str], trace: list[str]) -> None:
        nonlocal best_score, best_sequence, best_state, best_trace

        heuristic_now = evaluate_state(cur)
        sig = (depth, cur.state_signature())
        if visited_depth_score.get(sig, -inf) >= heuristic_now:
            return
        visited_depth_score[sig] = heuristic_now

        actions = legal_actions(cur, cards)
        if depth >= max_depth or not actions:
            rolled = advance_one_full_turn(cur)
            terminal_score = evaluate_state(rolled)
            terminal_trace = trace + [f"AdvanceTurn -> {summarize(rolled)}"]

            if terminal_score > best_score:
                best_score = terminal_score
                best_sequence = list(seq)
                best_state = rolled
                best_trace = terminal_trace
            return

        next_states: list[tuple[PlayCardAction, GameState, float]] = []
        for action in actions:
            nxt = simulate_play(cur, action, cards)
            next_states.append((action, nxt, evaluate_state(nxt)))

        next_states.sort(key=lambda x: x[2], reverse=True)
        if beam_width is not None:
            next_states = next_states[:beam_width]

        for action, nxt, _ in next_states:
            label = _action_label(action)
            step_summary = f"Play={label} -> {summarize(nxt)}"
            dfs(nxt, depth + 1, seq + [label], trace + [step_summary])

    dfs(state.clone(), 0, [], [f"Start -> {summarize(state)}"])
    return PlanResult(best_sequence, best_score, best_state, best_trace)
