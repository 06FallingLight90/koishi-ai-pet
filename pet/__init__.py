"""Koishi AI Pet 包分层说明。

action/   — 动作系统：动作定义、注册表、帧动画播放、重力特效
agent/    — 调度层：PetAgent 编排 Brain + 截图 + UI 信号，含定时调度与状态机
brain/    — LLM 调用层：Behavior 决策、上下文组装、prompt 模板、记忆与窗口探测
food/     — 觅食本能：需求驱动的地面食物生成与食用
game/     — 回合制小游戏：猜数字、猜拳、井字棋、二十问
pulse/    — 状态引擎：vitals(生理参数) 与 mood(情绪参数) 的数值衰减与持久化
tools/    — 工具系统：注册表、执行器、上下文构建、工具自动发现与加载
ui/       — Qt 界面：宠物窗口、气泡对话、粒子特效、调试面板、系统托盘
voice/    — 语音输入：全局热键、麦克风采集、讯飞听写
"""

# 尽早安装崩溃信息收集钩子；即使安装失败也不阻塞主程序启动
try:
    from pet.crash_reporter import install as _install_crash_reporter

    _crash_reporter = _install_crash_reporter()
except Exception:
    pass

