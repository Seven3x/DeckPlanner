from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..card_defs import CardDefinition
from .behavior_registry import BehaviorBuildResult, UnsupportedBehaviorError, build_behavior

NORMALIZED_SCHEMA_VERSION = "sts2_cards.normalized.v1"
DEFAULT_NORMALIZED_DIR = Path("data/sts2/normalized")
DEFAULT_CATALOG_NAME = "cards.json"


@dataclass(frozen=True)
class NormalizedCard:
    card_id: str
    name: str
    character: str
    cost: int | str
    card_type: str
    rarity: str
    tags: list[str]
    text: str
    behavior_key: str
    params: dict[str, Any]
    source: dict[str, Any]


@dataclass(frozen=True)
class CatalogLoadSummary:
    total_cards: int
    executable_cards: int
    mapped_cards: int
    text_only_cards: int
    unimplemented_cards: int


class NormalizedCatalogError(ValueError):
    pass


def resolve_normalized_catalog_path(
    path: str | Path | None = None,
    *,
    version: str | None = None,
    normalized_dir: str | Path = DEFAULT_NORMALIZED_DIR,
) -> Path:
    if path is not None and version is not None:
        raise NormalizedCatalogError("Specify either 'path' or 'version', not both")

    if path is not None:
        return Path(path)

    base_dir = Path(normalized_dir)
    if version is not None:
        return base_dir / f"cards.{version}.json"

    return base_dir / DEFAULT_CATALOG_NAME


def load_normalized_catalog(
    path: str | Path | None = None,
    *,
    version: str | None = None,
    normalized_dir: str | Path = DEFAULT_NORMALIZED_DIR,
) -> tuple[dict[str, CardDefinition], CatalogLoadSummary]:
    resolved_path = resolve_normalized_catalog_path(
        path,
        version=version,
        normalized_dir=normalized_dir,
    )
    normalized_cards = load_normalized_cards(resolved_path)
    return build_card_catalog(normalized_cards)


def load_normalized_cards(path: str | Path) -> list[NormalizedCard]:
    input_path = Path(path)
    payload = json.loads(input_path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise NormalizedCatalogError("normalized cards file must be a JSON object")

    schema_version = payload.get("schema_version")
    if schema_version != NORMALIZED_SCHEMA_VERSION:
        raise NormalizedCatalogError(
            f"schema_version mismatch: expected '{NORMALIZED_SCHEMA_VERSION}', got '{schema_version}'"
        )

    raw_cards = payload.get("cards")
    if not isinstance(raw_cards, list):
        raise NormalizedCatalogError("normalized payload must include cards: []")

    cards: list[NormalizedCard] = []
    seen_ids: set[str] = set()
    for idx, row in enumerate(raw_cards):
        if not isinstance(row, dict):
            raise NormalizedCatalogError(f"cards[{idx}] must be an object")

        card = NormalizedCard(
            card_id=_required_str(row, "id", idx),
            name=_required_str(row, "name", idx),
            character=_required_str(row, "character", idx),
            cost=_required_cost(row, "cost", idx),
            card_type=_required_str(row, "type", idx),
            rarity=_required_str(row, "rarity", idx),
            tags=_required_str_list(row, "tags", idx),
            text=_required_str(row, "text", idx),
            behavior_key=_required_str(row, "behavior_key", idx),
            params=_required_dict(row, "params", idx),
            source=_required_dict(row, "source", idx),
        )

        if card.card_id in seen_ids:
            raise NormalizedCatalogError(f"duplicate card id '{card.card_id}'")
        seen_ids.add(card.card_id)
        cards.append(card)

    return cards


def build_card_catalog(normalized_cards: list[NormalizedCard]) -> tuple[dict[str, CardDefinition], CatalogLoadSummary]:
    card_defs: dict[str, CardDefinition] = {}

    mapped_cards = 0
    executable_cards = 0
    text_only_cards = 0
    unimplemented_cards = 0

    for card in normalized_cards:
        behavior_result = _safe_build_behavior(card.behavior_key, card.params)
        effective_status = behavior_result.status
        effective_note = behavior_result.note
        effective_executable = behavior_result.executable
        if effective_executable and not isinstance(card.cost, int):
            effective_executable = False
            effective_status = "unimplemented"
            cost_note = f"non-fixed cost '{card.cost}' is not executable in planner yet"
            effective_note = f"{effective_note}; {cost_note}" if effective_note else cost_note

        if effective_status == "mapped":
            mapped_cards += 1
        elif effective_status == "text_only":
            text_only_cards += 1
        else:
            unimplemented_cards += 1

        if effective_executable:
            executable_cards += 1

        tags = set(card.tags)
        if effective_executable:
            tags.add("behavior_mapped")
        else:
            tags.add("non_executable")
            tags.add(effective_status)

        source = dict(card.source)
        source["character"] = card.character
        source["rarity"] = card.rarity
        source["behavior_status"] = effective_status
        if effective_note:
            source["behavior_note"] = effective_note

        card_defs[card.card_id] = CardDefinition(
            card_id=card.card_id,
            name=card.name,
            cost=card.cost,
            card_type=card.card_type,
            effects=behavior_result.effects,
            exhaust=False,
            tags=tags,
            description=card.text,
            behavior_key=card.behavior_key,
            params=card.params,
            source=source,
            executable=effective_executable,
        )

    summary = CatalogLoadSummary(
        total_cards=len(normalized_cards),
        executable_cards=executable_cards,
        mapped_cards=mapped_cards,
        text_only_cards=text_only_cards,
        unimplemented_cards=unimplemented_cards,
    )
    return card_defs, summary


def _safe_build_behavior(behavior_key: str, params: dict[str, Any]) -> BehaviorBuildResult:
    try:
        return build_behavior(behavior_key, params)
    except UnsupportedBehaviorError as exc:
        return BehaviorBuildResult(
            effects=[],
            executable=False,
            status="unimplemented",
            note=str(exc),
        )


def _required_str(row: dict[str, Any], key: str, idx: int) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise NormalizedCatalogError(f"cards[{idx}].{key} must be a non-empty string")
    return value


def _required_cost(row: dict[str, Any], key: str, idx: int) -> int | str:
    value = row.get(key)
    if isinstance(value, bool):
        raise NormalizedCatalogError(f"cards[{idx}].{key} must be int or string")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip():
        return value
    raise NormalizedCatalogError(f"cards[{idx}].{key} must be int or string")


def _required_dict(row: dict[str, Any], key: str, idx: int) -> dict[str, Any]:
    value = row.get(key)
    if not isinstance(value, dict):
        raise NormalizedCatalogError(f"cards[{idx}].{key} must be an object")
    return value


def _required_str_list(row: dict[str, Any], key: str, idx: int) -> list[str]:
    value = row.get(key)
    if not isinstance(value, list):
        raise NormalizedCatalogError(f"cards[{idx}].{key} must be a list")

    tags: list[str] = []
    for tag_idx, tag in enumerate(value):
        if not isinstance(tag, str):
            raise NormalizedCatalogError(f"cards[{idx}].{key}[{tag_idx}] must be a string")
        if tag.strip():
            tags.append(tag.strip())
    return tags
