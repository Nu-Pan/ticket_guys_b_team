# std
import sys
from pathlib import Path

# third party
from pytest import MonkeyPatch
from typer.testing import CliRunner


SRC_DIR = Path(__file__).parents[2] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# local
import main as main_module
from agent_wrapper.agent_wrapper import CodexCliMode


def test_plan_docs_reads_instruction_from_stdin(
    monkeypatch: MonkeyPatch,
) -> None:
    """
    末尾引数 `-` の場合は標準入力を指示文として渡す。
    """
    calls: list[tuple[str, str | None, CodexCliMode]] = []

    def fake_impl(
        instruction: str,
        plan_id: str | None,
        codex_cli_mode: CodexCliMode,
    ) -> None:
        """
        plan docs 実装へ渡された引数を記録する。
        """
        calls.append((instruction, plan_id, codex_cli_mode))

    # CLI 経由で stdin の本文が実装関数へ渡ることを確認する。
    monkeypatch.setattr(main_module, "tgbt_plan_docs_impl", fake_impl)
    runner = CliRunner()
    result = runner.invoke(
        main_module.app,
        ["plan", "docs", "--plan-id", "plan-1", "--codex-cli-mode", "stub", "-"],
        input="from stdin\n",
    )

    assert result.exit_code == 0, result.output
    assert calls == [("from stdin\n", "plan-1", CodexCliMode.STUB)]


def test_plan_docs_reads_instruction_from_editor(
    monkeypatch: MonkeyPatch,
) -> None:
    """
    末尾引数がない場合はエディタ入力を指示文として渡す。
    """
    calls: list[tuple[str, str | None, CodexCliMode]] = []

    class FakeEditorInstructionInput:
        """
        実エディタを起動せず、固定の指示文を返す。
        """

        def read(self) -> str:
            """
            テスト用の指示文を返す。
            """
            return "from editor\n"

    def fake_impl(
        instruction: str,
        plan_id: str | None,
        codex_cli_mode: CodexCliMode,
    ) -> None:
        """
        plan docs 実装へ渡された引数を記録する。
        """
        calls.append((instruction, plan_id, codex_cli_mode))

    # 引数なしの場合に EditorInstructionInput が使われることを確認する。
    monkeypatch.setattr(
        main_module,
        "EditorInstructionInput",
        FakeEditorInstructionInput,
    )
    monkeypatch.setattr(main_module, "tgbt_plan_docs_impl", fake_impl)
    runner = CliRunner()
    result = runner.invoke(main_module.app, ["plan", "docs"])

    assert result.exit_code == 0, result.output
    assert calls == [("from editor\n", None, CodexCliMode.LIVE)]


def test_plan_docs_rejects_unknown_instruction_source() -> None:
    """
    末尾引数は `-` 以外を受け付けない。
    """
    runner = CliRunner()
    result = runner.invoke(main_module.app, ["plan", "docs", "request text"])

    assert result.exit_code != 0
    assert "指示文の入力元指定が不正です" in result.output
