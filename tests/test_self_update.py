"""启动时应用遗留 update.*.new 的自更新逻辑测试。"""

import shutil
import tempfile
from pathlib import Path

import pytest

from pet.self_update import apply_pending_update_scripts


@pytest.fixture
def workspace():
    d = Path(tempfile.mkdtemp(prefix="koishi_selfupd_"))
    yield d
    shutil.rmtree(d, ignore_errors=True)


def test_replaces_bat(workspace):
    (workspace / "update.bat").write_text("OLD", encoding="gbk")
    (workspace / "update.bat.new").write_text("NEW", encoding="gbk")
    apply_pending_update_scripts(workspace)
    assert (workspace / "update.bat").read_text(encoding="gbk") == "NEW"
    assert not (workspace / "update.bat.new").exists()


def test_replaces_sh_without_existing_target(workspace):
    # 目标不存在时同样完成替换
    (workspace / "update.sh.new").write_text("NEW", encoding="utf-8")
    apply_pending_update_scripts(workspace)
    assert (workspace / "update.sh").read_text(encoding="utf-8") == "NEW"


def test_noop_without_new_files(workspace):
    (workspace / "update.bat").write_text("OLD", encoding="gbk")
    apply_pending_update_scripts(workspace)
    assert (workspace / "update.bat").read_text(encoding="gbk") == "OLD"


def test_replaces_both(workspace):
    (workspace / "update.bat").write_text("OLD", encoding="gbk")
    (workspace / "update.bat.new").write_text("NEWBAT", encoding="gbk")
    (workspace / "update.sh.new").write_text("NEWSH", encoding="utf-8")
    apply_pending_update_scripts(workspace)
    assert (workspace / "update.bat").read_text(encoding="gbk") == "NEWBAT"
    assert (workspace / "update.sh").read_text(encoding="utf-8") == "NEWSH"
    assert not (workspace / "update.bat.new").exists()
    assert not (workspace / "update.sh.new").exists()


def test_failure_is_swallowed_and_new_kept(workspace):
    # 目标名被目录占用 → os.replace 失败 → 不抛异常，.new 保留待下次重试
    (workspace / "update.bat").mkdir()
    (workspace / "update.bat.new").write_text("NEW", encoding="gbk")
    apply_pending_update_scripts(workspace)
    assert (workspace / "update.bat.new").exists()
