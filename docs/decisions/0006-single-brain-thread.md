# 0006 脑线程单例与协作式取消

- 状态：已采纳
- 相关代码：`pet/agent/pet_agent.py`（`_async_brain`、`_cancel_running_thread`、`_retire`、`recover_stuck_brain`）、
  `pet/brain/behavior.py`（RLock、`_cancel_flag` 检查点）

## 背景

一次决策包含网络请求、流式解析与多轮工具调用，必须离开 GUI 线程；但：

- Qt 不允许从外部强制终止正在运行的 `QThread`，被杀线程持有的对象会在析构时崩溃；
- LLM 可能长时间不返回（服务端无响应），而用户交互（抓取、对话）需要能打断它；
- 看门狗需要在「疑似挂死」时接管，而它跑在主线程。

## 决定

- **同一时刻只允许一条脑线程**：启动新线程前先 `_cancel_running_thread`（置取消标志 + `quit()` + 有限等待）
  并 `_retire` 旧线程；`_retire` 只持有引用（放进 `_retired` 列表），**绝不析构仍在运行的 QThread**；
- **协作式取消**：`_cancel_flag` 与世代号 `_active_stream_id`，旧管线在下一个轮询点自行退出；
- **抢不到就让路**：`Behavior` 内部 `RLock` 拿不到时不排队——autonomous/interact 降级本地兜底，chat 回固定台词；
- **看门狗兜底**：超过 `BRAIN_STUCK_TIMEOUT`（默认 300 秒）无进展时取消线程（退休延迟到下一轮）、
  用 `state_machine.force(IDLE)` 绕过迁移表复位状态，再通知用户。

## 后果

- 不会出现「杀线程」引发的崩溃；交互永远不会被长请求卡死；
- 代价：旧管线可能再跑一小会儿才退出，期间它的结果会被世代号丢弃而不是立刻停止；
  退出时若仍有线程在跑，进程用 `os._exit()` 跳过解释器清理。
