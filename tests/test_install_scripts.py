"""安装/更新脚本（setup/update 的 bat 与 sh）的 PyPI 镜像源 fallback 测试。

4 个脚本共用同一套断言，按脚本名参数化；bat 需 Windows，sh 需 bash。
"""

import re
import subprocess
import sys

import pytest

from _helpers import (
    EXPECTED_MIRRORS,
    OFFICIAL_MIRROR,
    PROJECT_ROOT,
    MockRunner,
    extract_bash_fragment,
    extract_bat_fragment,
    find_bash,
    read_script,
)

SCRIPTS = ["setup.bat", "setup.sh", "update.bat", "update.sh"]


@pytest.fixture(params=SCRIPTS)
def script(request) -> str:
    """参数化脚本名；按平台与可用 bash 跳过跑不了的脚本。"""
    name = request.param
    if name.endswith(".bat") and not sys.platform.startswith("win"):
        pytest.skip("bat 逻辑仅 Windows 可执行")
    if name.endswith(".sh") and not find_bash():
        pytest.skip("需要 bash 才能执行 sh 脚本")
    return name


@pytest.fixture
def runner():
    r = MockRunner()
    yield r
    r.close()


def _mirrors(text: str, script: str) -> list[str]:
    if script.endswith(".sh"):
        return re.findall(r'"(https?://[^"]+)"', extract_bash_fragment(text))
    mirrors, _ = extract_bat_fragment(text)
    return mirrors.split()


def test_mirror_chain_matches_expected(script):
    assert _mirrors(read_script(script), script) == EXPECTED_MIRRORS


def test_official_mirror_is_last_fallback(script):
    assert _mirrors(read_script(script), script)[-1] == OFFICIAL_MIRROR


def test_no_hardcoded_single_mirror(script):
    """不允许出现写死单一镜像源的 pip install 调用。"""
    text = read_script(script)
    hardcoded = [ln for ln in text.splitlines()
                 if re.search(r"pip install", ln)
                 and re.search(r"-i\s+https?://", ln)
                 and "PIP_MIRRORS" not in ln and "mirror" not in ln]
    assert hardcoded == [], f"存在硬编码镜像源调用: {hardcoded}"


def test_syntax(script):
    text = read_script(script)
    if script.endswith(".sh"):
        bash = find_bash()
        assert bash, "未找到可用的 bash"
        proc = subprocess.run([bash, "-n", str(PROJECT_ROOT / script)],
                              capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
    else:
        # cmd 无独立语法检查：验证循环块括号配对且包含必需结构
        _, loop = extract_bat_fragment(text)
        assert "for %%m in (%PIP_MIRRORS%) do (" in loop
        assert "!errorlevel!" in loop


def _run_case(script: str, runner: MockRunner, fail_urls: list[str]):
    """执行脚本片段，返回 (返回码, 输出, 实际调用到的镜像源顺序)。"""
    text = read_script(script)
    if script.endswith(".sh"):
        body = (f'{extract_bash_fragment(text)}\n'
                'if pip_install --upgrade pip -q; then\n'
                '  echo RESULT=OK\nelse\n  echo RESULT=FAIL\nfi\n')
        rc, out = runner.run_bash(body, fail_urls)
    else:
        mirrors, loop = extract_bat_fragment(text)
        # 不能用 pip.bat 做 mock：cmd 从 bat 调用另一个 bat（无 call）会转移
        # 控制权并破坏父脚本的 echo/延迟展开状态。这里保留原脚本的循环结构，
        # 只把 pip 调用本身替换成等价的内联 mock（按 %%m 是否在失败列表决定 rc）。
        mock_call = (
            'set "MOCK_RC=0"\n'
            'for %%f in (%MOCK_FAIL_URLS%) do (if /i "%%f"=="%%m" set "MOCK_RC=1")\n'
            f'>>"{runner.log.as_posix()}" echo %%m\n'
            'if !MOCK_RC! equ 0 (ver >nul) else (cmd /c exit 1)'
        )
        loop = re.sub(r"^[ \t]*pip install .*$", mock_call, loop, flags=re.M)
        body = (
            "@echo off\n"
            "setlocal enabledelayedexpansion\n"
            f'set "PIP_MIRRORS={mirrors}"\n'
            'set "INSTALL_OK=0"\n'
            f"{loop}\n"
            "if !INSTALL_OK! equ 0 (echo RESULT=FAIL) else (echo RESULT=OK)\n"
        )
        rc, out = runner.run_bat(body, fail_urls)
    return rc, out, runner.calls()


def test_falls_back_until_success(script, runner):
    """前两个源失败时，应继续尝试第三个并成功，且不再尝试后续源。"""
    _, out, calls = _run_case(script, runner, EXPECTED_MIRRORS[:2])
    assert "RESULT=OK" in out, out
    assert calls == EXPECTED_MIRRORS[:3], "应依次尝试前三个源并在第三个成功后停止"


def test_tries_all_mirrors_then_fails(script, runner):
    """全部源失败时，应尝试完所有源（含官方兜底）后报错。"""
    _, out, calls = _run_case(script, runner, EXPECTED_MIRRORS)
    assert "RESULT=FAIL" in out, out
    assert calls == EXPECTED_MIRRORS, "全源失败时应完整遍历镜像链，最后一个是官方源"
    assert calls[-1] == OFFICIAL_MIRROR


def test_official_mirror_used_when_domestic_down(script, runner):
    """国内镜像全挂时，官方源仍能完成安装。"""
    _, out, calls = _run_case(script, runner, EXPECTED_MIRRORS[:-1])
    assert "RESULT=OK" in out, out
    assert calls == EXPECTED_MIRRORS
