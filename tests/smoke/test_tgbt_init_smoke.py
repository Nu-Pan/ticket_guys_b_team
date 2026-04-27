# std
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).parents[2]
TGBT_BIN = REPO_ROOT / "bin" / "tgbt"


def test_tgbt_init_preserves_existing_project_files(tmp_path: Path) -> None:
    """
    `tgbt init` は toy project 上で初期化し、既存ファイルを削除しない。
    """
    # smoke 用の toy project を構築する。
    toy_project = tmp_path / "toy_project"
    codex_home = toy_project / ".tgbt" / ".codex"
    codex_home.mkdir(parents=True)
    (toy_project / "AGENTS.md").write_text("agent instructions\n", encoding="utf-8")
    (codex_home / "sentinel.txt").write_text("keep\n", encoding="utf-8")

    # 実 CLI 経由で init を実行する。
    completed = subprocess.run(
        [str(TGBT_BIN), "init"],
        cwd=toy_project,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert (toy_project / ".tgbt").is_dir()
    assert (codex_home / "config.toml").is_file()
    assert (toy_project / "AGENTS.md").read_text(encoding="utf-8") == (
        "agent instructions\n"
    )
    assert (codex_home / "sentinel.txt").read_text(encoding="utf-8") == "keep\n"
