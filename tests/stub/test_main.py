"""CLI インターフェースと `env` / `plan docs` の動作を検証する。"""

from datetime import datetime
import json
from pathlib import Path
import subprocess

import pytest
from typer.testing import CliRunner
import yaml

from src.main import app
from src import codex_wrapper, env_runtime, plan_drafting, plan_service, state_io


RUNNER = CliRunner()


@pytest.fixture
def isolated_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """対象 repository を一時ディレクトリへ切り替える。"""

    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_root_help_lists_only_spec_commands() -> None:
    """ルートヘルプに `env` / `plan` / `run` だけが並ぶことを確認する。"""

    result = RUNNER.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "│ env " in result.stdout
    assert "│ plan" in result.stdout
    assert "│ run " in result.stdout
    assert "│ approve" not in result.stdout
    assert "│ ticket" not in result.stdout
    assert "│ review-queue" not in result.stdout
    assert "│ artifacts" not in result.stdout


def test_plan_help_lists_only_docs_subcommand() -> None:
    """`plan` 親コマンド配下に `docs` だけを公開する。"""

    result = RUNNER.invoke(app, ["plan", "--help"])

    assert result.exit_code == 0
    assert "│ docs" in result.stdout
    assert "│ env" not in result.stdout


def test_env_help_does_not_expose_codex_cli_mode() -> None:
    """`env` は Codex mode option を公開しない。"""

    result = RUNNER.invoke(app, ["env", "--help"])

    assert result.exit_code == 0
    assert "--codex-cli-mode" not in result.stdout


def test_removed_commands_fail_as_unknown_commands() -> None:
    """仕様外コマンドが unknown command として拒否されることを確認する。"""

    for command_name in ["approve", "ticket", "review-queue", "artifacts"]:
        result = RUNNER.invoke(app, [command_name])

        assert result.exit_code != 0
        assert f"No such command '{command_name}'." in result.stderr


def test_plan_docs_creates_a_new_plan_file_from_stub_record(
    isolated_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """新規 `plan docs --codex-cli-mode stub` が session record から Plan を生成する。"""

    plan_id = "plan-20260401-001"
    monkeypatch.setattr(plan_service, "_next_plan_id", lambda repo_root: plan_id)
    request_text = "CLI で plan / run を扱えるようにしたい"
    _write_docs_plan_stub_record(
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
        ["plan", "docs", "--codex-cli-mode", "stub", request_text],
    )

    assert result.exit_code == 0
    assert result.stderr == ""
    assert result.stdout.strip().splitlines() == [
        f"Updated: {isolated_repo / '.tgbt/plans' / f'{plan_id}.md'}",
        "Plan revision: 1",
        "Status: draft",
        (
            "Session record: "
            f"{isolated_repo / '.tgbt/codex/plan-20260401-001-rev-1-call-0001-plan_drafting.json'}"
        ),
    ]

    plan_path = state_io.plan_path(isolated_repo, plan_id)
    metadata, sections = _load_plan(plan_path)
    assert metadata["title"] == "CLI 初期実装"
    assert metadata["status"] == "draft"
    assert metadata["plan_kind"] == "docs"
    assert metadata["plan_revision"] == 1
    assert sections["目的"] == "CLI で plan / run を扱えるようにしたい"


def test_plan_docs_updates_existing_plan_from_stub_record_and_rewrites_sections(
    isolated_repo: Path,
) -> None:
    """既存 Plan 更新時に payload で section 全体が再構成される。"""

    plan_id = "plan-20260321-001"
    plan_path = state_io.plan_path(isolated_repo, plan_id)
    _write_plan(
        plan_path,
        metadata={
            "plan_id": plan_id,
            "plan_kind": "docs",
            "plan_revision": 1,
            "title": "既存タイトル",
            "status": "settled",
            "created_at": "2026-03-21T10:00:00+09:00",
            "updated_at": "2026-03-21T10:00:00+09:00",
            "last_run_id": "run-0003",
            "settled_at": "2026-03-21T11:00:00+09:00",
            "closure_reason": "completed",
        },
        sections=_default_plan_sections(purpose="既存の目的"),
    )
    existing_plan = state_io.load_plan_document(plan_path)
    _write_ticket(
        isolated_repo / ".tgbt/tickets/worker-0001.md",
        plan_id=plan_id,
        plan_revision=1,
        status="todo",
    )
    _write_docs_plan_stub_record(
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
            "docs",
            "--codex-cli-mode",
            "stub",
            "--plan-id",
            plan_id,
            "差し戻し条件を追記する",
        ],
    )

    assert result.exit_code == 0
    metadata, sections = _load_plan(plan_path)
    assert metadata["plan_revision"] == 2
    assert metadata["title"] == "更新後タイトル"
    assert metadata["status"] == "draft"
    assert metadata["plan_kind"] == "docs"
    assert metadata["last_run_id"] == "run-0003"
    assert "settled_at" not in metadata
    assert "closure_reason" not in metadata
    assert datetime.fromisoformat(str(metadata["updated_at"])) > datetime.fromisoformat(
        str(metadata["created_at"])
    )
    assert sections["成果物"] == "- 更新済み Plan file\n- strict replay fixture"
    assert not (isolated_repo / ".tgbt/tickets/worker-0001.md").exists()


