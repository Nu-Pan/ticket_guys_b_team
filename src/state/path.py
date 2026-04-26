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
        """
        リポジトリルートパス
        """
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


# パス集合クラスの実体
# 直接的に外部公開するのはこれだけ
TGBT_PATH = TGBTPath()
