<!-- 由 scripts/gen_docs.py 生成，请勿手工编辑 -->

# 粒子特效参考

特效注册表是 `pet/ui/particle.py` 里的 `_SPAWNERS`（名字 → 生成函数）。
新增特效只需在这里登记：调试面板的测试按钮由 `ParticleWidget.effect_names()` 自动列出，
动作到特效的映射（`pet/pulse` 与 `pet/agent/scheduled_tasks.py`）按同一个名字引用。

| 特效名 | 生成函数 | 默认纵向位置 | 说明 |
|---|---|---|---|
| `dust` | `_spawn_dust()` | 脚底（特殊值） | 落地灰尘：从脚底向上喷射后受重力下落。 |
| `stars` | `_spawn_stars()` | `1 / 4` | 开心星星：从身体中心向外扩散上飘。 |
| `zzz` | `_spawn_zzz()` | `1 / 2` | 睡觉 Zzz：缓慢右上飘，字号递增。 |
| `notes` | `_spawn_notes()` | `1 / 4` | 通话音符：♪♫ 缓慢上飘，暖色调。 |
| `hearts` | `_spawn_hearts()` | `1 / 4` | 爱心粒子：从头顶上飘。 |
| `dark_hearts` | `_spawn_dark_hearts()` | `1 / 4` | 黑色心型粒子：随机漂浮上升，理智低落时散发。 |
| `bubbles` | `_spawn_bubbles()` | `1 / 4` | 彩色肥皂泡：缓慢上飘，半透明柔和色调。 |
| `question_marks` | `_spawn_question_marks()` | `1 / 4` | 疑惑问号：从头顶缓慢上飘。 |
| `spiral` | `_spawn_spiral()` | `1 / 4` | 失落漩涡：紫黑色小漩涡从头顶飘出，慢慢上浮后消散（同爱心）。 |
| `fish` | `_spawn_fish()` | `1 / 4` | 钓到鱼：一个鱼 emoji 从头部出现，匀速上浮到一定高度后淡出。 |

## 位置与生命周期

- 默认纵向位置是相对宠物窗口高度的比例，`-1` 表示特殊值（脚底）；未登记的特效按 `1/3` 兜底
- 粒子窗口比宠物窗口大 `_MARGIN`（100px），特效在这里面绘制，超出会被裁掉
- 每个粒子按 `lifetime` 淡出（最后 30% 加速），`gravity` 为负值时持续上飘
