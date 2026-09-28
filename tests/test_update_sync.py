"""update.bat 源码拉取/替换过程的本地逻辑测试。

网络阶段（GitHub API 查询、Release zip 下载）不适合单测；此处覆盖
update.bat 中可离线验证的核心逻辑：

- pyproject.toml 版本号提取（PS_LOCAL 脚本生成逻辑，原样提取执行）
- Release tag 的 v/V 前缀剥离
- robocopy 源码同步的排除规则（新版文件覆盖、用户数据保留、
  运行中的 update.bat 不被自身覆盖、update.bat.new 另存）
"""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from _helpers import read_script

IS_WIN = sys.platform.startswith("win")

pytestmark = pytest.mark.skipif(not IS_WIN, reason="bat 逻辑仅 Windows 可执行")


def _run_cmd(body: str, cwd: Path, timeout: int = 120) -> tuple[int, str]:
    bat = cwd / "_harness.bat"
    bat.write_text(body, encoding="gbk")
    proc = subprocess.run(["cmd", "/c", "_harness.bat"], cwd=str(cwd),
                          capture_output=True, text=True, timeout=timeout,
                          encoding="gbk", errors="replace")
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def _extract(pattern: str) -> str:
    m = re.search(pattern, read_script("update.bat"), re.M)
    assert m, f"未匹配到: {pattern}"
    return m.group(0)


def _run_cmd_file(cwd: Path, cmd: str) -> subprocess.CompletedProcess:
    """把命令写入 bat 执行。

    不用 `cmd /c <命令字符串>`：直接传参会触发 cmd /c 的引号解析
    陷阱，robocopy 会把带引号的路径当作相对路径拼接到 cwd 上。
    """
    bat = cwd / "_harness.bat"
    bat.write_text(f"@echo off\n{cmd}\n", encoding="gbk")
    return subprocess.run(["cmd", "/c", "_harness.bat"], cwd=str(cwd),
                          capture_output=True, text=True, timeout=120,
                          encoding="gbk", errors="replace")


class TestVersionParsing:
    """从 pyproject.toml 提取版本号（提取 PS_LOCAL 的两行生成逻辑执行）。"""

    def _parse(self, content: str) -> str:
        lines = [re.sub(r'^(>>\s+|>)\s*"%PS_LOCAL%"\s+echo\s+', "", ln)
                 for ln in read_script("update.bat").splitlines()
                 if re.match(r'^(>>\s+|>)\s*"%PS_LOCAL%"\s+echo\s+', ln)]
        ps_body = "\n".join(lines)
        assert ps_body, "未找到 PS_LOCAL 生成逻辑"

        with tempfile.TemporaryDirectory(prefix="koishi_ver_test_") as d:
            pyproject = Path(d) / "pyproject.toml"
            pyproject.write_text(content, encoding="utf-8")
            ps1 = Path(d) / "local_ver.ps1"
            ps1.write_text(ps_body.replace("'%~dp0pyproject.toml'",
                                           f"'{pyproject.as_posix()}'"),
                           encoding="utf-8")
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-File", str(ps1)],
                capture_output=True, text=True, timeout=60)
            return proc.stdout.strip()

    def test_parses_version(self):
        assert self._parse('[project]\nversion = "1.5.2"\n') == "1.5.2"

    def test_takes_first_version_field(self):
        # 正则 -match 取首个匹配：应命中的是 [project] 的 version 而非注释
        assert self._parse('version = "9.9.9"\nname = "x"\n') == "9.9.9"

    def test_missing_version_yields_empty(self):
        assert self._parse('[project]\nname = "x"\n') == ""


class TestTagStrip:
    """Release tag 去掉 v/V 前缀后再与本地版本比较。"""

    def _strip(self, tag: str) -> str:
        lines = re.findall(
            r'^(?:set "REL_VER=!REL_TAG!"\n|'
            r'if /i "!REL_VER:~0,1!"=="[vV]" set "REL_VER=!REL_VER:~1!"\n)',
            read_script("update.bat") + "\n", re.M)
        assert lines, "未找到 REL_VER 前缀剥离逻辑"
        body = ("@echo off\n"
                "setlocal enabledelayedexpansion\n"
                f'set "REL_TAG={tag}"\n'
                + "".join(lines)
                + "echo STRIPPED=!REL_VER!\n")
        with tempfile.TemporaryDirectory(prefix="koishi_tag_test_") as d:
            _, out = _run_cmd(body, Path(d))
        m = re.search(r"STRIPPED=(\S+)", out)
        return m.group(1) if m else ""

    def test_strips_lowercase_v(self):
        assert self._strip("v1.2.3") == "1.2.3"

    def test_strips_uppercase_v(self):
        assert self._strip("V1.2.3") == "1.2.3"

    def test_keeps_plain_version(self):
        assert self._strip("1.2.3") == "1.2.3"


