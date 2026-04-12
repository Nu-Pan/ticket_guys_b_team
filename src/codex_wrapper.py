"""Codex CLI wrapper の `plan_drafting` 実装。"""

from collections.abc import Mapping
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from .codex_common import CodexCliMode
from . import env_runtime, plan_drafting, state_io


SESSION_RECORD_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class CodexCliRequest:
    """Codex CLI wrapper への request。"""

    plan_id: str
    plan_revision: int
    ticket_id: str | None
    run_id: str | None
    codex_call_id: str
    call_purpose: str
    codex_cli_mode: CodexCliMode
    cwd: str
    prompt_text: str
    stub_record_path: str | None = None


@dataclass(frozen=True)
class CodexCliResult:
    """Codex CLI wrapper の成功結果。"""

    plan_id: str
    plan_revision: int
    ticket_id: str | None
    run_id: str | None
    codex_call_id: str
    call_purpose: str
    codex_cli_mode: CodexCliMode
    codex_profile: str
    resolved_model: str
    resolved_reasoning_effort: str
    returncode: int
    stdout: str
    stderr: str
    last_message_text: str
    business_output: dict[str, object]
    session_record_path: str
    replayed_from: str | None
    generated_artifacts: list[str]
    stop_reason: str
    redaction_report: dict[str, int]


class CodexWrapperError(RuntimeError):
    """wrapper 共通エラー。"""


class CodexSpawnError(CodexWrapperError):
    """process spawn 失敗。"""


class CodexExecutionError(CodexWrapperError):
    """Codex CLI 実行失敗。"""


class CodexBusinessOutputError(CodexWrapperError):
    """business output 不正。"""


class StubRecordRequiredError(CodexWrapperError):
    """stub source path 未指定。"""


class StubRecordNotFoundError(CodexWrapperError):
    """stub source 不足。"""


class StubRecordSchemaError(CodexWrapperError):
    """stub source schema 不正。"""


class StubReplayMismatchError(CodexWrapperError):
    """strict replay 不一致。"""


class SessionRecordWriteError(CodexWrapperError):
    """session record 保存失敗。"""


class IllegalRuntimeError(CodexWrapperError):
    """repo-local runtime が live 実行要件を満たさない。"""


def build_storage_request(request: CodexCliRequest) -> dict[str, object]:
    """保存用 canonical request を構築する。"""

    profile_spec = _resolve_profile_spec(request.call_purpose)
    return {
        "plan_id": request.plan_id,
        "plan_revision": request.plan_revision,
        "ticket_id": request.ticket_id,
        "run_id": request.run_id,
        "codex_call_id": request.codex_call_id,
        "call_purpose": request.call_purpose,
        "cwd": request.cwd,
        "prompt_text": request.prompt_text,
        "codex_profile": profile_spec.name,
        "resolved_model": profile_spec.model,
        "resolved_reasoning_effort": profile_spec.model_reasoning_effort,
    }


def execute(request: CodexCliRequest) -> CodexCliResult:
    """request に従って live/stub を実行する。"""

    _validate_request(request)
    if request.codex_cli_mode is CodexCliMode.LIVE:
        return _execute_live(request)
    return _execute_stub(request)


def _validate_request(request: CodexCliRequest) -> None:
    """request の基本妥当性を検証する。"""

    if request.call_purpose != plan_drafting.CALL_PURPOSE:
        raise CodexBusinessOutputError("unsupported call_purpose")
    if not Path(request.cwd).is_absolute():
        raise CodexBusinessOutputError("cwd must be an absolute path")
    if request.ticket_id is not None:
        raise CodexBusinessOutputError("plan_drafting requires ticket_id=None")
    if request.run_id is not None:
        raise CodexBusinessOutputError("plan_drafting requires run_id=None")
    if request.codex_cli_mode is CodexCliMode.STUB and not request.stub_record_path:
        raise StubRecordRequiredError("stub_record_path is required in stub mode")
    if request.stub_record_path is not None and not Path(request.stub_record_path).is_absolute():
        raise CodexBusinessOutputError("stub_record_path must be an absolute path")
    _resolve_profile_spec(request.call_purpose)


