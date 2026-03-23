# STS2 行为边界已确认决策

## 已落实的边界

### Q1. AoE 伤害近似

- 已采用：
  - `AoE 对单敌多敌一样处理`

### Q2. 随机目标近似

- 已采用：
  - `随机目标在执行时做随机数，计算时考虑近似`

### Q3. trigger power 扩展边界

- 本阶段允许到：
  - 确定性事件
  - 单一额外数值条件
  - 单一简单过滤条件
  - 单一卡牌 ID 精确过滤
- 已纳入实例：
  - `DanseMacabre`
  - `Parry`
- 明确保留不做：
  - 多层嵌套条件
  - doom / summon / 复杂资源体系条件
  - 多事件混合触发
  - 长链式条件
  - 通用复杂卡牌过滤系统

### Q4. 资源系统优先级

- 已采用：
  - 仅保守支持第一个资源子系统 `orb/channel/focus`

### Q5. 临时持续时间语义

- 已采用：
  - `this turn` 建模为“当前玩家回合生效，并在下个玩家回合开始时归零”

### Q6. curse/status/passive 处理方式

- 已采用：
  - 不把被动 curse/status 算进 executable coverage
  - 引入 `passive_modeled`
  - 单独统计 `passive_modeled_cards`
  - 不进入 planner legal actions
- 已纳入 `passive_modeled` 的卡牌：
  - `BadLuck`
  - `Burn`
  - `Decay`
  - `Infection`
  - `Toxic`

### Q7. 返回手牌 / 卡牌实例身份

- 当前继续保持：
  - `unimplemented`
- 原因：
  - 当前引擎缺少 card instance identity / zone transfer 语义
  - 用近似会污染模型

## 本轮 5 条已确认决策

### 1. `Strangle`

- 已确认：
  - `enemy loses HP` 目前不要近似成普通伤害
  - 继续保持 `unimplemented`
- 原因：
  - `lose HP` 与 `deal damage` 在是否吃格挡上有明确语义差异
  - 这类效果需要独立语义，当前阶段不做错误近似

### 2. `Parry`

- 已确认：
  - 允许扩展到“单一卡牌 ID 精确过滤”的 trigger
  - 但只限这一种小范围扩展
- 已执行：
  - 新增 `event_card_id_is`
  - `Parry` 已映射为可执行 trigger
- 明确保留不做：
  - 不扩成通用复杂过滤系统
  - 不同时引入多重复杂条件

### 3. `SerpentForm`

- 已确认：
  - 技术上可做，但本阶段不优先
  - 除非被已支持的低风险模板自然覆盖，否则不专门扩引擎
- 当前状态：
  - 保持 `unimplemented`

### 4. `Shroud` / doom trigger 族

- 已确认：
  - 继续延期
  - 当前不要把 doom 拉进模型
- 当前状态：
  - 保持 `unimplemented`
- 原因：
  - 当前不为 doom 新增资源子系统或 trigger 分支

### 5. `Bolas` / `ThrummingHatchet`

- 已确认：
  - `return this to your Hand` 继续保持 `unimplemented`
- 原因：
  - 当前缺少 `card instance identity`
  - 当前缺少 `zone transfer` 语义
  - 不用“抽一张替代副本”之类近似去糊

## 当前开放问题数量

- `0`
