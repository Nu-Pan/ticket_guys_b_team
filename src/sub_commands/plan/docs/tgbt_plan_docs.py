# std
import json
from pathlib import Path
from uuid import uuid4

# pip
import typer
from pydantic import ValidationError

# local
from agent_wrapper.agent_wrapper import AgentProfile
from agent_wrapper.codex_wrapper import CodexWrapper
from schemas.plan import (
    Assumption,
    CompletionCriterion,
    PlannedProcedure,
    RiskNote,
    TgbtPlan,
)
from state.path import TGBT_PATH
from util.error import tgbt_error
from util.text import stdtqs


def _plan_dir() -> Path:
    """
    plan 正本 JSON を保存するディレクトリを返す。
    """
    return TGBT_PATH.tgbt / "plan"


def _plan_read_dir() -> Path:
    """
    人間閲覧用 Markdown を保存するディレクトリを返す。
    """
    return TGBT_PATH.tgbt / "plan_read"


def _plan_json_path(plan_id: str) -> Path:
    """
    plan id に対応する正本 JSON パスを返す。
    """
    return _plan_dir() / f"{plan_id}.json"


def _plan_markdown_path(plan_id: str) -> Path:
    """
    plan id に対応する閲覧用 Markdown パスを返す。
    """
    return _plan_read_dir() / f"{plan_id}.md"


def _new_plan_id() -> str:
    """
    新しい plan id を生成する。
    """
    return f"plan-{uuid4().hex}"


def _render_id_text_items(
    items: list[CompletionCriterion]
    | list[RiskNote]
    | list[PlannedProcedure]
    | list[Assumption],
) -> str:
    """
    id と text を持つ plan 項目の Markdown list を描画する。
    """
    if len(items) == 0:
        return "- なし"

    return "\n".join(f"- `{item.id}` {item.text}" for item in items)


def _render_plain_items(items: list[str]) -> str:
    """
    文字列 list の Markdown list を描画する。
    """
    if len(items) == 0:
        return "- なし"

    return "\n".join(f"- {item}" for item in items)


def _render_plan_markdown(plan_id: str, plan: TgbtPlan) -> str:
    """
    TgbtPlan から人間閲覧用 Markdown を生成する。
    """
    # 人間が plan id と schema version を確認できるように先頭へ集約する。
    original_instructions = "\n\n".join(
        f"```text\n{item.text}\n```" for item in plan.original_instructions
    )
    if not original_instructions:
        original_instructions = "なし"

    return "\n".join(
        [
            f"# tgbt plan: {plan_id}",
            "",
            f"- schema_version: `{plan.schema_version}`",
            "",
            "## Original Instructions",
            "",
            original_instructions,
            "",
            "## Completion Criteria",
            "",
            _render_id_text_items(plan.completion_criteria),
            "",
            "## Risk Notes",
            "",
            _render_id_text_items(plan.risk_notes),
            "",
            "## Planned Procedures",
            "",
            _render_id_text_items(plan.planned_procedures),
            "",
            "## Assumptions",
            "",
            _render_id_text_items(plan.assumptions),
            "",
            "## Self Check Notes",
            "",
            _render_plain_items(plan.self_check_notes),
        ]
    )


def _save_plan(plan_id: str, plan: TgbtPlan) -> None:
    """
    plan 正本 JSON と閲覧用 Markdown を保存する。
    """
    # plan 関連ディレクトリは必要になった時点で作成する。
    _plan_dir().mkdir(parents=True, exist_ok=True)
    _plan_read_dir().mkdir(parents=True, exist_ok=True)

    # JSON を正本として保存し、Markdown は派生物として保存する。
    plan_json = json.dumps(
        plan.model_dump(mode="json"),
        ensure_ascii=False,
        indent=2,
    )
    _plan_json_path(plan_id).write_text(plan_json + "\n", encoding="utf-8")
    _plan_markdown_path(plan_id).write_text(
        _render_plan_markdown(plan_id, plan) + "\n",
        encoding="utf-8",
    )


def _load_plan(plan_id: str) -> TgbtPlan:
    """
    plan id に対応する正本 JSON を読み込む。
    """
    plan_json_path = _plan_json_path(plan_id)
    if not plan_json_path.exists():
        raise tgbt_error(
            "指定された plan が見つかりません",
            "plan_id を確認してから再実行してください",
            actual={"plan_json_path": plan_json_path},
        )

    # 正本 JSON は保存前後とも TgbtPlan として検証する。
    try:
        return TgbtPlan.model_validate_json(
            plan_json_path.read_text(encoding="utf-8")
        )
    except (OSError, ValidationError) as error:
        raise tgbt_error(
            "plan 正本 JSON の読み込みに失敗しました",
            "plan JSON の内容を確認してください",
            actual={"plan_json_path": plan_json_path, "error": str(error)},
        )


