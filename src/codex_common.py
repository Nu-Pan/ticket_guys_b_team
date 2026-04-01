"""Codex CLI 連携で共有する基本型。"""

import enum


VALID_REASONING_EFFORTS = {"minimal", "low", "medium", "high", "xhigh"}


class CodexCliMode(str, enum.Enum):
    """Codex CLI の実行モード。"""

    LIVE = "live"
    STUB = "stub"
