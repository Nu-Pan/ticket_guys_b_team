# std
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# pip
from pydantic import BaseModel

# local
from schemas.markdown import MarkdownPromptBlock


class AgentProfile(Enum):
    """
    エージェントに何かをさせる時のプロファイル
    """

    HIGH_READ = "tgbt_high_read"
    HIGH_WRITE = "tgbt_high_write"
    MEDIUM_READ = "tgbt_medium_read"
    MEDIUM_WRITE = "tgbt_medium_write"
    LOW_READ = "tgbt_low_read"
    LOW_WRITE = "tgbt_low_write"
    MINIMUM_READ = "tgbt_minimum_read"
    MINIMUM_WRITE = "tgbt_minimum_write"

    READ = "tgbt_medium_read"
    WRITE = "tgbt_medium_write"


@dataclass(frozen=True)
class AgentRunResult:
    """
    エージェント実行結果
    """

    is_ok: bool
    reponse: str
    log_file_path: Path
    structured_response: BaseModel | None = None
    error_message: str | None = None


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
        # 抽象インターフェースとして、派生クラス側の初期化実装を要求する。
        ...

    @abstractmethod
    def run(
        self,
        agent_profile: AgentProfile,
        instruction: list[MarkdownPromptBlock],
        output_schema: type[BaseModel] | None = None,
        use_knowledge_system: bool = False,
        caller_schema_prompt: str | None = None,
    ) -> AgentRunResult:
        """
        エージェントに作業を実行させる。
        """
        # 抽象インターフェースとして、派生クラス側の実行実装を要求する。
        ...
