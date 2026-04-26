# local
from state.path import TGBT_PATH
from util.text import stdtqs


def _ensure_tgbt_codex() -> None:
    """
    `<repo-root>/.tgbt/.codex` を正しい状態にする
    """
    body = stdtqs(
        """
        # ----
        # グローバル設定
        # ----

        # 基本設定
        model = "gpt-5.5"
        model_reasoning_effort = "high"
        plan_mode_reasoning_effort = "high"
        model_verbosity = "high"
        approval_policy = "on-request"
        sandbox_mode = "workspace-write"
        personality = "pragmatic"

        # Web検索モード
        # NOTE
        #   cached はライブ取得せず、OpenAI 管理のインデックスを使う
        sandbox_workspace_write.network_access = true
        web_search = "cached"

        # 参照リンクを vsocde フレンドリーにする
        file_opener = "vscode"

        # 基本指示は使わない
        #developer_instructions = ...

        # ----
        # セッション履歴
        # ----

        [history]
        persistence = "none"

        # ----
        # Web 検索
        # ----

        [tools.web_search]
        context_size = "high"

        # ----
        # マルチエージェント
        # ----

        [agents]

        max_threads = 6
        max_depth = 1
        """
    )
    TGBT_PATH.tgbt_codex.mkdir(parents=True, exist_ok=True)
    TGBT_PATH.tgbt_codex_config.write_text(body, encoding="utf-8")


def tgbt_init_impl() -> None:
    """
    `tgbt init` の実装
    tgbt からの Codex CLI 呼び出しが、
    """

    # TODO
    # - `<repo-root>/.tgbt/.codex` を正しい状態にする
    # - `<repo-root>/AGENTS.md` を正しい状態にする
    # - `<repo-root>/AGENTS.md` 以外の `AGENTS.md` を削除
    # - `ROUTING.md` を正しい状態にする
    # - 既存の実行ログ類を削除

    _ensure_tgbt_codex()
