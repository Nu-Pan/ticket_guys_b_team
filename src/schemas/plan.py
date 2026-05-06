# std
import re
from typing import ClassVar

# pip
from pydantic import BaseModel, ConfigDict, field_validator

# local
from schemas.markdown import (
    MarkdownSection,
    render_document,
    render_id_text_items,
    render_metadata_item,
    render_plain_items,
    render_text_blocks,
)

_PLAN_ID_PATTERN = re.compile(r"^[A-Z]+-\d{3}$")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _validate_prefixed_id(value: str, prefix: str) -> str:
    """
    plan item ID が prefix と 3 桁連番形式に従うことを検証する。
    """
    # schema prompt で要求する ID 形式は機械的に検証できるため schema 側で弾く。
    if not _PLAN_ID_PATTERN.fullmatch(value) or not value.startswith(f"{prefix}-"):
        raise ValueError(f"ID must match {prefix}-001 format.")
    return value


class OriginalInstruction(StrictModel):
    """
    人間から与えられた指示文
    """

    text: str


class CompletionCriterion(StrictModel):
    """
    計画を完了とする条件
    """

    id: str  # e.g. "COMP-001"
    text: str

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        """completion criterion ID の形式を検証する."""
        return _validate_prefixed_id(value, "COMP")


class RiskNote(StrictModel):
    """
    計画のリスク要素
    """

    id: str  # e.g. "RISK-001"
    text: str

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        """risk note ID の形式を検証する."""
        return _validate_prefixed_id(value, "RISK")


class PlannedProcedure(StrictModel):
    """
    計画の構成手順
    """

    id: str  # e.g. "PROC-001"
    text: str

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        """planned procedure ID の形式を検証する."""
        return _validate_prefixed_id(value, "PROC")


class Assumption(StrictModel):
    """
    計画を立てるにあたって用いた仮定。
    人間の指示が無い隙間については AI による仮定を置いても良いとしている。
    """

    id: str  # e.g. "ASMP-001"
    text: str

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        """assumption ID の形式を検証する."""
        return _validate_prefixed_id(value, "ASMP")


class TgbtPlan(StrictModel):
    """
    `tgbt run` の実行対象となる「計画」
    この構造化された計画情報が正本である
    """

    TGBT_OUTPUT_SCHEMA_PROMPT: ClassVar[str] = """\
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
"""

    schema_version: str
    original_instructions: list[OriginalInstruction]
    completion_criteria: list[CompletionCriterion]
    risk_notes: list[RiskNote]
    planned_procedures: list[PlannedProcedure]
    assumptions: list[Assumption]
    self_check_notes: list[str]

    @field_validator("schema_version")
    @classmethod
    def _validate_schema_version(cls, value: str) -> str:
        """plan schema version を現行値に固定する."""
        # schema_version は運用上の固定値なので、生成指示だけでなく再検証でも保証する。
        if value != "1":
            raise ValueError('schema_version must be "1".')
        return value


def render_plan_markdown(plan_id: str, plan: TgbtPlan) -> str:
    """
    TgbtPlan から人間閲覧用 Markdown を生成する。
    """
    return render_document(
        title=f"tgbt plan: {plan_id}",
        metadata=[
            render_metadata_item("schema_version", plan.schema_version),
        ],
        sections=[
            MarkdownSection(
                title="Original Instructions",
                body=render_text_blocks(plan.original_instructions),
            ),
            MarkdownSection(
                title="Completion Criteria",
                body=render_id_text_items(plan.completion_criteria),
            ),
            MarkdownSection(
                title="Risk Notes",
                body=render_id_text_items(plan.risk_notes),
            ),
            MarkdownSection(
                title="Planned Procedures",
                body=render_id_text_items(plan.planned_procedures),
            ),
            MarkdownSection(
                title="Assumptions",
                body=render_id_text_items(plan.assumptions),
            ),
            MarkdownSection(
                title="Self Check Notes",
                body=render_plain_items(plan.self_check_notes),
            ),
        ],
    )
