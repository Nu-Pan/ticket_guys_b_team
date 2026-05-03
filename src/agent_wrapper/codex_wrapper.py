# std
import json
import os
import subprocess
import time
from datetime import date
from dataclasses import asdict
from pathlib import Path

# pip
from pydantic import BaseModel, ValidationError

# local
from schemas.markdown import MarkdownPromptBlock, render_prompt
from state.path import TGBT_PATH
from util.error import tgbt_error
from util.tgbt_call_log import record_related_log_path
from util.text import stdtqs
from .agent_wrapper import AgentProfile, AgentRunResult, AgentWrapper

_OUTPUT_SCHEMA_PROMPT_ATTRIBUTE = "TGBT_OUTPUT_SCHEMA_PROMPT"
_SMOKE_TEST_EXPECTED_RESPONSE = "tgbt-codex-smoke-ok"
_SMOKE_TEST_INSTRUCTION = (
    f"Reply with exactly this text and nothing else: {_SMOKE_TEST_EXPECTED_RESPONSE}"
)
_SMOKE_TEST_CACHE_FILE_NAME = "codex_prerequirements_smoke_passed_on"


class CodexWrapper(AgentWrapper):
    """Codex CLI を tgbt 管理下の設定で呼び出す wrapper。"""

    def __init__(self) -> None:
        """状態を持たない wrapper を初期化する。"""
        # 現時点では保持すべき状態は無い。
        pass

    def run(
        self,
        agent_profile: AgentProfile,
        instruction: list[MarkdownPromptBlock],
        output_schema: type[BaseModel] | None = None,
    ) -> AgentRunResult:
        """Codex CLI に作業を実行させる。

        Args:
            agent_profile: Codex CLI 実行時に使う tgbt profile。
            instruction: Codex CLI に渡す作業指示。
            output_schema: 最終応答に要求する pydantic schema。

        Returns:
            Codex CLI の実行結果と tgbt 側の呼び出しログ。
        """
        return _run_codex_cli(
            agent_profile=agent_profile,
            instruction=instruction,
            output_schema=output_schema,
        )


