# std
import os
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

# local
from util.error import tgbt_error


class EditorInstructionInput:
    """
    エディタを起動してユーザーから指示文を受け取る入力口。
    """

    def read(self) -> str:
        """
        エディタで編集された一時ファイルの本文を返す。
        """
        # 編集用の一時ファイルを作り、エディタ終了後に本文を読み戻す。
        with tempfile.TemporaryDirectory() as temp_dir:
            instruction_file = Path(temp_dir) / "instruction.md"
            instruction_file.write_text("", encoding="utf-8")

            self._run_editor(instruction_file)
            return instruction_file.read_text(encoding="utf-8")

    def _run_editor(self, instruction_file: Path) -> None:
        """
        利用可能なエディタを起動する。
        """
        # `$EDITOR` が指定されている場合は、その指定を唯一の候補として使う。
        editor = os.environ.get("EDITOR", "").strip()
        if editor:
            command = shlex.split(editor)
            if not command:
                raise tgbt_error(
                    "エディタコマンドの解釈に失敗しました",
                    "$EDITOR に実行可能なエディタコマンドを指定してください",
                    actual={"EDITOR": editor},
                )
            self._run_required_command(command, instruction_file)
            return

        # `$EDITOR` 未指定時は仕様で定められた順に候補を試す。
        fallback_commands = [
            ["code", "--wait"],
            ["vim"],
            ["vi"],
        ]
        errors: list[str] = []
        for command in fallback_commands:
            if shutil.which(command[0]) is None:
                errors.append(f"{command[0]}: not found")
                continue

            try:
                completed = self._run_command(command, instruction_file)
            except FileNotFoundError:
                errors.append(f"{command[0]}: not found")
                continue

            if completed.returncode == 0:
                return
            errors.append(f"{command[0]}: exit code {completed.returncode}")

        raise tgbt_error(
            "起動可能なエディタが見つかりませんでした",
            "$EDITOR に利用可能なエディタコマンドを指定してください",
            actual={"attempts": errors},
        )

    def _run_required_command(self, command: list[str], instruction_file: Path) -> None:
        """
        明示指定されたエディタコマンドを実行する。
        """
        try:
            completed = self._run_command(command, instruction_file)
        except FileNotFoundError:
            raise tgbt_error(
                "エディタコマンドが見つかりませんでした",
                "$EDITOR に利用可能なエディタコマンドを指定してください",
                actual={"command": command},
            )

        if completed.returncode != 0:
            raise tgbt_error(
                "エディタが異常終了しました",
                "エディタの設定を確認してから再実行してください",
                actual={
                    "command": command,
                    "returncode": completed.returncode,
                },
            )

    def _run_command(
        self,
        command: list[str],
        instruction_file: Path,
    ) -> subprocess.CompletedProcess[str]:
        """
        指示文ファイルを引数に追加してエディタコマンドを起動する。
        """
        return subprocess.run(
            [*command, str(instruction_file)],
            check=False,
            text=True,
        )