def _execute_live(request: CodexCliRequest) -> CodexCliResult:
    """live 実行を行う。"""

    repo_root = Path(request.cwd)
    profile_spec = _resolve_profile_spec(request.call_purpose)
    try:
        env_runtime.require_legal_live_runtime(repo_root)
    except RuntimeError as error:
        raise IllegalRuntimeError(str(error)) from error

    session_record_path = state_io.plan_drafting_session_record_relative_path(
        repo_root,
        plan_id=request.plan_id,
        plan_revision=request.plan_revision,
        codex_call_id=request.codex_call_id,
    )
    session_record_abspath = repo_root / session_record_path

    with tempfile.TemporaryDirectory(prefix="tgbt-plan-drafting-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        schema_path = temp_dir / "plan_drafting.schema.json"
        last_message_path = temp_dir / "last_message.json"
        schema_path.write_text(
            json.dumps(plan_drafting.JSON_SCHEMA, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        argv = [
            "codex",
            "exec",
            "--profile",
            profile_spec.name,
            "--output-schema",
            str(schema_path),
            "--output-last-message",
            str(last_message_path),
            "--cd",
            request.cwd,
            request.prompt_text,
        ]
        runtime_env = dict(os.environ)
        runtime_env["CODEX_HOME"] = state_io.absolute_path_string(
            state_io.repo_local_codex_home(repo_root)
        )

        try:
            completed = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                check=False,
                env=runtime_env,
            )
        except OSError as error:
            raise CodexSpawnError(f"failed to spawn codex exec: {error}") from error

        raw_last_message = ""
        if last_message_path.exists():
            raw_last_message = last_message_path.read_text(encoding="utf-8").strip()

        payload: plan_drafting.PlanDraftingPayload | None = None
        payload_error: json.JSONDecodeError | plan_drafting.PlanDraftingValidationError | None = None
        try:
            payload = plan_drafting.validate_payload(_parse_json_object(raw_last_message))
        except (json.JSONDecodeError, plan_drafting.PlanDraftingValidationError) as error:
            payload_error = error

        if completed.returncode != 0:
            _write_session_record(
                request=request,
                session_record_abspath=session_record_abspath,
                stdout=completed.stdout,
                stderr=completed.stderr,
                raw_last_message=raw_last_message,
                business_output=_payload_to_business_output(payload),
                stop_reason="codex_exec_failed",
                returncode=completed.returncode,
            )
            raise CodexExecutionError(
                _format_execution_error(
                    returncode=completed.returncode,
                    stderr=completed.stderr,
                    payload_error=payload_error,
                )
            )

        if payload_error is not None:
            _write_session_record(
                request=request,
                session_record_abspath=session_record_abspath,
                stdout=completed.stdout,
                stderr=completed.stderr,
                raw_last_message=raw_last_message,
                business_output=None,
                stop_reason="invalid_business_output",
                returncode=completed.returncode,
            )
            raise CodexBusinessOutputError(
                f"plan_drafting payload validation failed: {payload_error}"
            ) from payload_error

        assert payload is not None

        result = _build_success_result(
            request=request,
            stdout=completed.stdout,
            stderr=completed.stderr,
            payload=payload,
            session_record_path=state_io.absolute_path_string(session_record_abspath),
            replayed_from=None,
        )
        _write_session_record(
            request=request,
            session_record_abspath=session_record_abspath,
            stdout=completed.stdout,
            stderr=completed.stderr,
            raw_last_message=raw_last_message,
            business_output=_payload_to_business_output(payload),
            stop_reason=result.stop_reason,
            returncode=completed.returncode,
        )
        return result


def _execute_stub(request: CodexCliRequest) -> CodexCliResult:
    """stub 実行を行う。"""

    assert request.stub_record_path is not None
    stub_record_abspath = Path(request.stub_record_path)
    if not stub_record_abspath.exists():
        raise StubRecordNotFoundError(
            f"stub record was not found: {request.stub_record_path}"
        )

    try:
        record = json.loads(stub_record_abspath.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StubRecordSchemaError(
            f"failed to load stub record: {request.stub_record_path}"
        ) from error

    if not isinstance(record, dict):
        raise StubRecordSchemaError("stub record must be a JSON object")

    source_request = record.get("request")
    source_result = record.get("result")
    if not isinstance(source_request, dict) or not isinstance(source_result, dict):
        raise StubRecordSchemaError("stub record request/result must be objects")

    current_request = redact_request_for_storage(build_storage_request(request))[0]
    comparable_source_request = dict(source_request)
    if comparable_source_request != current_request:
        raise StubReplayMismatchError("strict replay request mismatch")

    for identity_field in (
        "plan_id",
        "plan_revision",
        "ticket_id",
        "run_id",
        "codex_call_id",
        "call_purpose",
    ):
        if record.get(identity_field) != getattr(request, identity_field):
            raise StubReplayMismatchError(
                f"strict replay identity mismatch: {identity_field}"
            )

    try:
        payload = plan_drafting.validate_payload(source_result.get("business_output"))
    except plan_drafting.PlanDraftingValidationError as error:
        raise StubRecordSchemaError(
            "stub record business_output is invalid"
        ) from error

    redaction_report = source_result.get("redaction_report")
    if not isinstance(redaction_report, dict):
        raise StubRecordSchemaError("stub record redaction_report must be an object")
    profile_spec = _resolve_profile_spec(request.call_purpose)
    if source_result.get("codex_profile") != profile_spec.name:
        raise StubRecordSchemaError("stub record codex_profile is invalid")
    if source_result.get("resolved_model") != profile_spec.model:
        raise StubRecordSchemaError("stub record resolved_model is invalid")
    if source_result.get("resolved_reasoning_effort") != profile_spec.model_reasoning_effort:
        raise StubRecordSchemaError(
            "stub record resolved_reasoning_effort is invalid"
        )

    stdout = source_result.get("stdout")
    stderr = source_result.get("stderr")
    last_message_text = source_result.get("last_message_text")
    if not isinstance(stdout, str) or not isinstance(stderr, str):
        raise StubRecordSchemaError("stub record stdout/stderr must be strings")
    if not isinstance(last_message_text, str):
        raise StubRecordSchemaError("stub record last_message_text must be a string")

    return CodexCliResult(
        plan_id=request.plan_id,
        plan_revision=request.plan_revision,
        ticket_id=None,
        run_id=None,
        codex_call_id=request.codex_call_id,
        call_purpose=request.call_purpose,
        codex_cli_mode=CodexCliMode.STUB,
        codex_profile=profile_spec.name,
        resolved_model=profile_spec.model,
        resolved_reasoning_effort=profile_spec.model_reasoning_effort,
        returncode=int(source_result.get("returncode", 0)),
        stdout=stdout,
        stderr=stderr,
        last_message_text=last_message_text,
        business_output={
            "schema_name": plan_drafting.CALL_PURPOSE,
            "schema_version": 1,
            "call_purpose": plan_drafting.CALL_PURPOSE,
            "summary": payload.summary,
            "title": payload.title,
            "sections": payload.sections,
        },
        session_record_path=state_io.absolute_path_string(stub_record_abspath),
        replayed_from=state_io.absolute_path_string(stub_record_abspath),
        generated_artifacts=[state_io.absolute_path_string(stub_record_abspath)],
        stop_reason=str(source_result.get("stop_reason", "stub_replay")),
        redaction_report={str(key): int(value) for key, value in redaction_report.items()},
    )


def _build_success_result(
    *,
    request: CodexCliRequest,
    stdout: str,
    stderr: str,
    payload: plan_drafting.PlanDraftingPayload,
    session_record_path: str,
    replayed_from: str | None,
) -> CodexCliResult:
    """成功 result を構築する。"""

    profile_spec = _resolve_profile_spec(request.call_purpose)
    business_output = {
        "schema_name": plan_drafting.CALL_PURPOSE,
        "schema_version": 1,
        "call_purpose": plan_drafting.CALL_PURPOSE,
        "summary": payload.summary,
        "title": payload.title,
        "sections": payload.sections,
    }
    redacted_stdout, stdout_report = redact_text(stdout)
    redacted_stderr, stderr_report = redact_text(stderr)
    redacted_output, output_report = redact_business_output(business_output)
    assert redacted_output is not None
    last_message_text = canonicalize_json(redacted_output)
    redaction_report = merge_redaction_reports(
        stdout_report,
        stderr_report,
        output_report,
    )
    return CodexCliResult(
        plan_id=request.plan_id,
        plan_revision=request.plan_revision,
        ticket_id=None,
        run_id=None,
        codex_call_id=request.codex_call_id,
        call_purpose=request.call_purpose,
        codex_cli_mode=request.codex_cli_mode,
        codex_profile=profile_spec.name,
        resolved_model=profile_spec.model,
        resolved_reasoning_effort=profile_spec.model_reasoning_effort,
        returncode=0,
        stdout=redacted_stdout,
        stderr=redacted_stderr,
        last_message_text=last_message_text,
        business_output=redacted_output,
        session_record_path=session_record_path,
        replayed_from=replayed_from,
        generated_artifacts=[session_record_path],
        stop_reason="completed",
        redaction_report=redaction_report,
    )


def _write_session_record(
    *,
    request: CodexCliRequest,
    session_record_abspath: Path,
    stdout: str,
    stderr: str,
    raw_last_message: str,
    business_output: dict[str, object] | None,
    stop_reason: str,
    returncode: int,
) -> None:
    """session record を保存する。"""

    profile_spec = _resolve_profile_spec(request.call_purpose)
    redacted_request, request_report = redact_request_for_storage(build_storage_request(request))
    redacted_stdout, stdout_report = redact_text(stdout)
    redacted_stderr, stderr_report = redact_text(stderr)
    redacted_last_message, last_message_report = redact_text(raw_last_message)
    redacted_output, output_report = redact_business_output(business_output)
    if redacted_output is not None:
        redacted_last_message = canonicalize_json(redacted_output)
    redaction_report = merge_redaction_reports(
        request_report,
        stdout_report,
        stderr_report,
        last_message_report,
        output_report,
    )

    record = {
        "schema_version": SESSION_RECORD_SCHEMA_VERSION,
        "plan_id": request.plan_id,
        "plan_revision": request.plan_revision,
        "ticket_id": request.ticket_id,
        "run_id": request.run_id,
        "codex_call_id": request.codex_call_id,
        "call_purpose": request.call_purpose,
        "codex_cli_mode": request.codex_cli_mode.value,
        "request": redacted_request,
        "result": {
            "plan_id": request.plan_id,
            "plan_revision": request.plan_revision,
            "ticket_id": request.ticket_id,
            "run_id": request.run_id,
            "codex_call_id": request.codex_call_id,
            "call_purpose": request.call_purpose,
            "codex_cli_mode": request.codex_cli_mode.value,
            "codex_profile": profile_spec.name,
            "resolved_model": profile_spec.model,
            "resolved_reasoning_effort": profile_spec.model_reasoning_effort,
            "returncode": returncode,
            "stdout": redacted_stdout,
            "stderr": redacted_stderr,
            "last_message_text": redacted_last_message,
            "business_output": redacted_output,
            "generated_artifacts": [
                state_io.absolute_path_string(session_record_abspath)
            ],
            "stop_reason": stop_reason,
            "session_record_path": state_io.absolute_path_string(session_record_abspath),
            "replayed_from": None,
            "redaction_report": redaction_report,
        },
        "saved_at": state_io.current_timestamp(),
    }

    try:
        state_io.write_text_atomically(
            session_record_abspath,
            json.dumps(record, ensure_ascii=False, indent=2) + "\n",
            create_only=True,
        )
    except OSError as error:
        raise SessionRecordWriteError(
            f"failed to write session record: {session_record_abspath}"
        ) from error


def redact_request_for_storage(
    request_dict: dict[str, object],
) -> tuple[dict[str, object], dict[str, int]]:
    """保存用 request に redaction を適用する。"""

    prompt_text = request_dict["prompt_text"]
    assert isinstance(prompt_text, str)
    redacted_prompt_text, prompt_report = redact_text(prompt_text)
    redacted_request = dict(request_dict)
    redacted_request["prompt_text"] = redacted_prompt_text
    return redacted_request, prompt_report


def redact_business_output(
    business_output: dict[str, object] | None,
) -> tuple[dict[str, object] | None, dict[str, int]]:
    """business_output 配下の string leaf を redaction する。"""

    if business_output is None:
        return None, {}
    redacted_output, report = _redact_object(business_output)
    assert isinstance(redacted_output, dict)
    return redacted_output, report


def _redact_object(value: object) -> tuple[object, dict[str, int]]:
    """任意 object の string leaf を redaction する。"""

    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        output_list: list[object] = []
        report: dict[str, int] = {}
        for item in value:
            redacted_item, item_report = _redact_object(item)
            output_list.append(redacted_item)
            report = merge_redaction_reports(report, item_report)
        return output_list, report
    if isinstance(value, Mapping):
        output_dict: dict[str, object] = {}
        report = {}
        for key, item in value.items():
            redacted_item, item_report = _redact_object(item)
            output_dict[str(key)] = redacted_item
            report = merge_redaction_reports(report, item_report)
        return output_dict, report
    return value, {}


def merge_redaction_reports(*reports: dict[str, int]) -> dict[str, int]:
    """redaction report を合成する。"""

    merged: dict[str, int] = {}
    for report in reports:
        for key, value in report.items():
            merged[key] = merged.get(key, 0) + value
    return merged


def _payload_to_business_output(
    payload: plan_drafting.PlanDraftingPayload | None,
) -> dict[str, object] | None:
    """payload を session record 保存用 dict へ戻す。"""

    if payload is None:
        return None
    return {
        "schema_name": plan_drafting.CALL_PURPOSE,
        "schema_version": 1,
        "call_purpose": plan_drafting.CALL_PURPOSE,
        "summary": payload.summary,
        "title": payload.title,
        "sections": payload.sections,
    }


def _format_execution_error(
    *,
    returncode: int,
    stderr: str,
    payload_error: json.JSONDecodeError | plan_drafting.PlanDraftingValidationError | None,
) -> str:
    """Codex CLI 実行失敗を人間向けに要約する。"""

    detail = f"codex exec failed with returncode {returncode}"
    stderr_summary = _summarize_error_text(stderr)
    if stderr_summary:
        return f"{detail}: stderr={stderr_summary}"
    if payload_error is not None:
        return f"{detail}: last_message was unusable ({payload_error})"
    return detail


def _summarize_error_text(text: str, *, max_length: int = 200) -> str:
    """CLI エラー出力から原因に近い 1 行を要約する。"""

    redacted_text, _ = redact_text(text.strip())
    if not redacted_text:
        return ""

    lines = [line.strip() for line in redacted_text.splitlines() if line.strip()]
    preferred_line = ""
    for line in reversed(lines):
        if '"message":' in line:
            preferred_line = line
            break
    if not preferred_line:
        for line in reversed(lines):
            if "ERROR:" in line:
                preferred_line = line
                break
    if not preferred_line and lines:
        preferred_line = lines[-1]

    if len(preferred_line) <= max_length:
        return preferred_line
    return preferred_line[: max_length - 3] + "..."


def redact_text(text: str) -> tuple[str, dict[str, int]]:
    """spec に従って文字列を redaction する。"""

    patterns = [
        (
            "PEM_PRIVATE_KEY",
            re.compile(
                r"-----BEGIN [^-]+ PRIVATE KEY-----.*?-----END [^-]+ PRIVATE KEY-----",
                re.DOTALL,
            ),
            "<REDACTED:PEM_PRIVATE_KEY>",
        ),
        (
            "AUTH_CREDENTIAL",
            re.compile(r"Authorization:\s*[^\r\n]+|Bearer\s+[A-Za-z0-9._\-]+"),
            "<REDACTED:AUTH_CREDENTIAL>",
        ),
        (
            "COOKIE",
            re.compile(r"(?:Cookie|Set-Cookie):\s*[^\r\n]+"),
            "<REDACTED:COOKIE>",
        ),
        (
            "CREDENTIALS",
            re.compile(r"([A-Za-z][A-Za-z0-9+\-.]*://)([^/\s:@]+:[^/\s@]+)@"),
            r"\1<REDACTED:CREDENTIALS>@",
        ),
        (
            "SECRET",
            re.compile(
                r'((?i:api_key|apikey|token|access_token|refresh_token|secret|client_secret|password|passwd|session)\s*(?:=|:)\s*)(\"[^\"]*\"|\'[^\']*\'|[^\s,]+)'
            ),
            r"\1<REDACTED:SECRET>",
        ),
        (
            "TOKEN",
            re.compile(
                r"sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]+|xox[baprs]-[A-Za-z0-9-]+"
            ),
            "<REDACTED:TOKEN>",
        ),
    ]

    redacted = text
    report: dict[str, int] = {}
    for rule_name, pattern, replacement in patterns:
        redacted, count = pattern.subn(replacement, redacted)
        if count:
            report[rule_name] = report.get(rule_name, 0) + count
    return redacted, report


def canonicalize_json(payload: dict[str, object]) -> str:
    """JSON object を決定的に serialize する。"""

    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _parse_json_object(text: str) -> dict[str, object]:
    """単一 JSON object を parse する。"""

    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise json.JSONDecodeError("top-level JSON must be an object", text, 0)
    return parsed


def _resolve_profile_spec(call_purpose: str) -> env_runtime.CodexProfileSpec:
    """wrapper 実行に使う canonical profile を返す。"""

    try:
        return env_runtime.resolve_profile_spec_for_call_purpose(call_purpose)
    except ValueError as error:
        raise CodexBusinessOutputError(str(error)) from error
