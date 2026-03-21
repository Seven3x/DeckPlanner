from __future__ import annotations

from pathlib import Path
import sys


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


REPO_ROOT = _repo_root()
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from slay2_ai.game_state import EnemyState, GameState
from slay2_ai.importers import load_normalized_catalog
from slay2_ai.planner import legal_actions


def main() -> None:
    repo_root = REPO_ROOT
    normalized_path = repo_root / "data/sts2/normalized/cards.json"

    cards, summary = load_normalized_catalog(normalized_path)

    print(f"Catalog file: {normalized_path.relative_to(repo_root)}")
    print(f"Total cards: {summary.total_cards}")
    print(f"Executable cards: {summary.executable_cards}")
    print(f"Mapped cards: {summary.mapped_cards}")
    print(f"Text-only cards: {summary.text_only_cards}")
    print(f"Unimplemented cards: {summary.unimplemented_cards}")

    state = GameState(
        player_hp=40,
        player_max_hp=60,
        energy=3,
        block=0,
        buffs={},
        debuffs={},
        hand=[
            "sample.strike_alpha",
            "sample.banked_charge",
            "sample.unknown_formula",
        ],
        draw_pile=["sample.combo_probe"],
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
    assert summary.text_only_cards > 0, "expected at least one text-only card"
    assert "sample.unknown_formula" not in action_ids, "text_only card should not be executable"
    print("Validation checks passed.")


if __name__ == "__main__":
    main()
