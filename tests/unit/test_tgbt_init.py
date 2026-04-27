# std
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

# third party
from pytest import MonkeyPatch


SRC_DIR = Path(__file__).parents[2] / "src"


def _load_tgbt_init_module() -> ModuleType:
    """
    init 実装をテスト用に読み込む。
    """
    # `src/` ルートの import を解決できるようにする。
    if str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))

    # 対象ファイルだけをテスト用の別名で読み込む。
    spec = importlib.util.spec_from_file_location(
        "tgbt_init_under_test",
        SRC_DIR / "sub_commands" / "init" / "tgbt_init.py",
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_tgbt_init_impl_creates_tgbt_dir_and_initializes_codex(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """
    `tgbt init` はカレントを repo root として `.tgbt` を作成する。
    """
    module = _load_tgbt_init_module()
    calls: list[Path] = []

    class FakeCodexWrapperLive:
        """
        live Codex を起動せず、初期化呼び出しだけを記録する。
        """

        def init_repo(self) -> None:
            """
            初期化が呼ばれたカレントを記録する。
            """
            calls.append(Path.cwd())

    # テスト用 repo root から init を実行する。
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(module.TGBT_PATH, "_repo_root", None)
    monkeypatch.setattr(module, "CodexWrapperLive", FakeCodexWrapperLive)

    module.tgbt_init_impl()

    assert (tmp_path / ".tgbt").is_dir()
    assert module.TGBT_PATH.repo_root == tmp_path
    assert calls == [tmp_path]
