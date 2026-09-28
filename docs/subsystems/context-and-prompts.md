# 上下文与提示词组装

每轮请求发给模型的内容由三部分拼成：**静态块**（`pet/brain/prompts.py`）、
**运行时块**（`pet/brain/context_builder.py`）、**多轮历史**（`pet/brain/base.py`）。
块的机械清单与组合白名单见 [reference/prompt-blocks.md](../reference/prompt-blocks.md)（生成物）。

## 1. system prompt 的拼接顺序

`ContextBuilder._build_system(mode, task)`：

1. `prompts.build_system_prompt(mode, task)` 产出的静态块，顺序固定：
   身份 → 独立生活设定 → 输入可信度 → `<<FEELING>>` 锚点 → 你的人格 → 人格台词范例 →
   称呼 → 表达底线 → 记忆格式（仅 `autonomous` / `chat`）→ **感知段**（按 `mode`，末尾是动作表）→ **任务段**（按 `task`）。
   人格与范例为空、记忆格式不适用时会跳过对应块。
2. 运行时块，拼好后替换掉 `<<FEELING>>` 锚点：
   - `[你现在的状态]`：`_build_feeling()`（数值→自然语言）+ `_build_attention_hint()`（仅自主任务，连续未互动档位）；
   - `[你惦记着的事]`：`_build_needs_note()`（未满足需求 + 该怎么做）+ `_memory_event_note()`（忽然想起来的旧事），
     **只在 `_NEEDS_TASKS`（`autonomous` / `chat`）注入**；
   - `[最近发生了什么]`：`_recent_events_note()`（近期事件，含工具上报与动作产出）。
3. 最后追加 `[你对用户的记忆]`：`memory_store.retrieve_context(user_message)` 的召回结果（可能为空）。

`mode` 决定感知段（视觉 / 非视觉 / 对话 / 交互），`task` 决定任务段（自主 / 对话 / 交互），
合法组合是白名单，写错直接抛 `ValueError`——新增模式或任务要**同时**改
`_PERCEPTION_SECTIONS`、`_TASK_SECTIONS` 与 `build_system_prompt` 里的组合白名单三处。

## 2. user 段与历史

- user 段承载**每轮都会变的东西**：时间前缀（`_time_prefix`）、窗口探测结果、用户消息或截图。
  时间不写进 system——system 前缀稳定才能命中 prompt 缓存（`LLM_CACHE_PROMPT`）。
- 历史多轮由 `BrainMixin.get_multi_turn_messages` 装配，先按条数上限淘汰、再按 token 预算淘汰；
  历史里的 system 片段会被 `_merge_system_history` 并成一段 `[上下文备注]` 追加到 system 末尾，
  保持「一个 system + 若干 user/assistant」的干净结构。
- 交互任务（`interact`）只发 system + user 两条，不带历史。

## 3. 动态块的生命周期

| 块 | 状态保存在哪 | 什么时候消失 |
|---|---|---|
| 需求（`_active_needs`） | `ContextBuilder` 内存字典（需求 → 起始时间） | 数值恢复即移除；重启后「已持续」归零 |
| 旧事（`_recent_event_ids`） | 同上（上一轮注入过的 id） | 每轮更新，候选耗尽时允许重复 |
| 近期事件 | `PetAgent` 的事件缓冲区 | 超出 `RECENT_EVENT_WINDOW_S` 保鲜窗口后不再注入 |
| 求关注提示 | `PetAgent.rounds_without_user` | 用户一说话就清零 |
| 召回记忆 | 记忆库（SQLite） | 每轮重新召回，与冷却、有效分相关（见 [memory.md](memory.md)） |

作息需求（`bedtime` / `drowsy`）不依赖数值，按钟点判定，文案里不出现具体时间
（`system` 里放钟点会让缓存每秒失效）。

## 4. 三条任务路径的差异

| | autonomous | chat | interact |
|---|---|---|---|
| mode | `autonomous_vision` / `autonomous_non_vision` | `chat_vision` / `chat_non_vision` | `interact` |
| 记忆格式块 | 有 | 有 | 无 |
| `[你惦记着的事]` | 注入 | 注入 | **不注入** |
| 求关注提示 | 有 | 无 | 无 |
| 历史多轮 | 有 | 有 | 无 |
| 感知段 | 视觉 / 窗口探测 | 视觉 / 窗口探测 | 只有动作表 |

`interact` 是对单一事件的反射（被抓、放下、投喂、窗口消失），塞长上下文只会让台词跑偏，
所以它的 prompt 最薄。

## 5. 设计取舍（改提示词前请先读）

1. **system 稳定、变化进 user**：时间、窗口、用户消息、截图都在 user 段；
   否则 prompt 缓存每一轮都会失效。
2. **数值不直接进提示词**：先由 `_build_feeling` 译成感受，档位与数值区间一一对应；
   改档位要连带改 `_NEED_THRESHOLD`（60 在两处都必须是中性档）与相关测试。
3. **「该怎么做」集中在一处**：需求对应的做法只写在「你惦记着的事」章节（`_NEED_HINTS`），
   感受描述里不放祈使句——两处都给指令时模型会挑一条，行为变得不可预测。
4. **被动注入不产生副作用**：旧事走只读查询（不 touch 记忆的访问统计），
   见 [memory.md](memory.md) §3。
5. **块与任务解耦**：块是常量、任务决定组合，新增任务只需加一个构建函数并在白名单登记。

## 6. 不变量与坑

1. 新增 `mode` / `task` 要改**三处**（`_PERCEPTION_SECTIONS`、`_TASK_SECTIONS`、组合白名单），
   否则 `ValueError` 或组合被拒。
2. `_PERCEPTION_SECTIONS` 里的动作表是 `_Lazy(generate_action_section)`——**每次求值会重读 config**，
   所以改调度间隔后提示词里的时长范围会同步变化（也是它不能被缓存的原因）。
3. 需求阈值（`_NEED_THRESHOLD = 60`）与感受档位必须一致；`sanity` 用
   `SANITY_CRITICAL_THRESHOLD` 而非 60。两条都有注释与测试锁定。
4. `_NEEDS_TASKS` 决定哪些任务注入需求块，改它等于改 `interact` 的台词风格。
5. 任何块的文案改动都会体现在生成物 `docs/reference/prompt-blocks.md` 里 ——
   改完记得 `python scripts/gen_docs.py`，否则 CI 的文档检查会红。
6. 时间前缀与窗口信息**不要挪进 system**，代价是 prompt 缓存整体失效。
