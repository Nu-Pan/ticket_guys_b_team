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
    assert "review-queue" in result.stdout


def test_bin_tgbt_resolves_repo_root_outside_repository() -> None:
    """リポジトリ外の作業ディレクトリでも起動できることを確認する。"""

    result = subprocess.run(
        [str(CLI_PATH), "plan", "CLI だけ確認する"],
        cwd="/tmp",
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""
