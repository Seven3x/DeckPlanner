# STS2 未实现行为分析（0.98.2）

- 源文件：`data/sts2/normalized/cards.0.98.2.json`
- 生成时间（UTC）：`2026-03-22T15:33:06+00:00`
- 未实现筛选条件：`behavior_key == "unimplemented"`

## 概览

| 指标 | 值 |
| --- | --- |
| 总卡牌数 | 577 |
| 未实现卡牌数 | 543 |
| 未实现占比 | 94.11% |
| 分析 Top N | 30 |

## 分布统计

### 按角色

| 键 | 数量 |
| --- | --- |
| regent | 84 |
| defect | 83 |
| ironclad | 83 |
| necrobinder | 82 |
| silent | 81 |
| colorless | 61 |
| event | 26 |
| curse | 18 |
| token | 11 |
| status | 10 |
| quest | 3 |
| deprecated | 1 |

### 按类型

| 键 | 数量 |
| --- | --- |
| skill | 213 |
| attack | 181 |
| power | 112 |
| curse | 18 |
| status | 14 |
| other | 5 |

### 按稀有度

| 键 | 数量 |
| --- | --- |
| uncommon | 210 |
| rare | 153 |
| common | 93 |
| special | 78 |
| basic | 9 |

### 按费用

| 键 | 数量 |
| --- | --- |
| 1 | 269 |
| 0 | 100 |
| 2 | 94 |
| 3 | 38 |
| -1 | 29 |
| -2 | 10 |
| 4 | 1 |
| 5 | 1 |
| 6 | 1 |

## 文本高频统计

### 最常见完整文本 Top 30

| 排名 | 数量 | 文本 | 示例卡牌 |
| --- | --- | --- | --- |
| 1 | 3 | 不能被打出 | Injury, Soot, Wound |
| 2 | 2 | 永恒,不能被打出 | Curse of the Bell, Greed |
| 3 | 2 | 消耗 | Debris, Spore Mind |
| 4 | 1 | 奇巧,获得1点敏捷。 / 获得4点荆棘。 | Abrasive |
| 5 | 1 | 中毒会额外触发1次。 | Accelerant |
| 6 | 1 | 小刀额外造成4点伤害。 | Accuracy |
| 7 | 1 | 抽3张牌。 / 丢弃1张牌。 | Acrobatics |
| 8 | 1 | 造成18点伤害。 / 将这张牌的一张0能量复制品添加到你的弃牌堆。 | Adaptive Strike |
| 9 | 1 | 消耗,获得1能量。 / 抽2张牌。 | Adrenaline |
| 10 | 1 | 你每打出一张牌，都获得1点格挡。 | Afterimage |
| 11 | 1 | 消耗,召唤6。 | Afterlife |
| 12 | 1 | 在你的回合开始时，将你弃牌堆的一张随机攻击牌放入你的手牌并将其升级。 | Aggression |
| 13 | 1 | 消耗,获得一瓶随机药水。 | Alchemize |
| 14 | 1 | 获得2能量。 | Alignment |
| 15 | 1 | 造成10点伤害。 / 将你弃牌堆中的所有0能量牌放入你的手牌。 | All for One |
| 16 | 1 | 造成6点伤害。 / 将一张此牌的复制品加入你的弃牌堆。 | Anger |
| 17 | 1 | 消耗,将你抽牌堆中的所有稀有牌放入你的手牌。 | Anointed |
| 18 | 1 | 在本回合获得3点敏捷。 | Anticipate |
| 19 | 1 | 消耗,固有,升级你的全部卡牌。 | Apotheosis |
| 20 | 1 | 虚无,消耗,获得1层无实体。 | Apparition |
| 21 | 1 | 获得5点格挡。 / 升级你手牌中的一张牌。 | Armaments |
| 22 | 1 | 你每打出一张无色牌，都获得1点力量。 | Arsenal |
| 23 | 1 | 永恒,不能被打出,虚无 | Ascender's Bane |
| 24 | 1 | 造成6点伤害。 / 你的消耗牌堆中每有一张牌，伤害增加3。 | Ashen Strike |
| 25 | 1 | 固有,消耗,造成10点伤害。 / 给予1层易伤。 | Assassinate |
| 26 | 1 | 对所有敌人造成14点伤害。 | Astral Pulse |
| 27 | 1 | 你每抽10张牌，获得1能量。 | Automation |
| 28 | 1 | 获得5点格挡。 / 抽2张牌。 | Backflip |
| 29 | 1 | 永恒,不能被打出,在你的回合结束时，如果这张牌在你的手牌中，则失去13点生命。 | Bad Luck |
| 30 | 1 | 造成7点伤害。 / 生成1个闪电充能球。 | Ball Lightning |

