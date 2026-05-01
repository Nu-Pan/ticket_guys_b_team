# std
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# pip
from pydantic import BaseModel


class AgentProfile(Enum):
    """
    エージェントに何かをさせる時のプロファイル
    """

    READ = "tgbt_read"
    WRITE = "tgbt_write"


@dataclass(frozen=True)
class AgentRunResult:
    """
    エージェント実行結果
    """

    is_ok: bool
    reponse: str
    log_file_path: Path
    structured_response: BaseModel | None = None


class AgentWrapper(ABC):
    """
    Codex CLI, Claude Code CLI などの AI エージェントを呼び出すためのインターフェースクラス。
    このクラスは純粋仮想基底で、実際に使用する製品ごとの派生クラスを実装することを前提とする。
    """

    @abstractmethod
    def __init__(self) -> None:
        """
        コンストラクタ
        """
        ...

    @abstractmethod
    def init_repo(self) -> None:
        """
        tgbt 操作対象リポジトリを、エージェントが想定通りの挙動になるように初期化する。
        """
        ...

    @abstractmethod
    def run(
        self,
        agent_profile: AgentProfile,
        instruction: str,
        output_schema: type[BaseModel] | None = None,
    ) -> AgentRunResult:
        """
        エージェントに作業を実行させる。
        """
        ...
