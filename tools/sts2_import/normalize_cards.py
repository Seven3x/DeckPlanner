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
from raw_catalog_builder import build_catalog_from_directory

SCHEMA_VERSION = "sts2_cards.normalized.v1"
REQUIRED_FIELDS = ["name", "character", "cost", "type", "rarity", "text"]
DEFAULT_SINGLE_INPUT = "data/sts2/raw/cards_sample.json"
DEFAULT_SINGLE_OUTPUT = "data/sts2/normalized/cards.json"
DEFAULT_MANIFEST = "source_manifest.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize raw STS2 card data into canonical schema")

    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "--input",
        default=None,
        help="Path to raw card data JSON",
    )
    input_group.add_argument(
        "--input-dir",
        default=None,
        help="Versioned raw catalog directory, e.g. data/sts2/raw/<version>",
    )

    parser.add_argument(
        "--manifest",
        default=DEFAULT_MANIFEST,
        help="Manifest filename used in --input-dir mode",
    )
    parser.add_argument(
        "--version",
        default=None,
        help="Catalog version label used for output naming and source metadata",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path for normalized output JSON",
    )
    return parser.parse_args()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _relative_to_repo(path: Path) -> str:
    repo_root = _repo_root()
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path.resolve())


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


def _normalize_source(
    raw_source: Any,
    *,
    default_input_path: Path,
    index: int,
    version: str | None,
) -> dict[str, Any]:
    source: dict[str, Any] = {}
    if raw_source is not None:
        if not isinstance(raw_source, dict):
            raise ValueError("source must be an object when provided")
        source.update(raw_source)

    raw_file_default = _relative_to_repo(default_input_path)
    source.setdefault("raw_file", raw_file_default)
    source.setdefault("raw_index", index)
    source.setdefault("importer", "tools/sts2_import/normalize_cards.py")
    source.setdefault("schema_version", SCHEMA_VERSION)

    if version:
        source.setdefault("version", version)
    if "source_file" not in source and isinstance(source.get("raw_file"), str):
        source["source_file"] = source["raw_file"]

    return source


def normalize_cards(
    raw_cards: list[dict[str, Any]],
    *,
    default_input_path: Path,
    version: str | None,
) -> list[dict[str, Any]]:
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

            source = _normalize_source(
                raw.get("source"),
                default_input_path=default_input_path,
                index=index,
                version=version,
            )

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


def _validate_output_payload(payload: dict[str, Any], schema_path: Path) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    if not isinstance(schema, dict):
        raise ValueError("cards.schema.json must be a JSON object")

    required_top = schema.get("required", [])
    for key in required_top:
        if key not in payload:
            raise ValueError(f"normalized payload missing required top-level key '{key}'")

    if schema.get("additionalProperties") is False:
        allowed = set(schema.get("properties", {}).keys())
        extras = sorted(set(payload.keys()) - allowed)
        if extras:
            raise ValueError(f"normalized payload has unknown top-level keys: {extras}")

    cards = payload.get("cards")
    if not isinstance(cards, list):
        raise ValueError("normalized payload cards must be a list")

    card_count = payload.get("card_count")
    if not isinstance(card_count, int):
        raise ValueError("normalized payload card_count must be an integer")
    if card_count != len(cards):
        raise ValueError(f"card_count mismatch: {card_count} != {len(cards)}")

    defs = schema.get("$defs", {})
    card_schema = defs.get("card", {}) if isinstance(defs, dict) else {}
    card_required = card_schema.get("required", []) if isinstance(card_schema, dict) else []
    card_props = card_schema.get("properties", {}) if isinstance(card_schema, dict) else {}

    enum_type = set(card_props.get("type", {}).get("enum", []))
    enum_rarity = set(card_props.get("rarity", {}).get("enum", []))
    enum_behavior = set(card_props.get("behavior_key", {}).get("enum", []))

    for idx, card in enumerate(cards):
        if not isinstance(card, dict):
            raise ValueError(f"cards[{idx}] must be an object")

        for key in card_required:
            if key not in card:
                raise ValueError(f"cards[{idx}] missing required key '{key}'")

        if card_schema.get("additionalProperties") is False:
            allowed_card = set(card_props.keys())
            extras = sorted(set(card.keys()) - allowed_card)
            if extras:
                raise ValueError(f"cards[{idx}] has unknown keys: {extras}")

        if not isinstance(card.get("id"), str) or not card["id"].strip():
            raise ValueError(f"cards[{idx}].id must be a non-empty string")
        if not isinstance(card.get("name"), str) or not card["name"].strip():
            raise ValueError(f"cards[{idx}].name must be a non-empty string")
        if not isinstance(card.get("character"), str) or not card["character"].strip():
            raise ValueError(f"cards[{idx}].character must be a non-empty string")

        cost = card.get("cost")
        if isinstance(cost, bool) or not isinstance(cost, (int, str)):
            raise ValueError(f"cards[{idx}].cost must be int or string")
        if isinstance(cost, int) and cost < 0:
            raise ValueError(f"cards[{idx}].cost must be >= 0")
        if isinstance(cost, str) and not cost.strip():
            raise ValueError(f"cards[{idx}].cost string must not be empty")

        card_type = card.get("type")
        if not isinstance(card_type, str) or card_type not in enum_type:
            raise ValueError(f"cards[{idx}].type invalid: {card_type}")

        rarity = card.get("rarity")
        if not isinstance(rarity, str) or rarity not in enum_rarity:
            raise ValueError(f"cards[{idx}].rarity invalid: {rarity}")

        tags = card.get("tags")
        if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
            raise ValueError(f"cards[{idx}].tags must be list[string]")

        text = card.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"cards[{idx}].text must be a non-empty string")

        behavior_key = card.get("behavior_key")
        if not isinstance(behavior_key, str) or behavior_key not in enum_behavior:
            raise ValueError(f"cards[{idx}].behavior_key invalid: {behavior_key}")

        if not isinstance(card.get("params"), dict):
            raise ValueError(f"cards[{idx}].params must be an object")
        if not isinstance(card.get("source"), dict):
            raise ValueError(f"cards[{idx}].source must be an object")


