"""动作产出（outcome）"""

from dataclasses import dataclass
from typing import Callable, Optional

# 处理器返回要注入的文案；返回空串或 None 视为本次无产出
OutcomeHandler = Callable[[], Optional[str]]


@dataclass(frozen=True)
class Outcome:
    """一个动作的产出定义。"""
    handler: OutcomeHandler
    once: bool = True  # True 只注入一轮；False 进入窗口期


_OUTCOMES: dict[str, Outcome] = {}


def register(action_name: str, handler: OutcomeHandler, once: bool = True) -> None:
    """为动作注册产出（同名后注册的覆盖先注册的）。"""
    _OUTCOMES[action_name] = Outcome(handler, once)


def outcome_for(action_name: str) -> Optional[Outcome]:
    """取动作的产出定义，未注册返回 None。"""
    return _OUTCOMES.get(action_name)


def registered_actions() -> set[str]:
    """已注册产出的动作名集合（供调试与测试）。"""
    return set(_OUTCOMES)
