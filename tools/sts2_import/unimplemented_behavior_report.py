from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


REPO_ROOT = _repo_root()

PUNCT_TRANSLATION = str.maketrans(
    {
        "，": ",",
        "。": ".",
        "；": ";",
        "：": ":",
        "！": "!",
        "？": "?",
        "（": "(",
        "）": ")",
        "【": "[",
        "】": "]",
        "“": '"',
        "”": '"',
        "、": ",",
    }
)

CLAUSE_SPLITTER = re.compile(r"[\n。！？!?；;，,]")
DIGIT_RE = re.compile(r"\d+")
SPACE_RE = re.compile(r"\s+")
SEPARATOR_RE = re.compile(r"\s*([,.;:!?/])\s*")


@dataclass(frozen=True)
class KeywordSpec:
    keyword: str
    patterns: tuple[str, ...]


KEYWORD_SPECS: tuple[KeywordSpec, ...] = (
    KeywordSpec("apply", (r"\bapply\b", "给予", "施加")),
    KeywordSpec("gain", (r"\bgain\b", "获得")),
    KeywordSpec("draw", (r"\bdraw\b", "抽", "抽牌")),
    KeywordSpec("deal", (r"\bdeal\b", "造成", "攻击")),
    KeywordSpec("exhaust", (r"\bexhaust\b", "消耗")),
    KeywordSpec("discard", (r"\bdiscard\b", "丢弃")),
    KeywordSpec("retain", (r"\bretain\b", "保留")),
    KeywordSpec("poison", (r"\bpoison\b", "中毒")),
    KeywordSpec("weak", (r"\bweak\b", "虚弱")),
    KeywordSpec("vulnerable", (r"\bvulnerable\b", "易伤")),
    KeywordSpec("burn", (r"\bburn\b", "灼伤")),
    KeywordSpec("block", (r"\bblock\b", "格挡")),
    KeywordSpec("energy", (r"\benergy\b", "能量")),
    KeywordSpec("whenever", (r"\bwhenever\b", "每当")),
    KeywordSpec("at_the_start", (r"at the start", "回合开始时")),
    KeywordSpec("at_the_end", (r"at the end", "回合结束时")),
    KeywordSpec("if", (r"\bif\b", "如果")),
    KeywordSpec("for_each", (r"for each", "每有", "每张", "每次")),
    KeywordSpec("choose", (r"\bchoose\b", "选择")),
    KeywordSpec("random", (r"\brandom\b", "随机")),
    KeywordSpec("upgrade", (r"\bupgrade\b", "升级")),
)

DIRECT_SIMPLE_BLOCKERS = (
    "每当",
    "回合开始时",
    "回合结束时",
    "永久",
    "本局游戏",
    "本场战斗",
    "复制",
    "随机",
    "选择",
    "如果",
    "每有",
    "每次",
    "召唤",
    "铸造",
    "充能球",
    "变化",
    "重放",
)

PARAMETER_HINTS = (
    "如果",
    "每有",
    "每张",
    "每次",
    "随机",
    "选择",
    "x",
    "<x>",
    "至多",
    "最右侧",
)

TRIGGER_HINTS = (
    "每当",
    "回合开始时",
    "回合结束时",
    "当你",
    "下个回合",
    "直到",
)

