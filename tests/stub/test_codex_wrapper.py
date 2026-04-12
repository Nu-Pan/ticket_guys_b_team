"""Codex wrapper の `plan_drafting` 実装を検証する。"""

import json
from pathlib import Path
import subprocess
from typing import cast

import pytest

from src.codex_common import CodexCliMode
from src import codex_wrapper, env_runtime, plan_drafting, state_io


def test_execute_live_builds_expected_argv_and_saves_redacted_session_record(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """live 実行が argv を組み立て、redacted session record を保存する。"""

    _ensure_repo_local_runtime(tmp_path)
    request = codex_wrapper.CodexCliRequest(
        plan_id="plan-20260401-001",
        plan_revision=1,
        ticket_id=None,
        run_id=None,
        codex_call_id="call-0001",
        call_purpose=plan_drafting.CALL_PURPOSE,
        codex_cli_mode=CodexCliMode.LIVE,
        cwd=str(tmp_path),
        prompt_text="Authorization: Bearer sk-abcdefghijklmnopqrstuvwxyz123456",
    )
    seen_argv: list[str] = []

    def fake_run(
        argv: list[str],
        *,
        capture_output: bool,
        text: bool,
        check: bool,
        env: dict[str, str],
    ) -> subprocess.CompletedProcess[str]:
        assert capture_output is True
        assert text is True
        assert check is False
        assert env["CODEX_HOME"] == str(tmp_path / ".tgbt/.codex")
        seen_argv[:] = argv
        assert "--profile" in argv
        assert argv[argv.index("--profile") + 1] == env_runtime.PROFILE_DRAFTING
        assert "--model" not in argv
        assert "-c" not in argv
        assert "--output-schema" in argv
        assert "--output-last-message" in argv
        assert "--cd" in argv

        schema_path = Path(argv[argv.index("--output-schema") + 1])
        last_message_path = Path(argv[argv.index("--output-last-message") + 1])
        assert schema_path.exists()
        payload = {
            "schema_name": plan_drafting.CALL_PURPOSE,
            "schema_version": 1,
            "call_purpose": plan_drafting.CALL_PURPOSE,
            "summary": "live payload",
            "title": "live title",
            "sections": {
                "purpose": "目的 text",
                "out_of_scope": "- scope",
                "deliverables": "- deliverable",
                "constraints": "api_key: super-secret",
                "acceptance_criteria": "- accepted",
                "open_questions": "- none",
                "risks": "- redaction",
                "execution_strategy": "- strategy",
            },
        }
        last_message_path.write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(
            argv,
            0,
            stdout="Authorization: Bearer sk-abcdefghijklmnopqrstuvwxyz123456",
            stderr="token=super-secret",
        )

    monkeypatch.setattr(codex_wrapper.subprocess, "run", fake_run)

    result = codex_wrapper.execute(request)

    assert seen_argv[0:2] == ["codex", "exec"]
    assert (tmp_path / ".tgbt/.codex/config.toml").read_text(encoding="utf-8") == (
        env_runtime.render_runtime_config(tmp_path)
    )
    assert (tmp_path / ".tgbt/instructions.md").read_text(encoding="utf-8") == (
        env_runtime.render_runtime_instructions(tmp_path)
    )
    assert result.codex_cli_mode is CodexCliMode.LIVE
    assert result.codex_profile == env_runtime.PROFILE_DRAFTING
    assert result.resolved_model == env_runtime.DEFAULT_PROFILE_MODEL
    assert result.resolved_reasoning_effort == "high"
    assert result.session_record_path == str(
        tmp_path / ".tgbt/codex/plan-20260401-001-rev-1-call-0001-plan_drafting.json"
    )
    assert "<REDACTED:AUTH_CREDENTIAL>" in result.stdout
    assert "<REDACTED:SECRET>" in result.stderr
    sections = cast(dict[str, str], result.business_output["sections"])
    assert "<REDACTED:SECRET>" in sections["constraints"]
    assert "AUTH_CREDENTIAL" in result.redaction_report

    session_record = json.loads(Path(result.session_record_path).read_text(encoding="utf-8"))
    assert session_record["request"]["prompt_text"] == "<REDACTED:AUTH_CREDENTIAL>"
    assert session_record["request"]["codex_profile"] == env_runtime.PROFILE_DRAFTING
    assert session_record["request"]["resolved_model"] == env_runtime.DEFAULT_PROFILE_MODEL
    assert session_record["request"]["resolved_reasoning_effort"] == "high"
    assert "<REDACTED:SECRET>" in session_record["result"]["stderr"]
    assert session_record["result"]["codex_profile"] == env_runtime.PROFILE_DRAFTING
    assert session_record["result"]["resolved_model"] == env_runtime.DEFAULT_PROFILE_MODEL
    assert session_record["result"]["resolved_reasoning_effort"] == "high"
    assert session_record["result"]["returncode"] == 0
    assert session_record["result"]["session_record_path"] == result.session_record_path
    assert session_record["result"]["generated_artifacts"] == [result.session_record_path]


def test_execute_live_surfaces_cli_failure_before_payload_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """非 0 終了時は JSON 不在より先に CLI failure を報告する。"""

    _ensure_repo_local_runtime(tmp_path)
    request = codex_wrapper.CodexCliRequest(
        plan_id="plan-20260401-001",
        plan_revision=1,
        ticket_id=None,
        run_id=None,
        codex_call_id="call-0001",
        call_purpose=plan_drafting.CALL_PURPOSE,
        codex_cli_mode=CodexCliMode.LIVE,
        cwd=str(tmp_path),
        prompt_text="live prompt",
    )

    def fake_run(
        argv: list[str],
        *,
        capture_output: bool,
        text: bool,
        check: bool,
        env: dict[str, str],
    ) -> subprocess.CompletedProcess[str]:
        assert capture_output is True
        assert text is True
        assert check is False
        assert env["CODEX_HOME"] == str(tmp_path / ".tgbt/.codex")
        return subprocess.CompletedProcess(
            argv,
            1,
            stdout="",
            stderr=(
                "OpenAI Codex v0.118.0 (research preview)\n"
                "ERROR: {\n"
                '  "type": "error",\n'
                '  "error": {\n'
                '    "message": "Invalid schema for response_format '
                '\'codex_output_schema\': In context=(\'properties\', '
                '\'schema_name\'), schema must have a \'type\' key."\n'
                "  }\n"
                "}\n"
            ),
        )

    monkeypatch.setattr(codex_wrapper.subprocess, "run", fake_run)

    with pytest.raises(
        codex_wrapper.CodexExecutionError,
        match=r"codex exec failed with returncode 1: stderr=.*schema must have a 'type' key",
    ):
        codex_wrapper.execute(request)

    session_record_path = (
        tmp_path / ".tgbt/codex/plan-20260401-001-rev-1-call-0001-plan_drafting.json"
    )
    session_record = json.loads(session_record_path.read_text(encoding="utf-8"))
    assert session_record["result"]["returncode"] == 1
    assert session_record["result"]["stop_reason"] == "codex_exec_failed"
    assert "schema must have a 'type' key" in session_record["result"]["stderr"]


def test_execute_live_fails_fast_when_repo_local_runtime_is_illegal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """live 実行前に runtime 不正を検知し、subprocess を起動しない。"""

    request = codex_wrapper.CodexCliRequest(
        plan_id="plan-20260401-001",
        plan_revision=1,
        ticket_id=None,
        run_id=None,
        codex_call_id="call-0001",
        call_purpose=plan_drafting.CALL_PURPOSE,
        codex_cli_mode=CodexCliMode.LIVE,
        cwd=str(tmp_path),
        prompt_text="live prompt",
    )

    def fail_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise AssertionError("subprocess.run must not be called")

    monkeypatch.setattr(codex_wrapper.subprocess, "run", fail_run)

    with pytest.raises(
        codex_wrapper.IllegalRuntimeError,
        match=r"repo-local Codex runtime is illegal; run `tgbt env` first:",
    ):
        codex_wrapper.execute(request)


def test_execute_stub_replays_saved_record(tmp_path: Path) -> None:
    """stub 実行が source record を strict replay する。"""

    request = _build_request(tmp_path, prompt_text="stub prompt", codex_call_id="call-0001")
    assert request.stub_record_path is not None
    path = tmp_path / request.stub_record_path
    _write_stub_record(path, request=request, title="stub title")

    result = codex_wrapper.execute(request)

    assert result.codex_cli_mode is CodexCliMode.STUB
    assert result.session_record_path == request.stub_record_path
    assert result.replayed_from == request.stub_record_path
    assert result.generated_artifacts == [request.stub_record_path]
    assert result.business_output["title"] == "stub title"


def test_execute_stub_rejects_request_mismatch(tmp_path: Path) -> None:
    """strict replay request 不一致を拒否する。"""

    request = _build_request(tmp_path, prompt_text="stub prompt", codex_call_id="call-0001")
    assert request.stub_record_path is not None
    path = tmp_path / request.stub_record_path
    _write_stub_record(path, request=request, title="stub title")

    mismatched_request = _build_request(
        tmp_path,
        prompt_text="different prompt",
        codex_call_id="call-0001",
    )

    with pytest.raises(codex_wrapper.StubReplayMismatchError):
        codex_wrapper.execute(mismatched_request)


def test_summarize_error_text_prefers_message_line() -> None:
    """stderr 要約は banner ではなく message 行を優先する。"""

    summary = codex_wrapper._summarize_error_text(
        (
            "OpenAI Codex v0.118.0 (research preview)\n"
            "ERROR: {\n"
            '  "message": "Invalid schema for response_format '
            '\'codex_output_schema\': schema must have a \'type\' key."\n'
            "}\n"
        )
    )

    assert "schema must have a 'type' key" in summary


def _build_request(tmp_path: Path, *, prompt_text: str, codex_call_id: str) -> codex_wrapper.CodexCliRequest:
    """共通 request を作る。"""

    return codex_wrapper.CodexCliRequest(
        plan_id="plan-20260401-001",
        plan_revision=1,
        ticket_id=None,
        run_id=None,
        codex_call_id=codex_call_id,
        call_purpose=plan_drafting.CALL_PURPOSE,
        codex_cli_mode=CodexCliMode.STUB,
        cwd=str(tmp_path),
        prompt_text=prompt_text,
        stub_record_path=str(
            tmp_path / ".tgbt/codex/plan-20260401-001-rev-1-call-0001-plan_drafting.json"
        ),
    )


def _write_stub_record(
    path: Path,
    *,
    request: codex_wrapper.CodexCliRequest,
    title: str,
) -> None:
    """strict replay 用 session record を作る。"""

    payload = {
        "schema_name": plan_drafting.CALL_PURPOSE,
        "schema_version": 1,
        "call_purpose": plan_drafting.CALL_PURPOSE,
        "summary": "stub payload",
        "title": title,
        "sections": {
            "purpose": "目的",
            "out_of_scope": "- scope",
            "deliverables": "- deliverable",
            "constraints": "- constraints",
            "acceptance_criteria": "- acceptance",
            "open_questions": "- none",
            "risks": "- risks",
            "execution_strategy": "- strategy",
        },
    }
    storage_request, _ = codex_wrapper.redact_request_for_storage(
        codex_wrapper.build_storage_request(request)
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "plan_id": request.plan_id,
                "plan_revision": request.plan_revision,
                "ticket_id": request.ticket_id,
                "run_id": request.run_id,
                "codex_call_id": request.codex_call_id,
                "call_purpose": request.call_purpose,
                "codex_cli_mode": "live",
                "request": storage_request,
                "result": {
                    "plan_id": request.plan_id,
                    "plan_revision": request.plan_revision,
                    "ticket_id": request.ticket_id,
                    "run_id": request.run_id,
                    "codex_call_id": request.codex_call_id,
                    "call_purpose": request.call_purpose,
                    "codex_cli_mode": "live",
                    "codex_profile": env_runtime.PROFILE_DRAFTING,
                    "resolved_model": env_runtime.DEFAULT_PROFILE_MODEL,
                    "resolved_reasoning_effort": "high",
                    "returncode": 0,
                    "stdout": "",
                    "stderr": "",
                    "last_message_text": codex_wrapper.canonicalize_json(payload),
                    "business_output": payload,
                    "generated_artifacts": [str(path)],
                    "stop_reason": "completed",
                    "session_record_path": str(path),
                    "replayed_from": None,
                    "redaction_report": {},
                },
                "saved_at": state_io.current_timestamp(),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _ensure_repo_local_runtime(repo_root: Path) -> None:
    """live 実行用の repo-local runtime を合法状態で用意する。"""

    env_runtime.regenerate_repo_local_runtime(repo_root)
