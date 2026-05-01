# std
import json
import os
import subprocess
import time
from pathlib import Path

# pip
from pydantic import BaseModel, ValidationError

# local
from state.path import TGBT_PATH
from util.text import stdtqs
from .agent_wrapper import AgentProfile, AgentRunResult, AgentWrapper

_OUTPUT_SCHEMA_PROMPT_ATTRIBUTE = "TGBT_OUTPUT_SCHEMA_PROMPT"


def _ensure_codex_settings() -> None:
    """
    Codex CLI の挙動に影響する設定ファイル類を `tgbt` が想定する状態に修正する。
    """
    # `<repo-root>/.tgbt/.codex/config.toml` を想定のものに置き換える
    body = stdtqs("""
        # ----
        # グローバル設定
        # ----

        # 基本設定
        model = "gpt-5.5"
        model_reasoning_effort = "medium"
        plan_mode_reasoning_effort = "medium"
        personality = "pragmatic"
        project_root_markers = [".tgbt"]

        # Web検索モード
        sandbox_workspace_write.network_access = true

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
        approval_policy = "never"

        # ----
        # プロファイル (write)
        # ----        

        [profiles.tgbt_write]

        sandbox_mode = "workspace-write"
        approval_policy = "never"

        """)
    TGBT_PATH.tgbt_codex.mkdir(parents=True, exist_ok=True)
    TGBT_PATH.tgbt_codex_config.write_text(body, encoding="utf-8")


def _get_output_schema_prompt(output_schema: type[BaseModel]) -> str:
    """
    schema 型に紐づく追加 prompt 規則を取り出す。
    """
    # schema 固有の意味論は wrapper ではなく schema 側に任意属性として持たせる。
    schema_prompt = getattr(output_schema, _OUTPUT_SCHEMA_PROMPT_ATTRIBUTE, None)
    if isinstance(schema_prompt, str):
        return schema_prompt.strip()
    return ""


def _build_structured_output_instruction(
    instruction: str,
    output_schema: type[BaseModel],
) -> str:
    """
    構造化応答を要求する Codex prompt を構築する。
    """
    schema_prompt = _get_output_schema_prompt(output_schema)
    return stdtqs(f"""
        Structured output rules:
        - The final response must conform to the {output_schema.__name__} schema.
        - Do not return Markdown.
        - Do not return prose outside the schema.

        {schema_prompt}

        Task instruction:
        {instruction}
        """)


class CodexWrapper(AgentWrapper):
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

    def run(
        self,
        agent_profile: AgentProfile,
        instruction: str,
        output_schema: type[BaseModel] | None = None,
    ) -> AgentRunResult:
        """
        Codex CLI に作業を実行させる。
        """
        # Codex CLI に tgbt 管理下の設定だけを参照させる。
        env = os.environ.copy()
        env["CODEX_HOME"] = str(TGBT_PATH.tgbt_codex)

        # 構造化応答が必要な場合だけ、一時ディレクトリに schema と出力先を用意する。
        structured_response_file_path: Path | None = None
        structured_schema_file_path: Path | None = None
        if output_schema is not None:
            tmp_dir = TGBT_PATH.tgbt_codex / "tmp" / str(time.time_ns())
            tmp_dir.mkdir(parents=True, exist_ok=False)

            structured_schema_file_path = tmp_dir / "output_schema.json"
            structured_schema_file_path.write_text(
                json.dumps(
                    output_schema.model_json_schema(),
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            structured_response_file_path = tmp_dir / "last_message.json"

        # 構造化応答のための共通指示は wrapper 側で付与する。
        codex_instruction = instruction
        if output_schema is not None:
            codex_instruction = _build_structured_output_instruction(
                instruction=instruction,
                output_schema=output_schema,
            )

        # Codex CLI に渡す引数を構築
        command = [
            "codex",
            "exec",
            "--profile",
            agent_profile.value,
        ]
        if structured_schema_file_path is not None:
            command.extend(
                [
                    "--output-schema",
                    str(structured_schema_file_path),
                    "--output-last-message",
                    str(structured_response_file_path),
                ]
            )
        command.append(codex_instruction)

        # Codex CLI 呼び出し
        # NOTE
        #   prompt は shell を通さず引数として渡す。
        completed = subprocess.run(
            command,
            cwd=TGBT_PATH.repo_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        # Codex CLI が成功した場合だけ、構造化応答を pydantic で再検証する。
        structured_response: BaseModel | None = None
        structured_response_error: str | None = None
        is_ok = completed.returncode == 0
        if output_schema is not None and is_ok:
            if structured_response_file_path is None:
                structured_response_error = (
                    "Structured response file path is not prepared."
                )
                is_ok = False
            elif not structured_response_file_path.exists():
                structured_response_error = "Structured response file was not created."
                is_ok = False
            else:
                try:
                    structured_response = output_schema.model_validate_json(
                        structured_response_file_path.read_text(encoding="utf-8")
                    )
                except (OSError, ValidationError) as error:
                    structured_response_error = str(error)
                    is_ok = False

        # 実行内容を後から確認できるように標準出力と標準エラーを保存する。
        log_dir = TGBT_PATH.tgbt_logs / "codex"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file_path = log_dir / f"{time.time_ns()}.log"
        log_file_path.write_text(
            stdtqs(f"""
                command: {command}
                returncode: {completed.returncode}
                is_ok: {is_ok}
                structured_schema_file_path: {structured_schema_file_path}
                structured_response_file_path: {structured_response_file_path}
                structured_response_error:
                {structured_response_error}

                stdout:
                {completed.stdout}

                stderr:
                {completed.stderr}
                """),
            encoding="utf-8",
        )

        return AgentRunResult(
            is_ok=is_ok,
            reponse=completed.stdout,
            log_file_path=log_file_path,
            structured_response=structured_response,
        )
