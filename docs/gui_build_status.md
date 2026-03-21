# GUI Build Status

## 当前 GUI 目标
- 为 `slay2_ai` 提供一个本地单机助手面板（PySide6 + Qt Widgets）。
- 在不重构核心逻辑的前提下，建立可扩展 GUI 工程骨架。
- 先完成“可运行窗口 + 分层架构 + 基础调用链路”。

## 当前阶段
- Stage 1: 工程骨架与主窗口布局（进行中，已可运行）。

## 已完成项
- 新建 GUI 包：`src/slay2_ai_gui/`。
- 完成分层：`app.py`、`main_window.py`、`models/`、`widgets/`、`services/`、`logging/`。
- 主窗口布局完成：
  - 左侧状态区（4 个 tabs）：总览、手牌与牌堆、Triggers/Pending、搜索结果详情。
  - 右侧操作区（6 个按钮）：运行 demo、搜索最优序列、手动执行动作、加载 JSON、刷新状态、清空日志。
  - 底部日志区（4 通道）：事件触发、效果执行、搜索过程、错误异常。
- 建立 `CoreGameService` 作为 GUI 到核心逻辑的薄适配层。
- 建立 `GuiLogBus` 多通道日志桥，支持后续扩展更多日志来源。
- “运行 demo / 搜索最优序列 / 刷新状态 / 清空日志”已打通基础链路。
- “手动执行动作 / 加载 JSON”提供了 Stage-1 占位实现和扩展接口。
- `requirements.txt` 已加入 `PySide6` 依赖。

## 待完成项
- JSON 到 `GameState` 的完整映射与校验。
- 手动动作执行从“首个合法动作”升级为可选动作（下拉/列表）。
- 事件/效果日志从“服务层摘要”升级为“核心执行过程细粒度日志”。
- 搜索结果详情支持分支对比、终局状态快照、点击回放。
- 增加 UI 自动化测试与服务层单元测试。

## 新增文件列表
- `src/slay2_ai_gui/__init__.py`
- `src/slay2_ai_gui/__main__.py`
- `src/slay2_ai_gui/app.py`
- `src/slay2_ai_gui/main_window.py`
- `src/slay2_ai_gui/models/__init__.py`
- `src/slay2_ai_gui/models/view_models.py`
- `src/slay2_ai_gui/widgets/__init__.py`
- `src/slay2_ai_gui/widgets/action_panel.py`
- `src/slay2_ai_gui/widgets/log_panel.py`
- `src/slay2_ai_gui/widgets/status_tabs.py`
- `src/slay2_ai_gui/services/__init__.py`
- `src/slay2_ai_gui/services/core_adapter.py`
- `src/slay2_ai_gui/logging/__init__.py`
- `src/slay2_ai_gui/logging/log_bus.py`
- `docs/gui_build_status.md`

## 已知风险 / 技术债
- 当前 `triggers.emit_event`、`effects.apply` 没有统一日志 hook，GUI 只能记录服务层摘要。
- Stage-1 未引入线程/异步，搜索耗时增大后可能阻塞 UI。
- JSON 导入协议尚未固化，后续需定义 schema 与兼容策略。
- 当前状态展示以只读为主，尚未支持复杂交互编辑。

## 与核心逻辑的耦合点
- `CoreGameService` 直接调用：
  - `slay2_ai.card_defs.build_demo_cards`
  - `slay2_ai.demo.base_state`
  - `slay2_ai.planner.search_best_sequence / legal_actions / simulate_play`
  - `slay2_ai.evaluator.evaluate_state`
- GUI 不直接修改 `planner.py`/`game_state.py`/`effects.py` 内部实现，核心逻辑保持原状。

## 下一阶段建议
1. 先补 `JSON -> GameState` 适配器与字段校验，打通“加载后可刷新展示”。
2. 将“手动执行动作”改成可选动作列表，并显示动作预期影响。
3. 在不破坏核心逻辑的前提下，为 event/effect/search 增加标准日志回调接口。
4. 搜索功能放入 `QThread` 或 `QtConcurrent`，避免 UI 阻塞。
5. 增加基础测试（service 层 + GUI 冒烟启动测试）。
