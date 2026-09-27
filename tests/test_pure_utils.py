"""纯逻辑函数测试：无 IO、无 Qt 依赖。"""

from pet.config import _convert
from pet.game.tic_tac_toe import _board_text, _check_winner, _is_full
from pet.tools.executor import ToolExecutor, _log_preview
from pet.tools.knowledge.chunker import chunk_text
from pet.tools.timer.core import TimerTool
from pet.version_check import _strip_v, _ver_newer


class TestChunkText:
    def test_empty_or_blank_returns_empty(self):
        assert chunk_text("") == []
        assert chunk_text("   \n\n  ") == []

    def test_short_fragment_filtered(self):
        assert chunk_text("太短") == []

    def test_short_text_single_chunk(self):
        assert chunk_text("这是一段足够长的文本内容") == ["这是一段足够长的文本内容"]

    def test_overlap_clamped_below_max_chars(self):
        # overlap >= max_chars 时会被夹取，保证切分步长大于 0
        chunks = chunk_text("甲" * 250, max_chars=100, overlap=100)
        assert len(chunks) > 1
        assert all(len(c) <= 100 for c in chunks)

    def test_long_paragraph_hard_split(self):
        chunks = chunk_text("乙" * 1000, max_chars=300, overlap=0)
        assert len(chunks) > 1
        assert all(len(c) <= 300 for c in chunks)

    def test_paragraphs_merged_until_limit(self):
        text = "\n\n".join(["段落内容足够长以便测试合并行为"] * 6)
        chunks = chunk_text(text, max_chars=60, overlap=0)
        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk.strip()


class TestVersionCompare:
    def test_strip_single_v_prefix(self):
        assert _strip_v("v1.5.4") == "1.5.4"
        assert _strip_v("V1.5.4") == "1.5.4"
        assert _strip_v("1.5.4") == "1.5.4"
        assert _strip_v("vv1") == "v1"

    def test_numeric_order_not_lexical(self):
        assert _ver_newer("1.5.10", "1.5.9")
        assert not _ver_newer("1.5.9", "1.5.10")

    def test_equal_version_is_not_newer(self):
        assert not _ver_newer("1.5.4", "1.5.4")

    def test_invalid_version_returns_false(self):
        assert not _ver_newer("not-a-version", "1.5.4")
        assert not _ver_newer("1.5.4", "not-a-version")


class TestTicTacToe:
    def test_row_column_diagonal_win(self):
        assert _check_winner([["X", "X", "X"], ["O", "O", ""], ["", "", ""]]) == "X"
        assert _check_winner([["O", "X", ""], ["O", "X", ""], ["", "X", ""]]) == "X"
        assert _check_winner([["X", "O", ""], ["O", "X", ""], ["", "", "X"]]) == "X"
        assert _check_winner([["", "O", "X"], ["O", "X", ""], ["X", "", ""]]) == "X"

    def test_no_winner_on_empty_or_mixed_board(self):
        assert _check_winner([["", "", ""], ["", "", ""], ["", "", ""]]) is None
        assert _check_winner([["X", "O", "X"], ["X", "O", "O"], ["O", "X", ""]]) is None

    def test_board_full(self):
        assert _is_full([["X", "O", "X"], ["X", "O", "O"], ["O", "X", "X"]])
        assert not _is_full([["X", "O", "X"], ["X", "O", "O"], ["O", "X", ""]])

    def test_board_text_uses_dots_for_empty(self):
        text = _board_text([["X", "", "O"], ["", "X", ""], ["", "", "O"]])
        assert text.splitlines()[0].strip() == "1 2 3"
        assert "A X . O" in text


class TestValidateArgs:
    SCHEMA = {
        "count": {"type": "int", "required": True},
        "mode": {"type": "str", "enum": ["fast", "slow"], "default": "fast"},
        "flag": {"type": "bool", "default": False},
    }

    def test_type_mismatch_rejected(self):
        args, err = ToolExecutor._validate_args({"count": "5"}, self.SCHEMA)
        assert args == {}
        assert "类型错误" in err

    def test_missing_required_rejected(self):
        _, err = ToolExecutor._validate_args({}, self.SCHEMA)
        assert "缺少必需参数" in err

    def test_enum_out_of_range_rejected(self):
        _, err = ToolExecutor._validate_args({"count": 1, "mode": "turbo"}, self.SCHEMA)
        assert "不在允许范围" in err

    def test_defaults_and_extra_keys(self):
        args, err = ToolExecutor._validate_args({"count": 3, "aside": "看看"}, self.SCHEMA)
        assert err == ""
        assert args == {"count": 3, "mode": "fast", "flag": False, "aside": "看看"}

    def test_explicit_value_beats_default(self):
        args, err = ToolExecutor._validate_args({"count": 1, "mode": "slow"}, self.SCHEMA)
        assert err == ""
        assert args["mode"] == "slow"


class TestLogPreview:
    def test_long_value_truncated_with_marker(self):
        preview = _log_preview({"data": "x" * 400})
        assert "<+100字>" in preview

    def test_short_value_untouched(self):
        assert _log_preview({"ok": 1}) == "{ ok=1 }"

    def test_non_dict_uses_str(self):
        assert _log_preview([1, 2]) == "[1, 2]"


class TestFormatDuration:
    def test_under_one_minute(self):
        assert TimerTool._format_duration(30) == "30秒"

    def test_minute_scales(self):
        assert TimerTool._format_duration(60) == "1分钟"
        assert TimerTool._format_duration(90) == "1分30秒"
        assert TimerTool._format_duration(600) == "10分钟"

    def test_hour_scales(self):
        assert TimerTool._format_duration(3600) == "1小时"
        assert TimerTool._format_duration(3661) == "1小时1分1秒"
        assert TimerTool._format_duration(7320) == "2小时2分"


class TestConvertSettingValues:
    def test_bool_variants(self):
        assert _convert("1", "bool") is True
        assert _convert("TRUE", "bool") is True
        assert _convert("yes", "bool") is True
        assert _convert("0", "bool") is False
        assert _convert(False, "bool") is False

    def test_number_conversion(self):
        assert _convert("5", "int") == 5
        assert _convert("2.5", "float") == 2.5

    def test_str_list_splits_and_strips(self):
        assert _convert("a, b ,c", "str_list") == ["a", "b", "c"]
        assert _convert("", "str_list") == []
        assert _convert(["x"], "str_list") == ["x"]
