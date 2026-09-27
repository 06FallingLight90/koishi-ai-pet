"""帧动画节奏测试：tick 分配、呼吸位移、配置修正、动作超时兜底。"""

import pytest

from pet.action.action_queue import ActionQueue
from pet.config import config
from pet.ui.pet_animations import PetAnimator


class TestBuildTickPlan:
    def test_ratio_pair_kept(self):
        plan = PetAnimator._build_tick_plan({"tick_counts": 60, "frame_ratios": [0.9, 0.1]}, 2)
        assert plan == [54, 6]

    def test_indivisible_split_stays_even(self):
        # 8 帧 / 90 tick：逐帧独立取整会得到 11×7 + 13，累计取整只差 1 tick
        plan = PetAnimator._build_tick_plan({"tick_counts": 90, "frame_ratios": [0.125] * 8}, 8)
        assert sum(plan) == 90
        assert max(plan) - min(plan) <= 1

    def test_every_frame_gets_at_least_one_tick(self):
        plan = PetAnimator._build_tick_plan({"tick_counts": 5, "frame_ratios": [0.5, 0.5]}, 2)
        assert all(t >= 1 for t in plan)
        assert sum(plan) == 5

    def test_missing_ratios_split_evenly(self):
        assert PetAnimator._build_tick_plan({"tick_counts": 30}, 3) == [10, 10, 10]

    def test_ratio_length_mismatch_falls_back_to_even(self):
        cfg = {"tick_counts": 30, "frame_ratios": [0.5, 0.5]}
        assert PetAnimator._build_tick_plan(cfg, 3) == [10, 10, 10]


class TestSanitizeConfig:
    def test_ratio_sum_normalized(self):
        cfg = PetAnimator._sanitize_config({"tick_counts": 60, "frame_ratios": [3, 1]}, 2, "demo")
        assert cfg["frame_ratios"] == [0.75, 0.25]

    def test_ratio_length_mismatch_dropped(self):
        cfg = PetAnimator._sanitize_config(
            {"tick_counts": 60, "frame_ratios": [0.5, 0.5]}, 3, "demo")
        assert "frame_ratios" not in cfg

    def test_ratios_not_a_list_dropped(self):
        cfg = PetAnimator._sanitize_config({"tick_counts": 60, "frame_ratios": 1.0}, 2, "demo")
        assert "frame_ratios" not in cfg

    def test_non_positive_ratio_dropped(self):
        cfg = PetAnimator._sanitize_config({"tick_counts": 60, "frame_ratios": [1.0, 0]}, 2, "demo")
        assert "frame_ratios" not in cfg

    def test_tick_counts_below_frame_count_bumped(self):
        cfg = PetAnimator._sanitize_config({"tick_counts": 2}, 8, "demo")
        assert cfg["tick_counts"] == 8

    def test_tick_counts_garbage_falls_back(self):
        assert PetAnimator._sanitize_config({"tick_counts": "abc"}, 2, "demo")["tick_counts"] == 30

    def test_input_config_not_mutated(self):
        original = {"tick_counts": 2}
        PetAnimator._sanitize_config(original, 8, "demo")
        assert original == {"tick_counts": 2}


class TestBobOffset:
    def test_rest_at_cycle_start(self):
        assert PetAnimator._bob_offset(0, 2, 30) == 0

    def test_peak_at_halfway(self):
        assert PetAnimator._bob_offset(15, 2, 30) == -2

    def test_returns_to_rest_at_cycle_end(self):
        assert PetAnimator._bob_offset(30, 2, 30) == 0

    def test_never_sinks_below_rest(self):
        # 只向上抬，否则脚底会被窗口裁掉
        offsets = [PetAnimator._bob_offset(t, 2, 30) for t in range(90)]
        assert all(-2 <= o <= 0 for o in offsets)

    def test_single_pixel_amplitude_still_moves(self):
        assert {PetAnimator._bob_offset(t, 1, 30) for t in range(30)} == {0, -1}

    def test_disabled_returns_rest(self):
        assert PetAnimator._bob_offset(15, 0, 30) == 0
        assert PetAnimator._bob_offset(15, 2, 0) == 0


class TestParseBob:
    def test_missing_bob_is_off(self):
        assert PetAnimator._parse_bob({}, "demo") == (0, 0)

    def test_amplitude_clamped(self):
        assert PetAnimator._parse_bob({"bob": {"amplitude": 9, "period_ticks": 30}}, "demo") == (4, 30)

    def test_garbage_bob_ignored(self):
        assert PetAnimator._parse_bob({"bob": {"amplitude": "big"}}, "demo") == (0, 0)


class TestAnimTimeout:
    def test_base_timeout_without_duration(self):
        assert ActionQueue._anim_timeout_ms({}) == max(1000, config.ACTION_TIMEOUT_MS)

    def test_extended_beyond_action_duration(self):
        # sleep 默认时长 108s，超过 90s 兜底超时
        assert ActionQueue._anim_timeout_ms({"duration": 108}) >= 108_000

    def test_garbage_duration_falls_back_to_base(self):
        assert ActionQueue._anim_timeout_ms({"duration": "abc"}) == max(1000, config.ACTION_TIMEOUT_MS)


_APP = None  # 必须持有引用，否则 QApplication 会被回收


@pytest.fixture(scope="module")
def animator():
    global _APP
    from PySide6.QtWidgets import QApplication
    try:
        _APP = QApplication.instance() or QApplication([])
    except Exception as e:  # 无显示环境
        pytest.skip(f"Qt 不可用: {e}")
    anim = PetAnimator()
    yield anim
    anim.stop()


class TestBobWiring:
    """走真实素材：确认 JSON 配置能传到动画器并按时发位移。"""

    def test_idle_declares_bob(self, animator):
        data = animator._load_action("idle")
        assert (data["bob_amplitude"], data["bob_period"]) == (2, 30)

    def test_bob_resets_after_stop(self, animator):
        seen: list[int] = []
        animator.bob_changed.connect(seen.append)

        assert animator.play("idle", duration=1)
        for _ in range(16):
            animator._next_frame()
        assert min(seen) == -2  # 半个周期后抬到最高

        animator.stop()
        assert seen[-1] == 0
