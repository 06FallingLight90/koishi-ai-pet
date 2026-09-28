# 0005 理智不参与衰减、且用临界值判定

- 状态：已采纳
- 相关代码：`pet/pulse/mood.py`（`apply_decay`、`MoodDecayConfig`）、
  `pet/brain/context_builder.py`（`_circadian_need` 之外的 `unsteady` 判定与 sanity 档位）、
  `pet/agent/scheduled_tasks.py`（低理智切 `grim` 动画与 `dark_hearts`）
- 相关文档：[subsystems/vitals-and-mood.md](../subsystems/vitals-and-mood.md) §3、§4

## 背景

- 好感与愉悦都有「向基线回归」的自然衰减，理智没有天然基线概念；
- 需求判定统一用 `< 60`，但理智平时就在 80 起步、由事件压低，用 60 会把正常波动全算成「惦记」；
- 另外还存在一套 `MoodThresholds`（`sanity_low=30` / `sanity_mad=10`），用于发出信号。

## 决定

- **理智不参与自然衰减**：只由 LLM 输出行、摸头、事件驱动；
- 需求判定与感受档位改用 `config.SANITY_CRITICAL_THRESHOLD`（默认 20）及其派生档位
  （≥2/3 阈值「有点神神叨叨」、≥1/3「脑子快炸了」、更低「理智彻底崩坏」）；
- 动画与粒子也读同一个阈值，保证「数值跨过这条线」时提示词、表情、特效同步变化。

## 后果

- 低理智是一条明确可调的线：调 `SANITY_CRITICAL_THRESHOLD` 会同时影响需求、文案、动画与粒子；
- 代价：`MoodThresholds.sanity_low/mad` 仍在，但**调它们不改变行为**（只影响无消费者的信号）。
  排障手册里专门记了这条，避免下次再被绕进去。
