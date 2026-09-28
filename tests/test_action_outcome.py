"""动作产出注册表测试：注册、查表、注入方式，以及内置玩法的装配。"""

from pet.action import outcome


class TestOutcomeRegistry:
    def test_unregistered_returns_none(self):
        assert outcome.outcome_for("no_such_action") is None

    def test_register_then_lookup(self, monkeypatch):
        monkeypatch.setitem(outcome._OUTCOMES, "_probe", outcome.Outcome(lambda: "旧的"))
        outcome.register("_probe", lambda: "新的")
        assert outcome.outcome_for("_probe").handler() == "新的"

    def test_once_defaults_to_true(self, monkeypatch):
        monkeypatch.setitem(outcome._OUTCOMES, "_probe", outcome.Outcome(lambda: "x"))
        outcome.register("_probe", lambda: "y")
        assert outcome.outcome_for("_probe").once is True

    def test_once_can_be_disabled(self, monkeypatch):
        monkeypatch.setitem(outcome._OUTCOMES, "_probe", outcome.Outcome(lambda: "x"))
        outcome.register("_probe", lambda: "y", once=False)
        assert outcome.outcome_for("_probe").once is False

    def test_registered_actions_includes_new(self, monkeypatch):
        monkeypatch.setitem(outcome._OUTCOMES, "_probe", outcome.Outcome(lambda: ""))
        assert "_probe" in outcome.registered_actions()

    def test_handler_may_return_empty(self, monkeypatch):
        # 空串表示本次无产出，调用方据此跳过注入
        monkeypatch.setitem(outcome._OUTCOMES, "_probe", outcome.Outcome(lambda: ""))
        assert not outcome.outcome_for("_probe").handler()


class TestFishingIsWired:
    def test_fishing_registered_on_import(self):
        from pet.action import fishing  # noqa: F401

        assert "fishing" in outcome.registered_actions()

    def test_fishing_is_once(self):
        from pet.action import fishing  # noqa: F401

        # 钓鱼是「结果」，应只交代一轮而非在窗口期反复出现
        assert outcome.outcome_for("fishing").once is True

    def test_fishing_handler_always_returns_text(self):
        from pet.action import fishing  # noqa: F401

        spec = outcome.outcome_for("fishing")
        assert spec is not None
        # 无论钓到与否都要有交代，不能返回空
        for _ in range(20):
            assert "钓" in spec.handler()
