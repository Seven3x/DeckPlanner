# STS2 导入计划

## 导入目标

- 在不复制游戏源代码的前提下，构建可维护的 STS2 卡牌导入流水线。
- 保持导入路径为离线、本地文件驱动。
- 将原始数据归一化为稳定 schema，供 planner 和 GUI 使用。
- 即使行为执行支持不完整，也要支持完整卡牌目录导入（目录级完整性）。
- 为不可执行卡牌保留显式的 `text_only` / `unimplemented` 回退。

## 目录结构

- `tools/sts2_import/`
  - `normalize_cards.py`
  - `raw_catalog_builder.py`
  - `import_sts2_database.py`
  - `behavior_registry.py`
  - `import_status_report.py`
  - `sample_raw_loader.py`
  - `README.md`
- `data/sts2/raw/`
  - `cards_sample.json` (legacy single-file sample)
  - `<version>/` (versioned multi-file raw catalog)
    - `source_manifest.json`
    - multiple raw JSON files
- `data/sts2/normalized/`
  - `cards.json` (legacy default output)
  - `cards.<version>.json` (versioned normalized output)
  - schema files (`cards.schema.json`, `cards.schema.example.json`)
- `src/slay2_ai/importers/`
  - 运行时行为映射器和归一化加载器

## 标准 schema

每张归一化卡牌都使用以下字段：

- `id`：稳定且唯一的卡牌 ID
- `name`：显示名称
- `character`：所属池 / 角色键
- `cost`：整数费用或特殊字符串（`X`、`variable`）
- `type`：`attack` / `skill` / `power` / `status` / `curse` / `other`
- `rarity`：`basic` / `common` / `uncommon` / `rare` / `special`
- `tags`：文本标签列表
- `text`：用于显示的卡牌文本
- `behavior_key`：运行时行为映射键
- `params`：行为参数对象
- `source`：导入来源对象（包含版本 / 源文件元数据）

## 原始数据 -> 归一化流程

支持两条导入路径：

1. 原生原始目录路径（`raw_catalog_builder.py` + `normalize_cards.py`）
2. 外部单卡数据库路径（`import_sts2_database.py`）

原生路径继续负责仓库自有的原始卡牌目录。
外部路径专门用于从第三方单卡 JSON 导出中导入完整卡牌目录。

### 单文件模式

1. 将原始 JSON 放到 `data/sts2/raw/` 下。
2. 运行 `tools/sts2_import/normalize_cards.py --input ...`。
3. 脚本会校验必填字段、行为参数以及归一化 schema 结构。
4. 脚本会把归一化结果写入 `data/sts2/normalized/cards.json`（或自定义输出路径）。

### 带版本目录模式

1. 创建 `data/sts2/raw/<version>/`，其中包含 `source_manifest.json` 和多个原始 JSON 文件。
2. 可选的预合并检查：运行 `tools/sts2_import/raw_catalog_builder.py --input-dir ...`。
3. 运行 `tools/sts2_import/normalize_cards.py --input-dir data/sts2/raw/<version>`。
4. 脚本会合并文件、对重复 `id` 去重、校验行为/schema，并写出：
   - `data/sts2/normalized/cards.<version>.json`

校验内容包括：

- 必填卡牌字段
- 重复 `id` 检查（包括跨文件的冲突重复）
- 费用类型检查（`int` 或受支持的特殊标记）
- 行为键有效性
- `schedule_effect` 和 `conditional` 的嵌套行为校验
- 归一化负载的 schema 结构检查（`card_count`、必填字段、枚举字段）

### 外部单卡数据库模式

1. 将外部文件放在递归目录树下，例如：
   - `data/sts2/external/sts2_database/<version>/.../*.json`
2. 运行：
   - `python tools/sts2_import/import_sts2_database.py --input-dir ... --version <version>`
3. 导入器会递归扫描所有 `*.json`，只导入能识别的数据形态，并记录无效/不匹配文件及跳过原因。
4. 脚本会写出：
   - `data/sts2/normalized/cards.<version>.json`

外部导入器映射规则：

- 仅当文本明确为单效果时，才保守映射非常安全的行为（`deal_damage`、`gain_block`、`draw_cards`、`gain_energy`）。
- 也允许对精确单行 `Apply X Weak / Vulnerable / Poison.` 卡牌做极低风险的单目标 debuff 映射。
- 复杂 / power / 触发型 / 含糊不清的卡牌默认归为 `unimplemented`。
- 在 `source` 中保留丰富的来源信息，包括原始文件路径以及原始文本 / 变量 / 升级元数据。

仓库说明：

- 在当前仓库快照中，预留的外部目录可能是空的。
- 实际用于导入收敛的单卡数据集位于 `data/sts2/raw/ea_01/`，并且与外部导入器兼容，因为每个文件本身已经采用相同的单卡载荷结构。

## `behavior_key` 设计

已映射行为：

- `deal_damage`
- `gain_block`
- `draw_cards`
- `gain_energy`
- `apply_buff`
- `apply_debuff`
- `set_next_attack_bonus`
- `replay_next_card`
- `schedule_effect`
- `conditional`

回退行为：

- `text_only`
- `unimplemented`

## 与 `slay2_ai` 的运行时集成

- Runtime loader: `src/slay2_ai/importers/sts2_loader.py`
- Behavior mapper: `src/slay2_ai/importers/behavior_registry.py`
- Output: `dict[str, CardDefinition]`

集成规则：

- 已映射的行为键会转成真实的 `Effect` 对象。
- `text_only` / `unimplemented` 卡牌会以下列形式加载：
  - `executable=False`
  - empty `effects`
  - explicit tags and source markers
- Planner 会跳过不可执行卡牌，以避免错误模拟。
- 加载器现在同时支持：
  - `cards.json`
  - `cards.<version>.json` (by `version` argument)

## 导入状态报告

`tools/sts2_import/import_status_report.py` 会输出覆盖率指标：

- 总卡牌数
- 可执行卡牌数
- 已映射卡牌数
- 仅文本卡牌数
- 未实现卡牌数
- 行为键计数
- 角色计数
- 类型计数
- 稀有度计数

它也可以输出 Markdown 报告：

- `docs/sts2_import_status_<version>.md`

## 当前已支持

- 仅支持离线、本地文件导入
- 单文件和带版本目录的原始数据导入
- 多文件合并 + 重复检测 / 去重
- 归一化 schema + 行为校验
- 常见动作卡的运行时映射
- 条件效果和延迟效果映射
- 显式的不可执行占位卡牌
- 用于追踪导入进度的覆盖率 / 报告生成

## 尚未支持

- 每一种 STS2 卡牌机制的完整可执行行为
- 完整的条件语言
- 需要自定义引擎状态的复杂专有机制
- 自动升级处理（`+` 版本）和本地化包

## 当前对“完整卡牌导入”的定义

目录级完整性：所有卡牌都以稳定 ID 和元数据的形式出现在归一化数据中。
这并不意味着所有卡牌都已经在 planner/runtime 中可执行。

## 下一步扩展路径

1. 增加更丰富的条件注册表和触发器构造逻辑。
2. 增加卡牌升级变体和本地化元数据。
3. 增加导入器 + 规划器兼容性的回归测试。
4. 在 GUI 侧增加可选择版本的卡牌目录切换入口。
