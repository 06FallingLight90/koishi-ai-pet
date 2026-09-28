# 0002 被动注入的记忆不更新访问统计

- 状态：已采纳
- 相关代码：`pet/brain/memory.py`（`random_events`、`touch`、`query_core` / `query_recent` 的 `exclude_ids` 下推）
- 相关文档：[subsystems/memory.md](../subsystems/memory.md) §3

## 背景

记忆的「有效分」= `importance × 衰减 × recency_factor`，其中 `recency_factor` 只看 `last_accessed_at`，
最近被召回过的记忆最多 +50%。核心槽的门槛是有效分 ≥ 3.5。

「忽然想起来的旧事」这条通道（`random_events`）每轮都会随机抽一条事件记忆注入上下文。
如果它走正常的召回路径（`touch`），随机抽中就会让这条记忆白拿 +50% 加成、挤进核心槽、下轮更可能被抽中——
形成自我强化循环；同时 `access_count` 被污染还会影响 L3→L2 晋升与容量淘汰。

## 决定

- `random_events` **只读**：不 `touch`、不计召回冷却，也不参与配额；
- `touch` 只在「真正入选召回」时发生；
- 被冗余抑制或 `exclude_ids` 排除的 id 在 **SQL 层**剔除（而不是取回来再过滤），确保它们不会被 `touch`。

## 后果

- 被动注入不会改变任何记忆的排序地位，抽中内容对召回质量是「中性」的；
- 代价：反复出现的旧事不会因此「变新」，也不会让 L3 记忆晋升，纯靠正常召回与工具检索来改变权重；
- 有测试锁定（`tests/test_memory.py`：注入后所有行 `access_count == 0`）。
