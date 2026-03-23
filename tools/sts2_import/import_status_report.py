from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


REPO_ROOT = _repo_root()
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from slay2_ai.importers import build_card_catalog, load_normalized_cards


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate import coverage/status report for normalized STS2 cards")
    parser.add_argument(
        "--input",
        default="data/sts2/normalized/cards.json",
        help="Path to normalized cards file",
    )
    parser.add_argument(
        "--version",
        default=None,
        help="Version label override (default: infer from filename/source metadata)",
    )
    parser.add_argument(
        "--markdown-out",
        default=None,
        help="Optional markdown output path (default: docs/sts2_import_status_<version>.md)",
    )
    return parser.parse_args()


def _load_payload(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("normalized payload must be a JSON object")
    return payload


def _infer_version(path: Path, cards: list[Any], override: str | None) -> str:
    if override:
        return override

    match = re.match(r"^cards\.(?P<version>.+)\.json$", path.name)
    if match:
        return match.group("version")

    for card in cards:
        if isinstance(card, dict):
            source = card.get("source")
            if isinstance(source, dict):
                version = source.get("version")
                if isinstance(version, str) and version.strip():
                    return version.strip()

    return "default"


def _format_counter_rows(counter: Counter[str]) -> list[tuple[str, int]]:
    return sorted(counter.items(), key=lambda item: (-item[1], item[0]))


def _build_markdown(
    *,
    input_path: str,
    version: str,
    generated_at: str,
    summary_rows: list[tuple[str, int]],
    behavior_counts: Counter[str],
    character_counts: Counter[str],
    type_counts: Counter[str],
    rarity_counts: Counter[str],
) -> str:
    lines: list[str] = []
    lines.append(f"# STS2 Import Status ({version})")
    lines.append("")
    lines.append(f"- Source file: `{input_path}`")
    lines.append(f"- Generated at (UTC): `{generated_at}`")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("| --- | ---: |")
    for key, value in summary_rows:
        lines.append(f"| {key} | {value} |")
    lines.append("")

    def add_table(title: str, rows: list[tuple[str, int]]) -> None:
        lines.append(f"## {title}")
        lines.append("")
        lines.append("| Key | Count |")
        lines.append("| --- | ---: |")
        for key, value in rows:
            lines.append(f"| {key} | {value} |")
        lines.append("")

    add_table("Behavior Key Counts", _format_counter_rows(behavior_counts))
    add_table("Character Counts", _format_counter_rows(character_counts))
    add_table("Type Counts", _format_counter_rows(type_counts))
    add_table("Rarity Counts", _format_counter_rows(rarity_counts))

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    args = parse_args()

    input_path = (REPO_ROOT / args.input).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Normalized input does not exist: {input_path}")

    payload = _load_payload(input_path)
    raw_cards = payload.get("cards")
    if not isinstance(raw_cards, list):
        raise ValueError("normalized payload must include cards: []")

    normalized_cards = load_normalized_cards(input_path)
    _, summary = build_card_catalog(normalized_cards)

    behavior_counts = Counter(card.behavior_key for card in normalized_cards)
    character_counts = Counter(card.character for card in normalized_cards)
    type_counts = Counter(card.card_type for card in normalized_cards)
    rarity_counts = Counter(card.rarity for card in normalized_cards)

    resolved_version = _infer_version(input_path, raw_cards, args.version)

    print(f"Catalog file: {input_path.relative_to(REPO_ROOT)}")
    print(f"Version: {resolved_version}")
    print(f"Total cards: {summary.total_cards}")
    print(f"Executable cards: {summary.executable_cards}")
    print(f"Mapped cards: {summary.mapped_cards}")
    print(f"Passive modeled cards: {summary.passive_modeled_cards}")
    print(f"Text-only cards: {summary.text_only_cards}")
    print(f"Unimplemented cards: {summary.unimplemented_cards}")

    print("Behavior key counts:")
    for key, count in _format_counter_rows(behavior_counts):
        print(f"  {key}: {count}")

    print("Character counts:")
    for key, count in _format_counter_rows(character_counts):
        print(f"  {key}: {count}")

    print("Type counts:")
    for key, count in _format_counter_rows(type_counts):
        print(f"  {key}: {count}")

    print("Rarity counts:")
    for key, count in _format_counter_rows(rarity_counts):
        print(f"  {key}: {count}")

    summary_rows = [
        ("total_cards", summary.total_cards),
        ("executable_cards", summary.executable_cards),
        ("mapped_cards", summary.mapped_cards),
        ("passive_modeled_cards", summary.passive_modeled_cards),
        ("text_only_cards", summary.text_only_cards),
        ("unimplemented_cards", summary.unimplemented_cards),
    ]

    markdown_path: Path | None = None
    if args.markdown_out:
        markdown_path = (REPO_ROOT / args.markdown_out).resolve()
    elif resolved_version:
        markdown_path = (REPO_ROOT / "docs" / f"sts2_import_status_{resolved_version}.md").resolve()

    if markdown_path is not None:
        generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        markdown = _build_markdown(
            input_path=str(input_path.relative_to(REPO_ROOT)),
            version=resolved_version,
            generated_at=generated_at,
            summary_rows=summary_rows,
            behavior_counts=behavior_counts,
            character_counts=character_counts,
            type_counts=type_counts,
            rarity_counts=rarity_counts,
        )
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(markdown, encoding="utf-8")
        print(f"Markdown report written to: {markdown_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