@pytest.fixture
def sync_dirs():
    """构造模拟的「新版源码」与「本地项目目录」，返回 (src, proj, workdir)。"""
    with tempfile.TemporaryDirectory(prefix="koishi_sync_test_") as d:
        workdir = Path(d)
        src = workdir / "src"    # 模拟解压出的新版源码
        proj = workdir / "proj"  # 模拟本地项目目录

        # --- 新版源码（含应被排除的用户数据文件，模拟 Release 包意外携带）---
        (src / "pet").mkdir(parents=True)
        (src / "pet" / "app.py").write_text("# v2", encoding="utf-8")
        (src / "new_feature.py").write_text("new", encoding="utf-8")
        (src / "README.md").write_text("readme v2", encoding="utf-8")
        (src / "update.bat").write_text("@echo off rem NEW SCRIPT", encoding="gbk")
        (src / "update.sh").write_text("#!/bin/bash", encoding="utf-8")
        (src / "config.json").write_text('{"evicted": true}', encoding="utf-8")
        (src / "venv" / "Scripts").mkdir(parents=True)
        (src / "venv" / "Scripts" / "fake.exe").write_bytes(b"evil")

        # --- 本地项目目录（含用户数据）---
        (proj / "pet").mkdir(parents=True)
        (proj / "pet" / "app.py").write_text("# v1", encoding="utf-8")
        (proj / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
        venv_scripts = proj / "venv" / "Scripts"
        venv_scripts.mkdir(parents=True)
        (venv_scripts / "python.exe").write_bytes(b"fake")
        (proj / "logs").mkdir()
        (proj / "logs" / "app.log").write_text("log", encoding="utf-8")
        (proj / "config.json").write_text("{}", encoding="utf-8")
        (proj / "pet.db").write_bytes(b"db")
        (proj / "pet.db-wal").write_bytes(b"wal")
        (proj / "update.bat").write_text("@echo off rem OLD SCRIPT", encoding="gbk")

        yield src, proj, workdir


def _run_robocopy(src: Path, proj: Path, workdir: Path):
    cmd = _extract(r"^robocopy .*$")
    cmd = cmd.replace("!SRC_DIR!", str(src)).replace("!PROJ_DIR!", str(proj))
    proc = _run_cmd_file(workdir, cmd)
    # robocopy 退出码 <8 视为成功（1=已复制等）
    assert proc.returncode < 8, f"robocopy rc={proc.returncode}: {proc.stdout}"


class TestSourceSync:
    """robocopy 源码同步的排除规则（用户数据安全）。"""

    def test_updates_source_files(self, sync_dirs):
        """新版源码文件被正确同步到项目目录。"""
        src, proj, workdir = sync_dirs
        _run_robocopy(src, proj, workdir)
        assert (proj / "pet" / "app.py").read_text(encoding="utf-8") == "# v2"
        assert (proj / "new_feature.py").exists()
        assert (proj / "README.md").read_text(encoding="utf-8") == "readme v2"

    def test_preserves_user_data(self, sync_dirs):
        """venv/logs/config.json/数据库等用户数据不被删除，也不被源内同名文件覆盖。"""
        src, proj, workdir = sync_dirs
        _run_robocopy(src, proj, workdir)
        assert (proj / "venv" / "Scripts" / "python.exe").exists()
        assert (proj / "logs" / "app.log").exists()
        assert (proj / "config.json").exists()
        assert (proj / "config.json").read_text(encoding="utf-8") == "{}"
        assert (proj / "pet.db").exists()
        assert (proj / "pet.db-wal").exists()
        # Release 包中的同名文件不得覆盖本地数据
        assert not (proj / "venv" / "Scripts" / "fake.exe").exists(), (
            "源 venv/ 内文件被复制进来，本地环境被污染")

    def test_running_update_script_not_overwritten(self, sync_dirs):
        """robocopy 不覆盖正在运行的 update.bat（否则报错退出码 8）。"""
        src, proj, workdir = sync_dirs
        _run_robocopy(src, proj, workdir)
        assert (proj / "update.bat").read_text(encoding="gbk") == "@echo off rem OLD SCRIPT"

    def test_new_script_saved_as_dot_new(self, sync_dirs):
        """新版 update.bat 通过单独的 copy 步骤另存为 update.bat.new。"""
        src, proj, workdir = sync_dirs
        _run_robocopy(src, proj, workdir)
        line = _extract(r'^if exist "!SRC_DIR!\\update\.bat" copy /y .*$')
        cmd = (line.replace("!SRC_DIR!", str(src))
                   .replace("%~dp0", str(proj) + "\\"))
        proc = _run_cmd_file(workdir, cmd)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert "NEW SCRIPT" in (proj / "update.bat.new").read_text(encoding="gbk")
        # 原脚本内容保持不变
        assert (proj / "update.bat").read_text(encoding="gbk") == "@echo off rem OLD SCRIPT"
