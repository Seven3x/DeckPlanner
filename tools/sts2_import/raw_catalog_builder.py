from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MANIFEST_FILENAME = "source_manifest.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a merged STS2 raw catalog from a versioned directory"
    )
    parser.add_argument(
        "--input-dir",
        required=True,
        help="Raw catalog directory, e.g. data/sts2/raw/<version>",
    )
    parser.add_argument(
        "--manifest",
        default=MANIFEST_FILENAME,
        help="Manifest filename inside input dir",
    )
    parser.add_argument(
        "--version",
        default=None,
        help="Override version (default: manifest version or directory name)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional output path for merged raw catalog JSON",
    )
    return parser.parse_args()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _relative_to_repo(path: Path) -> str:
    repo_root = _repo_root()
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path.resolve())


def _extract_cards(payload: Any, path: Path) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        cards = payload
    elif isinstance(payload, dict):
        cards = payload.get("cards")
    else:
        raise ValueError(f"Raw file must be JSON list/object: {path}")

    if not isinstance(cards, list):
        raise ValueError(f"Raw file must provide cards list: {path}")

    normalized: list[dict[str, Any]] = []
    for idx, row in enumerate(cards):
        if not isinstance(row, dict):
            raise ValueError(f"{_relative_to_repo(path)} cards[{idx}] must be an object")
        normalized.append(row)
    return normalized


def _infer_source_kind(file_name: str) -> str:
    lower = file_name.lower()
    if "status" in lower:
        return "status_pool"
    if "curse" in lower:
        return "curse_pool"
    if "neutral" in lower:
        return "neutral_pool"
    return "character_pool"


def _normalize_source(
    raw_source: Any,
    *,
    version: str,
    source_file: str,
    source_kind: str,
    import_timestamp: str,
    manifest_file: str | None,
    raw_index_in_file: int,
) -> dict[str, Any]:
    source: dict[str, Any] = {}
    if raw_source is not None:
        if not isinstance(raw_source, dict):
            raise ValueError(f"source must be object when provided in {source_file}")
        source.update(raw_source)

    source.setdefault("version", version)
    source.setdefault("source_file", source_file)
    source.setdefault("source_kind", source_kind)
    source.setdefault("import_timestamp", import_timestamp)
    source.setdefault("raw_file", source_file)
    source.setdefault("raw_index_in_file", raw_index_in_file)
    if manifest_file:
        source.setdefault("source_manifest", manifest_file)
    return source


def _build_file_specs(
    input_dir: Path,
    manifest: dict[str, Any] | None,
    manifest_name: str,
) -> list[dict[str, str]]:
    if manifest and isinstance(manifest.get("files"), list) and manifest["files"]:
        file_specs: list[dict[str, str]] = []
        for idx, row in enumerate(manifest["files"]):
            if not isinstance(row, dict):
                raise ValueError(f"manifest.files[{idx}] must be an object")

            rel_path = row.get("path")
            if not isinstance(rel_path, str) or not rel_path.strip():
                raise ValueError(f"manifest.files[{idx}].path must be a non-empty string")

            source_kind = row.get("source_kind")
            if source_kind is None:
                source_kind = _infer_source_kind(Path(rel_path).name)
            if not isinstance(source_kind, str) or not source_kind.strip():
                raise ValueError(f"manifest.files[{idx}].source_kind must be a non-empty string")

            file_specs.append(
                {
                    "path": rel_path.strip(),
                    "source_kind": source_kind.strip(),
                }
            )
        return file_specs

    discovered_files = sorted(
        path for path in input_dir.glob("*.json") if path.name != manifest_name
    )
    if not discovered_files:
        raise ValueError(f"No raw json files found in {input_dir}")

    return [
        {
            "path": path.name,
            "source_kind": _infer_source_kind(path.name),
        }
        for path in discovered_files
    ]


def _canonical_card_for_dedupe(card: dict[str, Any]) -> str:
    payload = dict(card)
    payload.pop("source", None)
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


