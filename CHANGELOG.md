# 变更记录

本文件由 [`scripts/gen_changelog.py`](scripts/gen_changelog.py) 从 git 历史生成，
按 [Conventional Commits](CONTRIBUTING.md) 前缀分组；
起点 tag 为 `v1.5.0`，更早的历史没有规范化的提交信息、未回溯（见 GitHub Releases）。

发布前刷新一次：`python scripts/gen_changelog.py`，流程见 [docs/operations/release.md](docs/operations/release.md)。

## 未发布

**新功能**
- **action**: 动作产出机制与钓鱼玩法（a8477f7）
- **anim**: 新增失落动作与紫黑螺旋粒子（fde0ffd）
- **anim**: 呼吸加上等体积缩放，位移与缩放可分别配置（0e1c233）
- **anim**: 静止类动作加呼吸位移，并加固帧动画播放的超时与配置容错（e33a2c6）
- **recall**: 补全回忆工具引导，明确空结果与结果用法（8a44f52）
- **context**: 新增「你惦记着的事」章节，统一需求、作息与旧事记忆注入（25918c1）

**修复**
- **action**: 产出结算移至动作正常结束（26f0c7d）
- **file_ops**: 路径校验解析 symlink/junction 逃逸并补测试（d48b3c0）
- **timer**: 修正离线恢复时已到点/未到点定时器的处理（d36501d）
- **pulse**: sit 不再恢复精力、sleep 恢复速率减半，好感回归基线降至 50（bef25b7）
- **agent**: 修复脑线程取消后被析构触发 Qt abort 崩溃（a3b03fc）
- **timer**: 离线到期定时器恢复时锁内补发导致自死锁，改为锁外补发（59e805b）

**调优**
- **vitals**: 动作精力消耗减半，缓解精力下降过快（f4d2b3c）

**重构**
- 分离纯版本逻辑并延迟 pet.action 的 Qt 导入（4661e9a）
- **agent**: 清理历史遗留的 SLEEPING 状态与死方法（ad3116d）

**样式**
- **idle**: 待机呼吸幅度与节奏对齐思考动画（fa489e5）

**测试**
- **context_notes**: 消除 TestNeedsNote 对运行时段的依赖（80eba6b）
- 补测试运行说明与 CI，清理临时目录与真实 sleep（fc38184）
- **scripts**: 安装/更新脚本测试迁移到 pytest 并合并参数化（cda2c98）
- 新增单元测试套件与 pytest 配置（dev 可选依赖）（a852d0a）

**杂项**
- **anim**: 呼吸缩放只留给 sleep，其余动作回到纯位移（323254b）
- 测试目录改用 export-ignore 排除，移除 .gitignore 中的 test 规则（c3df1b0）

**其他**
- 降低鱼粒子上浮高度避免顶部被裁切（de37ba9）
- 修复鱼粒子水平居中，并将调试面板粒子特效改为扫描注册表（f0a7d08）
- 钓鱼判定增加命中日志（f48405f）
- 钓到鱼时新增鱼emoji上浮粒子特效（d7c35d0）
- 调整钓鱼命中概率为60%并改为recent窗口期注入（93bfe66）
- 调整个人认知提示词（a7e9770）

## v1.5.4 — 2026-09-27

**新功能**
- **prompt**: 新增输入可信边界与记忆写入约束（cdae6ed）
- **context**: 新增「最近发生了什么」事件流与工具通用事件接口（58abfe9）
- **prompt**: 放开沉默限制，新增自我生活引导与人格台词范例（841d9c4）
- **llm**: 新增首选/备选模型方案与失败回退切换（3af07ac）
- **prompt**: 约束 Speech 可理解性并放宽屏幕评论要求（60c96da）

**修复**
- **context**: 低理智状态改为无害表达，移除破坏性引导（fdbbc3b）
- **ui**: 修复模型列表选择后未回填模型名称（2455dae）