def _run_codex_cli(
    agent_profile: AgentProfile,
    instruction: list[MarkdownPromptBlock],
    output_schema: type[BaseModel] | None = None,
    *,
    check_cli_availability: bool = True,
) -> AgentRunResult:
    """Codex CLI を 1 回呼び出し、その実行ログを保存する。

    Args:
        agent_profile: Codex CLI 実行時に使う tgbt profile。
        instruction: Codex CLI に渡す作業指示。
        output_schema: 最終応答に要求する pydantic schema。
        check_cli_availability: 本命実行前の smoke test を行うか。

    Returns:
        Codex CLI の実行結果と tgbt 側の呼び出しログ。
    """
    # 必要な場合だけ、CLI の実行可能性を本命呼び出し前に確認する。
    if check_cli_availability:
        _ensure_codex_cli_is_available()

    # Codex CLI 用の設定は、Codex CLI を呼び出すタイミングで用意する。
    _ensure_codex_settings()

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
    codex_instruction_blocks = instruction
    if output_schema is not None:
        codex_instruction_blocks = _build_structured_output_instruction(
            instruction=instruction,
            output_schema=output_schema,
        )

    # Codex CLI に渡す引数を構築する。
    command: list[str] = [
        "codex",
        "exec",
        "--profile",
        agent_profile.value,
    ]
    if structured_schema_file_path is not None:
        # NOTE: schema file を作る分岐では output file も必ず用意している。
        assert structured_response_file_path is not None
        command.extend(
            [
                "--output-schema",
                str(structured_schema_file_path),
                "--output-last-message",
                str(structured_response_file_path),
            ]
        )

    # prompt 文字列への描画は、CLI 引数に積む直前まで遅延させる。
    codex_instruction = render_prompt(codex_instruction_blocks)
    command.append(codex_instruction)

    # Codex CLI を shell 経由ではなく argv として呼び出す。
    # NOTE: prompt に shell 特殊文字が含まれても shell 展開させないため。
    completed: subprocess.CompletedProcess[str] = subprocess.run(
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
            structured_response_error = "Structured response file path is not prepared."
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

    # 実行内容を後から確認できるように Codex CLI 呼び出しログを保存する。
    log_dir = TGBT_PATH.tgbt_logs_codex_call
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file_path = log_dir / f"{time.time_ns()}.json"
    config_toml: str | None = None
    if TGBT_PATH.tgbt_codex_config.exists():
        config_toml = TGBT_PATH.tgbt_codex_config.read_text(encoding="utf-8")

    structured_response_raw: str | None = None
    if (
        structured_response_file_path is not None
        and structured_response_file_path.exists()
    ):
        structured_response_raw = structured_response_file_path.read_text(
            encoding="utf-8"
        )

    log_file_path.write_text(
        json.dumps(
            {
                "command": command,
                "cwd": str(TGBT_PATH.repo_root),
                "environment": {
                    "CODEX_HOME": env["CODEX_HOME"],
                },
                "config": {
                    "config_toml_path": str(TGBT_PATH.tgbt_codex_config),
                    "config_toml": config_toml,
                },
                "input": {
                    "agent_profile": agent_profile.value,
                    "instruction": [asdict(block) for block in instruction],
                    "codex_instruction": codex_instruction,
                },
                "output_schema": {
                    "class_name": (
                        output_schema.__name__ if output_schema is not None else None
                    ),
                    "json_schema": (
                        output_schema.model_json_schema()
                        if output_schema is not None
                        else None
                    ),
                    "schema_file_path": (
                        str(structured_schema_file_path)
                        if structured_schema_file_path is not None
                        else None
                    ),
                },
                "result": {
                    "returncode": completed.returncode,
                    "is_ok": is_ok,
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                    "structured_response_file_path": (
                        str(structured_response_file_path)
                        if structured_response_file_path is not None
                        else None
                    ),
                    "structured_response_raw": structured_response_raw,
                    "structured_response": (
                        structured_response.model_dump(mode="json")
                        if structured_response is not None
                        else None
                    ),
                    "structured_response_error": structured_response_error,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    record_related_log_path(log_file_path)

    # 呼び出し元へ CLI 出力とログ位置を返す。
    return AgentRunResult(
        is_ok=is_ok,
        reponse=completed.stdout,
        log_file_path=log_file_path,
        structured_response=structured_response,
    )


def _ensure_codex_cli_is_available() -> None:
    """Codex CLI が利用可能であることを smoke test で確認する."""
    # 当日中に成功済みであれば、外部 CLI 呼び出しを省略する。
    cache_file_path = _smoke_test_cache_file_path()
    today = date.today().isoformat()
    if _is_smoke_test_cache_valid(cache_file_path, today):
        return

    # 本命呼び出しの前提確認なので、ここでは再帰的な事前確認を行わない。
    result = _run_codex_cli(
        agent_profile=AgentProfile.READ,
        instruction=[
            MarkdownPromptBlock(
                title="Task instruction",
                body=_SMOKE_TEST_INSTRUCTION,
            )
        ],
        check_cli_availability=False,
    )
    response = result.reponse.strip()
    if not result.is_ok or response != _SMOKE_TEST_EXPECTED_RESPONSE:
        raise tgbt_error(
            "Codex CLI 実行可能状態の事前チェックに失敗しました",
            """
            tgbt から Codex CLI を正しく呼び出せませんでした。
            Codex CLI のインストール状態、ログイン状態、ネットワーク接続、または tgbt 管理下の Codex 設定を確認してください。
            """,
            actual={
                "is_ok": result.is_ok,
                "response": response,
                "log_file_path": result.log_file_path,
            },
            expect={
                "response": _SMOKE_TEST_EXPECTED_RESPONSE,
            },
        )

    # 成功日だけを保存し、翌日以降は再度 smoke test を実行する。
    cache_file_path.write_text(f"{today}\n", encoding="utf-8")


def _smoke_test_cache_file_path() -> Path:
    """当日 smoke test 成功状態を記録するファイルパスを返す."""
    return TGBT_PATH.tgbt / _SMOKE_TEST_CACHE_FILE_NAME


def _is_smoke_test_cache_valid(cache_file_path: Path, today: str) -> bool:
    """smoke test の当日成功キャッシュが有効か判定する.

    Args:
        cache_file_path: smoke test 成功日を保存するファイル。
        today: 比較対象の日付文字列。

    Returns:
        キャッシュが存在し、保存日が今日と一致するなら True。
    """
    # cache file が無ければ、まだ成功確認済みではない。
    if not cache_file_path.exists():
        return False

    # 日付が一致するときだけ、当日中の成功キャッシュとして扱う。
    return cache_file_path.read_text(encoding="utf-8").strip() == today


def _build_structured_output_instruction(
    instruction: list[MarkdownPromptBlock],
    output_schema: type[BaseModel],
) -> list[MarkdownPromptBlock]:
    """構造化応答を要求する Codex prompt block を構築する.

    Args:
        instruction: 元の作業指示。
        output_schema: 最終応答に要求する pydantic schema。

    Returns:
        Codex CLI に渡す prompt の構成要素。
    """
    # 全 schema に共通する構造化応答ルールを先頭に置く。
    schema_prompt = _get_output_schema_prompt(output_schema)
    blocks: list[MarkdownPromptBlock] = [
        MarkdownPromptBlock(
            title="Structured output rules",
            body=stdtqs(f"""
                - The final response must conform to the {output_schema.__name__} schema.
                - Do not return Markdown.
                - Do not return prose outside the schema.
                """),
        ),
        *instruction,
    ]

    # schema 側に追加指示がある場合だけ、共通ルールとタスク指示の間に差し込む。
    if schema_prompt != "":
        blocks.insert(
            1,
            MarkdownPromptBlock(
                title="Schema-specific rules",
                body=schema_prompt,
            ),
        )

    return blocks


def _get_output_schema_prompt(output_schema: type[BaseModel]) -> str:
    """schema 型に紐づく追加 prompt 規則を取り出す.

    Args:
        output_schema: 追加 prompt 属性を持ちうる pydantic schema。

    Returns:
        schema 固有の追加 prompt。未定義なら空文字列。
    """
    # schema 固有の意味論は wrapper ではなく schema 側に任意属性として持たせる。
    schema_prompt = getattr(output_schema, _OUTPUT_SCHEMA_PROMPT_ATTRIBUTE, None)
    if isinstance(schema_prompt, str):
        return schema_prompt.strip()
    return ""


def _ensure_codex_settings() -> None:
    """Codex CLI の設定ファイルを tgbt が想定する内容へ更新する."""
    # `<repo-root>/.tgbt/.codex/config.toml` に書き込む設定本文を組み立てる。
    body = stdtqs("""
        # ----
        # グローバル設定
        # ----

        # 基本設定
        model = "gpt-5.5"
        model_reasoning_effort = "medium"
        plan_mode_reasoning_effort = "medium"
        personality = "pragmatic"
        project_root_markers = [".git"]

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

    # Codex CLI が参照する tgbt 管理下の設定ファイルを更新する。
    TGBT_PATH.tgbt_codex.mkdir(parents=True, exist_ok=True)
    TGBT_PATH.tgbt_codex_config.write_text(body, encoding="utf-8")
