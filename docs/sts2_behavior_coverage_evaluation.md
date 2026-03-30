# STS2 行为覆盖评估

## 数据集

- 源目录：`data/sts2/raw/ea_01`
- 归一化输出：`data/sts2/normalized/cards.ea_01.json`
- 状态报告：`docs/sts2_import_status_ea_01.md`

## 覆盖率摘要

| 指标 | 初始值 | 最终值 |
| --- | ---: | ---: |
| total_cards | 577 | 577 |
| executable_cards | 115 | 154 |
| passive_modeled_cards | 0 | 5 |
| mapped_cards | 115 | 154 |
| unimplemented_cards | 462 | 418 |

## 本轮新增支持的主要模式

- `Lose HP. Gain Block.`
- `Lose HP. Gain Energy.`
- `Lose HP. Deal damage.`
- `Lose HP. Gain Energy. Draw cards.`
- `Enemy loses Strength this turn.`
- `This turn, whenever you play an Attack, gain Strength this turn.`
- `Whenever you play a card that costs N or more, gain Block.`
- `Next turn, gain Energy.`
- `Deal damage. Next turn, gain Energy.`
- `Deal damage. Next turn, draw cards.`
- `Gain Block. Next turn, draw cards and gain Energy.`
- `Exhaust 1 card. Next turn, gain Energy.`
- `Lose HP. Exhaust 1 card. Gain Strength.`
- `Lose HP. Deal damage to ALL enemies.`
- `Whenever you play Sovereign Blade, gain Block.`
- `Gain Block. Discard 1 card.`
- `Gain Block. Next turn, gain Energy.`
- `Lose Strength. Enemy loses Strength.`
- `Apply Weak. Gain Block.`
- `Gain Block. Apply Vulnerable.`
- `Deal damage to ALL enemies. Draw cards.`
- `Gain Block. Channel Frost/Dark/Glass.`
- `Deal damage. Apply Weak. Channel Dark.`
- `Deal damage to ALL enemies. Apply Weak and Vulnerable.`
- `Deal damage to ALL enemies. All enemies lose Strength this turn.`
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

## 本轮新增 passive-modeled coverage

- `BadLuck`
- `Burn`
- `Decay`
- `Infection`
- `Toxic`

这些卡牌满足：

- 已被显式映射为 `passive_in_hand_trigger`
- `behavior_status = passive_modeled`
- 不进入 planner legal actions
- 不计入 executable coverage

## 工程变更

### 新增/扩展行为能力

- `lose_hp`
  - 用于精确表达绕过格挡的 HP loss
- `passive_in_hand_trigger`
  - 用于标记“已建模但不可执行”的手牌内被动效果
- trigger 条件新增 `event_card_cost_gte`
  - 仅覆盖单一额外数值条件
- trigger 条件新增 `event_card_id_is`
  - 仅覆盖单一卡牌 ID 精确过滤
- importer 兼容 `Next turn,` 后换行造成的轻微标点变体
  - 例如 `Delay`
- 新增一批“现有效果顺序组合”模板
  - 无需引入新资源子系统或复杂条件
- 继续扩展 `orb/channel/focus` 的保守支持面
  - 仍未把 doom、return-to-hand、复杂 Power 拉入当前模型

### 统计与分类

- `CatalogLoadSummary` 新增 `passive_modeled_cards`
- loader 会把 `model_status` / `behavior_status` 写入 `source`
- 状态报告把 executable 与 passive_modeled 分开统计

## 刻意保持未实现的模式

- `Strangle` / 其他 `enemy loses HP` 持续触发族
- `return this to your Hand`
- 依赖 card instance identity 的延迟 zone transfer
- `Bolas` / `ThrummingHatchet` 这类延迟回手牌
- doom / summon / Osty / forge / stars 等复杂资源体系
- `Shroud` / doom trigger 族
- `SerpentForm` 这类本阶段不优先专门扩引擎的复杂 Power
- 多层条件 / 多事件混合 / 长链式 trigger power

## 风险与边界说明

- `passive_modeled` 仅表示“模型显式认识到该效果”，不代表它是玩家可主动执行的动作
- 本轮没有把 curse/status 被动效果混入 executable coverage
- `lose_hp` 被单独建模，避免错误复用“受格挡影响”的伤害逻辑
- 用户已明确拍板：
  - `Strangle` 不做 lose-HP 到普通伤害的近似
  - `Parry` 允许单一卡牌 ID 精确过滤，但不扩成通用过滤系统
  - `SerpentForm` 本阶段不优先
  - `Shroud` / doom 族继续延期
  - `Bolas` / `ThrummingHatchet` 不做“抽一张替代副本”的假近似
- trigger power 只扩到：
  - 确定性事件
  - 单一额外数值条件
  - 单一简单过滤条件
  - 单一卡牌 ID 精确过滤
- `enemy loses HP` 与 `deal damage` 不等价，因此相关持续触发族故意保持 `unimplemented`
- Q7 相关效果继续保持 `unimplemented`，因为当前仍缺少 card instance identity / zone transfer 语义

## 验证

- importer：通过
- import status report：通过
- loader smoke check：通过
- planner legal actions smoke check：通过
- 定向验证：
  - `DanseMacabre` 仅在打出费用 `>= N` 的牌时触发
  - `BladeOfInk` 的临时力量在下回合开始时归零
  - `Predator` 正确挂起 `next_turn_draw`
  - `Burn` / `Decay` / `BadLuck` / `Infection` / `Toxic` 不进入 legal actions
  - `Parry` 仅在 `card_id == SovereignBlade` 时触发
  - `Brand` / `Breakthrough` 已可执行并进入运行时
  - `Survivor` 正确生成 discard 选择并弃掉指定牌
  - `Delay` 正确挂起 `next_turn_energy`
  - `SharedFate` 正确同时降低双方 `strength`
  - `LegSweep` 正确同时施加 `weak` 并获得格挡
  - `SweepingBeam` 正确执行 `aoe_damage + draw`
  - `Glacier` 正确执行 `gain_block + channel_frost`
  - `DyingStar` 的敌方临时 `strength` 下降会在下回合恢复
  - `Shockwave` 正确同时施加 `weak` 与 `vulnerable`
  - `Mangle` 的敌方临时 `strength` 下降会在下回合恢复
  - `MeteorStrike` 正确执行 `deal_damage + channel_plasma`
  - `Hotfix` / `FocusedStrike` 的临时 `focus` 会在下回合归零
  - `Haze` 正确施加 `poison`

## 下一步建议

- 继续优先 Attack / Skill 的高频安全模板
- 若继续扩 trigger power，优先考虑：
  - 单一简单 tag 过滤
  - 已确认边界内的单一卡牌 ID 过滤
- 若要进一步利用 `passive_modeled`，建议单独设计“非动作型被动注入”机制，而不是修改 planner legal actions
