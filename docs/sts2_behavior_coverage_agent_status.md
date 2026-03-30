# STS2 行为覆盖代理状态

## 当前输入

- 输入卡牌目录：`data/sts2/raw/ea_01`
- 输出卡牌目录：`data/sts2/normalized/cards.ea_01.json`
- 状态报告：`docs/sts2_import_status_ea_01.md`

## 本阶段目标

- 在 catalog ingestion 已完成的前提下，继续提升 behavior coverage
- 优先提升 Attack / Skill 的可执行覆盖率
- 仅在 Q3 边界内谨慎扩展 trigger power
- 本轮用户已确认：
  - `Strangle` 保持 `unimplemented`
  - `Parry` 可扩到单一卡牌 ID 精确过滤
  - `SerpentForm` 本阶段不专门扩引擎
  - `Shroud` / doom 族继续延期
  - `Bolas` / `ThrummingHatchet` 保持 `unimplemented`
- 引入并统计 `passive_modeled`
- 保持 Q7 相关“返回此牌到手牌”效果为 `unimplemented`

## 本阶段基线

- 初始 executable coverage：`115 / 577`
- 初始 passive-modeled coverage：`0 / 577`
- 初始 unimplemented：`462 / 577`

## 本阶段迭代记录

### 第 1 轮

- executable / passive_modeled / unimplemented：`123 / 5 / 449`
- 新增支持：
  - `Lose HP. Gain Block.`
  - `Lose HP. Gain Energy.`
  - `Lose HP. Deal damage.`
  - `Lose HP. Gain Energy. Draw cards.`
  - `Enemy loses Strength this turn.`
  - `This turn, whenever you play an Attack, gain Strength this turn.`
  - `Whenever you play a card that costs N or more, gain Block.`
  - 手牌内被动 end-of-turn HP loss 归类为 `passive_modeled`
- 规则变更：
  - 新增 `lose_hp` effect
  - 新增 `passive_in_hand_trigger` 行为键，专门承载不可执行但已建模的手牌被动效果
  - 加载器与状态报告新增 `passive_modeled_cards`
  - 触发上下文新增 `card_cost`，支持单一额外数值条件
- 验证：
  - importer / status report / loader smoke / planner legal actions smoke 通过
  - 定向验证通过：
    - `DanseMacabre` 只在打出费用 `>= N` 的牌时获得格挡
    - `BladeOfInk` 在本回合攻击触发临时力量，并于下回合归零
    - `Burn` / `Decay` / `BadLuck` / `Infection` / `Toxic` 不进入 legal actions

### 第 2 轮

- executable / passive_modeled / unimplemented：`128 / 5 / 444`
- 新增支持：
  - `Next turn, gain Energy.`
  - `Deal damage. Next turn, gain Energy.`
  - `Deal damage. Next turn, draw cards.`
  - `Gain Block. Next turn, draw cards and gain Energy.`
  - `Exhaust 1 card. Next turn, gain Energy.`
- 典型覆盖卡牌：
  - `Outmaneuver`
  - `Hegemony`
  - `Predator`
  - `GuidingStar`
  - `Relax`
  - `Scavenge`
- 验证：
  - importer / status report / loader smoke / planner legal actions smoke 通过
  - 定向验证确认 `Predator` 会正确挂起 `next_turn_draw`

### 第 3 轮

- executable / passive_modeled / unimplemented：`131 / 5 / 441`
- 新增支持：
  - `Lose HP. Exhaust 1 card. Gain Strength.`
  - `Lose HP. Deal damage to ALL enemies.`
  - `Whenever you play Sovereign Blade, gain Block.`
- 典型覆盖卡牌：
  - `Brand`
  - `Breakthrough`
  - `Parry`
- 规则变更：
  - trigger 条件新增 `event_card_id_is`
  - 明确只支持“单一卡牌 ID 精确过滤”，不扩成通用复杂过滤系统
- 验证：
  - importer / status report / loader smoke / planner legal actions smoke 通过
  - 定向验证通过：
    - `Parry` 只在 `card_id == SovereignBlade` 时获得格挡
    - `Acrobatics` 不会误触发 `Parry`
    - `Brand` / `Breakthrough` 已作为 executable 卡进入运行时