**重构**
- **event**: 摔落事件仅由站立窗口丢失触发，移除落地记录（696787e）
- **food**: 觅食事件归并到通用事件机制（1f524ba）

**样式**
- **prompt**: 省略号统一为半角三点（0b86c7d）

**文档**
- 项目功能清单精简，自我生活与模型容灾并入自主行动，事件记忆并入持久记忆（b617ee6）

**杂项**
- 版本号 1.5.4，README 补充双模型方案、事件记忆与 note_event 接口（8481ef9）

## v1.5.3 — 2026-09-11

**新功能**
- **prompt**: 鼓励模型依据截图与文本线索主动调用 recall（48caddb）
- **memory**: 核心槽保底轮转与工具检索晋升（30673b3）
- PyPI mirror fallback in setup/update scripts and self-apply pending update scripts（b65ca6c）
- **memory**: filter memory browsing by creation date range（57d699d）
- register recall memory-retrieval meta tool（400476c）
- add MemoryStore singleton and recall search support（51ccd06）

**修复**
- **prompt**: 耗时动作示例改用与可用动作一致的参数写法，去掉 duration=（f7264e2）
- **ui**: 透传 speech duration，工具 aside 气泡显示 2s（b46b1e1）
- release SQLite write lock on uncommitted updates and heal poisoned connections（6dd2772）
- bound stream-connect phase and add brain-stuck watchdog（b07d8bf）
- **tools**: truncate long tool results in executor logs（ae9f647）
- **memory**: guard query term merging for whole-sentence queries（bb848a2）

**重构**
- rename knowledge group memory to knowledge and update docs（25c07d9）

**文档**
- **prompt**: 觅食示例精简为就地写法，避免与 tool 描述重复强调（41374b1）

**杂项**
- 版本号 1.5.3，推荐模型改为 deepseek-flash / mimo-v2.5，去掉模型名 placeholder（6ad7f02）
- **memory**: 精简核心槽与工具检索晋升的注释（a6ca4ff）

**其他**
- Update self_update.py（a61e99f）
- End games neutrally on user timeout or close, no forfeit loss（ce1f90f）
- 调整prompt（63d30ef）
- 调整prompt（ad17267）
- 调整工具使用描述（d9334c8）
- Update prompts.py（a86812d）

## v1.5.2 — 2026-09-01

**其他**
- Update pyproject.toml（ce0904a）
- Fix false negative in setup.bat 64-bit check: missing sys import（370a121）
- Guide mood output after games; tune mood decay rates（e961637）
- Add timestamp prefix to head pat context note（ac7946d）
- Refactor system prompt assembly; move identity guide to first line（4cf4880）
- 调整提示词（00f8f5e）
- Rename game_board_panel to tictac_panel（272a448）
- Add single-instance lock to prevent multi-instance conflicts（4d32271）

## v1.5.1 — 2026-08-29

**修复**
- 合并历史 system 消息到主 prompt，适配 ollama qwen3 模板（0ff49a7）

**其他**
- Update pyproject.toml（16f9768）
- Adjust meta tool max rounds to 99（c6253b9）
- Emphasize continue-play instruction in twenty questions play returns（6a1dc22）
- Add twenty questions game with panel; raise tool max rounds to 30（ef2c0a3）
- Adjust mood decay: grace window 600s to 60s, joy regression rate 1.5 to 2.5（53bf2de）
- README: add DeepSeek-V4-Flash-Vision-Exp as recommended vision model（28b8128）
- Inject head-pat note into context remarks when user petted within a mid_tick window（c83b84b）
- Ensure each emotion in sequence plays at least 1.5s（122da9b）
- 调整部分提示词（5d22485）
- Fix database is locked causing UI freeze: unified SQLite connections, enable WAL + busy_timeout, fast-fail saves on main thread（f86a61d）
- 修复macos安装失败的问题，更新python版本要求（1167f5b）
- Guide aside to follow pet personality（83d4396）
- Support multiple emotions and remove emotion-linked particles（e993082）
- Update README.md（b10a835）
- Deduplicate self-feeding context via system path only（483be30）
- Update pyproject.toml（fb82ad4）

