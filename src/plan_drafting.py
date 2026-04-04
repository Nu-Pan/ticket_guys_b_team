"""`plan_drafting` payload と prompt を扱う。"""

from dataclasses import dataclass
import json

from . import state_io


CALL_PURPOSE = "plan_drafting"
SECTION_KEY_ORDER = (
    "purpose",
    "out_of_scope",
    "deliverables",
    "constraints",
    "acceptance_criteria",
    "open_questions",
    "risks",
    "execution_strategy",
)
SECTION_KEY_TO_HEADING = {
    "purpose": "目的",
    "out_of_scope": "スコープ外",
    "deliverables": "成果物",
    "constraints": "制約",
    "acceptance_criteria": "受け入れ条件",
    "open_questions": "未確定事項",
    "risks": "想定リスク",
    "execution_strategy": "実行方針",
}
JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "schema_name",
        "schema_version",
        "call_purpose",
        "summary",
        "title",
        "sections",
    ],
    "properties": {
        "schema_name": {"type": "string", "const": CALL_PURPOSE},
        "schema_version": {"type": "integer", "const": 1},
        "call_purpose": {"type": "string", "const": CALL_PURPOSE},
        "summary": {"type": "string"},
        "title": {"type": "string"},
        "sections": {
            "type": "object",
            "additionalProperties": False,
            "required": list(SECTION_KEY_ORDER),
            "properties": {
                key: {"type": "string"}
                for key in SECTION_KEY_ORDER
            },
        },
    },
}


class PlanDraftingValidationError(ValueError):
    """`plan_drafting` payload の検証失敗。"""


@dataclass(frozen=True)
class PlanDraftingPayload:
    """`plan_drafting` payload の正規化済み表現。"""

    summary: str
    title: str
    sections: dict[str, str]


def build_prompt(
    *,
    request_text: str,
    plan_id: str,
    plan_revision: int,
    existing_plan: state_io.PlanDocument | None,
) -> str:
    """Codex へ渡す `plan_drafting` prompt を構築する。"""

    context = {
        "plan_id": plan_id,
        "plan_revision": plan_revision,
        "request_text": request_text,
        "existing_plan": None,
    }
    if existing_plan is not None:
        context["existing_plan"] = {
            "title": existing_plan.metadata["title"],
            "status": existing_plan.metadata["status"],
            "sections": existing_plan.sections,
        }

    schema = {
        "schema_name": CALL_PURPOSE,
        "schema_version": 1,
        "call_purpose": CALL_PURPOSE,
        "summary": "short summary",
        "title": "plan title",
        "sections": {
            key: "string"
            for key in SECTION_KEY_ORDER
        },
    }

    prompt = {
        "role": "ticket_guys_b_team plan drafting agent",
        "instructions": [
            "最終メッセージは単一の JSON object のみを返すこと。",
            "Markdown fence、説明文、前置き、後書きを付けないこと。",
            "call_purpose は必ず plan_drafting にすること。",
            "canonical markdown 全文を返さず、title と sections proposal のみ返すこと。",
            "sections は purpose, out_of_scope, deliverables, constraints, acceptance_criteria, open_questions, risks, execution_strategy の 8 keys をすべて含めること。",
            "既存 Plan がある場合は、今回の更新指示を反映した Plan 全体を再構成すること。",
            "内容は日本語で記述すること。",
        ],
        "required_output_schema": schema,
        "context": context,
    }
    return json.dumps(prompt, ensure_ascii=False, indent=2)


def validate_payload(payload: object) -> PlanDraftingPayload:
    """`plan_drafting` payload を検証する。"""

    if not isinstance(payload, dict):
        raise PlanDraftingValidationError("plan_drafting payload must be an object")

    if payload.get("schema_name") != CALL_PURPOSE:
        raise PlanDraftingValidationError("schema_name must be plan_drafting")
    if payload.get("schema_version") != 1:
        raise PlanDraftingValidationError("schema_version must be 1")
    if payload.get("call_purpose") != CALL_PURPOSE:
        raise PlanDraftingValidationError("call_purpose must be plan_drafting")

    summary = payload.get("summary")
    title = payload.get("title")
    sections = payload.get("sections")

    if not isinstance(summary, str):
        raise PlanDraftingValidationError("summary must be a string")
    if not isinstance(title, str) or not title.strip():
        raise PlanDraftingValidationError("title must be a non-empty string")
    if not isinstance(sections, dict):
        raise PlanDraftingValidationError("sections must be an object")

    normalized_sections: dict[str, str] = {}
    for key in SECTION_KEY_ORDER:
        value = sections.get(key)
        if not isinstance(value, str):
            raise PlanDraftingValidationError(f"sections.{key} must be a string")
        normalized_sections[key] = value

    extra_keys = set(sections) - set(SECTION_KEY_ORDER)
    if extra_keys:
        raise PlanDraftingValidationError(
            f"sections contains unsupported keys: {sorted(extra_keys)}"
        )

    return PlanDraftingPayload(
        summary=summary,
        title=title.strip(),
        sections=normalized_sections,
    )


def payload_to_plan_sections(payload: PlanDraftingPayload) -> dict[str, str]:
    """payload を canonical Plan section 名へ写像する。"""

    return {
        SECTION_KEY_TO_HEADING[key]: payload.sections[key].strip()
        for key in SECTION_KEY_ORDER
    }
