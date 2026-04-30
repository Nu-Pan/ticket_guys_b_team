# std
from pathlib import Path

# local
from agent_wrapper.codex_wrapper import CodexWrapper
from state.path import TGBT_PATH
from util.error import tgbt_error

_TGBT_MEANINGFUL_DIR_NAMES = (
    "memo",
    "oracle",
    "docs",
    "tests",
)


def _ensure_tgbt_root_dir() -> None:
    """
    カレントディレクトリを tgbt 操作対象リポジトリとして初期化する。
    """
    # カレントをリポジトリルートとみなして `.tgbt` を作成する。
    expected_repo_root = Path.cwd()
    (expected_repo_root / ".tgbt").mkdir(exist_ok=True)

    # `.tgbt` 作成後に、通常の repo root 解決がカレントへ向くことを確認する。
    actual_repo_root = TGBT_PATH.repo_root
    if actual_repo_root.resolve() != expected_repo_root.resolve():
        raise tgbt_error(
            "tgbt 操作対象リポジトリルートパスの検証に失敗しました",
            """
            tgbt init は、tgbt 操作対象リポジトリのルートディレクトリで実行してください。
            """,
            actual={"repo_root": actual_repo_root},
            expect={"repo_root": expected_repo_root},
        )

    # tgbt が意味を持つトップレベルディレクトリを用意する。
    for dir_name in _TGBT_MEANINGFUL_DIR_NAMES:
        (actual_repo_root / dir_name).mkdir(exist_ok=True)


def tgbt_init_impl() -> None:
    """
    `tgbt init` の実装
    `tgbt` から Codex CLI を呼び出した時に、その挙動が想定通りのものになるように、 `<repo-root>` 配下の状態を修正する。
    """
    # repo root として使う `.tgbt` ディレクトリを先に用意する。
    _ensure_tgbt_root_dir()

    # Codex CLI 用のリポジトリ状態を整える。
    CodexWrapper().init_repo()