def build_catalog_from_directory(
    input_dir: Path,
    *,
    version: str | None = None,
    manifest_name: str = MANIFEST_FILENAME,
    import_timestamp: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    directory = input_dir.resolve()
    if not directory.exists() or not directory.is_dir():
        raise FileNotFoundError(f"Input directory does not exist: {directory}")

    manifest_path = directory / manifest_name
    manifest_payload: dict[str, Any] | None = None
    if manifest_path.exists():
        loaded_manifest = _load_json(manifest_path)
        if not isinstance(loaded_manifest, dict):
            raise ValueError("source_manifest.json must be a JSON object")
        manifest_payload = loaded_manifest

    resolved_version = version
    if not resolved_version and manifest_payload:
        manifest_version = manifest_payload.get("version")
        if isinstance(manifest_version, str) and manifest_version.strip():
            resolved_version = manifest_version.strip()
    if not resolved_version:
        resolved_version = directory.name

    timestamp = import_timestamp or datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    file_specs = _build_file_specs(directory, manifest_payload, manifest_name)
    manifest_file = _relative_to_repo(manifest_path) if manifest_path.exists() else None

    merged_cards: list[dict[str, Any]] = []
    seen_by_id: dict[str, str] = {}
    duplicate_ids: dict[str, list[str]] = {}

    for file_spec in file_specs:
        file_path = (directory / file_spec["path"]).resolve()
        if not file_path.exists():
            raise FileNotFoundError(f"manifest file entry not found: {file_path}")

        source_file = _relative_to_repo(file_path)
        source_kind = file_spec["source_kind"]
        raw_cards = _extract_cards(_load_json(file_path), file_path)

        for raw_index, raw_card in enumerate(raw_cards):
            row = dict(raw_card)
            row_source = _normalize_source(
                row.get("source"),
                version=resolved_version,
                source_file=source_file,
                source_kind=source_kind,
                import_timestamp=timestamp,
                manifest_file=manifest_file,
                raw_index_in_file=raw_index,
            )
            row["source"] = row_source

            card_id = row.get("id")
            if isinstance(card_id, str) and card_id.strip():
                canonical = _canonical_card_for_dedupe(row)
                if card_id in seen_by_id:
                    if seen_by_id[card_id] != canonical:
                        raise ValueError(
                            f"Duplicate card id with conflicting payload: '{card_id}' in {source_file}"
                        )
                    duplicate_ids.setdefault(card_id, []).append(source_file)
                    continue
                seen_by_id[card_id] = canonical

            merged_cards.append(row)

    metadata = {
        "version": resolved_version,
        "input_dir": _relative_to_repo(directory),
        "manifest_file": manifest_file,
        "source_file_count": len(file_specs),
        "raw_card_count": len(merged_cards) + sum(len(v) for v in duplicate_ids.values()),
        "duplicate_card_ids": sorted(duplicate_ids.keys()),
        "duplicate_rows_dropped": sum(len(v) for v in duplicate_ids.values()),
    }
    return merged_cards, metadata


def _default_output_path(version: str) -> Path:
    return _repo_root() / "data" / "sts2" / "raw" / f"catalog_merged.{version}.json"


def main() -> None:
    args = parse_args()
    repo_root = _repo_root()

    input_dir = (repo_root / args.input_dir).resolve()
    cards, metadata = build_catalog_from_directory(
        input_dir,
        version=args.version,
        manifest_name=args.manifest,
    )

    output_path: Path | None = None
    if args.output:
        output_path = (repo_root / args.output).resolve()
    elif metadata["version"]:
        output_path = _default_output_path(metadata["version"])

    payload = {
        "dataset": "sts2_catalog_merged",
        "version": metadata["version"],
        "cards": cards,
        "meta": metadata,
    }

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        try:
            rel_output = output_path.relative_to(repo_root)
        except ValueError:
            rel_output = output_path
        print(f"Wrote merged raw catalog to {rel_output}")

    duplicate_count = metadata["duplicate_rows_dropped"]
    print(
        f"Merged {len(cards)} cards from {metadata['source_file_count']} files "
        f"(dropped duplicates: {duplicate_count})"
    )


if __name__ == "__main__":
    main()
