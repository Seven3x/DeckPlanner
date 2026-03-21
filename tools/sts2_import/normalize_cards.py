from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from behavior_registry import (
    BehaviorValidationError,
    normalize_behavior_key,
    validate_behavior_spec,
)

SCHEMA_VERSION = "sts2_cards.normalized.v1"
REQUIRED_FIELDS = ["name", "character", "cost", "type", "rarity", "text"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize raw STS2 card data into canonical schema")
    parser.add_argument(
        "--input",
        default="data/sts2/raw/cards_sample.json",
        help="Path to raw card data JSON",
    )
    parser.add_argument(
        "--output",
        default="data/sts2/normalized/cards.json",
        help="Path for normalized output JSON",
    )
    return parser.parse_args()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_raw_cards(input_path: Path) -> list[dict[str, Any]]:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        cards = payload
    elif isinstance(payload, dict):
        cards = payload.get("cards")
    else:
        raise ValueError("Raw input must be a JSON object or a JSON array")

    if not isinstance(cards, list):
        raise ValueError("Raw input must contain a 'cards' list")

    normalized_cards: list[dict[str, Any]] = []
    for idx, row in enumerate(cards):
        if not isinstance(row, dict):
            raise ValueError(f"cards[{idx}] must be an object")
        normalized_cards.append(row)

    return normalized_cards


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower())
    normalized = normalized.strip("_")
    return normalized or "unknown_card"


def _normalize_cost(raw_cost: Any, path: str) -> int | str:
    if isinstance(raw_cost, bool):
        raise ValueError(f"{path}.cost must not be boolean")
    if isinstance(raw_cost, int):
        return raw_cost
    if isinstance(raw_cost, str):
        token = raw_cost.strip()
        if token.isdigit():
            return int(token)
        upper = token.upper()
        if upper == "X":
            return "X"
        if token.lower() in {"variable", "var"}:
            return "variable"
        raise ValueError(f"{path}.cost unsupported string value '{raw_cost}'")
    raise ValueError(f"{path}.cost must be int or string")


def _normalize_tags(raw_tags: Any, path: str) -> list[str]:
    if raw_tags is None:
        return []
    if isinstance(raw_tags, str):
        if not raw_tags.strip():
            return []
        return [segment.strip() for segment in raw_tags.split(",") if segment.strip()]
    if isinstance(raw_tags, list):
        tags: list[str] = []
        for idx, tag in enumerate(raw_tags):
            if not isinstance(tag, str):
                raise ValueError(f"{path}.tags[{idx}] must be string")
            if tag.strip():
                tags.append(tag.strip())
        return tags
    raise ValueError(f"{path}.tags must be list[string] or string")


def _normalize_source(raw_source: Any, input_path: Path, index: int) -> dict[str, Any]:
    source: dict[str, Any] = {}
    if raw_source is not None:
        if not isinstance(raw_source, dict):
            raise ValueError("source must be an object when provided")
        source.update(raw_source)

    repo_root = _repo_root()
    try:
        raw_file = str(input_path.relative_to(repo_root))
    except ValueError:
        raw_file = str(input_path)

    source.setdefault("raw_file", raw_file)
    source.setdefault("raw_index", index)
    source.setdefault("importer", "tools/sts2_import/normalize_cards.py")
    source.setdefault("schema_version", SCHEMA_VERSION)
    return source


def normalize_cards(raw_cards: list[dict[str, Any]], input_path: Path) -> list[dict[str, Any]]:
    normalized_cards: list[dict[str, Any]] = []
    errors: list[str] = []
    seen_ids: set[str] = set()

    for index, raw in enumerate(raw_cards):
        path = f"cards[{index}]"
        try:
            for field_name in REQUIRED_FIELDS:
                if field_name not in raw:
                    raise ValueError(f"{path}.{field_name} is required")

            name = raw["name"]
            if not isinstance(name, str) or not name.strip():
                raise ValueError(f"{path}.name must be a non-empty string")

            character = raw["character"]
            if not isinstance(character, str) or not character.strip():
                raise ValueError(f"{path}.character must be a non-empty string")

            card_id = raw.get("id")
            if card_id is None:
                card_id = f"{_slugify(character)}.{_slugify(name)}"
            if not isinstance(card_id, str) or not card_id.strip():
                raise ValueError(f"{path}.id must be a non-empty string when provided")
            card_id = card_id.strip()
            if card_id in seen_ids:
                raise ValueError(f"Duplicate card id '{card_id}'")
            seen_ids.add(card_id)

            card_type = raw["type"]
            if not isinstance(card_type, str) or not card_type.strip():
                raise ValueError(f"{path}.type must be a non-empty string")

            rarity = raw["rarity"]
            if not isinstance(rarity, str) or not rarity.strip():
                raise ValueError(f"{path}.rarity must be a non-empty string")

            text = raw["text"]
            if not isinstance(text, str) or not text.strip():
                raise ValueError(f"{path}.text must be a non-empty string")

            normalized_cost = _normalize_cost(raw["cost"], path)
            normalized_tags = _normalize_tags(raw.get("tags", []), path)

            behavior_key = normalize_behavior_key(raw.get("behavior_key"))
            params = raw.get("params", {})
            validation_errors = validate_behavior_spec(behavior_key, params, path=path)
            if validation_errors:
                errors.extend(validation_errors)

            source = _normalize_source(raw.get("source"), input_path=input_path, index=index)

            normalized_cards.append(
                {
                    "id": card_id,
                    "name": name.strip(),
                    "character": character.strip().lower(),
                    "cost": normalized_cost,
                    "type": card_type.strip().lower(),
                    "rarity": rarity.strip().lower(),
                    "tags": normalized_tags,
                    "text": text.strip(),
                    "behavior_key": behavior_key,
                    "params": params if isinstance(params, dict) else {},
                    "source": source,
                }
            )
        except (ValueError, BehaviorValidationError) as exc:
            errors.append(str(exc))

    if errors:
        raise ValueError("\n".join(errors))

    return normalized_cards


def main() -> None:
    args = parse_args()
    repo_root = _repo_root()

    input_path = (repo_root / args.input).resolve()
    output_path = (repo_root / args.output).resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"Raw input does not exist: {input_path}")

    raw_cards = _load_raw_cards(input_path)
    normalized_cards = normalize_cards(raw_cards, input_path=input_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_payload = {
        "schema_version": SCHEMA_VERSION,
        "card_count": len(normalized_cards),
        "cards": normalized_cards,
    }
    output_path.write_text(json.dumps(output_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    rel_input = input_path.relative_to(repo_root)
    rel_output = output_path.relative_to(repo_root)
    print(f"Normalized {len(normalized_cards)} cards from {rel_input} -> {rel_output}")


if __name__ == "__main__":
    main()
