"""上下文备注章节测试：最近事件、未满足需求、窗口标题提取。"""

import time
from types import SimpleNamespace

import pytest

from pet.brain.context_builder import ContextBuilder
from pet.config import config


class _FakeVitals:
    def __init__(self, satiety=100.0, energy=100.0):
        self._data = {"satiety": satiety, "energy": energy}

    def numeric_summary(self):
        return dict(self._data)


class _FakeMood:
    def __init__(self, joy=100.0, affection=100.0):
        self._data = {"joy": joy, "affection": affection}

    def numeric_summary(self):
        return dict(self._data)


class TestExtractWindowTitles:
    def test_empty_input(self):
        assert ContextBuilder._extract_window_titles("") == ""

    def test_titles_joined_and_noise_dropped(self):
        text = '1. "main.py - VSCode" ｜ 范围: 左0 上0 右100 下100\n2. "文档.md" ｜ 范围: 左0 上0 右50 下50'
        assert ContextBuilder._extract_window_titles(text) == "main.py - VSCode，文档.md"

    def test_falls_back_to_raw_text_without_quotes(self):
        assert ContextBuilder._extract_window_titles("没有标题的探测结果") == "没有标题的探测结果"


class TestRecentEventsNote:
    def _builder(self, events):
        return ContextBuilder(recent_events_fn=lambda: events)

    def test_no_provider_returns_empty(self):
        assert ContextBuilder()._recent_events_note() == ""

    def test_provider_exception_returns_empty(self):
        builder = ContextBuilder(recent_events_fn=lambda: 1 / 0)
        assert builder._recent_events_note() == ""

    def test_builtin_label_used_when_text_missing(self):
        now = time.time()
        note = self._builder([("grabbed", now, "")])._recent_events_note()
        assert "用户把你抓了起来" in note

    def test_custom_text_wins_over_label(self):
        now = time.time()
        note = self._builder([("timer", now, "你设的「吃药」定时器响了")])._recent_events_note()
        assert "吃药" in note

    def test_same_kind_keeps_latest_only(self):
        now = time.time()
        note = self._builder([
            ("head_pat", now - 100, "旧的一次摸头"),
            ("head_pat", now - 5, "新的一次摸头"),
        ])._recent_events_note()
        assert "新的一次摸头" in note
        assert "旧的一次摸头" not in note

    def test_events_outside_window_dropped(self, monkeypatch):
        monkeypatch.setattr(config, "RECENT_EVENT_WINDOW_S", 60)
        now = time.time()
        note = self._builder([("grabbed", now - 600, "")])._recent_events_note()
        assert note == ""

    def test_unknown_kind_without_text_skipped(self):
        assert self._builder([("mystery", time.time(), "")])._recent_events_note() == ""

    def test_events_ordered_oldest_first(self):
        now = time.time()
        note = self._builder([
            ("released", now - 1, "后发生的"),
            ("grabbed", now - 50, "先发生的"),
        ])._recent_events_note()
        assert note.index("先发生的") < note.index("后发生的")

    def test_max_lines_keeps_most_recent(self):
        now = time.time()
        # 7 条各有文案的有效事件，只有最近 5 条应被注入
        events = [(f"kind{i}", now - (7 - i), f"事件{i}") for i in range(7)]
        note = self._builder(events)._recent_events_note()
        assert len(note.splitlines()) == ContextBuilder._MAX_EVENT_LINES
        assert "事件0" not in note
        assert "事件1" not in note
        assert "事件6" in note


class TestNeedsNote:
    def _builder(self, satiety=100, energy=100, joy=100, affection=100):
        return ContextBuilder(
            vitals=_FakeVitals(satiety, energy),
            mood=_FakeMood(joy, affection),
        )

    def test_no_vitals_or_mood_returns_empty(self):
        assert ContextBuilder()._build_needs_note() == ""
        assert ContextBuilder(vitals=_FakeVitals())._build_needs_note() == ""

    def test_all_satisfied_returns_empty(self):
        assert self._builder()._build_needs_note() == ""

    def test_threshold_boundary_excluded(self):
        # 阈值 60：等于阈值不算未满足
        note = self._builder(satiety=60)._build_needs_note()
        assert note == ""
        note = self._builder(satiety=59)._build_needs_note()
        assert "吃点东西" in note

    def test_all_four_needs_mapped(self):
        note = self._builder(satiety=10, energy=10, joy=10, affection=10)._build_needs_note()
        for label in ("吃点东西", "歇一歇", "找点乐子", "想被陪陪"):
            assert label in note

    def test_first_occurrence_marked_as_new(self):
        note = self._builder(satiety=10)._build_needs_note()
        assert "刚起念" in note

    def test_elapsed_time_reported(self):
        builder = self._builder(satiety=10)
        builder._active_needs["hungry"] = time.time() - 180
        note = builder._build_needs_note()
        assert "已持续 3 分钟" in note

    def test_recovered_need_removed(self):
        builder = self._builder(satiety=10)
        assert "吃点东西" in builder._build_needs_note()
        builder._vitals = _FakeVitals(satiety=100)
        assert builder._build_needs_note() == ""
        assert builder._active_needs == {}

    def test_exception_from_vitals_returns_empty(self):
        broken = SimpleNamespace(numeric_summary=lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        builder = ContextBuilder(vitals=broken, mood=_FakeMood())
        assert builder._build_needs_note() == ""