### 第 4 轮

- executable / passive_modeled / unimplemented：`134 / 5 / 438`
- 新增支持：
  - `Gain Block. Discard 1 card.`
  - `Gain Block. Next turn, gain Energy.`
  - `Lose Strength. Enemy loses Strength.`
- 典型覆盖卡牌：
  - `Survivor`
  - `Delay`
  - `SharedFate`
- 规则变更：
  - importer 兼容 `Next turn,` 后换行形成的轻微标点变体
- 验证：
  - importer / status report / loader smoke / planner legal actions smoke 通过
  - 定向验证通过：
    - `Survivor` 正确要求 discard 选择并弃掉指定手牌
    - `Delay` 正确挂起 `next_turn_energy`
    - `SharedFate` 正确同时降低玩家与敌方 `strength`

### 第 5 轮

- executable / passive_modeled / unimplemented：`144 / 5 / 428`
- 新增支持：
  - `Apply Weak. Gain Block.`
  - `Gain Block. Apply Vulnerable.`
  - `Deal damage to ALL enemies. Draw cards.`
  - `Gain Block. Channel Frost/Dark/Glass.`
  - `Deal damage. Apply Weak. Channel Dark.`
  - `Deal damage to ALL enemies. Apply Weak and Vulnerable.`
  - `Deal damage to ALL enemies. All enemies lose Strength this turn.`
- 典型覆盖卡牌：
  - `LegSweep`
  - `Taunt`
  - `SweepingBeam`
  - `Glacier`
  - `ShadowShield`
  - `Glasswork`
  - `Null`
  - `MeteorShower`
  - `CrushUnder`
  - `DyingStar`
- 验证：
  - importer / status report / loader smoke / planner legal actions smoke 通过
  - 定向验证通过：
    - `LegSweep` 正确同时施加 `weak` 并获得格挡
    - `SweepingBeam` 正确执行 `aoe_damage + draw`
    - `Glacier` 正确执行 `gain_block + channel_frost`
    - `DyingStar` 的敌方临时 `strength` 下降会在下回合恢复

### 第 6 轮

- executable / passive_modeled / unimplemented：`154 / 5 / 418`
- 新增支持：
  - `Apply Weak and Vulnerable to ALL enemies.`
  - `Apply Poison to ALL enemies.`
  - `Deal damage. Enemy loses Strength this turn.`
  - `Deal damage. Gain Strength this turn.`
  - `Deal damage twice. Gain Strength. The enemy gains Strength.`
  - `Gain Strength. ALL enemies lose Strength.`
  - `Gain Focus this turn.`
  - `Deal damage. Gain Focus this turn.`
  - `Deal damage. Channel Plasma.`
  - `Deal damage to ALL enemies. Lose Focus.`
- 典型覆盖卡牌：
  - `Shockwave`
  - `Haze`
  - `Mangle`
  - `SetupStrike`
  - `FightMe`
  - `Resonance`
  - `Hotfix`
  - `FocusedStrike`
  - `MeteorStrike`
  - `Hyperbeam`
- 验证：
  - importer / status report / loader smoke / planner legal actions smoke 通过
  - 定向验证通过：
    - `Shockwave` 正确同时施加 `weak` 与 `vulnerable`
    - `Mangle` 的敌方临时 `strength` 下降会在下回合恢复
    - `MeteorStrike` 正确执行 `deal_damage + channel_plasma`
    - `Hotfix` / `FocusedStrike` 的临时 `focus` 会在下回合归零
    - `Haze` 正确施加 `poison`

## 本阶段结果

- 最终 executable coverage：`154 / 577`
- 最终 passive-modeled coverage：`5 / 577`
- 最终 unimplemented：`418 / 577`
- 相比本阶段基线：
  - executable `+39`
  - passive_modeled `+5`
  - unimplemented `-44`

## 本轮新增支持的主要模式

- 自损生命 + 基础收益组合：
  - `lose_hp + gain_block`
  - `lose_hp + gain_energy`
  - `lose_hp + deal_damage`
  - `lose_hp + gain_energy + draw`