def test_plan_docs_reports_missing_stub_record_and_does_not_create_plan(
    isolated_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """stub source が無い場合は wrapper failure で停止する。"""

    monkeypatch.setattr(plan_service, "_next_plan_id", lambda repo_root: "plan-20260401-001")

    result = RUNNER.invoke(
        app,
        ["plan", "docs", "--codex-cli-mode", "stub", "CLI だけ確認する"],
    )

    assert result.exit_code == 1
    assert "ERROR: stub record was not found:" in result.stderr
    assert not any(state_io.plans_dir(isolated_repo).glob("*.md"))


def test_plan_docs_rejects_empty_request_text(isolated_repo: Path) -> None:
    """空入力を拒否する。"""

    result = RUNNER.invoke(app, ["plan", "docs", "   "])

    assert result.exit_code == 1
    assert "ERROR: request_text must not be empty" in result.stderr


def test_plan_docs_live_reports_codex_cli_failure_details(
    isolated_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """live 実行失敗時に returncode/stderr を CLI へ伝える。"""

    _ensure_repo_local_runtime(isolated_repo)
    plan_id = "plan-20260401-001"
    monkeypatch.setattr(plan_service, "_next_plan_id", lambda repo_root: plan_id)

    def fake_run(
        argv: list[str],
        *,
        capture_output: bool,
        text: bool,
        check: bool,
        env: dict[str, str],
    ) -> subprocess.CompletedProcess[str]:
        assert env["CODEX_HOME"] == str(isolated_repo / ".tgbt/.codex")
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
                '\'codex_output_schema\': schema must have a \'type\' key."\n'
                "  }\n"
                "}\n"
            ),
        )

    monkeypatch.setattr(codex_wrapper.subprocess, "run", fake_run)

    result = RUNNER.invoke(app, ["plan", "docs", "CLI の初回本番実行を確認する"])

    assert result.exit_code == 1
    assert "ERROR: codex exec failed with returncode 1: stderr=" in result.stderr
    assert "schema must have a 'type' key" in result.stderr


