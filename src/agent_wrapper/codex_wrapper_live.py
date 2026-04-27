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
    body = stdtqs(
        """
        # ----
        # グローバル設定
        # ----

        # 基本設定
        model = "gpt-5.5"
        model_reasoning_effort = "medium"
        plan_mode_reasoning_effort = "medium"
        approval_policy = "never"
        personality = "pragmatic"
        profile = "tgbt_read"
        project_root_markers = [".tgbt"]

        # Web検索モード
        sandbox_workspace_write.network_access = true
        web_search = "cached"
        tools.web_search.context_size = "medium"

        # 参照リンクを vscode フレンドリーにする
        file_opener = "vscode"

        # ログインシェルは読み込ませない
        # NOTE
        #   tgbt からの codex 呼び出しに想定外の何かが混入するのを防ぐために無効化
        #   利便性と安全性を天秤にかけて、安全性を取った
        allow_login_shell = false

        # フィードバック系は副作用あるかもなので無効化
        analytics.enabled = false
        feedback.enabled = false

        # 更新チェックは無効化
        # NOTE
        #   tgbt 側で明示的に更新チェックが行われることを前提に無効化している
        check_for_update_on_startup = false

        # メモリー機能
        # NOTE
        #   Codex CLI のメモリー機能は使わない
        #   代わりに tgbt の知識システムだけを使う
        features.memories = false

        # 履歴関係
        # NOTE
        #   履歴は tgbt の仕組みで管理する
        #   reasoning はデバッグ用に詳細を残す
        history.persistence = "none"
        model_reasoning_summary = "detailed"
        model_verbosity = "medium"
        hide_agent_reasoning = false

        # ----
        # プロファイル (read)
        # ----

        [profiles.tgbt_read]

        sandbox_mode = "read-only"

        # ----
        # プロファイル (write)
        # ----        

        [profiles.tgbt_write]

        sandbox_mode = "workspace-write"

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
