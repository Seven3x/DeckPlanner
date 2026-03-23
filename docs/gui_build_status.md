# GUI 构建状态

## 当前 GUI 目标
- 为 `slay2_ai` 提供一个本地单机助手面板（PySide6 + Qt Widgets）。
- 保持 GUI 与核心逻辑解耦，在不重构 `slay2_ai` 的前提下完善交互能力。
- 完成“可交互 demo + planner 搜索 + 候选分支比较 + 步骤回放详情 + 手动打牌 + JSON 状态载入 + 四类真实日志”。

## 当前阶段
- Stage 4: MVP 收尾（状态载入 / 分支比较 / 详情增强 / 接口梳理）已完成。

## 第 4 阶段已完成项

### 1) 从 JSON 载入状态（可用）
- 右侧操作区 `加载 JSON` 按钮可选择文件并载入状态。
- 新增 `services/json_state_adapter.py`：
  - 在 GUI 侧完成 `JSON -> GameState` 适配，不改核心 `slay2_ai` 数据结构。
  - 支持字段：
    - `player` 基础状态
    - `enemy` 基础状态
    - `zones.hand/draw_pile/discard_pile/exhaust_pile`
    - `buffs/debuffs`
    - `pending_effects`
    - `triggers`
- 触发器条件（condition）当前支持：
  - `always`
  - `player_hp_ratio_lte`
  - `attack_count_before_gte`
- 对未支持 condition 的兼容策略（会写日志）：
  - trigger condition：按 `always` 处理
  - `Conditional` effect condition：默认走 `if_false`
- 提供示例文件：`docs/gui_state_schema_v1.example.json`

### 2) 动作分支比较（可用）
- 搜索结果区保留候选分支列表，并支持在候选列表中多选两个分支。
- 新增分支比较视图，展示：
  - 总分差异（A-B）
  - 动作序列逐步差异
  - 最终状态摘要差异（核心指标差异）
- 同时保留单分支步骤浏览能力：选中分支后可继续查看其步骤详情。

### 3) 步骤详情增强（可用）
- 每一步详情新增并统一展示：
  - 动作信息（card_id / discard_choices / exhaust_choices）
  - 动作前后状态摘要
  - 关键字段变化（HP/能量/格挡/牌堆计数/buff/debuff 等）
  - effect 日志
  - trigger / pending 变化
  - 相关日志片段（event/effect 摘要）

### 4) GUI 与核心接口梳理（已完成本阶段目标）
- 状态入口统一到 `CoreGameService._replace_state(...)`：
  - demo 载入
  - JSON 载入
  - manual action 状态迁移
- 主窗口职责保持在 UI 事件编排，不直接处理核心状态转换细节。
- 保持层次：
  - GUI Widgets (`widgets/*`) -> Service/Adapter (`services/*`) -> `slay2_ai` 核心
- `CoreGameService` 中状态管理、步骤构建、候选分支构建职责清晰化，便于后续扩展状态编辑器/外部数据源。

## 本阶段新增/修改文件
- 新增：
  - `src/slay2_ai_gui/services/json_state_adapter.py`
  - `docs/gui_state_schema_v1.example.json`
- 修改：
  - `src/slay2_ai_gui/services/core_adapter.py`
  - `src/slay2_ai_gui/services/__init__.py`
  - `src/slay2_ai_gui/models/view_models.py`
  - `src/slay2_ai_gui/models/__init__.py`
  - `src/slay2_ai_gui/widgets/status_tabs.py`
  - `src/slay2_ai_gui/main_window.py`
  - `docs/gui_build_status.md`

## JSON Schema（v1）摘要
- `schema_version: "slay2_gui_state.v1"`
- `player`:
  - `hp, max_hp, energy, block, buffs, debuffs`
- `enemy`:
  - `hp, max_hp, block, intent_damage, buffs, debuffs`
- `zones`:
  - `hand, draw_pile, discard_pile, exhaust_pile`
- `turn`:
  - `turn_index, cards_played_this_turn, attack_count_this_turn, skill_count_this_turn, rng_seed`
- `pending_effects[]`:
  - `execute_turn, label, effect`
- `triggers[]`:
  - `event, label, remaining_uses, expire_turn, condition, effect`

支持的 effect type（当前适配器）：
- `DealDamage`
- `GainBlock`
- `DrawCards`
- `GainEnergy`
- `ApplyBuff`
- `ApplyDebuff`
- `SetNextAttackBonus`
- `SetReplayNextCard`
- `DiscardCards`
- `ExhaustFromHand`
- `ScheduleEffect`
- `Conditional`
- `AddTriggerEffect`

## 使用说明（第 4 阶段）

### A. 从 JSON 载入状态
1. 点击右侧 `加载 JSON`。
2. 选择符合 `slay2_gui_state.v1` 的 JSON 文件（可参考 `docs/gui_state_schema_v1.example.json`）。
3. 载入成功后：
   - 左侧状态面板刷新为 JSON 中状态
   - 搜索结果会被清空（防止旧结果污染）
   - 日志区输出载入来源和兼容警告（如有）

### B. 比较两个候选分支
1. 点击 `搜索最优序列`。
2. 在“搜索结果详情”标签页的“候选分支”列表中，选择两个分支（支持多选）。
3. “分支对比”区域会显示：
   - 总分差异
   - 动作序列逐步对比
   - 最终状态差异（Player/Enemy/手牌/牌堆/Pending/Triggers）
4. 若只选中一个分支：
   - 对比区域显示该分支最终状态摘要
   - 下方仍可浏览该分支步骤详情

## 已知限制与后续建议
- `condition` 仍是“部分可恢复”能力；复杂自定义 callable 无法直接 JSON 反序列化。
- 搜索仍在主线程，深度较大时可能卡顿；下一阶段建议接入 `QThread` 或 `QtConcurrent`。
- 候选分支仍是“首步展开 + 后续最优”的近似视图，不是完整搜索树可视化。

## 验收对照（本阶段）
- GUI 可从 JSON 载入一个状态：已完成。
- GUI 可比较不同候选分支：已完成。
- 步骤详情更清楚：已完成。
- 服务层/适配层更稳定：已完成。
- 文档状态文件更新完整：已完成。
