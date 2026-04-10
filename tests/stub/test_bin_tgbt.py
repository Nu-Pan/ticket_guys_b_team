"""`bin/tgbt` の起動導線を検証するテスト。"""

import json
from pathlib import Path
import shutil
import subprocess

import pytest
import yaml

from src import codex_wrapper, plan_drafting, state_io


REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def isolated_launcher_root(tmp_path: Path) -> Path:
    """`bin/tgbt` 検証用の自己完結した launcher 配置を作る。"""

    launcher_root = tmp_path / "launcher"
    shutil.copytree(REPO_ROOT / "bin", launcher_root / "bin")
    shutil.copytree(REPO_ROOT / "src", launcher_root / "src")

    # NOTE: 仮想環境は共有しつつ、対象 state は invocation cwd 配下へ閉じ込める。
    (launcher_root / ".venv").symlink_to(REPO_ROOT / ".venv", target_is_directory=True)
    return launcher_root


def test_bin_tgbt_shows_help_from_repo_root(isolated_launcher_root: Path) -> None:
    """リポジトリ直下から `bin/tgbt` が起動できることを確認する。"""

    cli_path = isolated_launcher_root / "bin" / "tgbt"
    result = subprocess.run(
        [str(cli_path), "--help"],
        cwd=isolated_launcher_root,
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


def test_bin_tgbt_uses_invocation_cwd_as_target_repository(
    isolated_launcher_root: Path,
    tmp_path: Path,
) -> None:
    """launcher 配置とは別の invocation cwd を対象 repository として更新する。"""

    cli_path = isolated_launcher_root / "bin" / "tgbt"
    target_repo_root = tmp_path / "target-repo"
    plan_id = "plan-bin-test-001"
    plan_path = target_repo_root / ".tgbt" / "plans" / f"{plan_id}.md"
    session_record_path = (
        target_repo_root
        / ".tgbt"
        / "codex"
        / f"{plan_id}-rev-2-call-0001-plan_drafting.json"
    )
    counters_path = target_repo_root / ".tgbt" / "system" / "counters.json"

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
        target_repo_root,
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
            str(cli_path),
            "plan",
            "--plan-id",
            plan_id,
            "--codex-cli-mode",
            "stub",
            "bin/tgbt から stub 更新を確認する",
        ],
        cwd=target_repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    assert f"Updated: {plan_path}" in result.stdout
    assert "Plan revision: 2" in result.stdout
    assert "Status: draft" in result.stdout
    assert (
        f"Session record: {session_record_path}"
        in result.stdout
    )
    assert "bin 更新後タイトル" in plan_path.read_text(encoding="utf-8")


def _write_plan(path: Path, *, metadata: dict[str, object], sections: dict[str, str]) -> None:
    """Plan file をテスト用に作る。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    front_matter = yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False).strip()
    body = "\n\n".join(f"# {name}\n{content}" for name, content in sections.items())
    path.write_text(f"---\n{front_matter}\n---\n\n{body}\n", encoding="utf-8")


def _write_stub_record(
    repo_root: Path,
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
        "cwd": str(repo_root),
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
