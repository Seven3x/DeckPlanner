from __future__ import annotations

import argparse
from pathlib import Path
import sys


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


REPO_ROOT = _repo_root()
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from slay2_ai.game_state import EnemyState, GameState
from slay2_ai.importers import load_normalized_catalog, resolve_normalized_catalog_path
from slay2_ai.planner import legal_actions


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load normalized STS2 catalog into runtime for smoke checks")
    parser.add_argument(
        "--input",
        default=None,
        help="Optional normalized file path (default: cards.json or --version)",
    )
    parser.add_argument(
        "--version",
        default=None,
        help="Optional version label for loading cards.<version>.json from normalized dir",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = REPO_ROOT

    if args.input:
        normalized_path = (repo_root / args.input).resolve()
    else:
        normalized_path = resolve_normalized_catalog_path(
            version=args.version,
            normalized_dir=repo_root / "data/sts2/normalized",
        )

    cards, summary = load_normalized_catalog(normalized_path)

    try:
        catalog_file = normalized_path.relative_to(repo_root)
    except ValueError:
        catalog_file = normalized_path
    print(f"Catalog file: {catalog_file}")
    print(f"Total cards: {summary.total_cards}")
    print(f"Executable cards: {summary.executable_cards}")
    print(f"Mapped cards: {summary.mapped_cards}")
    print(f"Text-only cards: {summary.text_only_cards}")
    print(f"Unimplemented cards: {summary.unimplemented_cards}")

    preferred_hand = [
        "sample.strike_alpha",
        "sample.banked_charge",
        "sample.unknown_formula",
    ]
    if all(card_id in cards for card_id in preferred_hand):
        hand = preferred_hand
        text_only_probe = "sample.unknown_formula"
    else:
        executable_ids = sorted(card_id for card_id, card in cards.items() if card.executable)
        non_executable_ids = sorted(card_id for card_id, card in cards.items() if not card.executable)

        if not executable_ids:
            raise AssertionError("expected at least one executable card")

        hand = executable_ids[:2]
        text_only_probe = non_executable_ids[0] if non_executable_ids else executable_ids[0]
        hand.append(text_only_probe)

    draw_pile = [next(iter(cards.keys()))]

    state = GameState(
        player_hp=40,
        player_max_hp=60,
        energy=3,
        block=0,
        buffs={},
        debuffs={},
        hand=hand,
        draw_pile=draw_pile,
        discard_pile=[],
        exhaust_pile=[],
        turn_index=1,
        cards_played_this_turn=[],
        attack_count_this_turn=0,
        skill_count_this_turn=0,
        pending_effects=[],
        triggers=[],
        enemy_state=EnemyState(hp=45, max_hp=45, block=0, intent_damage=8),
        rng_seed=11,
    )

    actions = legal_actions(state, cards)
    action_ids = [action.card_id for action in actions]
    print(f"Legal actions from sample state: {action_ids}")

    assert summary.total_cards == len(cards), "summary total count mismatch"
    assert summary.executable_cards > 0, "expected at least one executable card"
    assert summary.unimplemented_cards > 0 or summary.text_only_cards > 0, (
        "expected at least one non-executable card"
    )
    assert text_only_probe not in action_ids, "text_only/non-executable card should not be executable"
    print("Validation checks passed.")


if __name__ == "__main__":
    main()
