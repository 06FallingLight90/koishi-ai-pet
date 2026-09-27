"""安全边界测试：文件路径白名单、URL 协议校验。"""

import pytest

from pet.tools.browser.core import BrowserTool
from pet.tools.file_ops import core as file_ops_core
from pet.tools.file_ops.core import FileOpsTool


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """把允许目录指向临时沙箱，避免触碰真实桌面/文档。"""
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    monkeypatch.setattr(file_ops_core, "_ALLOWED_ROOTS", [str(desktop)])
    monkeypatch.setattr(file_ops_core, "_get_special_folder", lambda _name: str(desktop))
    return desktop


class TestCheckPath:
    def test_allows_path_inside_root(self, sandbox):
        target = sandbox / "笔记.txt"
        assert FileOpsTool()._check_path(str(target)) == str(target)

    def test_allows_root_itself(self, sandbox):
        assert FileOpsTool()._check_path(str(sandbox)) == str(sandbox)

    @pytest.mark.parametrize("path", [
        "C:\\Windows\\System32\\drivers\\etc\\hosts",
        "~/.ssh/id_rsa",
    ])
    def test_rejects_outside_root(self, sandbox, path):
        with pytest.raises(PermissionError):
            FileOpsTool()._check_path(path)

    def test_rejects_parent_escape(self, sandbox):
        escape = sandbox / ".." / "outside.txt"
        with pytest.raises(PermissionError):
            FileOpsTool()._check_path(str(escape))

    def test_rejects_sibling_with_shared_prefix(self, sandbox):
        # 仅前缀相同的兄弟目录不得被误判为允许目录
        sibling = sandbox.parent / (sandbox.name + "_evil") / "file.txt"
        with pytest.raises(PermissionError):
            FileOpsTool()._check_path(str(sibling))


class TestReadFile:
    def test_missing_file_reports_error(self, sandbox):
        assert "error" in FileOpsTool().read_file(str(sandbox / "无此文件.txt"))

    def test_offset_beyond_limit_refused(self, sandbox):
        target = sandbox / "长文.txt"
        target.write_text("内容" * 10, encoding="utf-8")
        tool = FileOpsTool()
        result = tool.read_file(str(target), offset=tool._MAX_OFFSET)
        assert "error" in result

    def test_paged_read_reports_next_offset(self, sandbox):
        target = sandbox / "长文.txt"
        target.write_text("甲" * 50, encoding="utf-8")
        result = FileOpsTool().read_file(str(target), max_chars=20, offset=0)
        assert result["chars_read"] == 20
        assert result["has_next"] is True
        assert result["next_offset"] == 20

    def test_last_page_has_no_next(self, sandbox):
        target = sandbox / "短文.txt"
        target.write_text("乙" * 10, encoding="utf-8")
        result = FileOpsTool().read_file(str(target), max_chars=100, offset=0)
        assert result["has_next"] is False
        assert "next_offset" not in result

    def test_illegal_path_raises_permission_error(self, sandbox):
        # read_file 不做兜底，由执行器统一转为错误结果
        with pytest.raises(PermissionError):
            FileOpsTool().read_file("C:\\Windows\\win.ini")


class TestWriteOps:
    def test_write_note_rejects_subpath_filename(self, sandbox):
        # 白名单内的路径，但文件名带子路径 → 拒绝
        result = FileOpsTool().write_note("sub/备忘.txt", "内容")
        assert result["error"] == "文件名不合法"

    def test_write_note_rejects_parent_escape(self, sandbox):
        result = FileOpsTool().write_note("../逃逸.txt", "内容")
        assert "error" in result
        assert not (sandbox.parent / "逃逸.txt").exists()

    def test_write_note_writes_into_sandbox(self, sandbox):
        result = FileOpsTool().write_note("备忘.txt", "你好")
        assert result["status"] == "written"
        assert (sandbox / "备忘.txt").read_text(encoding="utf-8") == "你好"

    def test_write_file_rejects_unknown_mode(self, sandbox):
        result = FileOpsTool().write_file(str(sandbox / "a.txt"), "x", mode="x")
        assert "不支持的写入模式" in result["error"]

    def test_write_file_outside_root_reports_error(self, sandbox):
        result = FileOpsTool().write_file("C:\\Windows\\evil.txt", "x")
        assert "error" in result


class TestValidateUrl:
    def _tool(self) -> BrowserTool:
        return object.__new__(BrowserTool)

    @pytest.mark.parametrize("url", [
        "https://example.com/a?b=1",
        "http://localhost:8000",
        "HTTPS://EXAMPLE.COM",
    ])
    def test_http_and_https_allowed(self, url):
        assert self._tool()._validate_url(url) is None

    @pytest.mark.parametrize("url", [
        "file:///C:/Windows/win.ini",
        "javascript:alert(1)",
        "ftp://example.com/f",
        "data:text/html,<h1>x</h1>",
    ])
    def test_other_schemes_rejected(self, url):
        assert self._tool()._validate_url(url) is not None

    def test_empty_url_rejected(self):
        assert self._tool()._validate_url("") == "URL为空"

    def test_label_included_in_message(self):
        assert "页面地址" in self._tool()._validate_url("", label="页面地址")
