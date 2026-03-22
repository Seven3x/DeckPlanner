from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from normalize_cards import SCHEMA_VERSION, _validate_output_payload


MAPPED_BEHAVIOR_KEYS = {
    "deal_damage",
    "gain_block",
    "draw_cards",
    "gain_energy",
}

TYPE_MAP = {
    "attack": "attack",
    "skill": "skill",
    "power": "power",
    "status": "status",
    "curse": "curse",
}

RARITY_MAP = {
    "basic": "basic",
    "starter": "basic",
    "common": "common",
    "uncommon": "uncommon",
    "rare": "rare",
    "special": "special",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import external STS2 single-card database JSON files into normalized schema"
    )
    parser.add_argument(
        "--input-dir",
        required=True,
        help="Directory tree containing one-card-per-file JSON payloads",
    )
    parser.add_argument(
        "--version",
        default=None,
        help="Import version label used for output naming and source metadata",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output path for normalized cards JSON (default: data/sts2/normalized/cards.<version>.json)",
    )
    return parser.parse_args()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _relative_path(path: Path, base: Path) -> str:
    try:
        return str(path.resolve().relative_to(base.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def _resolve_input_dir(path_value: str, repo_root: Path) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = repo_root / path
    return path.resolve()


def _resolve_output_path(path_value: str | None, repo_root: Path, version: str) -> Path:
    if path_value:
        path = Path(path_value)
        if not path.is_absolute():
            path = repo_root / path
        return path.resolve()
    return (repo_root / "data" / "sts2" / "normalized" / f"cards.{version}.json").resolve()


def _normalize_cost(raw_cost: Any) -> int | str:
    if isinstance(raw_cost, bool):
        raise ValueError("card.cost must not be boolean")
    if isinstance(raw_cost, int):
        if raw_cost < 0:
            # Normalized schema disallows negative integer cost values.
            # Preserve source intent as a string token so cards stay in catalog
            # and remain non-executable at runtime.
            return str(raw_cost)
        return raw_cost
    if isinstance(raw_cost, str):
        token = raw_cost.strip()
        if not token:
            raise ValueError("card.cost string must not be empty")
        if token.isdigit():
            return int(token)
        if token.upper() == "X":
            return "X"
        if token.lower() in {"variable", "var"}:
            return "variable"
        return token
    raise ValueError("card.cost must be int or string")


def _normalize_type(raw_type: Any) -> str:
    if not isinstance(raw_type, str):
        return "other"
    return TYPE_MAP.get(raw_type.strip().lower(), "other")


def _normalize_rarity(raw_rarity: Any) -> str:
    if not isinstance(raw_rarity, str):
        return "special"
    return RARITY_MAP.get(raw_rarity.strip().lower(), "special")


def _pick_text(card: dict[str, Any]) -> str:
    for key in ("text_default_eng", "text_default_chs", "text_raw_eng", "text_raw_chs"):
        value = card.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise ValueError("card text missing: expected one of text_default_eng/text_default_chs/text_raw_eng/text_raw_chs")


def _remove_markup(text: str) -> str:
    return re.sub(r"\[(?:/?)[a-zA-Z_]+\]", "", text)


def _normalize_for_matching(text: str) -> str:
    stripped = _remove_markup(text).replace("\r\n", "\n").replace("\r", "\n").strip()
    return re.sub(r"\s+", " ", stripped)


def _parse_amount_token(token: str, variables: dict[str, Any]) -> int | None:
    token = token.strip()
    if token.isdigit():
        return int(token)

    placeholder = re.match(r"^\{(?P<name>[A-Za-z0-9_]+)(?::[^}]*)?\}$", token)
    if not placeholder:
        return None

    var_name = placeholder.group("name")
    value = variables.get(var_name)
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, str):
        matched = re.match(r"^\s*(\d+)", value)
        if matched:
            return int(matched.group(1))
    return None


def _infer_behavior(card: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    variables = card.get("variables")
    if not isinstance(variables, dict):
        variables = {}

    candidate_text = ""
    for key in ("text_default_eng", "text_raw_eng"):
        value = card.get(key)
        if isinstance(value, str) and value.strip():
            candidate_text = value.strip()
            break

    if not candidate_text:
        return "unimplemented", {}

    if "\n" in candidate_text or "\r" in candidate_text:
        return "unimplemented", {}

    text = _normalize_for_matching(candidate_text)
    patterns: list[tuple[re.Pattern[str], str]] = [
        (re.compile(r"^Deal (?P<amount>(?:\d+|X|\{[^{}]+\})) damage\.$", re.IGNORECASE), "deal_damage"),
        (re.compile(r"^Gain (?P<amount>(?:\d+|X|\{[^{}]+\})) Block\.$", re.IGNORECASE), "gain_block"),
        (re.compile(r"^Draw (?P<amount>(?:\d+|X|\{[^{}]+\})) cards?\.$", re.IGNORECASE), "draw_cards"),
        (re.compile(r"^Gain (?P<amount>(?:\d+|X|\{[^{}]+\})) Energy\.$", re.IGNORECASE), "gain_energy"),
    ]

    for pattern, behavior_key in patterns:
        matched = pattern.match(text)
        if not matched:
            continue
        amount = _parse_amount_token(matched.group("amount"), variables)
        if amount is None:
            return "unimplemented", {}
        return behavior_key, {"amount": amount}

    return "unimplemented", {}


def _is_single_card_payload(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    card = payload.get("card")
    return isinstance(card, dict)


def _normalize_single_card(
    *,
    payload: dict[str, Any],
    file_path: Path,
    input_dir: Path,
    repo_root: Path,
    import_version: str,
) -> dict[str, Any]:
    card = payload["card"]

    card_id = card.get("key")
    if not isinstance(card_id, str) or not card_id.strip():
        raise ValueError("card.key must be a non-empty string")

    name_eng = card.get("name_eng")
    name_chs = card.get("name_chs")
    if isinstance(name_eng, str) and name_eng.strip():
        name = name_eng.strip()
    elif isinstance(name_chs, str) and name_chs.strip():
        name = name_chs.strip()
    else:
        raise ValueError("card name missing: expected name_eng or name_chs")

    category = card.get("category")
    if not isinstance(category, str) or not category.strip():
        raise ValueError("card.category must be a non-empty string")

    normalized = {
        "id": card_id.strip(),
        "name": name,
        "character": category.strip().lower(),
        "cost": _normalize_cost(card.get("cost")),
        "type": _normalize_type(card.get("type")),
        "rarity": _normalize_rarity(card.get("rarity")),
        "tags": [],
        "text": _pick_text(card),
        "behavior_key": "unimplemented",
        "params": {},
        "source": {
            "source_kind": "sts2_database",
            "game_version": payload.get("game_version"),
            "database_version": payload.get("database_version"),
            "targetType": card.get("targetType"),
            "name_chs": card.get("name_chs"),
            "name_eng": card.get("name_eng"),
            "text_raw_chs": card.get("text_raw_chs"),
            "text_raw_eng": card.get("text_raw_eng"),
            "text_default_chs": card.get("text_default_chs"),
            "text_default_eng": card.get("text_default_eng"),
            "text_upgraded_chs": card.get("text_upgraded_chs"),
            "text_upgraded_eng": card.get("text_upgraded_eng"),
            "variables": card.get("variables"),
            "upgrades": card.get("upgrades"),
            "original_file": _relative_path(file_path, input_dir),
            "source_file": _relative_path(file_path, repo_root),
            "import_version": import_version,
            "version": import_version,
            "importer": "tools/sts2_import/import_sts2_database.py",
            "schema_version": SCHEMA_VERSION,
        },
    }

    behavior_key, params = _infer_behavior(card)
    normalized["behavior_key"] = behavior_key
    normalized["params"] = params
    return normalized


def _collect_json_files(input_dir: Path) -> list[Path]:
    return sorted(path for path in input_dir.rglob("*.json") if path.is_file())


def _ensure_unique_ids(cards: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for card in cards:
        card_id = card["id"]
        if card_id in seen:
            duplicates.add(card_id)
        seen.add(card_id)
    if duplicates:
        joined = ", ".join(sorted(duplicates))
        raise ValueError(f"Duplicate normalized card id(s) detected: {joined}")


def main() -> None:
    args = parse_args()
    repo_root = _repo_root()

    input_dir = _resolve_input_dir(args.input_dir, repo_root)
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")
    if not input_dir.is_dir():
        raise NotADirectoryError(f"Input path is not a directory: {input_dir}")

    resolved_version = (args.version.strip() if isinstance(args.version, str) and args.version.strip() else "")
    if not resolved_version:
        resolved_version = input_dir.name or "sts2_database"

    output_path = _resolve_output_path(args.output, repo_root, resolved_version)

    all_json_files = _collect_json_files(input_dir)
    normalized_cards: list[dict[str, Any]] = []
    skipped: list[tuple[str, str]] = []

    for file_path in all_json_files:
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception as exc:
            skipped.append((_relative_path(file_path, input_dir), f"invalid JSON: {exc}"))
            continue

        if not _is_single_card_payload(payload):
            skipped.append((_relative_path(file_path, input_dir), "not STS2 single-card database format"))
            continue

        try:
            normalized = _normalize_single_card(
                payload=payload,
                file_path=file_path,
                input_dir=input_dir,
                repo_root=repo_root,
                import_version=resolved_version,
            )
        except ValueError as exc:
            skipped.append((_relative_path(file_path, input_dir), str(exc)))
            continue

        normalized_cards.append(normalized)

    if not normalized_cards:
        raise ValueError("No valid STS2 single-card database entries were imported")

    _ensure_unique_ids(normalized_cards)

    payload = {
        "schema_version": SCHEMA_VERSION,
        "card_count": len(normalized_cards),
        "cards": normalized_cards,
    }
    schema_path = repo_root / "data" / "sts2" / "normalized" / "cards.schema.json"
    _validate_output_payload(payload, schema_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    executable_cards = sum(
        1
        for card in normalized_cards
        if card["behavior_key"] in MAPPED_BEHAVIOR_KEYS and isinstance(card["cost"], int)
    )
    unimplemented_cards = sum(1 for card in normalized_cards if card["behavior_key"] == "unimplemented")

    print(f"input_dir={_relative_path(input_dir, repo_root)}")
    print(f"output_file={_relative_path(output_path, repo_root)}")
    print(f"total_files_scanned={len(all_json_files)}")
    print(f"valid_cards_imported={len(normalized_cards)}")
    print(f"skipped_files={len(skipped)}")
    print(f"executable_cards={executable_cards}")
    print(f"unimplemented_cards={unimplemented_cards}")

    if skipped:
        preview = skipped[:10]
        print("skipped_file_samples:")
        for rel_path, reason in preview:
            print(f"  - {rel_path}: {reason}")
        if len(skipped) > len(preview):
            print(f"  - ... {len(skipped) - len(preview)} more")


if __name__ == "__main__":
    main()