### 最常见开头短语 Top 30

| 排名 | 数量 | 前缀 |
| --- | --- | --- |
| 1 | 95 | 造成<N>点伤害 |
| 2 | 80 | 消耗 |
| 3 | 43 | 获得<N>点格挡 |
| 4 | 24 | 在你的回合开始时 |
| 5 | 20 | 不能被打出 |
| 6 | 14 | 对所有敌人造成<N>点伤害 |
| 7 | 11 | 虚无 |
| 8 | 11 | 奥斯提造成<N>点伤害 |
| 9 | 8 | 抽<N>张牌 |
| 10 | 8 | 保留 |
| 11 | 6 | 奇巧 |
| 12 | 6 | 永恒 |
| 13 | 6 | 铸造<N> |
| 14 | 6 | 造成<N>点伤害两次 |
| 15 | 5 | 在你的回合结束时 |
| 16 | 5 | 失去<N>点生命 |
| 17 | 4 | 获得<N>能量 |
| 18 | 4 | 固有 |
| 19 | 4 | 召唤<N> |
| 20 | 3 | 你每打出一张牌 |
| 21 | 3 | 造成<N>点伤害<N>次 |
| 22 | 3 | 获得<N>层覆甲 |
| 23 | 3 | 获得<N>☆ |
| 24 | 3 | 获得<N>点力量 |
| 25 | 2 | 获得<N>点集中 |
| 26 | 2 | 在这个回合 |
| 27 | 2 | 获得<N>个充能球栏位 |
| 28 | 2 | 打出此牌后 |
| 29 | 2 | 每当有一张牌被消耗时 |
| 30 | 2 | 每当你打出一张灵魂时 |

### 关键词覆盖（含指定关键字）Top 30

| 排名 | 关键词 | 卡牌数 | 匹配模式 |
| --- | --- | --- | --- |
| 1 | deal | 229 | \bdeal\b, 造成, 攻击 |
| 2 | gain | 166 | \bgain\b, 获得 |
| 3 | exhaust | 107 | \bexhaust\b, 消耗 |
| 4 | draw | 101 | \bdraw\b, 抽, 抽牌 |
| 5 | block | 86 | \bblock\b, 格挡 |
| 6 | energy | 61 | \benergy\b, 能量 |
| 7 | apply | 56 | \bapply\b, 给予, 施加 |
| 8 | random | 43 | \brandom\b, 随机 |
| 9 | whenever | 43 | \bwhenever\b, 每当 |
| 10 | at_the_start | 40 | at the start, 回合开始时 |
| 11 | if | 34 | \bif\b, 如果 |
| 12 | vulnerable | 27 | \bvulnerable\b, 易伤 |
| 13 | for_each | 22 | for each, 每有, 每张, 每次 |
| 14 | weak | 21 | \bweak\b, 虚弱 |
| 15 | at_the_end | 16 | at the end, 回合结束时 |
| 16 | retain | 16 | \bretain\b, 保留 |
| 17 | choose | 15 | \bchoose\b, 选择 |
| 18 | poison | 12 | \bpoison\b, 中毒 |
| 19 | discard | 11 | \bdiscard\b, 丢弃 |
| 20 | upgrade | 4 | \bupgrade\b, 升级 |
| 21 | burn | 1 | \bburn\b, 灼伤 |

## 模板模式分析

模板归并规则：统一大小写；将数字归一化为 `<N>`；将独立 `X/x` 归一化为 `<X>`；统一中英文标点；压缩换行和空白。

