# std
from enum import Enum
from dataclasses import dataclass
from pathlib import Path


class AgentProfile(Enum):
    """
    エージェントに何かをさせる時のプロファイル
    """

    READ_ONLY = "read_only"
    REPO_WRITE = "repo write"


@dataclass(frozen=True)
class AgentRunResult:
    """
    エージェント実行結果
    """

    is_ok: bool
    reponse: str
    audit_log_file_path: Path


class AgentWrapper:
    """
    Codex CLI, Claude Code CLI などの AI エージェントを呼び出すためのインターフェースクラス。
    このクラスは純粋仮想規基底で、実際に使用する製品ごとの派生クラスを実装することを前提とする。
    """

    def __init__(self):
        """
        コンストラクタ
        """
        ...

    def init_repo(self):
        """
        tgbt 操作対象リポジトリを、エージェントが想定通りの挙動になるように初期化する。
        """
        ...

    def run(
        self,
        agent_profile: AgentProfile,
        instruction: str,
    ) -> AgentRunResult:
        """
        エージェントに作業を実行させる。
        """
        ...
