# STS2 行为问题待用户确认

## 已落实的边界

### Q1. AoE 伤害近似

- 已采用：
  - `AoE 对单敌多敌一样处理`

### Q2. 随机目标近似

- 已采用：
  - `随机目标在执行时做随机数，计算时考虑近似`

### Q3. trigger power 扩展边界

- 本轮已落实到：
  - 确定性事件
  - 单一额外数值条件
  - 单一简单过滤条件
- 本轮新增实例：
  - `DanseMacabre`
- 明确保留不做：
  - 多层嵌套条件
  - doom / summon / 复杂资源体系条件
  - 多事件混合触发
  - 长链式条件

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
- 本轮已纳入 `passive_modeled` 的卡牌：
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

## 当前待确认问题

### 1. `Strangle` 是否允许把 “lose HP” 近似成伤害？

- 卡牌 ID / 名称：
  - `Strangle` / `Strangle`
- 文本：
  - `Deal {Damage:diff()} damage. Whenever you play a card this turn, the enemy loses {StranglePower:diff()} HP.`
- 可能解释：
  - 解释 A：新增敌方 `lose_hp` 语义，绕过格挡
  - 解释 B：近似成 `deal_damage` 到当前敌人
  - 解释 C：继续保持 `unimplemented`
- 倾向方案：
  - 解释 C
- 不确定原因：
  - `lose HP` 与 `deal damage` 在是否吃格挡上有明确语义差异
- 影响范围：
  - 一小组 `enemy loses HP` 类持续效果，尤其是 attack/skill 挂载的临时 trigger

### 2. `Parry` 这类“精确卡名过滤”是否要纳入下一步 trigger 边界？

- 卡牌 ID / 名称：
  - `Parry` / `Parry`
- 文本：
  - `Whenever you play Sovereign Blade, gain {ParryPower:diff()} Block.`
- 可能解释：
  - 解释 A：新增按 `card_id` 精确过滤的简单 trigger 条件
  - 解释 B：把它视为超出当前边界，继续 `unimplemented`
- 倾向方案：
  - 解释 A，但仅限“单一卡牌 ID 精确过滤”
- 不确定原因：
  - 它仍是简单过滤，但会把 trigger 条件从 tag/character 扩到 card identity
- 影响范围：
  - 一小批“当你打出某张特定牌时”类型的 power

### 3. `SerpentForm` 是否值得在当前阶段纳入？

- 卡牌 ID / 名称：
  - `SerpentForm` / `Serpent Form`
- 文本：
  - `Whenever you play a card, deal {SerpentFormPower:diff()} damage to a random enemy.`
- 可能解释：
  - 解释 A：直接按当前随机目标近似映射为 `on_card_played -> deal_damage(enemy)`
  - 解释 B：因为当前阶段不优先啃 Power，继续 `unimplemented`
- 倾向方案：
  - 解释 B
- 不确定原因：
  - 从建模风险看它是可做的，但从阶段优先级看它会继续把精力推向 Power
- 影响范围：
  - 少量确定性 trigger power 的进一步扩展

### 4. `Shroud` / `Doom` 触发族是否继续延期？

- 卡牌 ID / 名称：
  - `Shroud` / `Shroud`
- 文本：
  - `Whenever you apply Doom, gain {Block:diff()} Block.`
- 可能解释：
  - 解释 A：为 `doom` 建立最小 debuff 键并纳入 trigger
  - 解释 B：继续延期，等 doom 资源/状态体系单独设计
- 倾向方案：
  - 解释 B
- 不确定原因：
  - 一旦引入 doom，后续很容易牵连更多持续效果、资源规则与结算时机
- 影响范围：
  - 一组 doom 相关 power 与 combo 卡牌

### 5. `Bolas` / `ThrummingHatchet` 的“return this to your Hand” 是否仍保持完全不近似？

- 卡牌 ID / 名称：
  - `Bolas` / `Bolas`
  - `ThrummingHatchet` / `Thrumming Hatchet`
- 文本：
  - `Deal {Damage:diff()} damage. At the start of your next turn, return this to your Hand.`
- 可能解释：
  - 解释 A：新增 card instance identity 与 zone transfer
  - 解释 B：近似为下回合额外摸到一张副本
  - 解释 C：保持 `unimplemented`
- 倾向方案：
  - 解释 C
- 不确定原因：
  - 当前任何“替代副本”近似都会污染牌区语义与规划结果
- 影响范围：
  - 一小组延迟回手攻击牌

## 当前开放问题数量

- `5`
