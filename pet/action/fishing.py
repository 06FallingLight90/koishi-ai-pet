"""钓鱼判定：桌宠执行 fishing 动作时掷一次骰子，决定这轮是否有收获。

本模块只负责「结果」与「文案」，并在 import 时把自己注册为 fishing 的动作产出，
注入时机与去重由 outcome 机制统一处理。
"""

import random

from pet.action.outcome import register

# 单次钓鱼的命中概率
CATCH_RATE = 0.25

# 稀有度权重：命中后按此比例抽稀有度
_RARITY_WEIGHTS: dict[str, int] = {"common": 70, "rare": 25, "legendary": 5}

# 稀有度 → (前置形容, 后置补语)：三档刻意拉开情绪梯度，让模型自己决定反应
_RARITY_WORDING: dict[str, tuple[str, str]] = {
    "common":    ("",       "，没什么特别的"),
    "rare":      ("少见的", "！"),
    "legendary": ("罕见的", "！这是一个值得记住的时刻！"),
}

# 30 种鱼：15 常见 / 10 稀少 / 5 罕见
FISH_TABLE: dict[str, tuple[str, ...]] = {
    "common": (
        "鲫鱼", "鲤鱼", "草鱼", "鲢鱼", "鳙鱼",
        "青鱼", "鲶鱼", "鳊鱼", "白条", "麦穗鱼",
        "泥鳅", "黄颡鱼", "鳑鲏", "罗非鱼", "鲮鱼",
    ),
    "rare": (
        "鲈鱼", "鳜鱼", "黑鱼", "鲳鱼", "黄花鱼",
        "带鱼", "鲷鱼", "鳗鱼", "河豚", "锦鲤",
    ),
    "legendary": (
        "金龙鱼", "巨骨舌鱼", "蓝鳍金枪鱼", "翻车鱼", "腔棘鱼",
    ),
}


def roll_catch() -> tuple[str, str] | None:
    """掷一次钓鱼结果：返回 (鱼名, 稀有度)；没钓到返回 None。"""
    if random.random() >= CATCH_RATE:
        return None
    rarities = list(FISH_TABLE)
    weights = [_RARITY_WEIGHTS[r] for r in rarities]
    rarity = random.choices(rarities, weights=weights, k=1)[0]
    return random.choice(FISH_TABLE[rarity]), rarity


def format_result(result: tuple[str, str] | None) -> str:
    """把判定结果翻译成注入用的一句话。"""
    if result is None:
        return "你守着鱼竿等了半天，什么也没钓上来"
    name, rarity = result
    prefix, suffix = _RARITY_WORDING[rarity]
    return f"你钓到了一条{prefix}{name}{suffix}"


def _outcome() -> str:
    """fishing 的动作产出：掷一次骰子并给出文案。"""
    return format_result(roll_catch())


register("fishing", _outcome)