## v1.5.0 — 2026-08-20

**新功能**
- unify game summary perspective; remove panel auto-hide; end-of-game guidance（38b7120）
- add game__start lifecycle and unique arg names; fix review findings（45494aa）
- add rock-paper-scissors game and refactor game panels（e590e0d）
- add tic-tac-toe game with interactive board（314bcf6）
- **prompt**: guide model to avoid repeating tool_call speech in final output（46a68e3）
- **game**: dynamic game__play args schema from registered games（25278d4）
- **speech**: record tool_call speech into conversation history（761f232）
- **speech**: log tool_call speech at info level（769041c）
- **prompt**: guide model to use speech param in tool calls（efc4851）
- **tool**: add universal speech param to all tool calls（8e4e484）
- **game**: add guess_number game with speech output on play（6b917ea）
- **game**: add turn-based game base with play/list/stop meta tool（9ef32dd）
- **attention**: inject user-neglect state into autonomous prompt by rounds（55a3cab）
- **mood**: add natural decay toward baseline for joy/affection（8bff8c0）
- disable tools for manual feeding interaction（287e5be）
- support per-trigger thinking and tools override for instant interactions（89acb1a）
- **food**: use AABB collision for eating detection, tick 200ms（f17016e）
- **crash**: collect faulthandler log for native crashes on abnormal exit（6b500bf）
- 觅食食物改为全屏随机位置，需结合 walk/drive/bounce 取食（1ef86cb）
- 觅食游戏——桌宠自主生成食物并吃掉（52ea8ea）

**修复**
- disable board cells during pet turn; auto-close board after game ends（41429f8）
- 修复interact/chat撞上LLM调用时主线程卡死，记忆保存移至后台线程（0ac26bb）
- **speech**: use counter+lock for model speech suppression, fix race（1ae69a7）
- **tool**: log full tool result without truncation（08ee87d）
- **agent**: cooperative cancel for brain thread, avoid UI freeze（1586103）
- **mood**: remove sanity floor clamp, sanity fully event-driven（47c7ae6）
- mark meta tools via ToolDef.meta and hide from right-click tool menu（7dbe79f）
- thinking 恢复直接播放（循环动画入队会阻塞队列至超时）（d291457）
- 等待动画改为入队执行，falling 时由队列暂停/落地恢复（861365f）
- 觅食进食时悬空不播等待动画，避免覆盖 falling（3a2f6c3）
- 修复觅食游戏 tick 不启动导致快照永不就绪（87d903e）
- 修复觅食游戏的 spawn 返回语义、动画泄漏与开关联动问题（ba905e0）

**重构**
- **game**: move speech lines to game hooks, keep base generic（4dae7e0）
- **food**: extract food game to pet/food module（0a0f140）
- wait_anim 统一为 _play_wait_anim，chat 同步支持（3f1b9ca）

**杂项**
- 精简跨线程相关注释（9c1f70b）
- 精简 food__status 工具描述（331311b）
- 精简 food__spawn 工具描述（cd5ecb7）

**其他**
- Fix IndentationError in game play summary（d33456d）
- 调整aside的概念（1cb68bc）
- Rename tool call speech param to aside（84d1999）
- Update prompts.py（8b59e71）
- Rename game start tool to init（8c43a89）
- Clean up redundant comments and show countdown as text（127399a）
- 调整desc（d5a8185）
- Update registry.py（7d38d52）
- 优化提示词（264fe78）
- 调整提示词（66a7b0e）
- 调整提示词（596f41b）
- 修改元工具调用上限（ead2f34）
- 更新提示词（1d0324b）
- 修改食物消失默认时间（702fe5e）
- 精简注释（f234174）