def _resolve_inputs(
    args: argparse.Namespace,
    repo_root: Path,
) -> tuple[list[dict[str, Any]], Path, str | None, dict[str, Any] | None]:
    if args.input_dir:
        input_dir = (repo_root / args.input_dir).resolve()
        raw_cards, catalog_meta = build_catalog_from_directory(
            input_dir,
            version=args.version,
            manifest_name=args.manifest,
        )
        resolved_version = catalog_meta.get("version")
        return raw_cards, input_dir, resolved_version, catalog_meta

    input_path_arg = args.input or DEFAULT_SINGLE_INPUT
    input_path = (repo_root / input_path_arg).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Raw input does not exist: {input_path}")

    raw_cards = _load_raw_cards(input_path)
    return raw_cards, input_path, args.version, None


def _default_output_for_version(version: str) -> Path:
    return _repo_root() / "data" / "sts2" / "normalized" / f"cards.{version}.json"


def _resolve_output_path(args: argparse.Namespace, resolved_version: str | None, repo_root: Path) -> Path:
    if args.output:
        return (repo_root / args.output).resolve()

    if resolved_version:
        return _default_output_for_version(resolved_version)

    return (repo_root / DEFAULT_SINGLE_OUTPUT).resolve()


def main() -> None:
    args = parse_args()
    repo_root = _repo_root()

    raw_cards, source_path, resolved_version, catalog_meta = _resolve_inputs(args, repo_root)
    normalized_cards = normalize_cards(
        raw_cards,
        default_input_path=source_path,
        version=resolved_version,
    )

    output_path = _resolve_output_path(args, resolved_version, repo_root)
    output_payload = {
        "schema_version": SCHEMA_VERSION,
        "card_count": len(normalized_cards),
        "cards": normalized_cards,
    }

    schema_path = repo_root / "data/sts2/normalized/cards.schema.json"
    _validate_output_payload(output_payload, schema_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    rel_output = _relative_to_repo(output_path)
    rel_source = _relative_to_repo(source_path)
    print(f"Normalized {len(normalized_cards)} cards from {rel_source} -> {rel_output}")
    print(f"card_count={len(normalized_cards)}")

    if catalog_meta:
        print(
            "catalog_summary="
            f"files:{catalog_meta['source_file_count']},"
            f"duplicates_dropped:{catalog_meta['duplicate_rows_dropped']},"
            f"version:{catalog_meta['version']}"
        )


if __name__ == "__main__":
    main()
