# DeckPlanner

一个基于 **状态模拟**、**事件驱动效果** 与 **动作序列搜索** 的卡牌决策规划 Python 原型项目。

## 项目目标

DeckPlanner 是一个本地研究型项目，目标是构建受 *Slay the Spire* 战斗启发的卡牌决策引擎。

本项目**不**给每张卡固定分数，而是显式建模：

- 游戏状态转移
- 原子化卡牌效果
- 触发器与延迟效果
- 回合内动作规划
- 结果状态启发式评估

核心问题是：

> 给定当前状态 `s`，本回合最优动作序列是什么？

---

## 设计原则

### 1. 状态优先，而非静态卡牌评分

卡牌价值依赖上下文状态，不做永久静态评分。

### 2. 效果原子化与可组合

复杂卡牌应拆解为可复用效果原语，例如：

- `DealDamage`
- `GainBlock`
- `DrawCards`
- `GainEnergy`
- `ApplyBuff`
- `ApplyDebuff`
- `AddTrigger`
- `ScheduleEffect`
- `Conditional`
- `ReplayCardEffect`

### 3. 事件驱动架构

引擎应支持基于事件响应的效果，例如：

- `on_turn_start`
- `on_turn_end`
- `on_card_played`
- `on_attack_played`
- `on_skill_played`
- `on_damage_taken`
- `on_block_gained`
- `on_draw`
- `on_discard`
- `on_exhaust`

### 4. 显式延迟/跨回合效果

延迟效果必须进入状态并在后续时点执行，不能被拍平成即时启发式加分。

### 5. 可搜索动作空间

规划器在当前回合内对可出牌序列进行搜索，当前支持：

- DFS
- 可选 beam search
- 后续可扩展 rollout

---

## 当前状态

当前目标是 **MVP**，覆盖：

- 单玩家
- 单敌人
- 手牌 / 抽牌堆 / 弃牌堆 / 消耗堆
- 基础出牌流程
- 回合开始/结束流程
- 延迟效果
- 单次触发器
- 简单启发式评估
- 回合内序列规划

---

## 推荐运行方式

```bash
PYTHONPATH=src python3 -m slay2_ai.demo
```

---

## 计划结构

```text
DeckPlanner/
├── README.md
├── game_state.py
├── card_defs.py
├── effects.py
├── triggers.py
├── evaluator.py
├── planner.py
├── demo.py
└── tests/
    ├── test_effects.py
    └── test_planner.py
```
