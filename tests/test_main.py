"""`src/main.py` の最小動作確認テスト。"""

import subprocess
from pathlib import Path


def test_main_prints_hello() -> None:
    """`main.py` 実行時に hello が出力されることを確認する。"""
    # スクリプト実行そのものを検証して、最小の起動確認を行う。
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "src" / "main.py"

    completed = subprocess.run(
        [str(repo_root / ".venv" / "bin" / "python"), str(script_path)],
        check=True,
        capture_output=True,
        text=True,
        cwd=repo_root,
    )

    assert completed.stdout == "hello\n"