| 排名 | 数量 | 归一化模式 | 类型分布 | 示例卡牌 |
| --- | --- | --- | --- | --- |
| 1 | 4 | 造成<N>点伤害. / 给予<N>层易伤 | attack:4 | Beam Cell, Squash, Bash, Break |
| 2 | 4 | 造成<N>点伤害. / 给予<N>层虚弱. / 给予<N>层易伤 | attack:4 | Uppercut, Comet, Falling Star, Gamma Blast |
| 3 | 3 | 获得<N>点格挡. / 抽<N>张牌 | skill:3 | Finesse, Shrug It Off, Backflip |
| 4 | 3 | 获得<N>层覆甲 | power:3 | Eternal Armor, Stone Armor, Neutron Aegis |
| 5 | 3 | 不能被打出 | status:2, curse:1 | Injury, Soot, Wound |
| 6 | 3 | 消耗, 获得<N>能量 | skill:3 | Production, Supercritical, Wisp |
| 7 | 2 | 抽<N>张牌. / 丢弃<N>张牌 | skill:2 | Acrobatics, Prepared |
| 8 | 2 | 消耗, 获得<N>能量. / 抽<N>张牌 | skill:2 | Adrenaline, Fuel |
| 9 | 2 | 消耗, 召唤<N> | skill:2 | Afterlife, Reanimate |
| 10 | 2 | 造成<N>点伤害. / 在你的下个回合开始时, 将此卡返回你的手牌 | attack:2 | Bolas, Thrumming Hatchet |
| 11 | 2 | 不能被打出, 在你的回合结束时, 如果这张牌在你的手牌中, 你受到<N>点伤害 | curse:1, status:1 | Decay, Burn |
| 12 | 2 | 造成<N>点伤害<N>次 | attack:2 | Peck, Celestial Might |
| 13 | 2 | 造成<N>点伤害. / 生成<N>个冰霜充能球 | attack:2 | Cold Snap, Ice Lance |
| 14 | 2 | 永恒, 不能被打出 | curse:2 | Curse of the Bell, Greed |
| 15 | 2 | 获得<N>点格挡. / 造成<N>点伤害 | attack:2 | Iron Wave, Dash |
| 16 | 2 | 消耗 | curse:1, status:1 | Spore Mind, Debris |
| 17 | 2 | 对所有敌人造成<N>点伤害<N>次 | attack:2 | Exterminate, Seven Stars |
| 18 | 2 | 造成<N>点伤害. / 抽<N>张牌 | attack:2 | Flash of Steel, Pommel Strike |
| 19 | 2 | 消耗, 给予<N>层虚弱. / 给予<N>层易伤 | skill:2 | Putrefy, Know Thy Place |
| 20 | 2 | 造成<N>点伤害. / 给予<N>层虚弱 | attack:2 | Neutralize, Sucker Punch |
| 21 | 2 | 铸造<N> | skill:2 | Spoils of Battle, The Smith |
| 22 | 2 | 随机对敌人造成<N>点伤害x次 | attack:2 | Volley, Stardust |
| 23 | 1 | 奇巧, 获得<N>点敏捷. / 获得<N>点荆棘 | power:1 | Abrasive |
| 24 | 1 | 中毒会额外触发<N>次 | power:1 | Accelerant |
| 25 | 1 | 小刀额外造成<N>点伤害 | power:1 | Accuracy |
| 26 | 1 | 造成<N>点伤害. / 将这张牌的一张<N>能量复制品添加到你的弃牌堆 | attack:1 | Adaptive Strike |
| 27 | 1 | 你每打出一张牌, 都获得<N>点格挡 | power:1 | Afterimage |
| 28 | 1 | 在你的回合开始时, 将你弃牌堆的一张随机攻击牌放入你的手牌并将其升级 | power:1 | Aggression |
| 29 | 1 | 消耗, 获得一瓶随机药水 | skill:1 | Alchemize |
| 30 | 1 | 获得<N>能量 | skill:1 | Alignment |

## 可安全扩展候选

以下分组仅用于下一阶段补规则优先级，不在本次变更中落地行为映射。

### 1. 很可能可直接映射的简单模式

- 卡牌数：**217**

