"""todo 工具实例的持有者 — 工具入口与面板共享同一实例，避免面板回指工具包。"""

from __future__ import annotations

import atexit

from pet.tools.todo.core import TodoListTool

_instance: TodoListTool | None = None


def init_instance() -> TodoListTool:
    """创建实例并登记退出清理（register() 阶段调用）；重复调用返回既有实例。"""
    global _instance
    if _instance is None:
        _instance = TodoListTool()
        atexit.register(_instance.close)
    return _instance


def get_instance() -> TodoListTool:
    """返回已创建的实例；尚未创建时抛 RuntimeError。"""
    if _instance is None:
        raise RuntimeError("[todo] 实例未初始化：register() 未执行或初始化失败")
    return _instance
