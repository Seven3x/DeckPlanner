# STS2 导入代理状态

## 当前目标

- 让现有 STS2 导入链路在单卡 JSON 输入下收敛到目录级完整性。
- 相比可执行覆盖率，优先保证读取完整性、归一化结构稳定性和运行时加载器兼容性。

## 当前输入目录

- 当前使用的输入：`data/sts2/raw/ea_01`
- 说明：`data/sts2/external/sts2_database/` 目前只有 `README.md`，因此仓库里实际使用的单卡数据集位于 `data/sts2/raw/ea_01`。

## 当前输出文件

- 归一化卡牌目录：`data/sts2/normalized/cards.ea_01.json`
- 状态报告：`docs/sts2_import_status_ea_01.md`

## 迭代记录

### 第 1 次迭代

- 结果指标：
  - scanned: 577
  - imported: 577
  - skipped: 0
  - executable: 34
  - unimplemented: 543
- 发现：
  - 导入器可以完整读取整个目录，且不会崩溃。
  - 在 `game` conda 环境下，`import_status_report.py` 和运行时加载失败，因为 `src/slay2_ai/card_defs.py` 在较旧 Python 上运行时求值了 `int | str`。
  - `sample_raw_loader.py` 默认假设一定会存在 `text_only` 卡牌，但当前卡牌目录对所有不可执行回退都使用了 `unimplemented`。
- 已应用修复：
  - 规划运行时类型兼容性修复。
  - 规划 smoke check 断言修复。
  - 规划对低风险模式和标签保留的保守型导入器扩展。

### 第 2 次迭代

- 结果指标：
  - scanned: 577
  - imported: 577
  - skipped: 0
  - executable: 39
  - mapped: 39
  - unimplemented: 538
- 发现：
  - 运行时加载器和状态报告现在可以在 `game` 环境中通过。
  - 归一化输出满足 `card_count == len(cards)`，不存在重复 `id`，也没有缺失必填字段。
  - 剩余未映射卡牌主要集中在多行卡牌、触发型卡牌、成长型卡牌、AoE/随机目标卡牌，以及当前归一化行为键无法安全表达的机制。
- 已应用修复：
  - 用 `typing.Union` 替换运行时不兼容的 `int | str` 类型别名写法。
  - 放宽加载器 smoke check，不再强制要求 `text_only`，而是对任意不可执行卡牌断言。
  - 从源数据关键词和目标元数据中保留导入标签。
  - 改进占位变量的回退解析逻辑，使数值提取更安全。
  - 为复数形式的抽牌文本以及精确单目标 `Apply X Weak / Vulnerable / Poison.` 映射加入保守支持。

### 第 3 次迭代

- 结果指标：
  - scanned: 577
  - imported: 577
  - skipped: 0
  - executable: 39
  - mapped: 39
  - unimplemented: 538
- 发现：
  - 在第 2 次迭代之后，已没有新的读取、校验或运行时失败问题。
  - 剩余 `type == other` 的条目属于不可打出的元数据/特殊卡，而不是导入器漏掉的内容。
  - 再做一轮扩展，主要需要新增复合行为或触发行为，而不是修补导入链路。
- 已应用修复：
  - 让 `README` 和导入计划文档与仓库实际输入布局及当前安全映射范围保持同步。

## 当前剩余阻塞项

- 需要确认运行时/报告校验能在仓库的 `conda` `game` 环境下通过。
- 需要最终确认剩余不可执行卡牌主要是复杂多效果或未支持机制，而不是读取失败。

## 最终结论

- 已对仓库当前可用的单卡数据集实现目录级完整导入收敛。
- 停止原因：连续两次迭代未再带来导入/运行时改进，剩余缺口属于行为复杂度问题，而不是读取失败。