| 排名 | 数量 | 模式 | 示例卡牌 |
| --- | --- | --- | --- |
| 1 | 4 | 造成<N>点伤害. / 给予<N>层易伤 | Beam Cell, Squash, Bash, Break |
| 2 | 4 | 造成<N>点伤害. / 给予<N>层虚弱. / 给予<N>层易伤 | Uppercut, Comet, Falling Star, Gamma Blast |
| 3 | 3 | 获得<N>点格挡. / 抽<N>张牌 | Finesse, Shrug It Off, Backflip |
| 4 | 3 | 消耗, 获得<N>能量 | Production, Supercritical, Wisp |
| 5 | 2 | 抽<N>张牌. / 丢弃<N>张牌 | Acrobatics, Prepared |
| 6 | 2 | 消耗, 获得<N>能量. / 抽<N>张牌 | Adrenaline, Fuel |
| 7 | 2 | 造成<N>点伤害<N>次 | Peck, Celestial Might |
| 8 | 2 | 获得<N>点格挡. / 造成<N>点伤害 | Iron Wave, Dash |
| 9 | 2 | 对所有敌人造成<N>点伤害<N>次 | Exterminate, Seven Stars |
| 10 | 2 | 造成<N>点伤害. / 抽<N>张牌 | Flash of Steel, Pommel Strike |
| 11 | 2 | 消耗, 给予<N>层虚弱. / 给予<N>层易伤 | Putrefy, Know Thy Place |
| 12 | 2 | 造成<N>点伤害. / 给予<N>层虚弱 | Neutralize, Sucker Punch |
| 13 | 1 | 获得<N>能量 | Alignment |
| 14 | 1 | 造成<N>点伤害. / 将你弃牌堆中的所有<N>能量牌放入你的手牌 | All for One |
| 15 | 1 | 消耗, 将你抽牌堆中的所有稀有牌放入你的手牌 | Anointed |
| 16 | 1 | 在本回合获得<N>点敏捷 | Anticipate |
| 17 | 1 | 消耗, 固有, 升级你的全部卡牌 | Apotheosis |
| 18 | 1 | 虚无, 消耗, 获得<N>层无实体 | Apparition |
| 19 | 1 | 获得<N>点格挡. / 升级你手牌中的一张牌 | Armaments |
| 20 | 1 | 固有, 消耗, 造成<N>点伤害. / 给予<N>层易伤 | Assassinate |
| 21 | 1 | 对所有敌人造成<N>点伤害 | Astral Pulse |
| 22 | 1 | 抽<N>张牌. / 你在本回合内不能再抽任何牌 | Battle Trance |
| 23 | 1 | 另一名玩家获得<N>能量 | Believe in You |
| 24 | 1 | 消耗, 添加<N>张小刀到你的手牌 | Blade Dance |
| 25 | 1 | 造成<N>点伤害. / 给予等量于所造成伤害的灾厄 | Blight Strike |
| 26 | 1 | 失去<N>点生命. / 获得<N>点格挡 | Blood Wall |
| 27 | 1 | 失去<N>点生命. / 获得<N>能量 | Bloodletting |
| 28 | 1 | 造成你当前格挡值的伤害 | Body Slam |
| 29 | 1 | 获得<N>点格挡. / 将一张眩晕添加到你的弃牌堆中 | Boost Away |
| 30 | 1 | 给予自身<N>层灾厄. / 获得<N>能量 | Borrowed Time |

### 2. 需要少量参数提取即可支持的模式

- 卡牌数：**71**