COMPLEX_HINTS = (
    "永久",
    "本局游戏",
    "本场战斗",
    "变化",
    "替换",
    "充能球",
    "召唤",
    "铸造",
    "重放",
    "复制品",
    "名字中含有",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze unimplemented behavior cards from normalized STS2 data")
    parser.add_argument(
        "--input",
        default="data/sts2/normalized/cards.0.98.2.json",
        help="Path to normalized cards file",
    )
    parser.add_argument(
        "--version",
        default=None,
        help="Version label override (default: infer from input filename/source metadata)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=30,
        help="Top-N entries for text/prefix/keyword/pattern sections",
    )
    parser.add_argument(
        "--markdown-out",
        default=None,
        help="Markdown output path (default: docs/sts2_unimplemented_analysis_<version>.md)",
    )
    parser.add_argument(
        "--json-out",
        default=None,
        help="JSON output path (default: data/sts2/normalized/unimplemented_analysis.<version>.json)",
    )
    return parser.parse_args()


def _load_payload(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("normalized payload must be a JSON object")
    cards = payload.get("cards")
    if not isinstance(cards, list):
        raise ValueError("normalized payload must include cards: []")
    return payload


def _infer_version(path: Path, cards: list[dict[str, Any]], override: str | None) -> str:
    if override:
        return override

    match = re.match(r"^cards\.(?P<version>.+)\.json$", path.name)
    if match:
        return match.group("version")

    for card in cards:
        source = card.get("source")
        if isinstance(source, dict):
            version = source.get("version")
            if isinstance(version, str) and version.strip():
                return version.strip()

    return "default"


def _normalize_text(text: str) -> str:
    normalized = text.strip().lower().replace("\r\n", "\n").translate(PUNCT_TRANSLATION)
    normalized = DIGIT_RE.sub("<N>", normalized)
    normalized = re.sub(r"\bx\b", "<X>", normalized)
    normalized = re.sub(r"\s*\n\s*", " / ", normalized)
    normalized = SEPARATOR_RE.sub(r"\1 ", normalized)
    normalized = SPACE_RE.sub(" ", normalized)
    return normalized.strip(" .")


def _normalize_for_match(text: str) -> str:
    normalized = text.strip().lower().replace("\r\n", "\n").translate(PUNCT_TRANSLATION)
    normalized = DIGIT_RE.sub("<N>", normalized)
    normalized = SPACE_RE.sub(" ", normalized)
    return normalized


def _extract_prefix(text: str) -> str:
    if not text:
        return ""
    first = CLAUSE_SPLITTER.split(text.strip(), maxsplit=1)[0].strip()
    if not first:
        return ""
    first = DIGIT_RE.sub("<N>", first)
    first = SPACE_RE.sub(" ", first)
    return first


def _counter_to_rows(counter: Counter[Any]) -> list[dict[str, Any]]:
    return [{"key": str(key), "count": count} for key, count in sorted(counter.items(), key=lambda item: (-item[1], str(item[0])))]


def _classify_candidate(card: dict[str, Any], normalized_text: str) -> str:
    card_type = str(card.get("type") or "").lower()

    if any(hint in normalized_text for hint in COMPLEX_HINTS):
        return "complex_defer"
    if card_type in {"status", "curse", "other"}:
        return "complex_defer"

    has_trigger = any(hint in normalized_text for hint in TRIGGER_HINTS)
    if card_type == "power" or has_trigger:
        return "needs_new_effect_or_trigger"

    has_param = any(hint in normalized_text for hint in PARAMETER_HINTS)
    if has_param:
        return "needs_small_param_extraction"

    has_blocker = any(hint in normalized_text for hint in DIRECT_SIMPLE_BLOCKERS)
    if not has_blocker:
        return "likely_direct_mapping"

    return "needs_small_param_extraction"


def _pattern_type_mix(cards: list[dict[str, Any]]) -> dict[str, int]:
    mix: Counter[str] = Counter()
    for card in cards:
        mix[str(card.get("type") or "unknown")] += 1
    return dict(sorted(mix.items(), key=lambda item: (-item[1], item[0])))


def _pick_examples(cards: list[dict[str, Any]], limit: int = 4) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for card in sorted(cards, key=lambda item: (str(item.get("character")), str(item.get("name"))))[:limit]:
        rows.append(
            {
                "name": str(card.get("name") or card.get("id") or "unknown"),
                "id": str(card.get("id") or ""),
                "character": str(card.get("character") or "unknown"),
                "type": str(card.get("type") or "unknown"),
                "text": str(card.get("text") or "").replace("\n", " / "),
            }
        )
    return rows


def _render_table(lines: list[str], headers: list[str], rows: list[list[str]]) -> None:
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")


def _build_markdown(
    *,
    input_path: str,
    version: str,
    generated_at: str,
    top_n: int,
    total_cards: int,
    unimplemented_cards: list[dict[str, Any]],
    counts_by_character: Counter[str],
    counts_by_type: Counter[str],
    counts_by_rarity: Counter[str],
    counts_by_cost: Counter[str],
    top_texts: list[dict[str, Any]],
    top_prefixes: list[dict[str, Any]],
    top_keywords: list[dict[str, Any]],
    top_patterns: list[dict[str, Any]],
    safe_candidate_groups: dict[str, dict[str, Any]],
    representative_examples: dict[str, Any],
) -> str:
    lines: list[str] = []
    lines.append(f"# STS2 Unimplemented Behavior Analysis ({version})")
    lines.append("")
    lines.append(f"- Source file: `{input_path}`")
    lines.append(f"- Generated at (UTC): `{generated_at}`")
    lines.append(f"- Unimplemented filter: `behavior_key == \"unimplemented\"`")
    lines.append("")

    unimplemented_count = len(unimplemented_cards)
    ratio = (unimplemented_count / total_cards * 100.0) if total_cards else 0.0

    lines.append("## 概览")
    lines.append("")
    _render_table(
        lines,
        ["Metric", "Value"],
        [
            ["total_cards", str(total_cards)],
            ["unimplemented_cards", str(unimplemented_count)],
            ["unimplemented_ratio", f"{ratio:.2f}%"],
            ["analysis_top_n", str(top_n)],
        ],
    )

    lines.append("## 分布统计")
    lines.append("")

    def append_counter_section(title: str, counter: Counter[str]) -> None:
        lines.append(f"### {title}")
        lines.append("")
        rows = [[key, str(count)] for key, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))]
        _render_table(lines, ["Key", "Count"], rows)

    append_counter_section("By Character", counts_by_character)
    append_counter_section("By Type", counts_by_type)
    append_counter_section("By Rarity", counts_by_rarity)
    append_counter_section("By Cost", counts_by_cost)

    lines.append("## 文本高频统计")
    lines.append("")

    lines.append(f"### 最常见完整文本 Top {top_n}")
    lines.append("")
    _render_table(
        lines,
        ["Rank", "Count", "Text", "Sample Cards"],
        [
            [
                str(index + 1),
                str(item["count"]),
                item["text"].replace("\n", " / "),
                ", ".join(item["sample_cards"]),
            ]
            for index, item in enumerate(top_texts)
        ],
    )

    lines.append(f"### 最常见开头短语 Top {top_n}")
    lines.append("")
    _render_table(
        lines,
        ["Rank", "Count", "Prefix"],
        [[str(index + 1), str(item["count"]), item["prefix"]] for index, item in enumerate(top_prefixes)],
    )

    lines.append(f"### 关键词覆盖（含指定关键字）Top {top_n}")
    lines.append("")
    _render_table(
        lines,
        ["Rank", "Keyword", "Cards", "Match Patterns"],
        [
            [
                str(index + 1),
                item["keyword"],
                str(item["count"]),
                ", ".join(item["match_patterns"]),
            ]
            for index, item in enumerate(top_keywords)
        ],
    )

    lines.append("## 模板模式分析")
    lines.append("")
    lines.append("模板归并规则：统一大小写；将数字归一化为 `<N>`；将独立 `X/x` 归一化为 `<X>`；统一中英文标点；压缩换行和空白。")
    lines.append("")
    _render_table(
        lines,
        ["Rank", "Count", "Normalized Pattern", "Type Mix", "Sample Cards"],
        [
            [
                str(index + 1),
                str(item["count"]),
                item["pattern"],
                ", ".join(f"{k}:{v}" for k, v in item["type_mix"].items()),
                ", ".join(card["name"] for card in item["sample_cards"]),
            ]
            for index, item in enumerate(top_patterns)
        ],
    )

    lines.append("## 可安全扩展候选")
    lines.append("")
    lines.append("以下分组仅用于下一阶段补规则优先级，不在本次变更中落地行为映射。")
    lines.append("")

    section_titles = {
        "likely_direct_mapping": "1. 很可能可直接映射的简单模式",
        "needs_small_param_extraction": "2. 需要少量参数提取即可支持的模式",
        "needs_new_effect_or_trigger": "3. 需要新 effect/trigger 支持的模式",
        "complex_defer": "4. 暂时不建议动的复杂模式",
    }

    for key in (
        "likely_direct_mapping",
        "needs_small_param_extraction",
        "needs_new_effect_or_trigger",
        "complex_defer",
    ):
        group = safe_candidate_groups[key]
        lines.append(f"### {section_titles[key]}")
        lines.append("")
        lines.append(f"- Card count: **{group['count']}**")
        lines.append("")
        _render_table(
            lines,
            ["Rank", "Count", "Pattern", "Sample Cards"],
            [
                [
                    str(index + 1),
                    str(item["count"]),
                    item["pattern"],
                    ", ".join(card["name"] for card in item["sample_cards"]),
                ]
                for index, item in enumerate(group["top_patterns"])
            ],
        )

    lines.append("## 代表样例")
    lines.append("")

    lines.append("### 最常见未实现 Attack/Skill/Power")
    lines.append("")
    top_by_type_rows: list[list[str]] = []
    for card_type in ("attack", "skill", "power"):
        entry = representative_examples["most_common_by_type"].get(card_type)
        if not entry:
            continue
        top_by_type_rows.append(
            [
                card_type,
                str(entry["count"]),
                entry["pattern"],
                ", ".join(card["name"] for card in entry["sample_cards"]),
            ]
        )
    _render_table(lines, ["Type", "Count", "Pattern", "Sample Cards"], top_by_type_rows)

    lines.append("### 各角色代表性未实现卡（每角色至少3张）")
    lines.append("")
    insufficient_pool = representative_examples.get("insufficient_pool", {})
    if insufficient_pool:
        note = ", ".join(f"{key}:{value}" for key, value in sorted(insufficient_pool.items()))
        lines.append(f"- 注：以下角色在未实现集合中总数不足3张，未纳入该表：{note}")
        lines.append("")
    character_rows: list[list[str]] = []
    for character, cards in sorted(representative_examples["by_character"].items()):
        names = ", ".join(card["name"] for card in cards)
        character_rows.append([character, str(len(cards)), names])
    _render_table(lines, ["Character", "Examples", "Cards"], character_rows)

    lines.append("### 高频模板样例（卡名 + 文本）")
    lines.append("")
    for index, item in enumerate(top_patterns[: min(15, len(top_patterns))], start=1):
        lines.append(f"#### 模板 {index}: {item['pattern']} (n={item['count']})")
        lines.append("")
        for card in item["sample_cards"]:
            lines.append(f"- {card['name']}: {card['text']}")
        lines.append("")

    lines.append("## 建议的下一步实现顺序")
    lines.append("")
    lines.append("1. 先覆盖 `likely_direct_mapping` 的高频 Attack/Skill 模板，快速提升可执行率。")
    lines.append("2. 其次支持 `needs_small_param_extraction` 的条件/随机/X 变量抽取，优先低分支文本。")
    lines.append("3. 再补 `needs_new_effect_or_trigger`，优先通用触发器（回合开始/结束、每当打牌）。")
    lines.append("4. `complex_defer` 维持保守策略，待 effect 系统能力扩展后再分批处理。")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    args = parse_args()

    input_path = (REPO_ROOT / args.input).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Normalized input does not exist: {input_path}")

    payload = _load_payload(input_path)
    cards = payload["cards"]
    card_dicts = [card for card in cards if isinstance(card, dict)]
    total_cards = len(card_dicts)

    version = _infer_version(input_path, card_dicts, args.version)

    unimplemented_cards = [card for card in card_dicts if str(card.get("behavior_key")) == "unimplemented"]

    counts_by_character: Counter[str] = Counter(str(card.get("character") or "unknown") for card in unimplemented_cards)
    counts_by_type: Counter[str] = Counter(str(card.get("type") or "unknown") for card in unimplemented_cards)
    counts_by_rarity: Counter[str] = Counter(str(card.get("rarity") or "unknown") for card in unimplemented_cards)
    counts_by_cost: Counter[str] = Counter(str(card.get("cost") if card.get("cost") is not None else "unknown") for card in unimplemented_cards)

    text_counter: Counter[str] = Counter()
    text_examples: defaultdict[str, list[str]] = defaultdict(list)
    prefix_counter: Counter[str] = Counter()
    pattern_counter: Counter[str] = Counter()
    pattern_cards: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)

    keyword_hits: dict[str, set[str]] = {spec.keyword: set() for spec in KEYWORD_SPECS}

    for card in unimplemented_cards:
        card_name = str(card.get("name") or card.get("id") or "unknown")
        text = str(card.get("text") or "").strip()
        if not text:
            continue

        text_counter[text] += 1
        if len(text_examples[text]) < 5:
            text_examples[text].append(card_name)

        prefix = _extract_prefix(text)
        if prefix:
            prefix_counter[prefix] += 1

        pattern = _normalize_text(text)
        if pattern:
            pattern_counter[pattern] += 1
            pattern_cards[pattern].append(card)

        match_text = _normalize_for_match(text)
        for spec in KEYWORD_SPECS:
            if any(re.search(pattern, match_text, flags=re.IGNORECASE) for pattern in spec.patterns):
                keyword_hits[spec.keyword].add(card_name)

    top_n = max(1, int(args.top_n))

    top_texts = [
        {"text": text, "count": count, "sample_cards": text_examples[text]}
        for text, count in text_counter.most_common(top_n)
    ]
    top_prefixes = [{"prefix": prefix, "count": count} for prefix, count in prefix_counter.most_common(top_n)]

    top_keywords = sorted(
        (
            {
                "keyword": spec.keyword,
                "count": len(keyword_hits[spec.keyword]),
                "match_patterns": list(spec.patterns),
            }
            for spec in KEYWORD_SPECS
        ),
        key=lambda item: (-item["count"], item["keyword"]),
    )[:top_n]

    top_patterns = []
    for pattern, count in pattern_counter.most_common(top_n):
        cards_for_pattern = pattern_cards[pattern]
        top_patterns.append(
            {
                "pattern": pattern,
                "count": count,
                "type_mix": _pattern_type_mix(cards_for_pattern),
                "sample_cards": _pick_examples(cards_for_pattern, limit=5),
            }
        )

    candidate_cards: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for card in unimplemented_cards:
        text = str(card.get("text") or "")
        normalized = _normalize_for_match(text)
        category = _classify_candidate(card, normalized)
        candidate_cards[category].append(card)

    safe_candidate_groups: dict[str, dict[str, Any]] = {}
    for key in (
        "likely_direct_mapping",
        "needs_small_param_extraction",
        "needs_new_effect_or_trigger",
        "complex_defer",
    ):
        cards_in_group = candidate_cards.get(key, [])
        local_counter: Counter[str] = Counter()
        local_cards: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
        for card in cards_in_group:
            text = str(card.get("text") or "").strip()
            if not text:
                continue
            pattern = _normalize_text(text)
            local_counter[pattern] += 1
            local_cards[pattern].append(card)

        safe_candidate_groups[key] = {
            "count": len(cards_in_group),
            "top_patterns": [
                {
                    "pattern": pattern,
                    "count": count,
                    "sample_cards": _pick_examples(local_cards[pattern], limit=5),
                }
                for pattern, count in local_counter.most_common(top_n)
            ],
        }

    representative_by_type: dict[str, Any] = {}
    for card_type in ("attack", "skill", "power"):
        subset = [card for card in unimplemented_cards if str(card.get("type") or "") == card_type and str(card.get("text") or "").strip()]
        if not subset:
            continue
        counter: Counter[str] = Counter(_normalize_text(str(card.get("text") or "")) for card in subset)
        pattern, count = counter.most_common(1)[0]
        cards_for_pattern = [card for card in subset if _normalize_text(str(card.get("text") or "")) == pattern]
        representative_by_type[card_type] = {
            "pattern": pattern,
            "count": count,
            "sample_cards": _pick_examples(cards_for_pattern, limit=5),
        }

    global_pattern_count = pattern_counter.copy()
    by_character_examples: dict[str, list[dict[str, str]]] = {}
    insufficient_pool: dict[str, int] = {}
    for character, char_count in sorted(counts_by_character.items(), key=lambda item: (-item[1], item[0])):
        if char_count < 3:
            insufficient_pool[character] = char_count
            continue
        char_cards = [card for card in unimplemented_cards if str(card.get("character") or "unknown") == character]
        ranked = sorted(
            char_cards,
            key=lambda card: (
                -global_pattern_count[_normalize_text(str(card.get("text") or ""))],
                str(card.get("name") or card.get("id") or ""),
            ),
        )
        selected: list[dict[str, str]] = []
        seen_names: set[str] = set()
        for card in ranked:
            name = str(card.get("name") or card.get("id") or "unknown")
            if name in seen_names:
                continue
            seen_names.add(name)
            selected.append(
                {
                    "name": name,
                    "id": str(card.get("id") or ""),
                    "type": str(card.get("type") or "unknown"),
                    "text": str(card.get("text") or "").replace("\n", " / "),
                }
            )
            if len(selected) >= 3:
                break
        by_character_examples[character] = selected

    representative_examples = {
        "most_common_by_type": representative_by_type,
        "by_character": by_character_examples,
        "insufficient_pool": insufficient_pool,
    }

    summary = {
        "total_cards": total_cards,
        "unimplemented_cards": len(unimplemented_cards),
        "unimplemented_ratio": round((len(unimplemented_cards) / total_cards), 6) if total_cards else 0.0,
    }

    report = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_file": str(input_path.relative_to(REPO_ROOT)),
        "version": version,
        "summary": summary,
        "counts_by_character": _counter_to_rows(counts_by_character),
        "counts_by_type": _counter_to_rows(counts_by_type),
        "counts_by_rarity": _counter_to_rows(counts_by_rarity),
        "counts_by_cost": _counter_to_rows(counts_by_cost),
        "top_texts": top_texts,
        "top_prefixes": top_prefixes,
        "top_keywords": top_keywords,
        "normalized_patterns": top_patterns,
        "safe_candidate_groups": safe_candidate_groups,
        "representative_examples": representative_examples,
    }

    markdown_out = (REPO_ROOT / args.markdown_out).resolve() if args.markdown_out else (REPO_ROOT / "docs" / f"sts2_unimplemented_analysis_{version}.md").resolve()
    json_out = (REPO_ROOT / args.json_out).resolve() if args.json_out else (REPO_ROOT / "data" / "sts2" / "normalized" / f"unimplemented_analysis.{version}.json").resolve()

    markdown = _build_markdown(
        input_path=str(input_path.relative_to(REPO_ROOT)),
        version=version,
        generated_at=report["generated_at"],
        top_n=top_n,
        total_cards=total_cards,
        unimplemented_cards=unimplemented_cards,
        counts_by_character=counts_by_character,
        counts_by_type=counts_by_type,
        counts_by_rarity=counts_by_rarity,
        counts_by_cost=counts_by_cost,
        top_texts=top_texts,
        top_prefixes=top_prefixes,
        top_keywords=top_keywords,
        top_patterns=top_patterns,
        safe_candidate_groups=safe_candidate_groups,
        representative_examples=representative_examples,
    )

    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.write_text(markdown, encoding="utf-8")

    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Input: {input_path.relative_to(REPO_ROOT)}")
    print(f"Version: {version}")
    print(f"Total cards: {total_cards}")
    print(f"Unimplemented cards: {len(unimplemented_cards)} ({(len(unimplemented_cards) / total_cards * 100.0):.2f}%)")
    print("Counts by character:")
    for key, count in sorted(counts_by_character.items(), key=lambda item: (-item[1], item[0])):
        print(f"  {key}: {count}")
    print("Counts by type:")
    for key, count in sorted(counts_by_type.items(), key=lambda item: (-item[1], item[0])):
        print(f"  {key}: {count}")
    print("Top normalized patterns:")
    for item in top_patterns[:10]:
        print(f"  {item['count']}: {item['pattern']}")
    print("Safe candidate groups:")
    for key in (
        "likely_direct_mapping",
        "needs_small_param_extraction",
        "needs_new_effect_or_trigger",
        "complex_defer",
    ):
        print(f"  {key}: {safe_candidate_groups[key]['count']}")
    print(f"Markdown report written to: {markdown_out.relative_to(REPO_ROOT)}")
    print(f"JSON report written to: {json_out.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
