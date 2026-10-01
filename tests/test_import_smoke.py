"""导入顺序冒烟：三个入口在冷解释器里导入 brain 均须成功。

`pet.brain` 包曾有真实顶层环（`__init__` → behavior → context_builder → 包 `__init__`，
见 Issue #19 与 docs/architecture.md §14），依赖 CPython「from 包 import 子模块」的回退
机制才能完成导入。环断开后由这三个入口检查：同进程内其他用例可能已经导入过 brain，
所以每项都在独立子进程里跑，保证从零开始的导入顺序。

子进程不加载 tests/conftest.py，需要自行顶替 pet.crash_reporter（与 conftest、gen_docs
同一手法）：否则 `pet/__init__.py` 会安装真实崩溃钩子，每次运行都改写 logs/startup.state
并留下虚假的 abnormal_exit 报告，挤占 logs/crash 的保留名额。
"""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# 各入口守护的对象：包入口（__init__ 链路完整执行）、环当事模块（独立冷导入）、
# 子模块入口（绕开包属性直导，Issue #19 指定）
_ENTRIES = ["pet.brain", "pet.brain.context_builder", "pet.brain.prompts"]


def _child_code(entry: str) -> str:
    return (
        # 顺序不能颠倒：pet/__init__.py 在导入期就安装崩溃钩子
        "import sys, types\n"
        "stub = types.ModuleType('pet.crash_reporter')\n"
        "stub.install = lambda: None\n"
        "sys.modules.setdefault('pet.crash_reporter', stub)\n"
        "import importlib\n"
        f"importlib.import_module({entry!r})\n"
        "assert 'pet.brain' in sys.modules, 'pet.brain 包未完成初始化'\n"
        "assert 'pet.brain.prompts' in sys.modules, 'pet.brain.prompts 未完成初始化'\n"
    )


@pytest.mark.parametrize("entry", _ENTRIES)
def test_cold_import_no_cycle(entry: str):
    try:
        proc = subprocess.run(
            [sys.executable, "-c", _child_code(entry)],
            cwd=ROOT,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        pytest.fail(f"入口 {entry} 导入超时（60s）")
    assert proc.returncode == 0, f"入口 {entry} 导入失败：\n{proc.stderr}"
