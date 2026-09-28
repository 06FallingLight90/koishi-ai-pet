"""钓鱼判定测试：命中概率、稀有度分档、鱼种表与文案。"""

import pytest

from pet.action import fishing


class TestRollCatch:
    def test_miss_when_random_above_rate(self, monkeypatch):
        monkeypatch.setattr(fishing.random, "random", lambda: 0.99)
        assert fishing.roll_catch() is None

    def test_boundary_value_counts_as_miss(self, monkeypatch):
        # 判定用 >=：随机值正好等于 CATCH_RATE 时算没钓到
        monkeypatch.setattr(fishing.random, "random", lambda: fishing.CATCH_RATE)
        assert fishing.roll_catch() is None

    def test_hit_below_rate_returns_fish_and_rarity(self, monkeypatch):
        monkeypatch.setattr(fishing.random, "random", lambda: fishing.CATCH_RATE - 0.01)
        monkeypatch.setattr(fishing.random, "choice", lambda seq: seq[0])
        result = fishing.roll_catch()
        assert result is not None
        name, rarity = result
        assert name in fishing.FISH_TABLE[rarity]

    def test_rarity_follows_weighted_choice(self, monkeypatch):
        monkeypatch.setattr(fishing.random, "random", lambda: 0.0)
        monkeypatch.setattr(fishing.random, "choices", lambda seq, weights, k: ["legendary"])
        monkeypatch.setattr(fishing.random, "choice", lambda seq: seq[0])
        assert fishing.roll_catch() == ("金龙鱼", "legendary")


class TestFishTable:
    def test_thirty_species(self):
        assert sum(len(group) for group in fishing.FISH_TABLE.values()) == 30

    def test_no_duplicate_names(self):
        names = [n for group in fishing.FISH_TABLE.values() for n in group]
        assert len(names) == len(set(names))

    def test_every_rarity_has_weight(self):
        assert set(fishing.FISH_TABLE) == set(fishing._RARITY_WEIGHTS)


class TestFormatResult:
    def test_miss_line(self):
        assert "什么也没钓上" in fishing.format_result(None)

    @pytest.mark.parametrize("rarity,name,expected", [
        ("common", "鲫鱼", "你钓到了一条鲫鱼，没什么特别的"),
        ("rare", "鳜鱼", "你钓到了一条少见的鳜鱼！"),
        ("legendary", "腔棘鱼", "你钓到了一条罕见的腔棘鱼！这是一个值得记住的时刻！"),
    ])
    def test_rarity_wording(self, rarity, name, expected):
        assert fishing.format_result((name, rarity)) == expected

    def test_common_stays_understated(self):
        # 占七成的寻常收获要压平语气，不能和上游档同样兴奋
        assert "！" not in fishing.format_result(("鲫鱼", "common"))

    def test_only_legendary_hints_at_memory(self):
        # 「值得记住」只给罕见档，避免引导被稀释
        assert "值得记住" in fishing.format_result(("腔棘鱼", "legendary"))
        assert "值得记住" not in fishing.format_result(("鳜鱼", "rare"))
        assert "值得记住" not in fishing.format_result(("鲫鱼", "common"))
