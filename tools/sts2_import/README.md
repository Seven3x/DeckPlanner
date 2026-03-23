# STS2 导入工具

该目录提供 Slay the Spire 2 卡牌数据的离线导入流水线。

## 目录说明

- `normalize_cards.py`：将仓库原生 raw 数据规范化为 `cards.json` 或 `cards.<version>.json`
- `raw_catalog_builder.py`：将版本目录下的多 raw 文件合并为一个 catalog
- `import_sts2_database.py`：将外部“单文件单卡 JSON”直接导入 normalized schema
- `behavior_registry.py`：normalizer 使用的行为键校验逻辑
- `import_status_report.py`：生成 normalized 文件的导入覆盖率统计
- `unimplemented_behavior_report.py`：对 `behavior_key == "unimplemented"` 做分布/文本/模板与候选规则分析
- `sample_raw_loader.py`：运行时加载 smoke check，验证导入结果可被 `slay2_ai` 消费

## 两条导入路径

仓库现在支持两条职责分离的导入路径：

1. 原生 raw catalog 路径（`raw_catalog_builder.py` + `normalize_cards.py`）
2. 外部单卡数据库路径（`import_sts2_database.py`）

职责区别：

- 原生路径用于仓库维护的 raw 数据集
- 外部路径用于第三方全量单卡 JSON 数据树

## 原始数据组织

### 1) 单文件模式（兼容旧流程）

- 将一个 JSON 放在 `data/sts2/raw/`
- payload 支持两种：
  - 卡牌数组 `[]`
  - 对象 `{"cards": []}`

参考样例：`data/sts2/raw/cards_sample.json`

### 2) 版本目录模式（原生 raw）

目录结构示例：

- `data/sts2/raw/<version>/`
  - `source_manifest.json`
  - `ironclad_cards.json`
  - `silent_cards.json`
  - `neutral_cards.json`
  - `status_cards.json`
  - `curse_cards.json`

示例目录：`data/sts2/raw/sample_full_catalog_v1/`

说明：

- `source_manifest.json` 可显式声明文件列表与 `source_kind`
- 若 manifest 不含 `files`，builder 会自动扫描 `*.json`（排除 manifest）

### 3) 外部单卡数据库模式（新）

建议结构：

- `data/sts2/external/sts2_database/<version>/`
  - 可按角色/状态/诅咒等任意分层
  - 每个文件是一个单卡 payload（顶层含 `card`）

当前仓库快照中的真实单卡数据集位于：

- `data/sts2/raw/ea_01/`

也就是，`external/sts2_database/` 当前主要是预留目录；若该目录下暂无版本子目录，可直接把 `data/sts2/raw/ea_01/` 当作单卡数据库输入运行 importer。

## 使用方式

### A. 构建原生 raw 合并 catalog（可选）

```bash
python tools/sts2_import/raw_catalog_builder.py \
  --input-dir data/sts2/raw/sample_full_catalog_v1
```

可选输出路径：

```bash
python tools/sts2_import/raw_catalog_builder.py \
  --input-dir data/sts2/raw/sample_full_catalog_v1 \
  --output /tmp/sts2_catalog_merged.json
```

### B. 规范化原生 raw

单文件到 `cards.json`：

```bash
python tools/sts2_import/normalize_cards.py \
  --input data/sts2/raw/cards_sample.json \
  --output data/sts2/normalized/cards.json
```

版本目录到 `cards.<version>.json`：

```bash
python tools/sts2_import/normalize_cards.py \
  --input-dir data/sts2/raw/sample_full_catalog_v1
```

等价显式写法：

```bash
python tools/sts2_import/normalize_cards.py \
  --input-dir data/sts2/raw/sample_full_catalog_v1 \
  --version sample_full_catalog_v1 \
  --output data/sts2/normalized/cards.sample_full_catalog_v1.json
```

说明：

- `--input` 与 `--input-dir` 互斥
- normalizer 会执行行为参数校验和 schema 结构校验
- 输出包含 `card_count`

### C. 导入外部单卡数据库（新）

基础命令：

```bash
python tools/sts2_import/import_sts2_database.py \
  --input-dir data/sts2/external/sts2_database/0.98.2 \
  --version 0.98.2
```

当前仓库内可直接运行的实际示例：

```bash
python tools/sts2_import/import_sts2_database.py \
  --input-dir data/sts2/raw/ea_01 \
  --version ea_01
```

可选输出路径：

```bash
python tools/sts2_import/import_sts2_database.py \
  --input-dir data/sts2/external/sts2_database/0.98.2 \
  --version 0.98.2 \
  --output data/sts2/normalized/cards.0.98.2.json
```

Importer 行为：

- 递归扫描 `--input-dir` 下所有 `.json`
- 仅导入符合“外部单卡数据库结构”的文件
- 不符合或解析失败的文件会跳过并统计
- 采用保守行为映射，仅对极少数明确文本映射到：
  - `deal_damage`
  - `gain_block`
  - `draw_cards`
  - `gain_energy`
  - `apply_debuff`（仅极明确的单句 `Weak / Vulnerable / Poison`）
- 无法安全映射的卡统一标记 `unimplemented`
- 在 `source` 中保留来源信息（版本、原始文本、变量、升级信息、原文件路径等）

## 导入状态报告

```bash
python tools/sts2_import/import_status_report.py \
  --input data/sts2/normalized/cards.sample_full_catalog_v1.json
```

命令输出包含：

- total cards
- executable cards
- mapped cards
- text_only cards
- unimplemented cards
- behavior key counts
- character counts
- type counts
- rarity counts

默认还会写入 markdown：

- `docs/sts2_import_status_<version>.md`

## 未实现行为分析报告

用于分析 `behavior_key == "unimplemented"` 的卡牌模式，给下一阶段补规则提供优先级依据。

```bash
python tools/sts2_import/unimplemented_behavior_report.py \
  --input data/sts2/normalized/cards.0.98.2.json
```

默认输出：

- 终端统计摘要（总体分布、Top 模板、候选分组计数）
- `docs/sts2_unimplemented_analysis_<version>.md`
- `data/sts2/normalized/unimplemented_analysis.<version>.json`

分析范围（仅统计，不改映射）：

- unimplemented 总量与按 character/type/rarity/cost 分布
- 文本高频（完整文本、开头短语、关键词）
- 轻量模板归并（数字归一化、标点统一、句式聚合）
- 安全扩展候选分组（直接映射/参数提取/需新 trigger/effect/复杂暂缓）

## 运行时加载检查

默认文件（`cards.json`）：

```bash
python tools/sts2_import/sample_raw_loader.py
```

版本文件（`cards.<version>.json`）：

```bash
python tools/sts2_import/sample_raw_loader.py --version sample_full_catalog_v1
```

## 关键说明

- `unimplemented` 是预期结果，不代表导入失败
- 当前“全量导入”定义为 catalog 完整性，不等于全部卡牌都已可执行
- 运行时导入适配位于 `src/slay2_ai/importers/`，与 GUI 主流程保持解耦
- smoke check 只要求存在“非可执行卡”，不再强制必须出现 `text_only`
