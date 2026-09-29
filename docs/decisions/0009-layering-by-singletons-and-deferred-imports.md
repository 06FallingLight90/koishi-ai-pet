# 0009 分层靠模块级单例与延迟导入维系

- 状态：已采纳（现状记录）
- 相关代码：`pet/config.py`（`config`）、`pet/tools/registry.py`（`TOOL_REGISTRY`）、
  `pet/tools/context.py`（`TOOL_CTX`）、`pet/game/gamebase.py`（`GAME`）、
  `pet/action/__init__.py`（模块级 `__getattr__` 延迟导入）
- 相关文档：[architecture.md](../architecture.md) §1、§11、§14

## 背景

这个项目没有依赖注入容器：单进程 GUI 程序，装配集中在 `pet/app.py` 的 `main()`，
运行期只有一条脑线程加几个 daemon 线程。但分层确实存在——`tools` 要驱动 `ui`（说话、做动作、记一笔），
`game` 要在脑线程里阻塞等玩家落子，而它们都不该 import 上层模块，否则立刻成环。

同时有几处「半 Qt」模块：`brain` 的提示词组装只需要动作注册表，不需要 Qt；
`pet/action/__init__.py` 要是老老实实 import 实现类，文档脚本和 brain 都会被拖进 PySide6。

## 决定

- **下层驱动上层走模块级单例**：`config`（配置）、`TOOL_REGISTRY`（工具）、`TOOL_CTX`（回调）、
  `GAME`（对局）都是模块级单例。下层只 import 单例所在的模块，真正的实现由 `main()` 装配时注入
  ——所以 `pet/tools/context.py` 不 import 任何 `pet.*` 模块，tools 层对 agent/ui 零依赖。
- **重依赖一律延迟**：Qt、平台后端（pywin32 / Quartz / xlib）、playwright 只在真正用到时才 import。
  `pet/action/__init__.py` 用模块级 `__getattr__` 把 `PetActions`、`ActionQueue` 推迟到首次取用，
  只依赖 `registry` 的调用方就不会被拖入 PySide6。
- **不追求「零环」**：允许用函数内 import 打断环，也接受包内自引用这类既有形状，
  代价如实记在 [architecture.md §14](../architecture.md)。依赖方向本身
  （上层可用下层、下层不许反向 import 上层）仍然是不可突破的红线。

## 后果

- 装配集中在一处，单进程应用的复杂度可控；文档脚本与测试能在不装 Qt 的前提下导入纯逻辑模块；
- 代价：依赖关系不能只看文件头的 import——大量依赖发生在函数体内和运行时回调里，
  静态检查会漏，改动时要靠 §14 的清单与 review；
- 代价：模块级单例天然是全局状态，测试要靠 `conftest.py` 的临时目录与空模块顶替来隔离。