| 排名 | 数量 | 模式 | 示例卡牌 |
| --- | --- | --- | --- |
| 1 | 2 | 随机对敌人造成<N>点伤害x次 | Volley, Stardust |
| 2 | 1 | 消耗, 获得一瓶随机药水 | Alchemize |
| 3 | 1 | 造成<N>点伤害. / 你的消耗牌堆中每有一张牌, 伤害增加<N> | Ashen Strike |
| 4 | 1 | 打出你弃牌堆中的<N>张随机攻击牌 | Beat Down |
| 5 | 1 | 如果奥斯提存活, 则他对所有敌人造成<N>点伤害并且你获得<N>点格挡. / 然后奥斯提死去 | Bone Shards |
| 6 | 1 | 随机给予敌人<N>层中毒<N>次 | Bouncing Flask |
| 7 | 1 | 如果敌方拥有中毒, 则给予<N>层中毒 | Bubble Bubble |
| 8 | 1 | 造成<N>点伤害. / 该敌人身上每有一层易伤就额外造成<N>点伤害 | Bully |
| 9 | 1 | 消耗, 将<N>张随机无色牌添加到你的手牌 | Bundle of Joy |
| 10 | 1 | 打出你抽牌堆顶部的x张牌 | Cascade |
| 11 | 1 | 从你的抽牌堆中随机打出<N>张牌 | Catastrophe |
| 12 | 1 | 造成<N>点伤害. / 你每有一张拥有☆耗能的卡牌, 这张牌就额外造成<N>点伤害 | Crescent Spear |
| 13 | 1 | 获得<N>点格挡. / 如果你在本回合中曾给予过灾厄, 则额外获得<N>次格挡 | Death's Door |
| 14 | 1 | 消耗, 抽<N>张牌. / 选择你手牌中的一张技能牌, 并将其打出<N>次 | Decisions, Decisions |
| 15 | 1 | 消耗, 从<N>张随机牌中选择<N>张加入你的手牌. 这张牌在本回合的耗能为<N>能量 | Discovery |
| 16 | 1 | 造成<N>点伤害. / 如果该敌人有易伤状态, 则攻击两次 | Dismantle |
| 17 | 1 | 消耗, 将一张随机技能牌添加到你的手牌中. 这张牌在本回合内可以免费打出 | Distraction |
| 18 | 1 | 消耗, 敌人身上每有一层易伤, 就获得<N>点力量 | Dominate |
| 19 | 1 | 造成<N>点伤害. / 随机升级你弃牌堆中的<N>张牌 | Drain Power |
| 20 | 1 | 对所有敌人造成<N>点伤害. / 每有一名敌人被击杀, 就重复此效果 | Echoing Slash |
| 21 | 1 | 消耗所有手牌. / 如果有至少<N>张牌通过这个方法被消耗了, 则获得<N>层无实体 | Eidolon |
| 22 | 1 | 保留, 造成<N>点伤害x次 | Eradicate |
| 23 | 1 | 抽<N>张牌. / 如果抽到的是技能牌, 则获得<N>点格挡 | Escape Plan |
| 24 | 1 | 获得<N>点格挡. / 如果你在本回合获得消耗过卡牌, 则额外获得<N>点格挡 | Evil Eye |
| 25 | 1 | 你的手牌中每有一张攻击牌, 就会获得能量 | Expect a Fight |
| 26 | 1 | 奥斯提造成<N>点伤害. / 如果这是这张牌第一次在本回合被打出, 则抽<N>张牌 | Fetch |
| 27 | 1 | 消耗, 消耗所有手牌. / 每张被消耗的牌造成<N>点伤害 | Fiend Fire |
| 28 | 1 | 消耗你所有的状态牌. / 每有一张被消耗的牌, 就随机对敌人造成<N>点伤害 | Flak Cannon |
| 29 | 1 | 奥斯提造成<N>点伤害. / 如果奥斯提本回合攻击过, 则这张牌的费用变为<N>能量 | Flatten |
| 30 | 1 | 手牌中每有一张技能牌, 造成<N>点伤害 | Flechettes |

### 3. 需要新 effect/trigger 支持的模式

- 卡牌数：**125**

