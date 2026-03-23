# STS2 行为覆盖代理状态

## 当前输入

- 输入卡牌目录：`data/sts2/raw/ea_01`
- 输出卡牌目录：`data/sts2/normalized/cards.ea_01.json`
- 状态报告：`docs/sts2_import_status_ea_01.md`
- 未实现分析：`docs/sts2_unimplemented_analysis_ea_01.md`

## 基线

- 初始可执行卡牌数：`39`
- 初始未实现卡牌数：`538`
- 目标：在不破坏加载器或规划器安全性的前提下，基于低风险文本模式，保守提升行为覆盖率。

## 迭代记录

### 第 1 次迭代

- 可执行 / 未实现：`39 / 538`
- 重点：
  - 检查高频未实现模板
  - 识别低风险复合模式
- 发现：
  - 最适合优先处理的是固定多段攻击、伤害 + debuff、格挡 + 抽牌、抽牌 + 弃牌、伤害 + 抽牌，以及能量 + 抽牌。
  - 运行时已经具备足够的基础 effect，可支撑通用的 `sequence` 包装层。
- 验证：
  - 基线导入器/报告/加载器通过

### 第 2 次迭代

- 可执行 / 未实现：`42 / 535`
- 新增模式：
  - 通过重复 `deal_damage` 支持固定多段伤害
- 规则变更：
  - 在运行时和 schema 中引入 `sequence` 行为支持
  - 加载器现在会识别归一化标签中的 `exhaust`
- 发现：
  - 增长幅度小于预期，因为句子归一化后残留的 `..` 分隔符挡住了大部分复合正则匹配。
- 验证：
  - 导入器/报告/加载器/规划器 smoke check 通过

### 第 3 次迭代

- 可执行 / 未实现：`69 / 508`
- 新增模式：
  - `damage + weak`
  - `damage + vulnerable`
  - `damage + weak + vulnerable`
  - `block + draw`
  - `draw + discard`
  - `damage + draw`
  - `block + damage`
  - `damage + draw + discard`
  - `weak + vulnerable`
  - 结合提取出的重复次数支持固定多段伤害
- 规则变更：
  - 修复导入器的英文文本归一化，使多行句子可以稳定匹配
- 验证：
  - 导入器/报告/加载器/规划器 smoke check 通过

### 第 4 次迭代

- 可执行 / 未实现：`83 / 494`
- 新增模式：
  - 占位符形式的 `gain_energy`
  - `gain_energy + draw`
  - `block + next_turn_block`
  - `block + next_turn_energy`
  - `exhaust_from_hand + draw`
  - `block + weak`
- 规则变更：
  - 新增 `discard_cards` 和 `exhaust_from_hand` 行为键
  - 复用 `schedule_effect` 表达安全的“下回合效果”
- 验证：
  - 导入器/报告/加载器 smoke check 通过
  - 针对延迟效果和手牌选择效果的规划器验证通过

### 第 5 次迭代

- 可执行 / 未实现：`85 / 492`
- 新增模式：
  - 精确单行 `gain strength`
  - 精确单行 `gain dexterity`
- 规则变更：
  - `GainBlock` 现在会应用玩家的 `dexterity`，作为一个最小化的本地引擎扩展
- 验证：
  - 导入器/报告/加载器 smoke check 通过
  - 针对 buff 交互的验证通过

### 第 6 次迭代

- 可执行 / 未实现：`101 / 476`
- 新增模式：
  - 以当前敌人状态为近似对象的简单 AoE 伤害
  - 以当前敌人状态为近似对象的随机目标重复伤害/debuff
  - 第一阶段充能球子系统支持：`channel_orb`、`focus`、`orb_slots`
  - 精确单行 `Dexterity this turn` / `Strength this turn`
  - `damage + channel_orb`
  - `channel_orb + draw`
- 规则变更：
  - 新增 `channel_orb` 行为键及计数器级运行时效果
  - 应用了经用户确认的 AoE/随机目标近似策略
  - 通过延迟的逆向 buff 效果，应用了经用户确认的 `this turn` 持续时间策略
- 验证：
  - 导入器/报告/加载器 smoke check 通过
  - 针对临时 buff 到期和充能球计数累积的规划器验证通过

## 新增支持的行为类别

- 单效果 buff：`apply_buff`，用于 `strength` 和 `dexterity`
- 计数器级充能球子系统支持：`channel_orb`、`focus`、`orb_slots`
- 通过 `sequence` 支持复合动作卡牌
- 固定次数的重复攻击
- 抽牌/弃牌类手牌操作卡牌
- 延迟到下回合生效的格挡或能量
- 借助标签感知运行时加载实现可执行的 `exhaust` 卡牌

## 剩余阻塞项

- 当前引擎中的 AoE 目标语义仍然是单敌人模型
- 随机目标语义在当前单敌人模型下仍只是近似实现
- 其余未覆盖内容仍以触发型和持续型 power 行为为主
- 目前只有第一个资源子系统（`orb/channel/focus`）完成了第一阶段支持；`summon/Osty`、`forge`、`stars`、`doom` 仍然延期
- 临时属性到期逻辑目前仅覆盖精确单行的自我 buff 模式

## 停止原因

- 覆盖率已从 `39` 实质性提升到 `101`
- 剩余未映射内容现在主要是触发、资源、被动、卡牌身份、条件等复杂度问题，而不是漏掉了简单模板
- 最高影响的开放决策已收敛为一个更小的未决集合
