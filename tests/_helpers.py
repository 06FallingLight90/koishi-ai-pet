"""安装/更新脚本测试用的共享工具。

测试重点是 4 个脚本（setup.bat / setup.sh / update.bat / update.sh）的
PyPI 镜像源 fallback 逻辑：镜像链顺序、官方源兜底、失败切换、全源失败报错。

为避免真实安装依赖，测试用 mock 的 pip / python 替换真实命令，
通过 MOCK_FAIL_URLS 指定"哪些镜像源会失败"。
"""

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 期望的镜像源顺序：国内镜像在前，官方源兜底
EXPECTED_MIRRORS = [
    "https://pypi.tuna.tsinghua.edu.cn/simple",
    "https://mirrors.aliyun.com/pypi/simple/",
    "https://pypi.mirrors.ustc.edu.cn/simple/",
    "https://repo.huaweicloud.com/repository/pypi/simple",
    "https://mirrors.cloud.tencent.com/pypi/simple",
    "https://pypi.org/simple",
]
OFFICIAL_MIRROR = "https://pypi.org/simple"

BASH_CANDIDATES = [
    r"C:\Program Files\Git\bin\bash.exe",
    r"C:\Program Files\Git\usr\bin\bash.exe",
    "/usr/bin/bash",
    "/bin/bash",
]


def read_script(name: str) -> str:
    """读取脚本内容；bat 为 GBK(cmd 代码页)，sh 为 UTF-8。"""
    path = PROJECT_ROOT / name
    enc = "gbk" if name.endswith(".bat") else "utf-8"
    return path.read_text(encoding=enc, errors="replace")


def find_bash():
    for candidate in BASH_CANDIDATES:
        if os.path.exists(candidate):
            return candidate
    return shutil.which("bash")


# ---------- 片段提取 ----------

def extract_bash_fragment(text: str) -> str:
    """提取 sh 脚本里的 PIP_MIRRORS 数组与 pip_install 函数。"""
    mirrors = re.search(r"^PIP_MIRRORS=\(.*?^\)", text, re.S | re.M)
    func = re.search(r"^pip_install\(\) \{.*?^\}", text, re.S | re.M)
    if not mirrors or not func:
        raise AssertionError("未找到 PIP_MIRRORS 数组或 pip_install 函数")
    return f"{mirrors.group(0)}\n\n{func.group(0)}\n"


def _match_paren(text: str, start: int) -> int:
    """从 start 处的 '(' 开始做括号配对，返回匹配的 ')' 下标。"""
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return i
    raise AssertionError("括号未配对")


def extract_bat_fragment(text: str) -> tuple[str, str]:
    """提取 bat 脚本里的镜像列表与依赖安装循环块，返回 (mirrors, loop)。"""
    m = re.search(r'set "PIP_MIRRORS=([^"]*)"', text)
    if not m:
        raise AssertionError("未找到 PIP_MIRRORS 变量定义")
    mirrors = m.group(1)

    # 定位包含 'pip install -e' 的那个 for 循环（排除 pip 升级的 python -m pip）
    pos = 0
    while True:
        idx = text.find("for %%m in (%PIP_MIRRORS%) do (", pos)
        if idx == -1:
            raise AssertionError("未找到镜像源遍历循环")
        open_paren = text.index("(", idx + len("for %%m in (%PIP_MIRRORS%) do"))
        end = _match_paren(text, open_paren)
        block = text[idx:end + 1]
        if "pip install -e" in block:
            return mirrors, block
        pos = end


# ---------- mock 命令 ----------

# 用 bash 函数 mock `python -m pip install ... -i <url>`：
# 比外部脚本可靠（Windows 上脚本可执行位无效，且 Git Bash 需要 POSIX 路径）
MOCK_PYTHON_FUNC = r"""python() {
    local url="" prev="" a f
    for a in "$@"; do
        if [ "$prev" = "-i" ]; then url="$a"; fi
        prev="$a"
    done
    echo "$url" >> "$MOCK_LOG"
    for f in $MOCK_FAIL_URLS; do
        if [ "$f" = "$url" ]; then return 1; fi
    done
    return 0
}
"""


def to_bash_path(path: Path) -> str:
    """Windows 路径转 Git Bash 的 POSIX 形式（C:/x → /c/x）；非 Windows 原样返回。"""
    posix = path.as_posix()
    if os.name == "nt" and re.match(r"^[A-Za-z]:", posix):
        return f"/{posix[0].lower()}{posix[2:]}"
    return posix


class MockRunner:
    """在临时目录里准备 mock pip/python，并执行脚本片段。"""

    def __init__(self):
        self.dir = Path(tempfile.mkdtemp(prefix="koishi_script_test_"))
        self.log = self.dir / "calls.log"

    def close(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    # --- bash ---

    def run_bash(self, body: str, fail_urls: list[str]) -> tuple[int, str]:
        script = self.dir / "case.sh"
        script.write_text(
            f"#!/usr/bin/env bash\n{MOCK_PYTHON_FUNC}\n{body}\n", encoding="utf-8"
        )
        env = dict(os.environ)
        env["MOCK_LOG"] = to_bash_path(self.log)
        env["MOCK_FAIL_URLS"] = " ".join(fail_urls)
        proc = subprocess.run([find_bash(), to_bash_path(script)], capture_output=True,
                              text=True, env=env, timeout=120,
                              encoding="utf-8", errors="replace")
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")

    # --- cmd ---

    def run_bat(self, body: str, fail_urls: list[str]) -> tuple[int, str]:
        script = self.dir / "case.bat"
        script.write_text(body, encoding="gbk")
        env = dict(os.environ)
        env["MOCK_LOG"] = str(self.log)
        env["MOCK_FAIL_URLS"] = " ".join(fail_urls)
        proc = subprocess.run(["cmd", "/c", "case.bat"], cwd=str(self.dir),
                              capture_output=True, text=True, env=env, timeout=120,
                              encoding="gbk", errors="replace")
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")

    def calls(self) -> list[str]:
        """mock 记录到的镜像源调用顺序。"""
        if not self.log.exists():
            return []
        return [ln.strip() for ln in
                self.log.read_text(encoding="utf-8", errors="replace").splitlines()
                if ln.strip()]