| 排名 | 数量 | 模式 | 示例卡牌 |
| --- | --- | --- | --- |
| 1 | 3 | 获得<N>层覆甲 | Eternal Armor, Stone Armor, Neutron Aegis |
| 2 | 2 | 造成<N>点伤害. / 在你的下个回合开始时, 将此卡返回你的手牌 | Bolas, Thrumming Hatchet |
| 3 | 1 | 奇巧, 获得<N>点敏捷. / 获得<N>点荆棘 | Abrasive |
| 4 | 1 | 中毒会额外触发<N>次 | Accelerant |
| 5 | 1 | 小刀额外造成<N>点伤害 | Accuracy |
| 6 | 1 | 你每打出一张牌, 都获得<N>点格挡 | Afterimage |
| 7 | 1 | 在你的回合开始时, 将你弃牌堆的一张随机攻击牌放入你的手牌并将其升级 | Aggression |
| 8 | 1 | 你每打出一张无色牌, 都获得<N>点力量 | Arsenal |
| 9 | 1 | 你每抽<N>张牌, 获得<N>能量 | Automation |
| 10 | 1 | 格挡不再在你的回合开始时消失 | Barricade |
| 11 | 1 | 每当你在你的回合获得格挡时, 其他玩家获得相应一半的格挡 | Beacon of Hope |
| 12 | 1 | 获得<N>点集中. / 在你的回合开始时, 失去<N>点集中 | Biased Cognition |
| 13 | 1 | 每当你使用或获得☆时, 对所有敌人造成<N>点伤害 | Black Hole |
| 14 | 1 | 每当你在本回合打出一张攻击牌时, 本回合获得<N>点力量 | Blade of Ink |
| 15 | 1 | 获得<N>点格挡. / 你的下一回合开始时格挡不会消失 | Blur |
| 16 | 1 | 消耗, 造成<N>点伤害. / 在你的回合开始时, 从消耗牌堆打出这张牌 | Bombardment |
| 17 | 1 | 阻止下<N>次你受到的生命值损伤 | Buffer |
| 18 | 1 | 每当你打出一张攻击牌时, 将一张随机攻击牌添加到你的手牌 | Calamity |
| 19 | 1 | 奥斯提的攻击额外造成<N>点伤害 | Calcify |
| 20 | 1 | 在你的回合开始时, 将<N>张随机牌添加到你的手牌中. 添加的牌会获得虚无 | Call of the Void |
| 21 | 1 | 每当你被攻击时, 对攻击者造成<N>点伤害 | Caltrops |
| 22 | 1 | 获得<N>点格挡. / 在下个回合获得<N>能量 | Charge Battery |
| 23 | 1 | 每当你花费☆时, 每花费一点☆, 获得<N>点格挡 | Child of the Stars |
| 24 | 1 | 在本回合保留你的手牌. / 在下个回合, / 获得<N>能量与<N>☆ | Convergence |
| 25 | 1 | 技能牌消耗变为<N>能量. / 每当你打出一张技能牌时, 将其消耗 | Corruption |
| 26 | 1 | 在你的回合开始时, 给予随机敌人<N>点灾厄 | Countdown |
| 27 | 1 | 在你的回合开始时, 将一张随机能力牌加入你的手牌 | Creative AI |
| 28 | 1 | 在你的回合开始时, 失去<N>点生命并获得<N>点格挡 | Crimson Mantle |
| 29 | 1 | 有易伤状态的敌人额外受到<N>%的伤害 | Cruelty |
| 30 | 1 | 每当你打出一张耗能大于等于<N>能量的牌时, 获得<N>点格挡 | Danse Macabre |

### 4. 暂时不建议动的复杂模式

- 卡牌数：**130**

