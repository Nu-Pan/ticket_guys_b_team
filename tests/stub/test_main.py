"""CLI インターフェースと `plan` の Codex 草案生成を検証するテスト。"""

from datetime import datetime
import json
from pathlib import Path
import subprocess

import pytest
from typer.testing import CliRunner
import yaml

from src.main import app
from src.codex_common import CodexCliMode
from src import codex_wrapper, plan_drafting, plan_service, state_io


RUNNER = CliRunner()


@pytest.fixture
def isolated_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """repository root 解決を一時ディレクトリへ差し替える。"""

    monkeypatch.setattr(state_io, "get_repository_root", lambda: tmp_path)
    return tmp_path


def test_root_help_lists_only_spec_commands() -> None:
    """ルートヘルプに仕様で公開されたコマンドだけが並ぶことを確認する。"""

    result = RUNNER.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "│ plan" in result.stdout
    assert "│ run" in result.stdout
    assert "│ approve" not in result.stdout
    assert "│ ticket" not in result.stdout
    assert "│ review-queue" not in result.stdout
    assert "│ artifacts" not in result.stdout


def test_removed_commands_fail_as_unknown_commands() -> None:
    """仕様外コマンドが unknown command として拒否されることを確認する。"""

    for command_name in ["approve", "ticket", "review-queue", "artifacts"]:
        result = RUNNER.invoke(app, [command_name])

        assert result.exit_code != 0
        assert f"No such command '{command_name}'." in result.stderr


