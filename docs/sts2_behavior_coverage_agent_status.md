# STS2 行为覆盖代理状态

## 当前输入

- 输入卡牌目录：`data/sts2/raw/ea_01`
- 输出卡牌目录：`data/sts2/normalized/cards.ea_01.json`
- 状态报告：`docs/sts2_import_status_ea_01.md`

## 本阶段目标

- 在 catalog ingestion 已完成的前提下，继续提升 behavior coverage
- 优先提升 Attack / Skill 的可执行覆盖率
- 仅在 Q3 边界内谨慎扩展 trigger power
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

## 本阶段结果

- 最终 executable coverage：`128 / 577`
- 最终 passive-modeled coverage：`5 / 577`
- 最终 unimplemented：`444 / 577`
- 相比本阶段基线：
  - executable `+13`
  - passive_modeled `+5`
  - unimplemented `-18`

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
- 不可执行但已建模的手牌被动 HP loss：
  - `passive_modeled`

## 刻意保持未实现的模式

- `Deal damage. At the start of your next turn, return this to your Hand.`
- 依赖 card instance identity / zone transfer 的延迟回手
- doom / summon / Osty / forge / stars 等资源系统相关 trigger
- 更复杂的持续型 power：
  - 多事件混合
  - 多层条件
  - 长链式条件
  - 语义明显超出当前 trigger/effect 模型的效果
- `enemy loses HP` 与 `deal damage` 不等价的持续触发族

## 风险与边界说明

- `passive_modeled` 只用于“已建模但不进入 legal actions”的效果，未混入 executable coverage
- 手牌被动效果当前只做显式建模与分层统计，没有把它们伪装成可打出的牌
- `lose_hp` 与 `deal_damage(target=player)` 分开处理，避免被格挡错误吸收
- `cost >= N` trigger 只支持单一额外数值条件，不继续扩到复杂资源或多条件组合
- `return this to your Hand` 仍然保持 `unimplemented`，避免污染模型

## 下一步建议

- 继续优先 Attack / Skill：
  - 小范围延迟收益模板
  - 少量明确的基础组合模板
- 若继续扩 trigger power，建议只考虑：
  - 单一精确卡牌过滤
  - 单一简单 tag 过滤
  - 仍可直接复用现有 effect 的模式
- 若要让 `passive_modeled` 进入真实运行时评估，下一步应单独设计“非动作型被动注入”机制，但不要混入 planner legal actions

## 停止原因

- executable coverage 已从 `115` 提升到 `128`，有实质提升
- passive-modeled coverage 已工程化拆分并单独统计
- Q3 边界内的 trigger power 已小幅扩张到“单一额外数值条件”
- 剩余高影响缺口主要转向复杂机制、资源系统、HP loss 语义差异与 card instance identity 问题