def _build_create_plan_prompt(instruction: str) -> str:
    """
    新規 plan 作成用の Codex prompt を構築する。
    """
    return stdtqs(f"""
        Create a new tgbt plan for `tgbt plan docs`.

        The final response must conform to the TgbtPlan schema.
        Do not return Markdown. Do not return prose outside the schema.

        Field rules:
        - schema_version: Use "1".
        - original_instructions: Preserve the user's original instruction text without paraphrasing.
        - completion_criteria: Write concrete observable conditions for completion.
        - risk_notes: Record ambiguity, missing information, likely execution risk, or oracle conflicts.
        - planned_procedures: Write ordered, atomic pre-execution work procedures.
        - assumptions: Record assumptions made to fill gaps not specified by the user or oracle.
        - self_check_notes: Record concise checks performed before finalizing the plan.

        ID rules:
        - completion_criteria ids: COMP-001, COMP-002, ...
        - risk_notes ids: RISK-001, RISK-002, ...
        - planned_procedures ids: PROC-001, PROC-002, ...
        - assumptions ids: ASMP-001, ASMP-002, ...

        Quality rules:
        - Prefer oracle over user instruction if they conflict.
        - Do not invent product-level decisions beyond necessary assumptions.
        - Make assumptions explicit instead of hiding them in procedure text.
        - Keep each list item focused on one idea.

        User instruction:
        ```text
        {instruction}
        ```
        """)


def _build_update_plan_prompt(
    instruction: str,
    existing_plan: TgbtPlan,
) -> str:
    """
    既存 plan 更新用の Codex prompt を構築する。
    """
    existing_plan_json = json.dumps(
        existing_plan.model_dump(mode="json"),
        ensure_ascii=False,
        indent=2,
    )

    return stdtqs(f"""
        Update the existing tgbt plan for `tgbt plan docs`.

        The final response must conform to the TgbtPlan schema.
        Do not return Markdown. Do not return prose outside the schema.

        Update rules:
        - Preserve existing original_instructions and append the new user instruction.
        - Preserve existing item ids when updating existing items.
        - Create new ids only for newly added items.
        - Keep schema_version as "1".
        - Prefer oracle over user instruction if they conflict.
        - Do not invent product-level decisions beyond necessary assumptions.
        - Make assumptions explicit instead of hiding them in procedure text.

        ID rules:
        - completion_criteria ids: COMP-001, COMP-002, ...
        - risk_notes ids: RISK-001, RISK-002, ...
        - planned_procedures ids: PROC-001, PROC-002, ...
        - assumptions ids: ASMP-001, ASMP-002, ...

        Existing plan JSON:
        ```json
        {existing_plan_json}
        ```

        New user instruction:
        ```text
        {instruction}
        ```
        """)


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
            "audit log を確認してください",
            actual={"audit_log_file_path": result.audit_log_file_path},
        )

    if not isinstance(result.structured_response, TgbtPlan):
        raise tgbt_error(
            "Codex CLI の構造化応答が TgbtPlan ではありません",
            "audit log を確認してください",
            actual={
                "audit_log_file_path": result.audit_log_file_path,
                "structured_response_type": (
                    type(result.structured_response).__name__
                ),
            },
            expect={"structured_response_type": TgbtPlan.__name__},
        )

    return result.structured_response


def create_plan(instruction: str) -> str:
    """
    instruction に従って plan を新しく作成する。
    作成したプランの ID を返す。
    """
    # 新規 plan id は tgbt 側で生成し、AI には決めさせない。
    plan_id = _new_plan_id()
    plan = _run_plan_prompt(_build_create_plan_prompt(instruction))
    _save_plan(plan_id, plan)
    return plan_id


def udate_plan(
    instruction: str,
    plan_id: str | None,
) -> str:
    """
    instruction に従って既存 plan を更新する。
    """
    if plan_id is None:
        raise tgbt_error(
            "更新対象の plan_id が指定されていません",
            "既存 plan を更新する場合は plan_id を指定してください",
        )

    # 既存正本を検証してから、Codex に更新版 plan の生成を依頼する。
    existing_plan = _load_plan(plan_id)
    updated_plan = _run_plan_prompt(
        _build_update_plan_prompt(
            instruction=instruction,
            existing_plan=existing_plan,
        )
    )
    _save_plan(plan_id, updated_plan)
    return plan_id


def tgbt_plan_docs_impl(
    instruction: str,
    plan_id: str | None,
) -> None:
    """
    `tgbt plan docs` の実装。
    """
    # 作成・更新処理を呼び出す
    if plan_id is None:
        plan_id = create_plan(instruction)
    else:
        plan_id = udate_plan(instruction, plan_id)

    # tgbt plan の結果として、人間閲覧用 Markdown を標準出力へ表示する。
    typer.echo(_plan_markdown_path(plan_id).read_text(encoding="utf-8"))