def test_plan_docs_live_requires_legal_repo_local_runtime(
    isolated_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """live 実行前に runtime 不正を検知し、`tgbt env` を案内する。"""

    def fail_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise AssertionError("subprocess.run must not be called")

    monkeypatch.setattr(codex_wrapper.subprocess, "run", fail_run)

    result = RUNNER.invoke(app, ["plan", "docs", "CLI の初回本番実行を確認する"])

    assert result.exit_code == 1
    assert "ERROR: repo-local Codex runtime is illegal; run `tgbt env` first:" in result.stderr
    assert "Next: run `tgbt env` to legalize the repo-local Codex runtime, then retry" in result.stderr


def test_env_returns_already_legal_without_creating_plan(isolated_repo: Path) -> None:
    """初回判定で合法なら no-op 成功する。"""

    _write_agents_md(isolated_repo)
    _ensure_repo_local_runtime(isolated_repo)

    result = RUNNER.invoke(app, ["env"])

    assert result.exit_code == 0
    assert result.stdout.strip().splitlines() == [
        "Status: already_legal",
        f"Log: {isolated_repo / '.tgbt/logs/env-latest.jsonl'}",
    ]
    log_lines = _load_env_log_entries(isolated_repo)
    assert [entry["event_type"] for entry in log_lines] == [
        "env_observed",
        "env_reconciled",
        "env_validated",
    ]
    _assert_env_base_event(log_lines[0], isolated_repo, "env_observed")
    _assert_env_base_event(log_lines[1], isolated_repo, "env_reconciled")
    _assert_env_base_event(log_lines[2], isolated_repo, "env_validated")
    assert log_lines[0]["blocking_issues"] == []
    assert log_lines[0]["diagnostics"] == []
    assert log_lines[1]["repair_attempted"] is False
    assert log_lines[1]["actions"] == []
    assert log_lines[2]["outcome"] == "already_legal"
    assert log_lines[2]["goal_reached"] is True
    assert log_lines[2]["blocking_issues"] == []
    assert log_lines[2]["diagnostics"] == []
    assert not state_io.plans_dir(isolated_repo).exists()
    assert not state_io.tickets_dir(isolated_repo).exists()
    assert not state_io.codex_dir(isolated_repo).exists()


def test_env_reconciles_runtime_files_without_plan_or_codex(
    isolated_repo: Path,
) -> None:
    """`tgbt env` は one-shot で runtime file を再生成する。"""

    _write_agents_md(isolated_repo)

    result = RUNNER.invoke(app, ["env"])

    assert result.exit_code == 0
    assert result.stdout.strip().splitlines() == [
        "Status: legalized",
        "Updated files:",
        f"- {isolated_repo / '.tgbt/.codex/config.toml'}",
        f"- {isolated_repo / '.tgbt/instructions.md'}",
        f"Log: {isolated_repo / '.tgbt/logs/env-latest.jsonl'}",
    ]
    assert env_runtime.evaluate_env_legality(isolated_repo).is_legal is True
    assert not state_io.plans_dir(isolated_repo).exists()
    assert not state_io.tickets_dir(isolated_repo).exists()
    assert not state_io.codex_dir(isolated_repo).exists()

    log_lines = _load_env_log_entries(isolated_repo)
    assert [entry["event_type"] for entry in log_lines] == [
        "env_observed",
        "env_reconciled",
        "env_validated",
    ]
    assert log_lines[0]["blocking_issues"] == [
        {
            "code": "missing_runtime_instructions",
            "severity": "blocking",
            "subject": "runtime_instructions",
            "path": str(isolated_repo / ".tgbt/instructions.md"),
            "message": ".tgbt/instructions.md was not found",
            "repair_policy": "auto_repair",
        },
        {
            "code": "missing_repo_local_codex_config",
            "severity": "blocking",
            "subject": "repo_local_codex_config",
            "path": str(isolated_repo / ".tgbt/.codex/config.toml"),
            "message": ".tgbt/.codex/config.toml was not found",
            "repair_policy": "auto_repair",
        },
    ]
    assert log_lines[1]["repair_attempted"] is True
    assert log_lines[1]["actions"] == [
        {
            "subject": "repo_local_codex_config",
            "path": str(isolated_repo / ".tgbt/.codex/config.toml"),
            "action_type": "create_or_replace_file",
            "result": "updated",
            "message": "regenerated repo-local Codex config",
        },
        {
            "subject": "runtime_instructions",
            "path": str(isolated_repo / ".tgbt/instructions.md"),
            "action_type": "create_or_replace_file",
            "result": "updated",
            "message": "regenerated shared runtime instructions for tgbt Codex invocations",
        },
    ]
    assert log_lines[2]["outcome"] == "legalized"
    assert log_lines[2]["goal_reached"] is True
    assert log_lines[2]["blocking_issues"] == []


def test_env_reports_missing_agents_md_as_diagnostics_and_still_succeeds(
    isolated_repo: Path,
) -> None:
    """runtime が合法なら AGENTS 欠落は diagnostics のみで扱う。"""

    result = RUNNER.invoke(app, ["env"])

    assert result.exit_code == 0
    assert result.stdout.strip().splitlines() == [
        "Status: legalized",
        "Updated files:",
        f"- {isolated_repo / '.tgbt/.codex/config.toml'}",
        f"- {isolated_repo / '.tgbt/instructions.md'}",
        "Diagnostics:",
        "- AGENTS.md was not found",
        f"Log: {isolated_repo / '.tgbt/logs/env-latest.jsonl'}",
    ]
    assert (isolated_repo / ".tgbt/.codex/config.toml").exists()
    assert (isolated_repo / ".tgbt/instructions.md").exists()
    assert state_io.env_log_path(isolated_repo).exists()
    log_lines = _load_env_log_entries(isolated_repo)
    assert log_lines[0]["diagnostics"] == [
        {
            "code": "missing_agents_md",
            "severity": "diagnostic",
            "subject": "agents_md",
            "path": str(isolated_repo / "AGENTS.md"),
            "message": "AGENTS.md was not found",
            "repair_policy": "observe_only",
        }
    ]
    assert log_lines[2]["outcome"] == "legalized"
    assert log_lines[2]["diagnostics"] == log_lines[0]["diagnostics"]
    assert not state_io.plans_dir(isolated_repo).exists()
    assert not state_io.tickets_dir(isolated_repo).exists()
    assert not state_io.codex_dir(isolated_repo).exists()


def test_env_reports_repo_root_codex_dir_as_diagnostics(isolated_repo: Path) -> None:
    """repository 直下 `.codex/` は diagnostics のみで扱う。"""

    _write_agents_md(isolated_repo)
    _ensure_repo_local_runtime(isolated_repo)
    state_io.repo_root_codex_dir(isolated_repo).mkdir()

    result = RUNNER.invoke(app, ["env"])

    assert result.exit_code == 0
    assert result.stdout.strip().splitlines() == [
        "Status: already_legal",
        "Diagnostics:",
        "- repository root .codex/ exists and is ignored by tgbt worker runtime",
        f"Log: {isolated_repo / '.tgbt/logs/env-latest.jsonl'}",
    ]
    log_lines = _load_env_log_entries(isolated_repo)
    assert log_lines[0]["diagnostics"] == [
        {
            "code": "repo_root_codex_dir_present",
            "severity": "diagnostic",
            "subject": "repo_root_codex_dir",
            "path": str(isolated_repo / ".codex"),
            "message": "repository root .codex/ exists and is ignored by tgbt worker runtime",
            "repair_policy": "observe_only",
        }
    ]


def test_env_fails_when_blocking_runtime_issue_remains_after_reconcile(
    isolated_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """補修後も runtime blocking issue が残れば非 0 終了する。"""

    _write_agents_md(isolated_repo)
    monkeypatch.setattr(env_runtime, "reconcile_repo_local_runtime", lambda repo_root: [])

    result = RUNNER.invoke(app, ["env"])

    assert result.exit_code == 1
    assert "ERROR: bootstrap issues remain after one-shot reconcile:" in result.stderr
    assert "Remaining issues:" in result.stderr
    assert ".tgbt/.codex/config.toml was not found" in result.stderr
    assert ".tgbt/instructions.md was not found" in result.stderr
    assert f"Log: {isolated_repo / '.tgbt/logs/env-latest.jsonl'}" in result.stderr
    log_lines = _load_env_log_entries(isolated_repo)
    assert log_lines[2]["event_type"] == "env_validated"
    assert log_lines[2]["outcome"] == "illegal"
    assert log_lines[2]["goal_reached"] is False
    blocking_issues = log_lines[2]["blocking_issues"]
    assert isinstance(blocking_issues, list)
    assert [issue["message"] for issue in blocking_issues] == [
        ".tgbt/instructions.md was not found",
        ".tgbt/.codex/config.toml was not found",
    ]


def test_env_writes_env_failed_when_observation_fails_after_invalidation(
    isolated_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """observation failure は current invocation の `env_failed` を残す。"""

    _write_agents_md(isolated_repo)
    state_io.env_log_path(isolated_repo).parent.mkdir(parents=True, exist_ok=True)
    state_io.env_log_path(isolated_repo).write_text("stale\n", encoding="utf-8")

    def fail_observation(repo_root: Path) -> env_runtime.EnvLegalityReport:
        raise OSError("runtime instructions could not be rendered")

    monkeypatch.setattr(env_runtime, "evaluate_env_legality", fail_observation)

    result = RUNNER.invoke(app, ["env"])

    assert result.exit_code == 1
    assert "ERROR: bootstrap observation failed: runtime instructions could not be rendered" in result.stderr
    assert f"Log: {isolated_repo / '.tgbt/logs/env-latest.jsonl'}" in result.stderr
    log_lines = _load_env_log_entries(isolated_repo)
    assert len(log_lines) == 1
    assert log_lines[0]["event_type"] == "env_failed"
    assert log_lines[0]["failure_stage"] == "observation"
    assert log_lines[0]["cause"] == "bootstrap observation failed: runtime instructions could not be rendered"
    assert log_lines[0]["diagnostics"] == []


def test_env_removes_stale_latest_when_log_publish_fails(
    isolated_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """current invocation の log 保存に失敗した場合、stale latest を残さない。"""

    _write_agents_md(isolated_repo)
    _ensure_repo_local_runtime(isolated_repo)
    state_io.env_log_path(isolated_repo).parent.mkdir(parents=True, exist_ok=True)
    state_io.env_log_path(isolated_repo).write_text("stale\n", encoding="utf-8")

    def fail_write_jsonl_log(path: Path, entries: list[dict[str, object]]) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(state_io, "write_jsonl_log", fail_write_jsonl_log)

    result = RUNNER.invoke(app, ["env"])

    assert result.exit_code == 1
    assert "ERROR: failed to persist env state: disk full" in result.stderr
    assert f"Log: {isolated_repo / '.tgbt/logs/env-latest.jsonl'}" not in result.stderr
    assert not state_io.env_log_path(isolated_repo).exists()


def test_run_accepts_spec_arguments_then_fails_explicitly() -> None:
    """`run` が `--plan-id` と既定 mode を受け取り、未実装エラーで停止する。"""

    result = RUNNER.invoke(app, ["run", "--plan-id", "plan-20260321-001"])

    assert result.exit_code == 1
    assert "ERROR: run command is not implemented yet" in result.stderr


def _load_plan(path: Path) -> tuple[dict[str, object], dict[str, str]]:
    """Plan file を読み戻す。"""

    metadata, body = state_io.load_markdown_with_front_matter(path)
    sections = state_io.parse_plan_sections(body)
    return metadata, sections


def _load_env_log_entries(repo_root: Path) -> list[dict[str, object]]:
    """env audit log を JSONL として読み戻す。"""

    return [
        json.loads(line)
        for line in state_io.env_log_path(repo_root).read_text(encoding="utf-8").splitlines()
    ]


def _assert_env_base_event(
    entry: dict[str, object],
    repo_root: Path,
    event_type: str,
) -> None:
    """共通 env audit field を確認する。"""

    assert entry["schema_name"] == "env_audit"
    assert entry["schema_version"] == 1
    assert entry["command_name"] == "env"
    assert entry["repo_root"] == str(repo_root)
    assert entry["event_type"] == event_type
    assert isinstance(entry["timestamp"], str)


def _default_plan_sections(*, purpose: str) -> dict[str, str]:
    """Plan section の既定値を返す。"""

    return {
        "目的": purpose,
        "スコープ外": "- スコープ外は別途整理する",
        "成果物": "- CLI から `plan` と `run` を起動できる",
        "制約": "- 既存 CLI 契約を壊さない",
        "受け入れ条件": "- `plan` と `run` の導線が明確である",
        "未確定事項": "- 将来の wrapper 拡張は別途検討する",
        "想定リスク": "- strict replay fixture の維持コストがある",
        "実行方針": "- まず Plan 草案を固めてから `run` に進む",
    }


def _write_plan(
    path: Path,
    *,
    metadata: dict[str, object],
    sections: dict[str, str],
) -> None:
    """Plan file をテスト用に作る。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    front_matter = yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False).strip()
    body_parts = [
        f"# {section_name}\n{sections[section_name]}"
        for section_name in state_io.PLAN_SECTION_ORDER
    ]
    path.write_text(
        f"---\n{front_matter}\n---\n\n" + "\n\n".join(body_parts) + "\n",
        encoding="utf-8",
    )


def _write_ticket(path: Path, *, plan_id: str, plan_revision: int, status: str) -> None:
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


def _write_docs_plan_stub_record(
    repo_root: Path,
    *,
    plan_id: str,
    plan_revision: int,
    codex_call_id: str,
    request_text: str,
    existing_plan: state_io.PlanDocument | None,
    payload: plan_drafting.PlanDraftingPayload,
) -> None:
    """`plan docs` 用 stub record を作る。"""

    prompt_text = plan_drafting.build_docs_prompt(
        request_text=request_text,
        plan_id=plan_id,
        plan_revision=plan_revision,
        existing_plan=existing_plan,
    )
    _write_plan_stub_record(
        repo_root,
        plan_id=plan_id,
        plan_revision=plan_revision,
        codex_call_id=codex_call_id,
        prompt_text=prompt_text,
        payload=payload,
    )


def _write_plan_stub_record(
    repo_root: Path,
    *,
    plan_id: str,
    plan_revision: int,
    codex_call_id: str,
    prompt_text: str,
    payload: plan_drafting.PlanDraftingPayload,
) -> None:
    """`plan_drafting` 用 stub record を作る。"""

    path = (
        repo_root
        / ".tgbt/codex"
        / f"{plan_id}-rev-{plan_revision}-{codex_call_id}-plan_drafting.json"
    )
    request = {
        "plan_id": plan_id,
        "plan_revision": plan_revision,
        "ticket_id": None,
        "run_id": None,
        "codex_call_id": codex_call_id,
        "call_purpose": plan_drafting.CALL_PURPOSE,
        "cwd": str(repo_root),
        "prompt_text": prompt_text,
        "model": codex_wrapper.DEFAULT_MODEL,
        "reasoning_effort": codex_wrapper.DEFAULT_REASONING_EFFORT,
    }
    storage_request, _ = codex_wrapper.redact_request_for_storage(request)
    payload_dict = {
        "schema_name": plan_drafting.CALL_PURPOSE,
        "schema_version": 1,
        "call_purpose": plan_drafting.CALL_PURPOSE,
        "summary": payload.summary,
        "title": payload.title,
        "sections": payload.sections,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
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
                    "last_message_text": codex_wrapper.canonicalize_json(payload_dict),
                    "business_output": payload_dict,
                    "generated_artifacts": [str(path)],
                    "stop_reason": "completed",
                    "session_record_path": str(path),
                    "replayed_from": None,
                    "redaction_report": {},
                },
                "saved_at": "2026-03-21T10:00:00+09:00",
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


def _write_agents_md(repo_root: Path) -> None:
    """`AGENTS.md` を作る。"""

    (repo_root / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