| 排名 | 数量 | 模式 | 示例卡牌 |
| --- | --- | --- | --- |
| 1 | 3 | 不能被打出 | Injury, Soot, Wound |
| 2 | 2 | 消耗, 召唤<N> | Afterlife, Reanimate |
| 3 | 2 | 不能被打出, 在你的回合结束时, 如果这张牌在你的手牌中, 你受到<N>点伤害 | Decay, Burn |
| 4 | 2 | 造成<N>点伤害. / 生成<N>个冰霜充能球 | Cold Snap, Ice Lance |
| 5 | 2 | 永恒, 不能被打出 | Curse of the Bell, Greed |
| 6 | 2 | 消耗 | Spore Mind, Debris |
| 7 | 2 | 铸造<N> | Spoils of Battle, The Smith |
| 8 | 1 | 造成<N>点伤害. / 将这张牌的一张<N>能量复制品添加到你的弃牌堆 | Adaptive Strike |
| 9 | 1 | 造成<N>点伤害. / 将一张此牌的复制品加入你的弃牌堆 | Anger |
| 10 | 1 | 永恒, 不能被打出, 虚无 | Ascender's Bane |
| 11 | 1 | 永恒, 不能被打出, 在你的回合结束时, 如果这张牌在你的手牌中, 则失去<N>点生命 | Bad Luck |
| 12 | 1 | 造成<N>点伤害. / 生成<N>个闪电充能球 | Ball Lightning |
| 13 | 1 | 对所有敌人造成<N>点伤害. / 本场战斗中每打出过一张虚无牌, 此牌费用就减少<N>能量 | Banshee's Cry |
| 14 | 1 | 当前每有一个充能球, 造成<N>点伤害 | Barrage |
| 15 | 1 | 造成<N>点伤害. / 铸造<N>. / 本回合此前你击中过该敌人几次, 就额外铸造<N> | Beat into Shape |
| 16 | 1 | 在你的回合结束时, 如果这张牌在你的手牌中, / 则失去<N>点生命 | Beckon |
| 17 | 1 | 造成<N>点伤害. / 选择你手牌中的一张牌, 将其变化为仆从俯冲 | BEGONE! |
| 18 | 1 | 消耗, 抽<N>张牌. / 获得<N>能量. / 获得<N>☆. / 铸造<N> | Big Bang |
| 19 | 1 | 召唤<N> | Bodyguard |
| 20 | 1 | 失去<N>个充能球栏位. / 获得<N>点力量. / 获得<N>点敏捷 | Bulk Up |
| 21 | 1 | 获得<N>点格挡. / 铸造<N> | Bulwark |
| 22 | 1 | 不能被打出, 能在休息处被孵化 | Byrdonis Egg |
| 23 | 1 | 获得<N>个充能球栏位 | Capacitor |
| 24 | 1 | 生成<N>个随机充能球 | Chaos |
| 25 | 1 | 选择你抽牌堆中的<N>张牌, 将其变化为/ 仆从打击 | CHARGE!! |
| 26 | 1 | 消耗, 当前每有一名敌人, 就生成<N>个冰霜充能球 | Chill |
| 27 | 1 | 造成<N>点伤害. / 本场战斗中所有爪击卡牌的伤害增加<N>点 | Claw |
| 28 | 1 | 召唤<N>. / 从你的抽牌堆中选一张牌消耗 | Cleanse |
| 29 | 1 | 不能被打出, 虚无 | Clumsy |
| 30 | 1 | 获得<N>点格挡. / 将你手牌中的全部状态牌变化为燃料 | Compact |

## 代表样例

### 最常见未实现 Attack/Skill/Power

| 类型 | 数量 | 模式 | 示例卡牌 |
| --- | --- | --- | --- |
| attack | 4 | 造成<N>点伤害. / 给予<N>层易伤 | Beam Cell, Squash, Bash, Break |
| skill | 3 | 获得<N>点格挡. / 抽<N>张牌 | Finesse, Shrug It Off, Backflip |
| power | 3 | 获得<N>层覆甲 | Eternal Armor, Stone Armor, Neutron Aegis |

### 各角色代表性未实现卡（每角色至少3张）

- 注：以下角色在未实现集合中总数不足3张，未纳入该表：deprecated:1

| 角色 | 示例数 | 卡牌 |
| --- | --- | --- |
| colorless | 3 | Eternal Armor, Finesse, Production |
| curse | 3 | Injury, Curse of the Bell, Decay |
| defect | 3 | Beam Cell, Supercritical, Cold Snap |
| event | 3 | Squash, Exterminate, Peck |
| ironclad | 3 | Bash, Break, Uppercut |
| necrobinder | 3 | Wisp, Afterlife, Putrefy |
| quest | 3 | Byrdonis Egg, Lantern Key, Spoils Map |
| regent | 3 | Comet, Falling Star, Gamma Blast |
| silent | 3 | Backflip, Acrobatics, Adrenaline |
| status | 3 | Soot, Wound, Burn |
| token | 3 | Fuel, Disintegration, Luminesce |

### 高频模板样例（卡名 + 文本）

#### 模板 1: 造成<N>点伤害. / 给予<N>层易伤 (n=4)

- Beam Cell: 造成3点伤害。 / 给予1层易伤。
- Squash: 造成10点伤害。 / 给予2层易伤。
- Bash: 造成8点伤害。 / 给予2层易伤。
- Break: 造成20点伤害。 / 给予5层易伤。

