"""CLI インターフェースの形状を検証するテスト。"""

from typer.testing import CliRunner

from src.main import app


RUNNER = CliRunner()


def test_root_help_lists_all_commands() -> None:
    """ルートヘルプに公開コマンドが並ぶことを確認する。"""

    result = RUNNER.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "plan" in result.stdout
    assert "approve" in result.stdout
    assert "ticket" in result.stdout
    assert "run" in result.stdout
    assert "review-queue" in result.stdout
    assert "artifacts" in result.stdout


def test_plan_accepts_request_text_and_optional_plan_id() -> None:
    """`plan` が要求文と `--plan-id` を受け付けることを確認する。"""

    result = RUNNER.invoke(
        app,
        ["plan", "--plan-id", "plan-20260321-001", "差し戻し条件を追記する"],
    )

    assert result.exit_code == 0


def test_approve_accepts_transition_target() -> None:
    """`approve` が plan_id と `--to` を受け付けることを確認する。"""

    result = RUNNER.invoke(
        app,
        ["approve", "plan-20260321-001", "--to", "approved"],
    )

    assert result.exit_code == 0


def test_ticket_accepts_plan_id() -> None:
    """`ticket` が plan_id を受け付けることを確認する。"""

    result = RUNNER.invoke(app, ["ticket", "plan-20260321-001"])

    assert result.exit_code == 0


def test_run_accepts_all_positional_arguments() -> None:
    """`run` が想定される位置引数列を受け付けることを確認する。"""

    result = RUNNER.invoke(
        app,
        ["run", "worker-001", "production", "gpt-5.2", "medium"],
    )

    assert result.exit_code == 0


def test_review_queue_accepts_optional_plan_id() -> None:
    """`review-queue` が任意の `--plan-id` を受け付けることを確認する。"""

    result = RUNNER.invoke(app, ["review-queue", "--plan-id", "plan-20260321-001"])

    assert result.exit_code == 0


def test_artifacts_requires_single_target_identifier() -> None:
    """`artifacts` が単一の識別子入力を要求することを確認する。"""

    missing_target = RUNNER.invoke(app, ["artifacts"])
    duplicate_target = RUNNER.invoke(
        app,
        [
            "artifacts",
            "--plan-id",
            "plan-20260321-001",
            "--ticket-id",
            "worker-001",
        ],
    )
    plan_target = RUNNER.invoke(app, ["artifacts", "--plan-id", "plan-20260321-001"])
    ticket_target = RUNNER.invoke(app, ["artifacts", "--ticket-id", "worker-001"])

    assert missing_target.exit_code != 0
    assert "Specify either --plan-id or --ticket-id." in missing_target.output
    assert duplicate_target.exit_code != 0
    assert "Specify only one of --plan-id or --ticket-id." in duplicate_target.output
    assert plan_target.exit_code == 0
    assert ticket_target.exit_code == 0
