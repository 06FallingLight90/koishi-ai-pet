"""版本号解析与比较的纯逻辑。

刻意不依赖 Qt：轻量测试环境（无 PySide6）也能直接导入验证。
"""

import logging

from packaging.version import InvalidVersion, parse as _parse_ver

logger = logging.getLogger(__name__)


def strip_v(tag: str) -> str:
    """去掉 tag 开头的单个 v/V 前缀（精确剥离，避免 lstrip 的字符集陷阱）。"""
    return tag[1:] if tag[:1] in ("v", "V") else tag


def ver_newer(remote: str, local: str) -> bool:
    """判断 remote 是否比 local 新（PEP 440 规范比较）。"""
    try:
        return _parse_ver(remote) > _parse_ver(local)
    except InvalidVersion:
        logger.debug(f"版本号无法解析，跳过比较: remote={remote} local={local}")
        return False
