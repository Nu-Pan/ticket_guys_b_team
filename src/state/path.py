# std
from pathlib import Path

# tgbt
from util.error import tgbt_error

_TGBT_GITIGNORE_BODY = ".codex/\n"
_REPO_ROOT_NOTATION = "<repo-root>"


class TGBTPath:
    """
    tgbt 起動時に一意に決まるファイル・ディレクトリパスを集めたクラス
    """

    def __init__(self) -> None:
        """
        コンストラクタ
        """
        # repo root は初回解決後にキャッシュする。
        self._repo_root: Path | None = None

    @property
    def repo_root(self) -> Path:
        """`<repo-root>`"""
        # 解決済みの repo root があれば再探索せず返す。
        if isinstance(self._repo_root, Path):
            return self._repo_root
        else:
            current = Path.cwd()
            for candidate in (current, *current.parents):
                if (candidate / ".git").exists():
                    self._repo_root = candidate
                    return self._repo_root
            else:
                raise tgbt_error(
                    "tgbt 操作対象リポジトリルートパスの解決に失敗しました",
                    """
                    tgbt 操作対象リポジトリのルートディレクトリに .git が存在する必要があります。
                    git リポジトリ配下で tgbt を実行してください。
                    """,
                    actual={"current": current},
                )

    @property
    def tgbt(self) -> Path:
        """`<repo-root>/.tgbt`"""
        # tgbt が管理する repo ローカル状態ディレクトリを返す。
        return self.repo_root / ".tgbt"

    @property
    def tgbt_gitignore(self) -> Path:
        """`<repo-root>/.tgbt/.gitignore`"""
        # `.tgbt` 配下の git 管理対象を制御する ignore file path を返す。
        return self.tgbt / ".gitignore"

    def ensure_tgbt_dir(self) -> None:
        """tgbt 管理ディレクトリと git 管理ルールを用意する。"""
        # `.tgbt` は必要になったタイミングで動的に作成する。
        self.tgbt.mkdir(parents=True, exist_ok=True)

        # `.codex` だけを git 管理対象外にし、それ以外の `.tgbt` 配下は追跡可能にする。
        self.tgbt_gitignore.write_text(_TGBT_GITIGNORE_BODY, encoding="utf-8")

    @property
    def tgbt_codex(self) -> Path:
        """`CODEX_HOME`"""
        # tgbt 管理下で Codex CLI に渡す CODEX_HOME を返す。
        return self.tgbt / ".codex"

    @property
    def tgbt_codex_config(self) -> Path:
        """`CODEX_HOME/config.toml`"""
        # tgbt 管理下の Codex CLI config path を返す。
        return self.tgbt_codex / "config.toml"

    @property
    def tgbt_logs(self) -> Path:
        """`<repo-root>/.tgbt/logs`"""
        # tgbt が生成するログ群の親ディレクトリを返す。
        return self.tgbt / "logs"

    @property
    def tgbt_logs_codex_call(self) -> Path:
        """`<repo-root>/.tgbt/logs/codex_call`"""
        # Codex CLI 呼び出しログの保存先ディレクトリを返す。
        return self.tgbt_logs / "codex_call"

    @property
    def tgbt_logs_tgbt_call(self) -> Path:
        """`<repo-root>/.tgbt/logs/tgbt_call`"""
        # tgbt CLI 呼び出しログの保存先ディレクトリを返す。
        return self.tgbt_logs / "tgbt_call"

    @property
    def tgbt_lock(self) -> Path:
        """`<repo-root>/.tgbt/tgbt.lock`"""
        # repo 単位の排他制御に使う lock file path を返す。
        return self.tgbt / "tgbt.lock"

    @property
    def tgbt_plan(self) -> Path:
        """`<repo-root>/.tgbt/plan`"""
        # plan 正本 JSON の保存先ディレクトリを返す。
        return self.tgbt / "plan"

    @property
    def tgbt_plan_read(self) -> Path:
        """`<repo-root>/.tgbt/plan_read`"""
        # 人間閲覧用 plan Markdown の保存先ディレクトリを返す。
        return self.tgbt / "plan_read"

    def tgbt_plan_json(self, plan_id: str) -> Path:
        """`<repo-root>/.tgbt/plan/<plan-id>.json`"""
        # plan id から正本 JSON path を組み立てる。
        return self.tgbt_plan / f"{plan_id}.json"

    def tgbt_plan_markdown(self, plan_id: str) -> Path:
        """`<repo-root>/.tgbt/plan_read/<plan-id>.md`"""
        # plan id から人間閲覧用 Markdown path を組み立てる。
        return self.tgbt_plan_read / f"{plan_id}.md"

    @property
    def tgbt_knowledge(self) -> Path:
        """`<repo-root>/.tgbt/knowledge`"""
        # tgbt 知識システムの管理ディレクトリを返す。
        return self.tgbt / "knowledge"

    @property
    def tgbt_knowledge_source_config(self) -> Path:
        """`<repo-root>/.tgbt/knowledge_source_config.json`"""
        # 知識ソースファイル除外設定の JSON path を返す。
        return self.tgbt / "knowledge_source_config.json"

    @property
    def tgbt_knowledge_index(self) -> Path:
        """`<repo-root>/.tgbt/knowledge/index.json`"""
        # 知識ソースファイル目次の JSON path を返す。
        return self.tgbt_knowledge / "index.json"

    @property
    def tgbt_knowledge_items(self) -> Path:
        """`<repo-root>/.tgbt/knowledge/items`"""
        # 生成済み知識ファイル群の保存先ディレクトリを返す。
        return self.tgbt_knowledge / "items"

    def tgbt_knowledge_item_markdown(self, knowledge_id: str) -> Path:
        """`<repo-root>/.tgbt/knowledge/items/<knowledge-id>.md`"""
        # knowledge id から知識 Markdown path を組み立てる。
        return self.tgbt_knowledge_items / f"{knowledge_id}.md"

    @property
    def agents_md(self) -> Path:
        """`<repo-root>/AGENTS.md`"""
        # 操作対象 repo の AGENTS.md path を返す。
        return self.repo_root / "AGENTS.md"


# パス集合クラスの実体
# 直接的に外部公開するのはこれだけ
TGBT_PATH = TGBTPath()


def repo_notation_path(path: Path) -> str:
    """repo root 配下の path を `<repo-root>/...` 表記に変換する."""
    # oracle のパス表記ルールに従い、repo 相対表記には必ず `<repo-root>` を付ける。
    relative_path = path.relative_to(TGBT_PATH.repo_root).as_posix()
    if relative_path == ".":
        return _REPO_ROOT_NOTATION
    return f"{_REPO_ROOT_NOTATION}/{relative_path}"


def repo_relative_path_from_notation(path_text: str) -> str:
    """`<repo-root>/...` 表記を内部保存用 repo 相対 path へ戻す."""
    # 既存 state は repo 相対 path を保存しているため、境界で notation だけを剥がす。
    prefix = f"{_REPO_ROOT_NOTATION}/"
    if path_text == _REPO_ROOT_NOTATION:
        return "."
    if path_text.startswith(prefix):
        return path_text.removeprefix(prefix)
    return path_text