def test_plan_creates_a_new_plan_file_from_stub_record(
    isolated_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """新規 `plan --codex-cli-mode stub` が session record から Plan を生成する。"""

    plan_id = "plan-20260401-001"
    monkeypatch.setattr(plan_service, "_next_plan_id", lambda repo_root: plan_id)
    request_text = "CLI で plan / run を扱えるようにしたい"
    _write_plan_stub_record(
        isolated_repo,
        plan_id=plan_id,
        plan_revision=1,
        codex_call_id="call-0001",
        request_text=request_text,
        existing_plan=None,
        payload=_plan_payload(
            title="CLI 初期実装",
            purpose="CLI で plan / run を扱えるようにしたい",
        ),
    )

    result = RUNNER.invoke(
        app,
        ["plan", "--codex-cli-mode", "stub", request_text],
    )

    assert result.exit_code == 0
    assert result.stderr == ""
    assert result.stdout.strip().splitlines() == [
        f"Updated: .tgbt/plans/{plan_id}.md",
        "Plan revision: 1",
        "Status: draft",
        "Session record: .tgbt/codex/plan-20260401-001-rev-1-call-0001-plan_drafting.json",
    ]

    plan_path = state_io.plan_path(isolated_repo, plan_id)
    metadata, sections = _load_plan(plan_path)
    assert metadata["title"] == "CLI 初期実装"
    assert metadata["status"] == "draft"
    assert metadata["plan_revision"] == 1
    assert sections["目的"] == "CLI で plan / run を扱えるようにしたい"
    assert sections["成果物"] == "- CLI から `plan` と `run` を起動できる"
    assert sections["実行方針"] == "- まず Plan 草案を固めてから `run` に進む"

    counter_state = state_io.load_counter_state(isolated_repo)
    assert counter_state.next_codex_call_seq == 2
    assert not state_io.lock_path(isolated_repo).exists()


def test_plan_updates_existing_plan_from_stub_record_and_rewrites_sections(
    isolated_repo: Path,
) -> None:
    """既存 Plan 更新時に payload で section 全体が再構成される。"""

    plan_id = "plan-20260321-001"
    plan_path = state_io.plan_path(isolated_repo, plan_id)
    _write_plan(
        plan_path,
        metadata={
            "plan_id": plan_id,
            "plan_revision": 1,
            "title": "既存タイトル",
            "status": "settled",
            "created_at": "2026-03-21T10:00:00+09:00",
            "updated_at": "2026-03-21T10:00:00+09:00",
            "last_run_id": "run-0003",
            "settled_at": "2026-03-21T11:00:00+09:00",
            "closure_reason": "completed",
        },
        sections={
            "目的": "既存の目的",
            "スコープ外": "- 既存のスコープ外",
            "成果物": "- 既存の成果物",
            "制約": "- 既存の制約",
            "受け入れ条件": "- 既存の受け入れ条件",
            "未確定事項": "- 既存の未確定事項",
            "想定リスク": "- 既存の想定リスク",
            "実行方針": "- 既存の実行方針",
        },
    )
    existing_plan = state_io.load_plan_document(plan_path)
    _write_ticket(
        isolated_repo / ".tgbt/tickets/worker-0001.md",
        plan_id=plan_id,
        plan_revision=1,
        status="todo",
    )
    _write_ticket(
        isolated_repo / ".tgbt/tickets/worker-0002.md",
        plan_id=plan_id,
        plan_revision=1,
        status="settled",
    )
    _write_ticket(
        isolated_repo / ".tgbt/tickets/worker-0003.md",
        plan_id=plan_id,
        plan_revision=2,
        status="todo",
    )
    _write_ticket(
        isolated_repo / ".tgbt/tickets/worker-0004.md",
        plan_id="plan-20260321-999",
        plan_revision=1,
        status="done",
    )
    _write_plan_stub_record(
        isolated_repo,
        plan_id=plan_id,
        plan_revision=2,
        codex_call_id="call-0001",
        request_text="差し戻し条件を追記する",
        existing_plan=existing_plan,
        payload=_plan_payload(
            title="更新後タイトル",
            purpose="差し戻し条件を含めた Plan に更新する",
            deliverables="- 更新済み Plan file\n- strict replay fixture",
        ),
    )

    result = RUNNER.invoke(
        app,
        [
            "plan",
            "--codex-cli-mode",
            "stub",
            "--plan-id",
            plan_id,
            "差し戻し条件を追記する",
        ],
    )

    assert result.exit_code == 0
    assert result.stdout.strip().splitlines() == [
        f"Updated: .tgbt/plans/{plan_id}.md",
        "Plan revision: 2",
        "Status: draft",
        "Session record: .tgbt/codex/plan-20260321-001-rev-2-call-0001-plan_drafting.json",
    ]

    metadata, sections = _load_plan(plan_path)
    assert metadata["plan_revision"] == 2
    assert metadata["title"] == "更新後タイトル"
    assert metadata["status"] == "draft"
    assert metadata["created_at"] == "2026-03-21T10:00:00+09:00"
    assert metadata["last_run_id"] == "run-0003"
    assert "settled_at" not in metadata
    assert "closure_reason" not in metadata
    assert datetime.fromisoformat(str(metadata["updated_at"])) > datetime.fromisoformat(
        str(metadata["created_at"])
    )
    assert sections["目的"] == "差し戻し条件を含めた Plan に更新する"
    assert sections["成果物"] == "- 更新済み Plan file\n- strict replay fixture"
    assert not (isolated_repo / ".tgbt/tickets/worker-0001.md").exists()
    assert not (isolated_repo / ".tgbt/tickets/worker-0002.md").exists()
    assert (isolated_repo / ".tgbt/tickets/worker-0003.md").exists()
    assert (isolated_repo / ".tgbt/tickets/worker-0004.md").exists()


def test_plan_reports_missing_stub_record_and_does_not_create_plan(
    isolated_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """stub source が無い場合は wrapper failure で停止する。"""

    monkeypatch.setattr(plan_service, "_next_plan_id", lambda repo_root: "plan-20260401-001")

    result = RUNNER.invoke(
        app,
        ["plan", "--codex-cli-mode", "stub", "CLI だけ確認する"],
    )

    assert result.exit_code == 1
    assert "ERROR: stub record was not found:" in result.stderr
    assert "Impact: no plan file or front matter was created or updated, but counters or session records may have changed" in result.stderr
    assert not any(state_io.plans_dir(isolated_repo).glob("*.md"))
    assert state_io.load_counter_state(isolated_repo).next_codex_call_seq == 2


def test_plan_rejects_empty_request_text(isolated_repo: Path) -> None:
    """空入力を拒否する。"""

    result = RUNNER.invoke(app, ["plan", "   "])

    assert result.exit_code == 1
    assert "ERROR: request_text must not be empty" in result.stderr
    assert "Impact: no plan file or front matter was created or updated" in result.stderr
    assert not any(state_io.plans_dir(isolated_repo).glob("*.md"))


def test_plan_rejects_missing_plan_id(isolated_repo: Path) -> None:
    """存在しない `plan_id` への更新を拒否する。"""

    result = RUNNER.invoke(
        app,
        ["plan", "--plan-id", "plan-20260321-001", "追記する"],
    )

    assert result.exit_code == 1
    assert "ERROR: plan_id was not found: plan-20260321-001" in result.stderr
    assert "Impact: no plan file or front matter was created or updated" in result.stderr
    assert not state_io.lock_path(isolated_repo).exists()


def test_plan_live_reports_codex_cli_failure_details(
    isolated_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """live 実行失敗時に returncode/stderr を CLI へ伝える。"""

    plan_id = "plan-20260401-001"
    monkeypatch.setattr(plan_service, "_next_plan_id", lambda repo_root: plan_id)

    def fake_run(
        argv: list[str],
        *,
        capture_output: bool,
        text: bool,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        assert capture_output is True
        assert text is True
        assert check is False
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

    result = RUNNER.invoke(
        app,
        ["plan", "CLI の初回本番実行を確認する"],
    )

    assert result.exit_code == 1
    assert (
        "ERROR: codex exec failed with returncode 1: stderr="
        in result.stderr
    )
    assert "schema must have a 'type' key" in result.stderr
    assert (
        "Impact: no plan file or front matter was created or updated, but counters or session records may have changed"
        in result.stderr
    )
    session_record_path = (
        isolated_repo / ".tgbt/codex/plan-20260401-001-rev-1-call-0001-plan_drafting.json"
    )
    session_record = json.loads(session_record_path.read_text(encoding="utf-8"))
    assert session_record["result"]["returncode"] == 1
    assert session_record["result"]["stop_reason"] == "codex_exec_failed"


def test_plan_rejects_when_repository_lock_already_exists(isolated_repo: Path) -> None:
    """既存 lock がある場合は更新を開始しない。"""

    lock_path = state_io.lock_path(isolated_repo)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text('{"command_name":"plan"}\n', encoding="utf-8")

    result = RUNNER.invoke(app, ["plan", "CLI だけ確認する"])

    assert result.exit_code == 1
    assert "ERROR: repository lock is already held" in result.stderr
    assert "Impact: no plan file or front matter was created or updated" in result.stderr
    assert lock_path.exists()
    assert not any(state_io.plans_dir(isolated_repo).glob("*.md"))


def test_plan_rejects_invalid_existing_plan_shape(isolated_repo: Path) -> None:
    """front matter または section 順序が壊れた Plan を拒否する。"""

    plan_path = state_io.plan_path(isolated_repo, "plan-20260321-001")
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(
        """---
plan_id: plan-20260321-001
plan_revision: 1
title: 壊れた Plan
status: draft
created_at: 2026-03-21T10:00:00+09:00
updated_at: 2026-03-21T10:00:00+09:00
---

# 目的
既存の目的

# 成果物
- 順序が壊れている

# スコープ外
- 本来は先に来る
""",
        encoding="utf-8",
    )

    result = RUNNER.invoke(
        app,
        ["plan", "--plan-id", "plan-20260321-001", "追記する"],
    )

    assert result.exit_code == 1
    assert "ERROR: state validation failed:" in result.stderr
    assert "Impact: no plan file or front matter was created or updated" in result.stderr
    assert not state_io.lock_path(isolated_repo).exists()


def test_run_accepts_spec_arguments_then_fails_explicitly() -> None:
    """`run` が `--plan-id` と既定 mode を受け取り、未実装エラーで停止する。"""

    result = RUNNER.invoke(app, ["run", "--plan-id", "plan-20260321-001"])

    assert result.exit_code == 1
    assert "ERROR: run command is not implemented yet" in result.stderr
    assert "Impact: no plan or ticket state mutation was performed" in result.stderr
    assert (
        "Next: implement run orchestration before retrying this command"
        in result.stderr
    )


def test_run_accepts_stub_mode_then_fails_explicitly() -> None:
    """`run` が `stub` mode を受け取り、未実装エラーで停止する。"""

    result = RUNNER.invoke(
        app,
        ["run", "--plan-id", "plan-20260321-001", "--codex-cli-mode", "stub"],
    )

    assert result.exit_code == 1
    assert "ERROR: run command is not implemented yet" in result.stderr


def test_run_rejects_removed_positional_interface() -> None:
    """旧 `ticket_id` ベースの位置引数インターフェースを拒否する。"""

    result = RUNNER.invoke(
        app,
        ["run", "worker-001", "production", "gpt-5.2", "medium"],
    )

    assert result.exit_code != 0
    assert "Missing option '--plan-id'." in result.stderr


def _load_plan(path: Path) -> tuple[dict[str, object], dict[str, str]]:
    """Plan file を読み戻す。"""

    metadata, body = state_io.load_markdown_with_front_matter(path)
    sections = state_io.parse_plan_sections(body)
    return metadata, sections


def _write_plan(
    path: Path,
    *,
    metadata: dict[str, object],
    sections: dict[str, str],
) -> None:
    """Plan file をテスト用に作る。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    front_matter = yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False).strip()
    body_parts: list[str] = []
    for section_name in state_io.PLAN_SECTION_ORDER:
        body_parts.append(f"# {section_name}\n{sections[section_name]}")
    path.write_text(
        f"---\n{front_matter}\n---\n\n" + "\n\n".join(body_parts) + "\n",
        encoding="utf-8",
    )


def _write_ticket(
    path: Path,
    *,
    plan_id: str,
    plan_revision: int,
    status: str,
) -> None:
    """Ticket file をテスト用に作る。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "ticket_id": path.stem,
        "plan_id": plan_id,
        "plan_revision": plan_revision,
        "status": status,
        "created_at": "2026-03-21T10:30:00+09:00",
        "updated_at": "2026-03-21T10:30:00+09:00",
    }
    front_matter = yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False).strip()
    path.write_text(
        f"---\n{front_matter}\n---\n\n# Title\nTicket\n",
        encoding="utf-8",
    )


def _plan_payload(
    *,
    title: str,
    purpose: str,
    out_of_scope: str = "- スコープ外は別途整理する",
    deliverables: str = "- CLI から `plan` と `run` を起動できる",
    constraints: str = "- 既存 CLI 契約を壊さない",
    acceptance_criteria: str = "- `plan` と `run` の導線が明確である",
    open_questions: str = "- 将来の wrapper 拡張は別途検討する",
    risks: str = "- strict replay fixture の維持コストがある",
    execution_strategy: str = "- まず Plan 草案を固めてから `run` に進む",
) -> plan_drafting.PlanDraftingPayload:
    """payload fixture を作る。"""

    return plan_drafting.PlanDraftingPayload(
        summary="Plan draft summary",
        title=title,
        sections={
            "purpose": purpose,
            "out_of_scope": out_of_scope,
            "deliverables": deliverables,
            "constraints": constraints,
            "acceptance_criteria": acceptance_criteria,
            "open_questions": open_questions,
            "risks": risks,
            "execution_strategy": execution_strategy,
        },
    )


def _write_plan_stub_record(
    repo_root: Path,
    *,
    plan_id: str,
    plan_revision: int,
    codex_call_id: str,
    request_text: str,
    existing_plan: state_io.PlanDocument | None,
    payload: plan_drafting.PlanDraftingPayload,
) -> None:
    """`plan_drafting` 用 stub record を作る。"""

    model, reasoning_effort = codex_wrapper.resolve_model_config()
    session_record_path = state_io.plan_drafting_session_record_relative_path(
        repo_root,
        plan_id=plan_id,
        plan_revision=plan_revision,
        codex_call_id=codex_call_id,
    )
    request = codex_wrapper.CodexCliRequest(
        plan_id=plan_id,
        plan_revision=plan_revision,
        ticket_id=None,
        run_id=None,
        codex_call_id=codex_call_id,
        call_purpose=plan_drafting.CALL_PURPOSE,
        codex_cli_mode=CodexCliMode.STUB,
        cwd=str(repo_root),
        prompt_text=plan_drafting.build_prompt(
            request_text=request_text,
            plan_id=plan_id,
            plan_revision=plan_revision,
            existing_plan=existing_plan,
        ),
        model=model,
        reasoning_effort=reasoning_effort,
        stub_record_path=session_record_path,
    )
    storage_request, _ = codex_wrapper.redact_request_for_storage(
        codex_wrapper.build_storage_request(request)
    )
    business_output = {
        "schema_name": plan_drafting.CALL_PURPOSE,
        "schema_version": 1,
        "call_purpose": plan_drafting.CALL_PURPOSE,
        "summary": payload.summary,
        "title": payload.title,
        "sections": payload.sections,
    }
    record = {
        "schema_version": 1,
        "plan_id": plan_id,
        "plan_revision": plan_revision,
        "ticket_id": None,
        "run_id": None,
        "codex_call_id": codex_call_id,
        "call_purpose": plan_drafting.CALL_PURPOSE,
        "codex_cli_mode": "live",
        "request": storage_request,
        "result": {
            "plan_id": plan_id,
            "plan_revision": plan_revision,
            "ticket_id": None,
            "run_id": None,
            "codex_call_id": codex_call_id,
            "call_purpose": plan_drafting.CALL_PURPOSE,
            "codex_cli_mode": "live",
            "returncode": 0,
            "stdout": "",
            "stderr": "",
            "last_message_text": codex_wrapper.canonicalize_json(business_output),
            "business_output": business_output,
            "generated_artifacts": [session_record_path],
            "stop_reason": "completed",
            "session_record_path": session_record_path,
            "replayed_from": None,
            "redaction_report": {},
        },
        "saved_at": "2026-03-21T10:00:00+09:00",
    }
    session_record_abspath = repo_root / session_record_path
    session_record_abspath.parent.mkdir(parents=True, exist_ok=True)
    session_record_abspath.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