- 精确的敌方临时力量下降：
  - `Enemy loses Strength this turn.`
- 技能型本回合攻击触发：
  - `This turn, whenever you play an Attack, gain Strength this turn.`
- 单一额外数值条件 trigger power：
  - `Whenever you play a card that costs N or more, gain Block.`
- 下回合延迟收益：
  - `next_turn_energy`
  - `next_turn_draw`
  - `next_turn_draw + energy`
- 额外低风险 Attack / Skill 组合：
  - `lose_hp + exhaust_from_hand + gain_strength`
  - `lose_hp + aoe_damage`
  - `gain_block + discard_cards`
  - `gain_block + next_turn_energy`
  - `player_strength_loss + enemy_strength_loss`
  - `apply_weak + gain_block`
  - `gain_block + apply_vulnerable`
  - `aoe_damage + draw`
  - `gain_block + channel_orb`
  - `deal_damage + apply_weak + channel_dark`
  - `aoe_damage + weak + vulnerable`
  - `aoe_damage + enemy_strength_loss_this_turn`
  - `apply_weak + vulnerable`
  - `apply_poison`
  - `deal_damage + enemy_strength_loss_this_turn`
  - `deal_damage + temp_strength`
  - `deal_damage_twice + player_strength + enemy_strength`
  - `player_strength_gain + enemy_strength_loss`
  - `temp_focus`
  - `deal_damage + temp_focus`
  - `deal_damage + channel_plasma`
  - `aoe_damage + focus_loss`
- 单一卡牌 ID 精确过滤 trigger：
  - `Whenever you play Sovereign Blade, gain Block.`
- 不可执行但已建模的手牌被动 HP loss：
  - `passive_modeled`

## 刻意保持未实现的模式

- `Strangle` 这类 `enemy loses HP` 持续触发族
- `Deal damage. At the start of your next turn, return this to your Hand.`
- 依赖 card instance identity / zone transfer 的延迟回手
- doom / summon / Osty / forge / stars 等资源系统相关 trigger
- `Shroud` / doom trigger 族
- `SerpentForm` 这类虽然技术上可做、但当前阶段不优先的复杂 Power
- 更复杂的持续型 power：
  - 多事件混合
  - 多层条件
  - 长链式条件
  - 语义明显超出当前 trigger/effect 模型的效果

## 风险与边界说明

- `passive_modeled` 只用于“已建模但不进入 legal actions”的效果，未混入 executable coverage
- 手牌被动效果当前只做显式建模与分层统计，没有把它们伪装成可打出的牌
- `lose_hp` 与 `deal_damage(target=player)` 分开处理，避免被格挡错误吸收
- `enemy loses HP` 不近似为 `deal_damage`，因此 `Strangle` 继续保持 `unimplemented`
- trigger power 当前只扩到：
  - 单一额外数值条件
  - 单一简单过滤条件
  - 单一卡牌 ID 精确过滤
- `Parry` 的扩展边界仅限单卡 ID，不继续扩到通用复杂过滤
- `Shroud` / doom 族继续延期，不为其引入额外资源子系统
- `return this to your Hand` 仍然保持 `unimplemented`，因为缺少 card instance identity / zone transfer，避免污染模型

## 下一步建议

- 继续优先 Attack / Skill：
  - 小范围延迟收益模板
  - 少量明确的基础组合模板
- 若继续扩 trigger power，建议只考虑：
  - 单一简单 tag 过滤
  - 已确认边界内的单一卡牌 ID 精确过滤
  - 仍可直接复用现有 effect 的模式
- 若要让 `passive_modeled` 进入真实运行时评估，下一步应单独设计“非动作型被动注入”机制，但不要混入 planner legal actions

## 停止原因

- executable coverage 已从 `115` 提升到 `131`，有实质提升
- passive-modeled coverage 已工程化拆分并单独统计
- Q3 边界内的 trigger power 已小幅扩张到“单一卡牌 ID 精确过滤”
- 剩余高影响缺口主要转向复杂机制、资源系统、doom、HP loss 语义差异与 card instance identity 问题
