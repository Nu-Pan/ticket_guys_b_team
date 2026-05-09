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
)

_EVAL_ID_PATTERN = re.compile(r"^[A-Z]+-\d{3}$")


class StrictModel(BaseModel):
    """
    oracle eval schema 全体で追加 field を禁止するための基底 model。
    """

    model_config = ConfigDict(extra="forbid")


def _validate_prefixed_id(value: str, prefix: str) -> str:
    """
    oracle eval item ID が prefix と 3 桁連番形式に従うことを検証する。
    """
    # schema prompt で要求する ID 形式は機械的に検証できるため schema 側で弾く。
    if not _EVAL_ID_PATTERN.fullmatch(value) or not value.startswith(f"{prefix}-"):
        raise ValueError(f"ID must match {prefix}-001 format.")
    return value


class OracleEvalFinding(StrictModel):
    """
    oracle のみを根拠として見つけた評価指摘。
    """

    id: str
    text: str


class OracleContradiction(OracleEvalFinding):
    """
    oracle 内の明示内容同士の矛盾。
    """

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        """contradiction ID の形式を検証する."""
        # contradiction 用の prefix で共通 ID 検証へ渡す。
        return _validate_prefixed_id(value, "CNTR")


class OracleIssue(OracleEvalFinding):
    """
    oracle 内の矛盾以外の明示的な問題点。
    """

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        """issue ID の形式を検証する."""
        # oracle issue 用の prefix で共通 ID 検証へ渡す。
        return _validate_prefixed_id(value, "ISSUE")


class OracleEvalReport(StrictModel):
    """
    `tgbt eval oracle` が返す oracle 評価結果。
    """

    TGBT_OUTPUT_SCHEMA_PROMPT: ClassVar[str] = """\
Field rules:
- schema_version: Use "1".
- contradictions: Record only contradictions found within oracle itself.
- issues: Record only explicit oracle issues other than contradictions.
  Include typos, wording variations that may be mistaken for separate concepts, path context mixups, permission-boundary conflicts, skill responsibility conflicts, incorrect references, and broken Markdown headings, lists, or emphasis.
  Include opportunities to simplify existing oracle text or optimize existing oracle document structure when the improvement does not add product details or change product intent.
- self_check_notes: Record concise checks performed before finalizing the report.

Scope rules:
- Evaluate only existing `<repo-root>/oracle` content and `<repo-root>/oracle/tests` content if present.
- Do not evaluate missing oracle coverage as a defect.
- Do not propose product specifications that are not already present in oracle.
- Do not evaluate ROUTING.md correctness.

ID rules:
- contradictions ids: CNTR-001, CNTR-002, ...
- issues ids: ISSUE-001, ISSUE-002, ...
"""

    schema_version: str
    contradictions: list[OracleContradiction]
    issues: list[OracleIssue]
    self_check_notes: list[str]

    @field_validator("schema_version")
    @classmethod
    def _validate_schema_version(cls, value: str) -> str:
        """oracle eval schema version を現行値に固定する."""
        # schema_version は運用上の固定値なので、生成指示だけでなく再検証でも保証する。
        if value != "1":
            raise ValueError('schema_version must be "1".')
        return value


def render_oracle_eval_report(report: OracleEvalReport) -> str:
    """
    OracleEvalReport から人間閲覧用 Markdown を生成する。
    """
    # OracleEvalReport の各フィールドを人間閲覧用 section に対応付ける。
    return render_document(
        title="tgbt eval oracle",
        metadata=[
            render_metadata_item("schema_version", report.schema_version),
        ],
        sections=[
            MarkdownSection(
                title="Contradictions",
                body=render_id_text_items(report.contradictions),
            ),
            MarkdownSection(
                title="Issues",
                body=render_id_text_items(report.issues),
            ),
            MarkdownSection(
                title="Self Check Notes",
                body=render_plain_items(report.self_check_notes),
            ),
        ],
    )
