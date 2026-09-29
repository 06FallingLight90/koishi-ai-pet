"""上下文裁剪测试：时间格式化、条数淘汰、token 预算、system 归位。"""

import time
from datetime import datetime, timedelta

import pytest

from pet.brain.base import BrainMixin, ContextEntry
from pet.brain.context_builder import ContextBuilder
from pet.config import config


def _brain(entries) -> BrainMixin:
    """db_path=None → 不落库，仅使用内存上下文。"""
    obj = BrainMixin(db_path=None)
    obj._context = list(entries)
    return obj


def _entry(content: str, role: str = "assistant", age_s: float = 0.0, summary: bool = False):
    return ContextEntry(role=role, content=content,
                        timestamp=time.time() - age_s, is_summary=summary)


class TestEstimateTokens:
    def test_chinese_counted_heavier(self):
        # 10 个汉字 → 15 token
        assert BrainMixin._estimate_tokens("汉字" * 5) == 15

    def test_ascii_lighter(self):
        assert BrainMixin._estimate_tokens("a" * 100) == 25

    def test_empty_text_at_least_one(self):
        assert BrainMixin._estimate_tokens("") == 1


class TestFormatContextTime:
    def test_today_uses_clock_only(self):
        now = datetime.now().replace(hour=9, minute=30)
        assert BrainMixin._format_context_time(now.timestamp()) == "09:30"

    def test_yesterday_and_before_yesterday(self):
        yesterday = datetime.now() - timedelta(days=1)
        assert BrainMixin._format_context_time(yesterday.timestamp()).startswith("昨天 ")
        two_days = datetime.now() - timedelta(days=2)
        assert BrainMixin._format_context_time(two_days.timestamp()).startswith("前天 ")

    def test_older_uses_date(self):
        older = datetime.now() - timedelta(days=5)
        assert len(BrainMixin._format_context_time(older.timestamp())) == len("09-01 09:30")


class TestGetMultiTurnMessages:
    def test_empty_context(self):
        assert _brain([]).get_multi_turn_messages() == []

    def test_keeps_chronological_order_with_time_prefix(self):
        entries = [
            _entry("第二条", age_s=10),
            _entry("第一条", age_s=100),
        ]
        messages = _brain(entries).get_multi_turn_messages()
        assert [m["content"].split("] ")[1] for m in messages] == ["第一条", "第二条"]

    def test_count_eviction_drops_oldest_dialogue_first(self):
        entries = [_entry(f"对话{i}", age_s=1000 - i * 10) for i in range(6)]
        entries.append(_entry("旧摘要", summary=True, age_s=5000))
        messages = _brain(entries).get_multi_turn_messages(max_entries=4)
        contents = [m["content"] for m in messages]
        # 摘要与最新的对话保留，最旧的对话先被丢弃
        assert any("旧摘要" in c for c in contents)
        assert not any("对话0" in c for c in contents)
        assert len(messages) == 4

    def test_summary_and_system_keep_system_role(self):
        entries = [_entry("摘要", summary=True), _entry("备注", role="system")]
        messages = _brain(entries).get_multi_turn_messages()
        assert all(m["role"] == "system" for m in messages)

    def test_skip_last_excludes_tail(self):
        entries = [_entry("保留", age_s=100), _entry("丢弃", age_s=1)]
        messages = _brain(entries).get_multi_turn_messages(skip_last=1)
        assert [m["content"].split("] ")[1] for m in messages] == ["保留"]

    def test_token_budget_truncates_but_keeps_one(self):
        entries = [_entry("字" * 200, age_s=1000 - i * 10) for i in range(5)]
        messages = _brain(entries).get_multi_turn_messages(max_entries=10, token_budget=100)
        assert len(messages) == 1


class TestTextSimilarity:
    def test_identical_text_scores_one(self):
        assert BrainMixin._text_similarity("今天天气不错", "今天天气不错") == pytest.approx(1.0)

    def test_unrelated_text_scores_low(self):
        assert BrainMixin._text_similarity("今天天气不错", "abcxyz") < 0.3

    def test_empty_side_scores_zero(self):
        assert BrainMixin._text_similarity("", "内容") == 0.0


class TestToolCallDowngrade:
    def test_tool_call_entries_scored_below_dialogue(self):
        brain = _brain([])
        tool_call = _entry("[工具调用] weather__get_current", age_s=10)
        dialogue = _entry("普通对话", age_s=10)
        assert brain._score_entry(tool_call) < brain._score_entry(dialogue)


class TestMergeSystemHistory:
    def test_system_notes_merged_into_first_system_message(self):
        builder = object.__new__(ContextBuilder)
        merged = builder._merge_system_history(
            "系统提示",
            [{"role": "system", "content": "备注一"},
             {"role": "user", "content": "你好"},
             {"role": "assistant", "content": "在的"}],
        )
        assert merged[0]["role"] == "system"
        assert "系统提示" in merged[0]["content"]
        assert "备注一" in merged[0]["content"]
        assert [m["content"] for m in merged[1:]] == ["你好", "在的"]

    def test_no_notes_keeps_system_untouched(self):
        builder = object.__new__(ContextBuilder)
        merged = builder._merge_system_history("系统提示", [{"role": "user", "content": "嗨"}])
        assert merged[0]["content"] == "系统提示"


class TestPoolCapUnified:
    """CONTEXT_MAX_ENTRIES 已合并进 CONTEXT_HISTORY_ENTRIES，不再是独立上限。"""

    def test_max_entries_follows_history_entries_config(self, monkeypatch):
        monkeypatch.setattr(config, "CONTEXT_HISTORY_ENTRIES", 5)
        brain = _brain([])
        assert brain._MAX_ENTRIES == 5

    def test_pool_size_stays_bounded_by_history_entries(self, monkeypatch):
        monkeypatch.setattr(config, "CONTEXT_HISTORY_ENTRIES", 5)
        brain = _brain([])
        for i in range(20):
            brain.add_context(role="assistant", content=f"消息{i}")
        # 池子在 CONTEXT_HISTORY_ENTRIES 到 CONTEXT_HISTORY_ENTRIES+_EVICT_BATCH_SIZE 之间震荡
        # （见 spec §3），不会再无限增长到旧的 CONTEXT_MAX_ENTRIES=30。
        # 断言直接对照配置值而非 brain._MAX_ENTRIES，避免用被测实现自证其行为。
        assert brain.context_count() <= config.CONTEXT_HISTORY_ENTRIES + BrainMixin._EVICT_BATCH_SIZE

    def test_orphan_config_keys_removed(self):
        with pytest.raises(AttributeError):
            config.CONTEXT_MAX_ENTRIES
        with pytest.raises(AttributeError):
            config.CONTEXT_MAX_SUMMARIES

    def test_max_summaries_property_removed(self):
        assert not hasattr(BrainMixin, "_MAX_SUMMARIES")
