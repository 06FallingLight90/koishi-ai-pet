"""桌宠帧动画模块 —— 基于 JSON 配置的帧序列播放。

每个动作目录下需包含 `<action>.json` 配置文件：

    {
      "desc": "待机动画，轻轻呼吸",
      "tick_counts": 120,
      "frame_ratios": [0.95, 0.05],
      "loop": true,
      "note": ""
    }

- tick_counts: 一个循环的总 tick 数，配合 PET_FPS 控制周期时长
- frame_ratios: 每张素材占比（和 = 1.0），按文件名字母序对应
- loop: 是否循环播放（默认 true）
- 每一tick时长 = 1000/PET_FPS（ms）
"""

import json
import logging
import math
import os
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QObject, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

from pet.config import config

logger = logging.getLogger(__name__)

_SUPPORTED_EXT = (".png", ".jpg", ".jpeg", ".bmp", ".webp")
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class PetAnimator(QObject):

    animation_finished = Signal(str)
    animation_interrupted = Signal(str)
    frame_changed = Signal(QPixmap)
    bob_changed = Signal(int)  # 呼吸位移（0 或负值，负值=上移）

    def __init__(self, pet_dir: str | None = None, parent=None):
        super().__init__(parent)
        self._pet_dir = str(pet_dir) if pet_dir else str(BASE_DIR / "assets" / "actions")

        self._frames: list[QPixmap] = []
        self._tick_plan: list[int] = []       # 每帧停留 tick 数
        self._tick_in_frame: int = 0           # 当前帧内已过 tick
        self._current_frame: int = 0
        self._current_action: str = ""
        self._loop: bool = True

        # 呼吸位移：按 tick 计算，只向上抬，避免脚底被窗口裁掉
        self._tick_count: int = 0
        self._bob_amplitude: int = 0
        self._bob_period: int = 0
        self._bob_now: int = 0

        self._frame_timer = QTimer(self)
        self._frame_timer.timeout.connect(self._next_frame)

        self._duration_timer = QTimer(self)
        self._duration_timer.setSingleShot(True)
        self._duration_timer.timeout.connect(self._on_duration_end)

        self._cache: dict[str, dict] = {}      # action → {frames, tick_plan, loop, bob_*}


    def play(self, action: str, duration: float | None = None) -> bool:
        """播放动作。

        loop 动作: duration 控制总时长（秒），None 则无限循环。
        one-shot: duration 忽略，时长由 tick_counts + PET_FPS 决定。
        """
        if self._current_action and not self._loop and self.is_playing:
            self._frame_timer.stop()
            self._duration_timer.stop()
            self.animation_interrupted.emit(self._current_action)
            self.animation_finished.emit(self._current_action)

        data = self._load_action(action)
        if not data:
            # 缺帧或配置损坏：停掉旧动画，让调用方（动作队列）能看出没播起来
            self._frame_timer.stop()
            self._duration_timer.stop()
            self._reset_bob()
            return False

        self._frame_timer.stop()
        self._duration_timer.stop()
        self._reset_bob()

        self._frames = data["frames"]
        self._tick_plan = data["tick_plan"]
        self._loop = data["loop"]
        self._bob_amplitude = data["bob_amplitude"]
        self._bob_period = data["bob_period"]
        self._current_action = action
        self._current_frame = 0
        self._tick_in_frame = 0
        self._tick_count = 0

        self.frame_changed.emit(self._frames[0])

        interval = self._calc_tick_interval()
        self._frame_timer.start(interval)

        if self._loop and duration is not None and duration > 0:
            self._duration_timer.start(int(duration * 1000))

        return True

    def stop(self):
        self._frame_timer.stop()
        self._duration_timer.stop()
        self._reset_bob()

    def has_frames(self, action: str) -> bool:
        return self._load_action(action) is not None

    def available_actions(self) -> list[str]:
        if not os.path.isdir(self._pet_dir):
            return []
        actions = []
        for name in sorted(os.listdir(self._pet_dir)):
            full = os.path.join(self._pet_dir, name)
            if os.path.isdir(full) and self._config_exists(name):
                actions.append(name)
        return actions

    @property
    def current_action(self) -> str:
        return self._current_action

    @property
    def is_playing(self) -> bool:
        return self._frame_timer.isActive()


    def _calc_tick_interval(self) -> int:
        return max(1, round(1000 / config.PET_FPS))

    def _load_action(self, action: str) -> dict | None:
        if action in self._cache:
            return self._cache[action]

        cfg = self._load_action_config(action)
        if cfg is None:
            return None

        action_dir = os.path.join(self._pet_dir, action)
        image_files = sorted(
            f for f in os.listdir(action_dir)
            if os.path.splitext(f)[1].lower() in _SUPPORTED_EXT
        )
        if not image_files:
            return None

        frames: list[QPixmap] = []
        for f in image_files:
            pixmap = QPixmap(os.path.join(action_dir, f))
            if pixmap.isNull():
                logger.warning(f"Failed to load image: {action}/{f}")
                return None
            dpr = QApplication.primaryScreen().devicePixelRatio() if QApplication.primaryScreen() else 1.0
            pixmap = pixmap.scaled(
                int(config.PET_WIDTH * dpr),
                int(config.PET_HEIGHT * dpr),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            pixmap.setDevicePixelRatio(dpr)
            frames.append(pixmap)

        cfg = self._sanitize_config(cfg, len(frames), action)
        tick_plan = self._build_tick_plan(cfg, len(frames))
        bob_amplitude, bob_period = self._parse_bob(cfg, action)
        data = {
            "frames": frames,
            "tick_plan": tick_plan,
            "loop": cfg.get("loop", True),
            "bob_amplitude": bob_amplitude,
            "bob_period": bob_period,
        }
        self._cache[action] = data
        return data

    @staticmethod
    def _build_tick_plan(cfg: dict, frame_count: int) -> list[int]:
        """按累计比例分配 tick。

        逐帧独立取整在除不尽时会把差额全推给尾帧（如 8 帧 / 90 tick → 11×7 + 13），
        累计取整把误差摊到各帧上（→ 11/12 交替）。
        """
        tick_counts = cfg.get("tick_counts", 30)
        ratios = cfg.get("frame_ratios", [1.0 / frame_count] * frame_count)

        if len(ratios) != frame_count:
            ratios = [1.0 / frame_count] * frame_count

        tick_plan: list[int] = []
        allocated = 0
        cumulative = 0.0
        for i in range(frame_count - 1):
            cumulative += ratios[i]
            target = int(cumulative * tick_counts + 0.5)
            ceiling = tick_counts - allocated - (frame_count - i - 1)
            ticks = max(1, min(target - allocated, ceiling))
            tick_plan.append(ticks)
            allocated += ticks
        tick_plan.append(max(1, tick_counts - allocated))
        return tick_plan

    @staticmethod
    def _sanitize_config(cfg: dict, frame_count: int, action: str) -> dict:
        """把不合法的时间配置就地修正成可用值。

        以前这里非法就返回 False，会让整个动作静默失效、动作队列一路干等到超时。
        改成能修就修：比例不合法则等分，tick 不够则抬到帧数。
        """
        cfg = dict(cfg)

        ratios = cfg.get("frame_ratios")
        if ratios is not None:
            try:
                values = [float(r) for r in ratios]
            except (TypeError, ValueError):
                values = []
            if len(values) == frame_count and all(v > 0 for v in values):
                total = sum(values)
                if abs(total - 1.0) > 0.01:
                    logger.warning(f"'{action}': frame_ratios sum = {total:.3f}，已按比例归一化")
                    values = [v / total for v in values]
                cfg["frame_ratios"] = values
            else:
                logger.warning(f"'{action}': frame_ratios 与 {frame_count} 帧不匹配，改为等分")
                cfg.pop("frame_ratios", None)

        try:
            tick_counts = max(1, int(cfg.get("tick_counts", 30)))
        except (TypeError, ValueError):
            logger.warning(f"'{action}': tick_counts 非法，改用 30")
            tick_counts = 30
        if tick_counts < frame_count:
            logger.warning(f"'{action}': tick_counts ({tick_counts}) < 帧数 ({frame_count})，已抬到帧数")
            tick_counts = frame_count
        cfg["tick_counts"] = tick_counts

        return cfg

    @staticmethod
    def _parse_bob(cfg: dict, action: str) -> tuple[int, int]:
        """读取呼吸配置 (幅值 px, 周期 tick)。

        幅值上限 4px：贴图 1:1 撑满窗口，抬过头会顶出画面。
        """
        bob = cfg.get("bob") or {}
        try:
            amplitude = max(0, min(4, int(bob.get("amplitude", 0) or 0)))
            period = max(0, min(900, int(bob.get("period_ticks", 0) or 0)))
        except (TypeError, ValueError):
            logger.warning(f"'{action}': bob 配置无效，已忽略")
            return 0, 0
        return amplitude, period

    def _config_exists(self, action: str) -> bool:
        return os.path.isfile(os.path.join(self._pet_dir, action, f"{action}.json"))

    def _load_action_config(self, action: str) -> dict | None:
        config_path = os.path.join(self._pet_dir, action, f"{action}.json")
        if not os.path.isfile(config_path):
            return None
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to parse config: {config_path}: {e}")
            return None

    def _on_duration_end(self):
        self._frame_timer.stop()
        self._reset_bob()
        self.animation_finished.emit(self._current_action)

    def _next_frame(self):
        self._tick_count += 1
        self._apply_bob()
        self._tick_in_frame += 1
        if self._tick_in_frame >= self._tick_plan[self._current_frame]:
            self._tick_in_frame = 0
            self._current_frame += 1
            if self._current_frame >= len(self._frames):
                if self._loop:
                    self._current_frame = 0
                else:
                    self._frame_timer.stop()
                    self._reset_bob()
                    self.animation_finished.emit(self._current_action)
                    return
            self.frame_changed.emit(self._frames[self._current_frame])

    def _reset_bob(self):
        """停播或切动作时把呼吸位移归零。"""
        self._bob_amplitude = 0
        self._bob_period = 0
        if self._bob_now != 0:
            self._bob_now = 0
            self.bob_changed.emit(0)

    @staticmethod
    def _bob_offset(tick: int, amplitude: int, period: int) -> int:
        """呼吸位移：sin² 曲线，整周期内只向上抬（负值），不向下沉。"""
        if amplitude <= 0 or period <= 0:
            return 0
        phase = math.sin(math.pi * (tick % period) / period)
        return -int(amplitude * phase * phase + 0.5)

    def _apply_bob(self):
        if not self._bob_amplitude:
            return
        dy = self._bob_offset(self._tick_count, self._bob_amplitude, self._bob_period)
        if dy != self._bob_now:
            self._bob_now = dy
            self.bob_changed.emit(dy)
