# GUI Build Status

## 当前 GUI 目标
- 为 `slay2_ai` 提供一个本地单机助手面板（PySide6 + Qt Widgets）。
- 保持 GUI 与核心逻辑解耦，在不重构 `slay2_ai` 的前提下完善交互能力。
- 完成“可交互 demo + planner 搜索 + 步骤回放详情 + 手动打牌 + 四类真实日志”。

## 当前阶段
- Stage 3: 从静态展示工具升级为可交互本地助手面板（已完成）。

## Stage 3 已完成项
- Demo 接入（GUI 内数据流）：
  - `运行 demo` 按钮直接创建 `GameState`（通过 `demo.base_state`）。
  - 运行 demo 后会清理旧日志、清空旧搜索结果、刷新左侧状态展示。
  - demo 载入后可立即继续执行搜索或手动动作。
- Planner 接入（最优序列 + 候选分支）：
  - `搜索最优序列` 按钮调用 `search_best_sequence` 获取最佳动作序列与评分。
  - 搜索结果区展示总分、最佳序列。
  - 候选前 N 分支通过薄封装生成：
    - 枚举当前合法首步动作
    - 对每个首步状态继续调用 planner 搜索后续最优
    - 按最终评分排序后展示前 N 条分支
- 步骤详情查看（可点击）：
  - 推荐序列与候选分支中的每一步都可点击查看详情。
  - 详情包含：
    - 本步动作
    - 动作前状态摘要
    - 动作后状态摘要
    - 关键 events / effects
    - trigger 变化
    - pending changes 变化
    - 评分前后变化
- 手动执行动作：
  - 操作区新增“手动打牌”下拉框，展示当前手牌中可执行卡牌。
  - 点击 `执行所选手牌` 后执行所选卡牌并刷新状态。
  - 当前阶段仅要求“按卡牌选择”，若该卡牌存在多种 discard/exhaust 分支，默认取第一种并写日志说明。
  - 为后续复杂选择型动作预留扩展点（已保留 action variant 概念）。
- 四类日志真实接线：
  - 事件触发日志：真实捕获 `emit_event` 调用。
  - 效果执行日志：真实捕获 effect `apply` 执行（含 card/trigger/pending 来源）。
  - 搜索过程日志：记录搜索参数、候选分支评估、planner trace 摘要。
  - 错误/异常日志：统一通过 `publish_exception` 进入错误通道。
  - 日志接线策略为 service 层最小侵入式 runtime hook，不改核心算法行为。

## 本阶段新增/修改文件
- 修改：
  - `src/slay2_ai_gui/services/core_adapter.py`
  - `src/slay2_ai_gui/models/view_models.py`
  - `src/slay2_ai_gui/models/__init__.py`
  - `src/slay2_ai_gui/widgets/action_panel.py`
  - `src/slay2_ai_gui/widgets/status_tabs.py`
  - `src/slay2_ai_gui/main_window.py`
  - `docs/gui_build_status.md`

## 现状说明（可交互真实能力）
- 可以在 GUI 内运行 demo 并获得真实初始状态。
- 可以从 GUI 触发 planner 搜索并展示最优序列与评分。
- 可以展示候选前 N 分支（基于首步展开 + 后续 planner 的薄封装）。
- 可以点击具体步骤查看动作前后状态与关键执行细节。
- 可以手动选择并执行一张当前可打出的手牌。
- 四类日志均为真实执行过程产物，不是纯占位文本。

## 仍待完成项（下一阶段）
- 引入异步搜索执行（`QThread` / `QtConcurrent`），避免较深搜索阻塞 UI。
- 为手动动作补齐复杂交互（discard/exhaust/targeting 可视编辑）。
- 增加可视化状态 diff 组件（目前为摘要 + 关键变化列表）。
- 完成 `JSON -> GameState` 的正式映射与校验。
- 增加 GUI 自动化测试与 service 层回归测试。

## 已知风险 / 技术债
- 当前 runtime hook 通过 monkey patch 实现，后续可收敛为核心层显式 hook 接口。
- 候选分支为“首步展开 + 后续最优”的近似视图，不是完整搜索树可视化。
- 搜索与分支构建仍在主线程执行，深度较大时会卡顿。
- 手动动作对多分支卡牌默认选第一种，尚未提供完整选择器。
