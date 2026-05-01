# std
import json
import re
import sys
from datetime import datetime

# pip
import typer
from pydantic import ValidationError

# local
from agent_wrapper.agent_wrapper import AgentProfile
from agent_wrapper.codex_wrapper import CodexWrapper
from schemas.plan import TgbtPlan, render_plan_markdown
from state.path import TGBT_PATH
from util.error import tgbt_error
from util.text import stdtqs
from util.editor_input import read_from_editor

_HTML_COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.DOTALL)


def _new_plan_id() -> str:
    """
    新しい plan id を生成する。
    """
    # 固定幅の日時を使い、plan id の文字列ソート順と作成順を揃える。
    return datetime.now().strftime("plan-%Y%m%d-%H%M%S-%f")


def _save_plan(plan_id: str, plan: TgbtPlan) -> None:
    """
    plan 正本 JSON と閲覧用 Markdown を保存する。
    """
    # plan 関連ディレクトリは必要になった時点で作成する。
    TGBT_PATH.tgbt_plan.mkdir(parents=True, exist_ok=True)
    TGBT_PATH.tgbt_plan_read.mkdir(parents=True, exist_ok=True)

    # JSON を正本として保存し、Markdown は派生物として保存する。
    plan_json = json.dumps(
        plan.model_dump(mode="json"),
        ensure_ascii=False,
        indent=2,
    )
    TGBT_PATH.tgbt_plan_json(plan_id).write_text(
        plan_json + "\n",
        encoding="utf-8",
    )
    TGBT_PATH.tgbt_plan_markdown(plan_id).write_text(
        render_plan_markdown(plan_id, plan) + "\n",
        encoding="utf-8",
    )


def _load_plan(plan_id: str) -> TgbtPlan:
    """
    plan id に対応する正本 JSON を読み込む。
    """
    # plan のパスを構築
    plan_json_path = TGBT_PATH.tgbt_plan_json(plan_id)
    if not plan_json_path.exists():
        raise tgbt_error(
            "指定された plan が見つかりません",
            "plan_id を確認してから再実行してください",
            actual={"plan_json_path": plan_json_path},
        )

    # 正本 JSON は保存前後とも TgbtPlan として検証する。
    try:
        return TgbtPlan.model_validate_json(plan_json_path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as error:
        raise tgbt_error(
            "plan 正本 JSON の読み込みに失敗しました",
            "plan JSON の内容を確認してください",
            actual={"plan_json_path": plan_json_path, "error": str(error)},
        )


def _run_plan_prompt(prompt: str) -> TgbtPlan:
    """
    Codex CLI に TgbtPlan schema 付きで plan 生成を依頼する。
    """
    # plan 生成ではリポジトリを変更せず、構造化された最終応答だけを受け取る。
    result = CodexWrapper().run(
        agent_profile=AgentProfile.READ,
        instruction=prompt,
        output_schema=TgbtPlan,
    )
    if not result.is_ok:
        raise tgbt_error(
            "Codex CLI による plan 生成に失敗しました",
            "log を確認してください",
            actual={"log_file_path": result.log_file_path},
        )

    if not isinstance(result.structured_response, TgbtPlan):
        raise tgbt_error(
            "Codex CLI の構造化応答が TgbtPlan ではありません",
            "log を確認してください",
            actual={
                "log_file_path": result.log_file_path,
                "structured_response_type": (type(result.structured_response).__name__),
            },
            expect={"structured_response_type": TgbtPlan.__name__},
        )

    return result.structured_response


def _read_instruction_from_editor(initial_instruction: str = "") -> str:
    """
    plan 用テンプレートを入れた人間指示ファイルをエディタで編集して読み込む。
    """
    # 人間向け説明は HTML コメントにして、編集完了後の機械処理で除外できるようにする。
    template = stdtqs("""
        <!--
        tgbt plan に渡す指示を Markdown で書いてください。

        - 作業で達成したいことを書いてください。
        - 重要な制約、対象ファイル、完了条件があれば書いてください。
        - 見出しを使う場合は `#` だけを使ってください。
        - `##` 以降の深い見出しは使わないでください。
        - このコメントブロックは tgbt が指示文から除外します。
        -->

        # 作業指示
        """)

    # CLI 引数で渡された文字列は、編集前の指示本文として見出しの下に注入する。
    if initial_instruction == "":
        initial_text = template + "\n"
    else:
        initial_text = f"{template}\n{initial_instruction}\n"

    # エディタ用テンプレートを注入し、戻り値は機械処理用の本文だけに絞る。
    instruction = read_from_editor(initial_text)

    # コメント除去後の前後空白は、テンプレート由来の余白を plan に残さないために落とす。
    return _HTML_COMMENT_PATTERN.sub("", instruction).strip()


def _create_plan(instruction: str) -> str:
    """
    instruction に従って plan を新しく作成する。
    作成したプランの ID を返す。
    """
    # 新規 plan id は tgbt 側で生成し、AI には決めさせない。
    plan_id = _new_plan_id()
    plan = _run_plan_prompt(stdtqs(f"""
        Create a new tgbt plan for `tgbt plan`.

        Quality rules:
        - Prefer oracle over user instruction if they conflict.
        - Do not invent product-level decisions beyond necessary assumptions.
        - Make assumptions explicit instead of hiding them in procedure text.
        - Keep each list item focused on one idea.

        User instruction:
        ```text
        {instruction}
        ```
        """))
    _save_plan(plan_id, plan)
    return plan_id


def _udate_plan(
    instruction: str,
    plan_id: str,
) -> str:
    """
    instruction に従って既存 plan を更新する。
    """
    existing_plan = _load_plan(plan_id)
    existing_plan_json = json.dumps(
        existing_plan.model_dump(mode="json"),
        ensure_ascii=False,
        indent=2,
    )
    updated_plan = _run_plan_prompt(stdtqs(f"""
        Update the existing tgbt plan for `tgbt plan`.

        Update rules:
        - Preserve existing original_instructions and append the new user instruction.
        - Preserve existing item ids when updating existing items.
        - Create new ids only for newly added items.
        - Keep schema_version as "1".
        - Prefer oracle over user instruction if they conflict.
        - Do not invent product-level decisions beyond necessary assumptions.
        - Make assumptions explicit instead of hiding them in procedure text.

        Existing plan JSON:
        ```json
        {existing_plan_json}
        ```

        New user instruction:
        ```text
        {instruction}
        ```
        """))
    _save_plan(plan_id, updated_plan)
    return plan_id


def tgbt_plan_impl(
    instruction_source: str | None,
    plan_id: str | None,
) -> None:
    """
    `tgbt plan` の実装。
    """
    # 指示文の入力元を CLI 引数から決める。
    if instruction_source is None:
        instruction = _read_instruction_from_editor()
    elif instruction_source == "-":
        instruction = sys.stdin.read()
    else:
        instruction = _read_instruction_from_editor(instruction_source)

    # 作成・更新処理を呼び出す
    if plan_id is None:
        plan_id = _create_plan(instruction)
    else:
        plan_id = _udate_plan(instruction, plan_id)

    # tgbt plan の結果として、人間閲覧用 Markdown を標準出力へ表示する。
    typer.echo(TGBT_PATH.tgbt_plan_markdown(plan_id).read_text(encoding="utf-8"))
