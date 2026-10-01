"""导入顺序冒烟：两个入口在冷解释器里导入 brain 均须成功。

`pet.brain` 包曾有真实顶层环（`__init__` → behavior → context_builder → 包 `__init__`，
见 Issue #19 与 docs/architecture.md §14），依赖 CPython「from 包 import 子模块」的回退
机制才能完成导入。环断开后由这两个入口检查：同进程内其他用例可能已经导入过 brain，
所以每项都在独立子进程里跑，保证从零开始的导入顺序。
"""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# 包入口（先执行 __init__）与子模块入口（直导 prompts，绕开包属性）
_ENTRIES = ["pet.brain", "pet.brain.prompts"]


@pytest.mark.parametrize("entry", _ENTRIES)
def test_cold_import_no_cycle(entry: str):
    code = (
        "import importlib, sys\n"
        f"importlib.import_module({entry!r})\n"
        "assert 'pet.brain' in sys.modules, 'pet.brain 包未完成初始化'\n"
        "assert 'pet.brain.prompts' in sys.modules, 'pet.brain.prompts 未完成初始化'\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert proc.returncode == 0, f"入口 {entry} 导入失败：\n{proc.stderr}"
