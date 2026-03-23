# STS2 行为问题待用户确认

## 已确认决策

### Q1. AoE 伤害近似

- 用户决策：
  - `AoE 对单敌多敌一样处理`
- 应用后的解释：
  - 在当前单敌人规划器/运行时模型中，AoE 伤害会映射为对当前敌人状态造成的伤害。
- 当前效果：
  - 为 `AstralPulse`、`DaggerSpray`、`Exterminate`、`Thunderclap` 等简单 AoE 攻击模板启用了保守映射。

### Q2. 随机目标近似

- 用户决策：
  - `随机目标在执行时做随机数，计算时考虑近似`
- 应用后的解释：
  - 在当前单敌人状态模型下，随机目标模板会近似映射到当前敌人。
- 当前效果：
  - 为 `Ricochet`、`RipAndTear`、`BouncingFlask` 等简单随机目标重复伤害/debuff 模板启用了保守映射。

### Q4. 资源系统优先级

- 用户决策：
  - `先支持第一个，其他几个写到状态或计划里`
- 应用后的解释：
  - 为列表中的第一个子系统 `orb/channel/focus` 增加了第一阶段支持。
- 当前效果：
  - 为 `Zap`、`Ball Lightning`、`Cold Snap`、`Coolheaded`、`Defragment`、`Capacitor` 启用了保守的计数器级支持。
- 延后处理的子系统：
  - `summon/Osty`
  - `forge`
  - `stars`
  - `doom`

### Q5. 临时持续时间语义

- 用户决策：
  - `如果是本回合，则为本次玩家出牌回合+敌人回合。如果是本场战斗，则到战斗结束为止（未写明均为本场战斗）`
- 应用后的解释：
  - `this turn` buff/debuff 会被建模为立即生效的效果，加上一个在下个玩家回合开始时执行的逆向计划效果。
- 当前效果：
  - 为 `Anticipate` 和 `FeedingFrenzy` 等精确单行临时属性 buff 启用了保守映射。

## 剩余问题

### Q3. 持续型触发 power 的边界还要不要继续扩大？

- 当前已启用的最小白名单：
  - `Afterimage`
  - `Rage`
  - `Storm`
  - `Subroutine`
- 当前支持范围：
  - 确定性事件
  - 非随机目标
  - 非复杂条件
  - 可直接复用现有 effect 的嵌套行为
- 仍待决定的扩展方向：
  - `Whenever you gain Block ...`
  - `Whenever you apply a debuff ...`
  - `Whenever you play a Colorless card ...`
  - `Whenever you play an Ethereal card ...`
  - `Whenever you play a card this turn, gain X Strength this turn`
- 倾向选项：
  - 下一步只扩大到“确定性 + 有简单条件过滤”的 trigger，例如按已打出牌的标签/类型过滤
- 不确定原因：
  - 再往前一步就需要在事件上下文里稳定携带卡牌标签、角色资源和更多条件判断，触发系统复杂度会明显上升。
- 影响：
  - 一批 power 卡，以及部分依赖事件计数/标签判断的技能牌

## Q6. 手牌中的被动 curse/status 效果是否应算入可执行覆盖？

- 范围：一类卡牌
- 示例卡牌：
  - `Burn`
  - `Decay`
  - `BadLuck`
- 原始文本：
  - `At the end of your turn, if this is in your Hand, take {Damage:diff()} damage.`
- 可能的解释：
  - 将它们建模为加载进牌组运行时的被动触发器
  - 因为它们不是玩家动作，所以保持不可执行
  - 把卡牌目录覆盖率和可打出动作覆盖率拆开统计
- 倾向选项：
  - 目前先不把它们计入可执行动作覆盖，但之后可以作为被动元数据加载
- 不确定原因：
  - 它们会影响规划，但不是通过合法的打牌动作产生影响。
- 影响：
  - curse/status 的真实感，以及回合结束评估

## Q7. “下回合将此牌返回手牌” 现在要作为可执行行为处理吗？

- 范围：一小类卡牌
- 示例卡牌：
  - `Bolas`
  - `ThrummingHatchet`
- 原始文本：
  - `Deal {Damage:diff()} damage. At the start of your next turn, return this to your Hand.`
- 可能的解释：
  - 增加带卡牌身份跟踪的延迟回手
  - 近似为抽到一张替代副本
  - 保持未实现
- 倾向选项：
  - 在卡牌身份回手语义明确之前，保持未实现
- 不确定原因：
  - 当前调度器支持延迟效果，但不支持把一个已经打出的具体卡牌实例延迟移动回手牌。
- 影响：
  - 一小组规模不大但并不简单的延迟收益攻击牌
