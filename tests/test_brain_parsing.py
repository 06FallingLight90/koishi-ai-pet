"""LLM 输出解析测试：文本行 → 行为结构。

解析器是「模型意图 → 实际行为」的唯一通道，回归会导致桌宠发呆或做错事，
因此覆盖各字段的解析分支、容错与默认回落。
"""

import pytest

from pet.action.registry import ACTION_NAMES
from pet.brain.behavior import Behavior


def _parser() -> Behavior:
    """构造仅含解析所需属性的实例（不触碰 LLM / DB / GUI）。"""
    obj = Behavior.__new__(Behavior)
    obj._actions = ACTION_NAMES
    return obj


def _run_finish_line(content: str) -> dict:
    """用流式路径的同款逻辑收集各行，便于与非流式路径对照。"""
    parser = _parser()
    actions, speech_parts = [], []
    summary, memory, emotion, mood, vitals = [], [], [], [], []
    for line in content.split("\n"):
        parser._finish_line(line, actions, speech_parts, summary, memory, emotion, mood, vitals)
    return {
        "actions": actions,
        "speech_parts": speech_parts,
        "summary": summary[0] if summary else None,
        "memory_line": memory[0] if memory else None,
        "emotion": ", ".join(emotion) if emotion else None,
        "mood": parser._parse_mood_line(mood[0]) if mood else None,
        "vitals": parser._parse_vitals_line(vitals[0]) if vitals else None,
    }


class TestParseBehavior:
    def test_full_output_fields(self):
        out = _parser()._parse_behavior(
            "Summary: 用户在写代码\n"
            "Emotion: happy\n"
            "Speech: 又在写代码呀...\n"
            "Action: walk right 300\n"
            "Memory: [偏好] 用户喜欢深夜写码\n"
            "Mood: affection+5 joy+3 sanity-2\n"
            "Vitals: satiety-2 energy-1\n"
        )
        assert out.summary == "用户在写代码"
        assert out.emotion == "happy"
        assert out.speech == "又在写代码呀..."
        assert out.actions[0].name == "walk"
        assert out.memory_line == "[偏好] 用户喜欢深夜写码"
        assert out.mood_deltas == {"affection": 5.0, "joy": 3.0, "sanity": -2.0}
        assert out.vitals_deltas == {"satiety": -2.0, "energy": -1.0}

    def test_multiple_speech_lines_joined_in_order(self):
        out = _parser()._parse_behavior("Speech: 第一句\nSpeech: 第二句\n")
        assert out.speech_parts == ["第一句", "第二句"]
        assert out.speech == "第一句 第二句"

    @pytest.mark.parametrize("raw", ["none", "None", "null", "", "无"])
    def test_silence_markers_produce_no_speech(self, raw):
        out = _parser()._parse_behavior(f"Speech: {raw}\nAction: sit 5\n")
        assert out.speech_parts == []
        assert out.speech is None

    def test_missing_action_falls_back_to_sit(self):
        out = _parser()._parse_behavior("Summary: 发呆\n")
        assert len(out.actions) == 1
        assert out.actions[0].name == "sit"
        assert out.actions[0].kwargs == {"duration": 5}

    def test_all_actions_unknown_falls_back_to_sit(self):
        out = _parser()._parse_behavior("Action: fly_to_moon 3\n")
        assert [a.name for a in out.actions] == ["sit"]

    def test_field_names_are_case_insensitive(self):
        out = _parser()._parse_behavior("SUMMARY: 大写字段\nACTION: sit 5\n")
        assert out.summary == "大写字段"
        assert out.actions[0].name == "sit"

    def test_colon_in_value_preserved(self):
        out = _parser()._parse_behavior("Speech: 现在是 10:30\n")
        assert out.speech == "现在是 10:30"

    def test_only_first_memory_mood_vitals_kept(self):
        out = _parser()._parse_behavior(
            "Memory: 第一条\nMemory: 第二条\n"
            "Mood: joy+1\nMood: joy+9\n"
        )
        assert out.memory_line == "第一条"
        assert out.mood_deltas == {"joy": 1.0}

    def test_empty_content_returns_default_sit(self):
        out = _parser()._parse_behavior("")
        assert [a.name for a in out.actions] == ["sit"]


class TestParseActionLine:
    def test_positional_and_keyword_args(self):
        step = _parser()._parse_action_line("walk right 300 speed=2")
        assert step.name == "walk"
        assert step.args == ("right", 300)
        assert step.kwargs == {"speed": 2}

    def test_unknown_action_returns_none(self):
        assert _parser()._parse_action_line("teleport") is None

    def test_empty_returns_none(self):
        assert _parser()._parse_action_line("   ") is None

    def test_name_is_lowercased(self):
        step = _parser()._parse_action_line("SIT 3")
        assert step.name == "sit"


class TestParseMoodVitals:
    def test_mood_handles_spaces_and_case(self):
        assert Behavior._parse_mood_line("AFFECTION + 5, joy -2") == {
            "affection": 5.0, "joy": -2.0
        }

    def test_mood_unknown_key_ignored(self):
        assert Behavior._parse_mood_line("hunger+5") is None

    def test_mood_without_delta_returns_none(self):
        assert Behavior._parse_mood_line("affection") is None

    def test_vitals_supported_keys_only(self):
        assert Behavior._parse_vitals_line("satiety+15 energy-3") == {
            "satiety": 15.0, "energy": -3.0
        }
        assert Behavior._parse_vitals_line("affection+5") is None


class TestFinishLineMatchesNonStreamPath:
    CONTENT = (
        "Summary: 观察\n"
        "Emotion: happy\n"
        "Speech: 你好\n"
        "Action: sit 5\n"
        "Memory: [偏好] 咖啡\n"
        "Mood: joy+2\n"
    )

    def test_stream_and_non_stream_agree(self):
        streamed = _run_finish_line(self.CONTENT)
        parsed = _parser()._parse_behavior(self.CONTENT)
        assert streamed["summary"] == parsed.summary
        assert streamed["emotion"] == parsed.emotion
        assert streamed["memory_line"] == parsed.memory_line
        assert streamed["mood"] == parsed.mood_deltas
        assert streamed["speech_parts"] == parsed.speech_parts
        assert [a.name for a in streamed["actions"]] == [a.name for a in parsed.actions]

    def test_finish_line_skips_blank(self):
        parser = _parser()
        actions, speech_parts = [], []
        parser._finish_line("   ", actions, speech_parts)
        assert actions == [] and speech_parts == []
