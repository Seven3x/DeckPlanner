# STS2 行为覆盖评估

## 数据集

- 源目录：`data/sts2/raw/ea_01`
- 归一化输出：`data/sts2/normalized/cards.ea_01.json`
- 状态报告：`docs/sts2_import_status_ea_01.md`
- 未实现分析：`docs/sts2_unimplemented_analysis_ea_01.md`

## 覆盖率摘要

| 指标 | 初始值 | 最终值 |
| --- | ---: | ---: |
| total_cards | 577 | 577 |
| executable_cards | 39 | 115 |
| mapped_cards | 39 | 115 |
| unimplemented_cards | 538 | 462 |

## 新增支持的模式

- exact `Deal X damage. Apply Y Vulnerable.`
- exact `Deal X damage. Apply Y Weak.`
- exact `Deal X damage. Apply Y Weak. Apply Y Vulnerable.`
- exact `Apply X Weak. Apply Y Vulnerable.`
- exact `Gain X Block. Draw Y cards.`
- exact `Draw X cards. Discard Y cards.`
- exact `Deal X damage. Draw Y cards.`
- exact `Deal X damage. Draw 1 card. Discard 1 card.`
- exact `Gain X Block. Deal Y damage.`
- exact `Deal X damage twice.`
- exact `Deal X damage N times.` where `N` resolves to a small fixed integer
- exact placeholder-form `Gain {Energy:energyIcons()}.`
- exact `Gain energy, then draw`
- exact `Gain block, next turn gain block`
- exact `Gain block, next turn gain energy`
- exact `Exhaust 1 card, then draw`
- exact `Gain block, apply weak`
- exact one-line `Gain Strength.` and `Gain Dexterity.`
- exact one-line `Gain Dexterity this turn.` / `Gain Strength this turn.`
- simple `Deal X damage to ALL enemies.`
- simple `Deal X damage to ALL enemies twice / N times.`
- simple `Deal X damage to a random enemy twice / N times.`
- simple `Apply X Poison to a random enemy N times.`
- `Deal X damage. Channel 1 Lightning/Frost.`
- `Channel 1 Frost. Draw Y cards.`
- `Channel 1 Lightning.`
- `Gain Focus.` / `Gain Orb Slots.`
- 最小白名单持续 trigger power：
  - `Whenever you play a card, gain Block`
  - `Whenever you play an Attack this turn, gain Block`
  - `Whenever you play a Power, Channel Lightning`
  - `Whenever you play a Power, gain Energy`
- 带简单条件过滤的 trigger power：
  - `Whenever you play a Colorless card, gain Strength`
  - `Whenever you play an Ethereal card, gain Block`
  - `Whenever you apply Vulnerable, draw`
  - `Whenever you apply a debuff to an enemy, they take damage`
- 带单一事件状态条件或临时复合效果的 trigger power：
  - `Whenever you gain Block, deal damage to a random enemy`
  - `Whenever you play a card this turn, gain Strength this turn`

## 新增行为类别

- `sequence`
  - 作为保守型多效果包装层，建立在已支持的基础 effect 之上
- `discard_cards`
  - 使抽牌/弃牌类卡牌可以安全执行
- `exhaust_from_hand`
  - 使先消耗再抽牌的卡牌可以安全执行
- `apply_buff`
  - 现在用于精确单行的 `strength` 和 `dexterity`
- `channel_orb`
  - 为 `lightning` 和 `frost` 提供第一阶段、计数器级的 orb/channel 支持
- `add_trigger`
  - 为极小的确定性白名单与简单条件过滤 trigger 提供持续触发支持
  - 现在也承载一小部分单一事件状态条件和临时复合 trigger

## 小型引擎扩展

- 运行时加载器现在会把 `exhaust` 关键词标签映射到 `CardDefinition.exhaust`
- `GainBlock` 现在会读取玩家的 `dexterity`，使精确的 `Gain Dexterity.` 卡牌对规划器有实际影响
- 第一阶段的 orb 支持会把已 channel 的 orb 数量以计数器形式存入运行时状态，便于后续扩展
- 精确的 `this turn` 自身 buff 会通过计划中的逆向效果，在下个玩家回合开始时失效

## 明确保持未实现的内容

- 更复杂的持续型触发 power
- summon/Osty 卡牌
- forge/star/doom 系统
- 延迟回手 / 卡牌身份跟踪机制
- 手牌中的被动 curse/status 效果作为可执行动作

## 风险说明

- `sequence` 只会组合已支持的基础 effect，不会猜测新的机制
- 重复伤害映射被限制在较小的固定次数内，以避免不安全的 `X` 式展开
- 占位符形式的 `Gain {...}.` 只有在占位符名称本身明确表示能量时才会映射为 energy
- buff 映射被有意限制在 `strength` 和 `dexterity`，没有做更广泛的泛化
- AoE/随机目标映射目前是在单敌人规划器/运行时模型下的有意近似
- orb 支持仍处于第一阶段且基于计数器；被动/evoke 语义仍不在范围内
- 当前 trigger 支持已覆盖极小白名单、简单条件过滤，以及少量单一事件状态条件/临时复合效果；资源条件、数值条件、复合条件或更复杂随机触发仍未纳入

## 建议

- 下一块较干净的扩展边界，是“带单一额外数值条件”的确定性触发 power。
- 再往后，一个高价值决策点是是否要在运行时评估中建模被动 curse/status 效果。
- 如果继续推进，资源系统的后续顺序建议为：`summon/Osty` -> `forge` -> `stars` -> `doom`。
