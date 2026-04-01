"""CLI インターフェースの形状を検証するテスト。"""

from typer.testing import CliRunner

from src.main import app


RUNNER = CliRunner()


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


def test_plan_accepts_request_text_and_optional_plan_id_then_fails_explicitly() -> None:
    """`plan` が仕様の引数を受け取り、未実装エラーで停止することを確認する。"""

    result = RUNNER.invoke(
        app,
        ["plan", "--plan-id", "plan-20260321-001", "差し戻し条件を追記する"],
    )

    assert result.exit_code == 1
    assert "ERROR: plan command is not implemented yet" in result.stderr
    assert "Impact: no plan file or front matter was created or updated" in result.stderr
    assert (
        "Next: implement plan persistence before retrying this command"
        in result.stderr
    )


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
