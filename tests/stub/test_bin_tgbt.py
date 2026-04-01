"""`bin/tgbt` の起動導線を検証するテスト。"""

from pathlib import Path
import subprocess


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


def test_bin_tgbt_resolves_repo_root_outside_repository_then_fails_explicitly() -> None:
    """リポジトリ外からも entrypoint を解決し、未実装エラーまで到達する。"""

    result = subprocess.run(
        [str(CLI_PATH), "plan", "CLI だけ確認する"],
        cwd="/tmp",
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert "ERROR: plan command is not implemented yet" in result.stderr
    assert "Impact: no plan file or front matter was created or updated" in result.stderr
