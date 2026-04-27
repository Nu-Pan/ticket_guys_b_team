# std
import os
import shutil
import subprocess
import time

# local
from state.path import TGBT_PATH
from util.text import stdtqs
from .agent_wrapper import AgentProfile, AgentRunResult, AgentWrapper


def _ensure_codex_settings() -> None:
    """
    Codex CLI の挙動に影響する設定ファイル類を `tgbt` が想定する状態に修正する。
    """
    # `<repo-root>/.codex` は削除する
    shutil.rmtree(TGBT_PATH.repo_root_codex, ignore_errors=True)

    # `<repo-root>/.tgbt/.codex` 配下を正しい状態にする
    # TODO
    #   中身の正しさが未調査
    body = stdtqs(
        """
        # ----
        # グローバル設定
        # ----

        # 基本設定
        model = "gpt-5.5"
        model_reasoning_effort = "high"
        plan_mode_reasoning_effort = "high"
        model_verbosity = "high"
        approval_policy = "on-request"
        sandbox_mode = "workspace-write"
        personality = "pragmatic"

        # Web検索モード
        # NOTE
        #   cached はライブ取得せず、OpenAI 管理のインデックスを使う
        sandbox_workspace_write.network_access = true
        web_search = "cached"

        # 参照リンクを vsocde フレンドリーにする
        file_opener = "vscode"

        # 基本指示は使わない
        #developer_instructions = ...

        # ----
        # セッション履歴
        # ----

        [history]
        persistence = "none"

        # ----
        # Web 検索
        # ----

        [tools.web_search]
        context_size = "high"

        # ----
        # マルチエージェント
        # ----

        [agents]

        max_threads = 6
        max_depth = 1

        # ----
        # プロファイル
        # ----

        [profiles.read_only]
        sandbox_mode = "read-only"
        approval_policy = "never"

        [profiles."repo write"]
        sandbox_mode = "workspace-write"
        approval_policy = "on-request"
        """
    )
    shutil.rmtree(TGBT_PATH.tgbt_codex, ignore_errors=True)
    TGBT_PATH.tgbt_codex.mkdir(parents=True, exist_ok=True)
    TGBT_PATH.tgbt_codex_config.write_text(body, encoding="utf-8")


def _ensure_agents_md() -> None:
    """
    `AGENTS.md` を正しい状態にする
    """
    # ルート直下のやつをやる
    # NOTE
    #   必要な指示文は都度 `tgbt` 側で生成すれば良いので、わざわざ `AGENTS.md` を使う理由がない。
    #   よって `<repo-root>` 配下（サブディレクトリ含む）の `AGENTS.md` は全て削除する。
    for agents_md in TGBT_PATH.repo_root.rglob("AGENTS.md"):
        agents_md.unlink(missing_ok=True)


class CodexWrapperLive(AgentWrapper):
    """
    Codex CLI を live mode で呼び出すための wrapper。
    """

    def __init__(self) -> None:
        """
        wrapper を初期化する。
        """
        # 現時点では保持すべき状態は無い。
        pass

    def init_repo(self) -> None:
        """
        Codex CLI が動作する前提を整える。
        """
        _ensure_codex_settings()
        _ensure_agents_md()

    def run(
        self,
        agent_profile: AgentProfile,
        instruction: str,
    ) -> AgentRunResult:
        """
        Codex CLI に作業を実行させる。
        """
        # Codex CLI に tgbt 管理下の設定だけを参照させる。
        env = os.environ.copy()
        env["CODEX_HOME"] = str(TGBT_PATH.tgbt_codex)

        # prompt は shell を通さず引数として渡す。
        command = [
            "codex",
            "exec",
            "--profile",
            agent_profile.value,
            instruction,
        ]
        completed = subprocess.run(
            command,
            cwd=TGBT_PATH.repo_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        # 実行内容を後から確認できるように標準出力と標準エラーを保存する。
        audit_log_dir = TGBT_PATH.tgbt_codex / "audit_logs"
        audit_log_dir.mkdir(parents=True, exist_ok=True)
        audit_log_file_path = audit_log_dir / f"{time.time_ns()}.log"
        audit_log_file_path.write_text(
            stdtqs(
                f"""
                command: {command}
                returncode: {completed.returncode}

                stdout:
                {completed.stdout}

                stderr:
                {completed.stderr}
                """
            ),
            encoding="utf-8",
        )

        return AgentRunResult(
            is_ok=completed.returncode == 0,
            reponse=completed.stdout,
            audit_log_file_path=audit_log_file_path,
        )