#### 模板 2: 造成<N>点伤害. / 给予<N>层虚弱. / 给予<N>层易伤 (n=4)

- Uppercut: 造成13点伤害。 / 给予1层虚弱。 / 给予1层易伤。
- Comet: 造成33点伤害。 / 给予3层虚弱。 / 给予3层易伤。
- Falling Star: 造成7点伤害。 / 给予1层虚弱。 / 给予1层易伤。
- Gamma Blast: 造成13点伤害。 / 给予2层虚弱。 / 给予2层易伤。

#### 模板 3: 获得<N>点格挡. / 抽<N>张牌 (n=3)

- Finesse: 获得4点格挡。 / 抽1张牌。
- Shrug It Off: 获得8点格挡。 / 抽1张牌。
- Backflip: 获得5点格挡。 / 抽2张牌。

#### 模板 4: 获得<N>层覆甲 (n=3)

- Eternal Armor: 获得7层覆甲。
- Stone Armor: 获得4层覆甲。
- Neutron Aegis: 获得8层覆甲。

#### 模板 5: 不能被打出 (n=3)

- Injury: 不能被打出
- Soot: 不能被打出
- Wound: 不能被打出

#### 模板 6: 消耗, 获得<N>能量 (n=3)

- Production: 消耗,获得2能量。
- Supercritical: 消耗,获得4能量。
- Wisp: 消耗,获得1能量。

#### 模板 7: 抽<N>张牌. / 丢弃<N>张牌 (n=2)

- Acrobatics: 抽3张牌。 / 丢弃1张牌。
- Prepared: 抽1张牌。 / 丢弃1张牌。

#### 模板 8: 消耗, 获得<N>能量. / 抽<N>张牌 (n=2)

- Adrenaline: 消耗,获得1能量。 / 抽2张牌。
- Fuel: 消耗,获得1能量。 / 抽1张牌。

#### 模板 9: 消耗, 召唤<N> (n=2)

- Afterlife: 消耗,召唤6。
- Reanimate: 消耗,召唤20。

#### 模板 10: 造成<N>点伤害. / 在你的下个回合开始时, 将此卡返回你的手牌 (n=2)

- Bolas: 造成3点伤害。 / 在你的下个回合开始时，将此卡返回你的手牌。
- Thrumming Hatchet: 造成11点伤害。 / 在你的下个回合开始时，将此卡返回你的手牌。

#### 模板 11: 不能被打出, 在你的回合结束时, 如果这张牌在你的手牌中, 你受到<N>点伤害 (n=2)

- Decay: 不能被打出,在你的回合结束时，如果这张牌在你的手牌中,你受到2点伤害。
- Burn: 不能被打出,在你的回合结束时，如果这张牌在你的手牌中，你受到2点伤害。

#### 模板 12: 造成<N>点伤害<N>次 (n=2)

- Peck: 造成2点伤害3次。
- Celestial Might: 造成6点伤害3次。

#### 模板 13: 造成<N>点伤害. / 生成<N>个冰霜充能球 (n=2)

- Cold Snap: 造成6点伤害。 / 生成1个冰霜充能球。
- Ice Lance: 造成19点伤害。 / 生成3个冰霜充能球。

#### 模板 14: 永恒, 不能被打出 (n=2)

- Curse of the Bell: 永恒,不能被打出
- Greed: 永恒,不能被打出

#### 模板 15: 获得<N>点格挡. / 造成<N>点伤害 (n=2)

- Iron Wave: 获得5点格挡。 / 造成5点伤害。
- Dash: 获得10点格挡。 / 造成10点伤害。

## 建议的下一步实现顺序

1. 先覆盖 `likely_direct_mapping` 的高频 Attack/Skill 模板，快速提升可执行率。
2. 其次支持 `needs_small_param_extraction` 的条件/随机/X 变量抽取，优先低分支文本。
3. 再补 `needs_new_effect_or_trigger`，优先通用触发器（回合开始/结束、每当打牌）。
4. `complex_defer` 维持保守策略，待 effect 系统能力扩展后再分批处理。
