# 文档索引

## 按目的选路径

| 我想… | 读这些 |
|---|---|
| 安装、配置模型、用内置工具 | [../README.md](../README.md) |
| 建立整体心智模型：线程怎么跑、一次决策经过什么 | [architecture.md](architecture.md) |
| 查某个配置项的类型/默认值/是否需重启 | [reference/config.md](reference/config.md) |
| 查动作、工具、粒子特效、提示词块的清单 | [reference/](reference/) |
| 搞懂 system prompt 是怎么拼出来的 | [subsystems/context-and-prompts.md](subsystems/context-and-prompts.md) + [reference/prompt-blocks.md](reference/prompt-blocks.md) |
| 给桌宠加一项工具能力 | [tool-development.md](tool-development.md) |
| 深入某一子系统（记忆、数值、动作、提示词、素材） | [subsystems/](subsystems/) |
| 参与开发：环境、测试、提交、PR | [../CONTRIBUTING.md](../CONTRIBUTING.md) |
| 发版、理解更新脚本行为 | [operations/release.md](operations/release.md) |
| 排查问题（日志、崩溃报告在哪） | [operations/troubleshooting.md](operations/troubleshooting.md) |
| 看懂 vitals / mood / needs / outcome 这些词 | [glossary.md](glossary.md) |
| 知道某个设计「为什么这么做」 | [decisions/](decisions/) |
| 看某个版本改了什么 | [../CHANGELOG.md](../CHANGELOG.md) |

## 文档地图

| 文件 | 角色 | 类型 | 内容 | 维护方式 |
|---|---|---|---|---|
| [architecture.md](architecture.md) | 架构解释 | 手写 | 分层与线程模型、启动链路、数据流、状态机、模块职责、红线与常见改动入口 | 改架构时人工更新 |
| [glossary.md](glossary.md) | 事实参考 | 手写 | 项目专有术语表 | 新增术语时人工补充 |
| [tool-development.md](tool-development.md) | 操作指南 | 手写 | 工具开发：目录约定、`register()` 模板、参数与返回值约定、`TOOL_CTX` 能力、`aside`、启用方式 | 改工具约定时人工更新 |
| [reference/config.md](reference/config.md) | 事实参考 | 生成 | 配置项全量（按设置页签分组）+ 字段含义 | `pet/config.py` 的 `_KEY_META` |
| [reference/actions.md](reference/actions.md) | 事实参考 | 生成 | 动作表：分类、参数、示例、时长范围 | `pet/action/registry.py` |
| [reference/tools.md](reference/tools.md) | 事实参考 | 生成 | 工具分组、方法、参数 | `pet/tools/**/__init__.py` 与 `pet/tools/registry.py` |
| [reference/effects.md](reference/effects.md) | 事实参考 | 生成 | 粒子特效名、生成函数、默认位置 | `pet/ui/particle.py` 的 `_SPAWNERS` |
| [reference/prompt-blocks.md](reference/prompt-blocks.md) | 事实参考 | 生成 | 提示词块、感知段/任务段组合、合法组合白名单 | `pet/brain/prompts.py` |
| [reference/modules.md](reference/modules.md) | 事实参考 | 生成 | 每个模块的一句话职责 | 模块 docstring |
| [subsystems/context-and-prompts.md](subsystems/context-and-prompts.md) | 架构解释 | 手写 | 上下文与提示词组装、三条任务的差异、动态块生命周期 | 改提示词结构时人工更新 |
| [subsystems/memory.md](subsystems/memory.md) | 架构解释 | 手写 | 记忆数据模型、写入与召回、维护与容量、坑 | 改记忆策略时人工更新 |
| [subsystems/vitals-and-mood.md](subsystems/vitals-and-mood.md) | 架构解释 | 手写 | 数值来源、衰减、阈值信号、到提示词的映射 | 改数值手感时人工更新 |
| [subsystems/actions-and-animation.md](subsystems/actions-and-animation.md) | 架构解释 | 手写 | 动作链路、队列与超时、帧动画的加载与运行、粒子 | 改动作系统时人工更新 |
| [subsystems/assets-pipeline.md](subsystems/assets-pipeline.md) | 事实参考 | 手写 | 素材规格、目录与命名、配置字段契约、入库检查清单 | 改素材规格或流程时人工更新 |
| [operations/release.md](operations/release.md) | 操作指南 | 手写 | 版本与 tag、更新脚本行为、发布检查清单、变更记录 | 改发布流程时人工更新 |
| [operations/troubleshooting.md](operations/troubleshooting.md) | 操作指南 | 手写 | 现象对照表、诊断命令、上报要带什么 | 遇到新坑时补充 |
| [decisions/](decisions/README.md) | 决策记录 | 手写 | 设计决策记录（ADR），索引见该目录的 README | 做出取舍时新增一条 |
| [../CHANGELOG.md](../CHANGELOG.md) | 事实参考 | 生成 | 按版本分组的变更记录 | `python scripts/gen_changelog.py` |
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | 操作指南 | 手写 | 开发流程、测试、提交与 PR 规范 | 流程变化时人工更新 |

**角色边界**（防止同一件事在多处各写一遍）：

- **架构解释**回答「是什么 / 为什么这样切分」，只保留能建立心智模型的那一层，细节一律链接出去；
- **操作指南**承载可执行步骤（命令、检查清单、排错流程），面向「我要做某件事」；
- **事实参考**承载会随代码变化的清单与字段（默认值、字段表、特效名），尽量由脚本生成；
- **决策记录**只写取舍的理由与代价，不复述做法。

复述别处的细节时，只保留「结论 + 链接」，权威定义放回上面对应的那一类。

## 文档如何更新

- **生成物**：`python scripts/gen_docs.py` 重新生成 [reference/](reference/)；
  `python scripts/gen_docs.py --check` 只校验，不一致返回退出码 1（CI 里跑的就是它，见 `tests/test_docs.py`）。
  生成文件开头有「请勿手工编辑」标记，手工改动会被下一次生成覆盖。
- **手写文档**：没有自动校验，改动相关代码时请一并更新；`tests/test_docs.py` 会保证
  每个包都在 `architecture.md` 的模块职责表里出现过、文档内的相对链接都指向存在的文件。
- 生成的文档里不含时间戳与版本号：内容只由代码决定，否则 `--check` 永远报脏。
- **变更记录**：`python scripts/gen_changelog.py` 从 git 历史生成 [`CHANGELOG.md`](../CHANGELOG.md)，
  发布前刷新一次；它不接 CI，原因见 [operations/release.md](operations/release.md) §4。
- **ADR**：做出设计取舍时在 [decisions/](decisions/README.md) 新增一条，并在该目录 README 的索引里登记
  （`tests/test_docs.py` 会检查索引完整性）。
- `docs/` 里还有几份历史本地草稿（`plan.md`、`iat_ws_python3.py`、`superpowers/`、
  `ChatHistoryWindow_*.md`），被 `.gitignore` 忽略、不进仓库；`tests/test_docs.py` 的忽略
  清单与 `.gitignore` 保持一致，要新增忽略项时两边都得改。

## 三条捷径

1. 第一次读代码：先看 `architecture.md` §1 的图与 §4 的数据流，再按 §9 找包。
2. 想加功能：直接看 `architecture.md` §12「常见改动入口」。
3. 不确定改动是否踩线：看 `architecture.md` §11「关键约定与不变量」。
