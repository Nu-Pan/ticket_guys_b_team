"""`plan` コマンドの業務処理を扱う。"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re

from .codex_common import CodexCliMode
from . import codex_wrapper, plan_drafting, state_io


PLAN_IMPACT = "no plan file or front matter was created or updated"
PLAN_WRAPPER_IMPACT = (
    "no plan file or front matter was created or updated, but counters or session "
    "records may have changed"
)


@dataclass
class PlanCommandError(Exception):
    """`plan` コマンドの CLI 向け失敗情報。"""

    cause: str
    impact: str
    next_step: str

    def __str__(self) -> str:
        """例外メッセージを返す。"""

        return self.cause


@dataclass(frozen=True)
class PlanCommandResult:
    """`plan` コマンド成功時の出力。"""

    updated_path: str
    plan_revision: int
    status: str
    session_record_path: str


def create_or_update_plan(
    *,
    request_text: str,
    plan_id: str | None,
    codex_cli_mode: CodexCliMode,
) -> PlanCommandResult:
    """Plan file を新規作成または更新する。"""

    normalized_request = request_text.strip()
    if not normalized_request:
        raise PlanCommandError(
            cause="request_text must not be empty",
            impact=PLAN_IMPACT,
            next_step="provide a non-empty plan request and retry the command",
        )

    try:
        repo_root = state_io.get_repository_root()
        state_io.ensure_plan_storage(repo_root)
        with state_io.repository_lock(repo_root, command_name="plan", plan_id=plan_id):
            if plan_id is None:
                target_plan_id = _next_plan_id(repo_root)
                return _create_new_plan(
                    repo_root=repo_root,
                    plan_id=target_plan_id,
                    request_text=normalized_request,
                    codex_cli_mode=codex_cli_mode,
                )

            return _update_existing_plan(
                repo_root=repo_root,
                plan_id=plan_id,
                request_text=normalized_request,
                codex_cli_mode=codex_cli_mode,
            )
    except FileExistsError as error:
        raise PlanCommandError(
            cause="repository lock is already held",
            impact=PLAN_IMPACT,
            next_step="remove a stale repository lock after confirming no other tgbt process is running, then retry",
        ) from error
    except state_io.StateValidationError as error:
        raise PlanCommandError(
            cause=f"state validation failed: {error}",
            impact=PLAN_IMPACT,
            next_step="restore a safe snapshot or fix the invalid state files before retrying",
        ) from error
    except codex_wrapper.CodexWrapperError as error:
        raise _translate_wrapper_error(error) from error
    except OSError as error:
        raise PlanCommandError(
            cause=f"failed to persist plan state: {error}",
            impact=PLAN_IMPACT,
            next_step="check filesystem permissions and retry after restoring a safe snapshot if needed",
        ) from error


def _next_plan_id(repo_root: Path) -> str:
    """当日分の次の `plan_id` を採番する。"""

    today = datetime.now().astimezone().strftime("%Y%m%d")
    pattern = re.compile(rf"^plan-{today}-(\d{{3}})\.md$")
    highest_sequence = 0

    for candidate in state_io.plans_dir(repo_root).glob(f"plan-{today}-*.md"):
        match = pattern.match(candidate.name)
        if match is None:
            continue
        highest_sequence = max(highest_sequence, int(match.group(1)))

    return f"plan-{today}-{highest_sequence + 1:03d}"


def _create_new_plan(
    *,
    repo_root: Path,
    plan_id: str,
    request_text: str,
    codex_cli_mode: CodexCliMode,
) -> PlanCommandResult:
    """新規 Plan を作成する。"""

    plan_revision = 1
    codex_call_id = state_io.allocate_codex_call_id(repo_root)
    session_record_relative_path = state_io.plan_drafting_session_record_relative_path(
        repo_root,
        plan_id=plan_id,
        plan_revision=plan_revision,
        codex_call_id=codex_call_id,
    )
    request = _build_codex_request(
        repo_root=repo_root,
        plan_id=plan_id,
        plan_revision=plan_revision,
        request_text=request_text,
        codex_call_id=codex_call_id,
        codex_cli_mode=codex_cli_mode,
        existing_plan=None,
        session_record_relative_path=session_record_relative_path,
    )
    result = codex_wrapper.execute(request)
    payload = plan_drafting.validate_payload(result.business_output)
    document = _build_plan_document_from_payload(
        plan_id=plan_id,
        plan_revision=plan_revision,
        payload=payload,
        existing_metadata=None,
    )
    plan_path = state_io.plan_path(repo_root, plan_id)
    state_io.write_text_atomically(
        plan_path,
        state_io.render_plan_document(document.metadata, document.sections),
        create_only=True,
    )
    return PlanCommandResult(
        updated_path=state_io.absolute_path_string(plan_path),
        plan_revision=plan_revision,
        status="draft",
        session_record_path=result.session_record_path,
    )


def _update_existing_plan(
    *,
    repo_root: Path,
    plan_id: str,
    request_text: str,
    codex_cli_mode: CodexCliMode,
) -> PlanCommandResult:
    """既存 Plan を更新する。"""

    path = state_io.plan_path(repo_root, plan_id)
    if not path.exists():
        raise PlanCommandError(
            cause=f"plan_id was not found: {plan_id}",
            impact=PLAN_IMPACT,
            next_step="check the target plan_id or create a new plan without --plan-id",
        )

    current_document = state_io.load_plan_document(path)
    current_revision = current_document.metadata["plan_revision"]
    assert isinstance(current_revision, int)
    next_revision = current_revision + 1
    codex_call_id = state_io.allocate_codex_call_id(repo_root)
    session_record_relative_path = state_io.plan_drafting_session_record_relative_path(
        repo_root,
        plan_id=plan_id,
        plan_revision=next_revision,
        codex_call_id=codex_call_id,
    )
    request = _build_codex_request(
        repo_root=repo_root,
        plan_id=plan_id,
        plan_revision=next_revision,
        request_text=request_text,
        codex_call_id=codex_call_id,
        codex_cli_mode=codex_cli_mode,
        existing_plan=current_document,
        session_record_relative_path=session_record_relative_path,
    )
    result = codex_wrapper.execute(request)
    payload = plan_drafting.validate_payload(result.business_output)
    document = _build_plan_document_from_payload(
        plan_id=plan_id,
        plan_revision=next_revision,
        payload=payload,
        existing_metadata=current_document.metadata,
    )
    _delete_active_tickets(repo_root, plan_id=plan_id, plan_revision=current_revision)
    state_io.write_text_atomically(
        path,
        state_io.render_plan_document(document.metadata, document.sections),
        create_only=False,
    )

    return PlanCommandResult(
        updated_path=state_io.absolute_path_string(path),
        plan_revision=next_revision,
        status="draft",
        session_record_path=result.session_record_path,
    )


def _build_codex_request(
    *,
    repo_root: Path,
    plan_id: str,
    plan_revision: int,
    request_text: str,
    codex_call_id: str,
    codex_cli_mode: CodexCliMode,
    existing_plan: state_io.PlanDocument | None,
    session_record_relative_path: str,
) -> codex_wrapper.CodexCliRequest:
    """Codex wrapper request を構築する。"""

    model, reasoning_effort = codex_wrapper.resolve_model_config()
    return codex_wrapper.CodexCliRequest(
        plan_id=plan_id,
        plan_revision=plan_revision,
        ticket_id=None,
        run_id=None,
        codex_call_id=codex_call_id,
        call_purpose=plan_drafting.CALL_PURPOSE,
        codex_cli_mode=codex_cli_mode,
        cwd=str(repo_root),
        prompt_text=plan_drafting.build_prompt(
            request_text=request_text,
            plan_id=plan_id,
            plan_revision=plan_revision,
            existing_plan=existing_plan,
        ),
        model=model,
        reasoning_effort=reasoning_effort,
        stub_record_path=(
            state_io.absolute_path_string(repo_root / session_record_relative_path)
            if codex_cli_mode is CodexCliMode.STUB
            else None
        ),
    )


def _build_plan_document_from_payload(
    *,
    plan_id: str,
    plan_revision: int,
    payload: plan_drafting.PlanDraftingPayload,
    existing_metadata: dict[str, object] | None,
) -> state_io.PlanDocument:
    """payload から Plan document を構築する。"""

    now = state_io.current_timestamp()
    metadata: dict[str, object]
    if existing_metadata is None:
        metadata = {
            "plan_id": plan_id,
            "plan_revision": plan_revision,
            "title": payload.title,
            "status": "draft",
            "created_at": now,
            "updated_at": now,
        }
    else:
        metadata = dict(existing_metadata)
        metadata["plan_revision"] = plan_revision
        metadata["title"] = payload.title
        metadata["status"] = "draft"
        metadata["updated_at"] = now
        metadata.pop("settled_at", None)
        metadata.pop("closure_reason", None)
    return state_io.PlanDocument(
        metadata=metadata,
        sections=plan_drafting.payload_to_plan_sections(payload),
    )


def _delete_active_tickets(repo_root: Path, *, plan_id: str, plan_revision: int) -> None:
    """更新前 revision に属する active Ticket を削除する。"""

    for ticket_path in state_io.tickets_dir(repo_root).glob("*.md"):
        metadata = state_io.load_ticket_metadata(ticket_path)
        if metadata.get("plan_id") != plan_id:
            continue
        if metadata.get("plan_revision") != plan_revision:
            continue
        ticket_path.unlink()

def _translate_wrapper_error(error: codex_wrapper.CodexWrapperError) -> PlanCommandError:
    """wrapper エラーを CLI 向けエラーへ写像する。"""

    if isinstance(
        error,
        (
            codex_wrapper.StubRecordRequiredError,
            codex_wrapper.StubRecordNotFoundError,
            codex_wrapper.StubReplayMismatchError,
            codex_wrapper.StubRecordSchemaError,
        ),
    ):
        next_step = (
            "restore the matching pre-call state and required session record under "
            ".tgbt/codex/, then retry"
        )
    else:
        next_step = (
            "restore a safe snapshot, inspect counters/session records, and retry "
            "the command"
        )

    return PlanCommandError(
        cause=str(error),
        impact=PLAN_WRAPPER_IMPACT,
        next_step=next_step,
    )
