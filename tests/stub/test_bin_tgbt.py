"""`bin/tgbt` の起動導線を検証するテスト。"""

import json
from pathlib import Path
import subprocess

import yaml

from src import codex_wrapper, plan_drafting, state_io


REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_PATH = REPO_ROOT / "bin" / "tgbt"


def test_bin_tgbt_shows_help_from_repo_root() -> None:
    """リポジトリ直下から `bin/tgbt` が起動できることを確認する。"""

    result = subprocess.run(
        [str(CLI_PATH), "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Usage: tgbt" in result.stdout
    assert "ticket_guys_b_team command line interface." in result.stdout
    assert "plan" in result.stdout
    assert "run" in result.stdout
    assert "review-queue" not in result.stdout


def test_bin_tgbt_resolves_repo_root_outside_repository_and_updates_plan_from_stub() -> None:
    """リポジトリ外からも entrypoint を解決し、stub fixture から Plan を更新できる。"""

    plan_id = "plan-bin-test-001"
    plan_path = REPO_ROOT / ".tgbt" / "plans" / f"{plan_id}.md"
    session_record_path = (
        REPO_ROOT / ".tgbt" / "codex" / f"{plan_id}-rev-2-call-0001-plan_drafting.json"
    )
    counters_path = REPO_ROOT / ".tgbt" / "system" / "counters.json"
    lock_path = REPO_ROOT / ".tgbt" / "system" / "locks" / "repository.lock.json"

    plan_backup = plan_path.read_text(encoding="utf-8") if plan_path.exists() else None
    session_backup = (
        session_record_path.read_text(encoding="utf-8")
        if session_record_path.exists()
        else None
    )
    counters_backup = counters_path.read_text(encoding="utf-8") if counters_path.exists() else None

    try:
        _write_plan(
            plan_path,
            metadata={
                "plan_id": plan_id,
                "plan_revision": 1,
                "title": "既存タイトル",
                "status": "draft",
                "created_at": "2026-03-21T10:00:00+09:00",
                "updated_at": "2026-03-21T10:00:00+09:00",
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
        _write_stub_record(
            session_record_path,
            plan_id=plan_id,
            request_text="bin/tgbt から stub 更新を確認する",
            title="bin 更新後タイトル",
            existing_plan=existing_plan,
        )
        counters_path.parent.mkdir(parents=True, exist_ok=True)
        counters_path.write_text(
            json.dumps(
                {
                    "next_ticket_seq": 1,
                    "next_run_seq": 1,
                    "next_codex_call_seq": 1,
                    "updated_at": "2026-03-21T10:00:00+09:00",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                str(CLI_PATH),
                "plan",
                "--plan-id",
                plan_id,
                "--codex-cli-mode",
                "stub",
                "bin/tgbt から stub 更新を確認する",
            ],
            cwd="/tmp",
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0
        assert result.stderr == ""
        assert f"Updated: .tgbt/plans/{plan_id}.md" in result.stdout
        assert "Plan revision: 2" in result.stdout
        assert "Status: draft" in result.stdout
        assert (
            f"Session record: .tgbt/codex/{plan_id}-rev-2-call-0001-plan_drafting.json"
            in result.stdout
        )
        assert "bin 更新後タイトル" in plan_path.read_text(encoding="utf-8")
    finally:
        _restore_file(plan_path, plan_backup)
        _restore_file(session_record_path, session_backup)
        _restore_file(counters_path, counters_backup)
        lock_path.unlink(missing_ok=True)
        _rmdir_if_empty(REPO_ROOT / ".tgbt" / "system" / "locks")
        _rmdir_if_empty(REPO_ROOT / ".tgbt" / "system")
        _rmdir_if_empty(REPO_ROOT / ".tgbt" / "codex")
        _rmdir_if_empty(REPO_ROOT / ".tgbt" / "plans")
        _rmdir_if_empty(REPO_ROOT / ".tgbt")


def _write_plan(path: Path, *, metadata: dict[str, object], sections: dict[str, str]) -> None:
    """Plan file をテスト用に作る。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    front_matter = yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False).strip()
    body = "\n\n".join(f"# {name}\n{content}" for name, content in sections.items())
    path.write_text(f"---\n{front_matter}\n---\n\n{body}\n", encoding="utf-8")


def _write_stub_record(
    path: Path,
    *,
    plan_id: str,
    request_text: str,
    title: str,
    existing_plan: state_io.PlanDocument,
) -> None:
    """`plan_drafting` 用 stub record を作る。"""

    payload = {
        "schema_name": plan_drafting.CALL_PURPOSE,
        "schema_version": 1,
        "call_purpose": plan_drafting.CALL_PURPOSE,
        "summary": "bin stub payload",
        "title": title,
        "sections": {
            "purpose": "bin 経由で update できることを確認する",
            "out_of_scope": "- live 実行の確認",
            "deliverables": "- 更新済み Plan file",
            "constraints": "- CLI entrypoint を維持する",
            "acceptance_criteria": "- `/tmp` からでも実行できる",
            "open_questions": "- なし",
            "risks": "- fixture ずれ",
            "execution_strategy": "- stub fixture から再構成する",
        },
    }
    prompt_text = plan_drafting.build_prompt(
        request_text=request_text,
        plan_id=plan_id,
        plan_revision=2,
        existing_plan=existing_plan,
    )
    request = {
        "plan_id": plan_id,
        "plan_revision": 2,
        "ticket_id": None,
        "run_id": None,
        "codex_call_id": "call-0001",
        "call_purpose": plan_drafting.CALL_PURPOSE,
        "cwd": str(REPO_ROOT),
        "prompt_text": prompt_text,
        "model": codex_wrapper.DEFAULT_MODEL,
        "reasoning_effort": codex_wrapper.DEFAULT_REASONING_EFFORT,
    }
    storage_request, _ = codex_wrapper.redact_request_for_storage(request)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "plan_id": plan_id,
                "plan_revision": 2,
                "ticket_id": None,
                "run_id": None,
                "codex_call_id": "call-0001",
                "call_purpose": plan_drafting.CALL_PURPOSE,
                "codex_cli_mode": "live",
                "request": storage_request,
                "result": {
                    "plan_id": plan_id,
                    "plan_revision": 2,
                    "ticket_id": None,
                    "run_id": None,
                    "codex_call_id": "call-0001",
                    "call_purpose": plan_drafting.CALL_PURPOSE,
                    "codex_cli_mode": "live",
                    "returncode": 0,
                    "stdout": "",
                    "stderr": "",
                    "last_message_text": codex_wrapper.canonicalize_json(payload),
                    "business_output": payload,
                    "generated_artifacts": [
                        f".tgbt/codex/{plan_id}-rev-2-call-0001-plan_drafting.json"
                    ],
                    "stop_reason": "completed",
                    "session_record_path": f".tgbt/codex/{plan_id}-rev-2-call-0001-plan_drafting.json",
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


def _restore_file(path: Path, original_text: str | None) -> None:
    """作業前のファイル状態を戻す。"""

    if original_text is None:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(original_text, encoding="utf-8")


def _rmdir_if_empty(path: Path) -> None:
    """空 directory だけを掃除する。"""

    try:
        if path.exists():
            path.rmdir()
    except OSError:
        return
