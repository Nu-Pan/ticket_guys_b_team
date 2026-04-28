# std
import subprocess
import sys
from pathlib import Path
from typing import Any

# third party
import pytest
import typer
from pytest import MonkeyPatch


SRC_DIR = Path(__file__).parents[2] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# local
from util import editor_input as editor_input_module
from util.editor_input import EditorInstructionInput


def test_editor_instruction_input_uses_editor_env(
    monkeypatch: MonkeyPatch,
) -> None:
    """
    `$EDITOR` が指定されている場合、そのコマンドで指示文を受け取る。
    """
    calls: list[list[str]] = []

    def fake_run(
        command: list[str],
        **kwargs: Any,
    ) -> subprocess.CompletedProcess[str]:
        """
        エディタの代わりに一時ファイルへ本文を書き込む。
        """
        _ = kwargs
        calls.append(command)
        Path(command[-1]).write_text("from editor\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    # `$EDITOR` のコマンド解釈と本文読み戻しを確認する。
    monkeypatch.setenv("EDITOR", "fake-editor --flag")
    monkeypatch.setattr(editor_input_module.subprocess, "run", fake_run)

    instruction = EditorInstructionInput().read()

    assert instruction == "from editor\n"
    assert calls[0][:2] == ["fake-editor", "--flag"]


def test_editor_instruction_input_falls_back_to_code_wait(
    monkeypatch: MonkeyPatch,
) -> None:
    """
    `$EDITOR` 未指定時は `code --wait` を最初に試す。
    """
    calls: list[list[str]] = []

    def fake_which(command: str) -> str | None:
        """
        fallback 候補をすべて存在するものとして扱う。
        """
        return f"/usr/bin/{command}"

    def fake_run(
        command: list[str],
        **kwargs: Any,
    ) -> subprocess.CompletedProcess[str]:
        """
        `code --wait` の起動だけを記録して成功させる。
        """
        _ = kwargs
        calls.append(command)
        Path(command[-1]).write_text("from code\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    # `$EDITOR` を空にし、仕様順の最初の候補が使われることを確認する。
    monkeypatch.delenv("EDITOR", raising=False)
    monkeypatch.setattr(editor_input_module.shutil, "which", fake_which)
    monkeypatch.setattr(editor_input_module.subprocess, "run", fake_run)

    instruction = EditorInstructionInput().read()

    assert instruction == "from code\n"
    assert calls == [[
        "code",
        "--wait",
        calls[0][-1],
    ]]


def test_editor_instruction_input_errors_when_editor_env_is_missing(
    monkeypatch: MonkeyPatch,
) -> None:
    """
    `$EDITOR` の明示指定が起動できない場合はエラー終了する。
    """

    def fake_run(
        command: list[str],
        **kwargs: Any,
    ) -> subprocess.CompletedProcess[str]:
        """
        存在しないエディタ指定を再現する。
        """
        _ = command, kwargs
        raise FileNotFoundError

    # 明示された `$EDITOR` が見つからない場合の終了を確認する。
    monkeypatch.setenv("EDITOR", "missing-editor")
    monkeypatch.setattr(editor_input_module.subprocess, "run", fake_run)

    with pytest.raises(typer.Exit):
        EditorInstructionInput().read()


def test_editor_instruction_input_falls_back_after_failure(
    monkeypatch: MonkeyPatch,
) -> None:
    """
    fallback 候補の起動に失敗した場合、次のエディタを試す。
    """
    calls: list[list[str]] = []

    def fake_which(command: str) -> str | None:
        """
        fallback 候補をすべて存在するものとして扱う。
        """
        return f"/usr/bin/{command}"

    def fake_run(
        command: list[str],
        **kwargs: Any,
    ) -> subprocess.CompletedProcess[str]:
        """
        `code` を失敗させ、`vim` で本文を書き込む。
        """
        _ = kwargs
        calls.append(command)
        if command[0] == "code":
            return subprocess.CompletedProcess(command, 1)
        Path(command[-1]).write_text("from vim\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    # `code` の失敗後に `vim` が使われることを確認する。
    monkeypatch.delenv("EDITOR", raising=False)
    monkeypatch.setattr(editor_input_module.shutil, "which", fake_which)
    monkeypatch.setattr(editor_input_module.subprocess, "run", fake_run)

    instruction = EditorInstructionInput().read()

    assert instruction == "from vim\n"
    assert [call[0] for call in calls] == ["code", "vim"]


def test_editor_instruction_input_errors_when_all_fallbacks_fail(
    monkeypatch: MonkeyPatch,
) -> None:
    """
    fallback 候補がすべて使えない場合はエラー終了する。
    """
    # 候補コマンドが存在しない状況を再現する。
    monkeypatch.delenv("EDITOR", raising=False)
    monkeypatch.setattr(editor_input_module.shutil, "which", lambda command: None)

    with pytest.raises(typer.Exit):
        EditorInstructionInput().read()
