# local
from agent_wrapper.codex_wrapper_live import CodexWrapperLive


def tgbt_init_impl() -> None:
    """
    `tgbt init` の実装
    `tgbt` から Codex CLI を呼び出した時に、その挙動が想定通りのものになるように、 `<repo-root>` 配下の状態を修正する。
    """
    CodexWrapperLive().init_repo()
