# std
from pathlib import Path

# tgbt
from util.error import tgbt_error


class TGBTPath:
    """
    tgbt 起動時に一意に決まるファイル・ディレクトリパスを集めたクラス
    """

    def __init__(self):
        """
        コンストラクタ
        """
        self._repo_root = None

    @property
    def repo_root(self) -> Path:
        """`<repo-root>`"""
        if isinstance(self._repo_root, Path):
            return self._repo_root
        else:
            current = Path.cwd()
            for candidate in (current, *current.parents):
                if (candidate / ".tgbt").is_dir():
                    self._repo_root = candidate
                    return self._repo_root
            else:
                raise tgbt_error(
                    "tgbt 操作対象リポジトリルートパスの解決に失敗しました",
                    """
                    tgbt 操作対象リポジトリのルートディレクトリに .tgbt を存在する必要があります。
                    これは通常 tgbt init の実行によって自動的に満たされます。
                    """,
                    actual={"current": current},
                )

    @property
    def repo_root_codex(self) -> Path:
        """`<repo-root>/.codex`"""
        return self.repo_root / ".codex"

    @property
    def tgbt(self) -> Path:
        """`<repo-root>/.tgbt`"""
        return self.repo_root / ".tgbt"

    @property
    def tgbt_codex(self) -> Path:
        """`<repo-root>/.tgbt/.codex`"""
        return self.tgbt / ".codex"

    @property
    def tgbt_codex_config(self) -> Path:
        """`<repo-root>/.tgbt/.codex/config.toml`"""
        return self.tgbt_codex / "config.toml"

    @property
    def tgbt_logs(self) -> Path:
        """`<repo-root>/.tgbt/logs`"""
        return self.tgbt / "logs"

    @property
    def tgbt_logs_codex_call(self) -> Path:
        """`<repo-root>/.tgbt/logs/codex_call`"""
        return self.tgbt_logs / "codex_call"

    @property
    def tgbt_logs_tgbt_call(self) -> Path:
        """`<repo-root>/.tgbt/logs/tgbt_call`"""
        return self.tgbt_logs / "tgbt_call"

    @property
    def tgbt_lock(self) -> Path:
        """`<repo-root>/.tgbt/tgbt.lock`"""
        return self.tgbt / "tgbt.lock"

    @property
    def tgbt_plan(self) -> Path:
        """`<repo-root>/.tgbt/plan`"""
        return self.tgbt / "plan"

    @property
    def tgbt_plan_read(self) -> Path:
        """`<repo-root>/.tgbt/plan_read`"""
        return self.tgbt / "plan_read"

    def tgbt_plan_json(self, plan_id: str) -> Path:
        """`<repo-root>/.tgbt/plan/<plan-id>.json`"""
        return self.tgbt_plan / f"{plan_id}.json"

    def tgbt_plan_markdown(self, plan_id: str) -> Path:
        """`<repo-root>/.tgbt/plan_read/<plan-id>.md`"""
        return self.tgbt_plan_read / f"{plan_id}.md"

    @property
    def agents_md(self) -> Path:
        """`<repo-root>/AGENTS.md`"""
        return self.repo_root / "AGENTS.md"


# パス集合クラスの実体
# 直接的に外部公開するのはこれだけ
TGBT_PATH = TGBTPath()
