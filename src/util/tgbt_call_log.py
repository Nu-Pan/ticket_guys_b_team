# std
import json
import sys
import time
import traceback
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from types import TracebackType

# pip
import typer

# local
from state.path import TGBT_PATH

_RELATED_LOG_PATHS: ContextVar[tuple[Path, ...]] = ContextVar(
    "TGBT_RELATED_LOG_PATHS",
    default=(),
)


def reset_related_log_paths() -> None:
    """
    tgbt 呼び出し単位の関連ログパス収集状態を初期化する。
    """
    _RELATED_LOG_PATHS.set(())


def record_related_log_path(log_file_path: Path) -> None:
    """
    現在の tgbt 呼び出しに関連するログパスを記録する。
    """
    # 同一呼び出し内で同じログが複数回積まれても、出力は一意に保つ。
    current_paths = _RELATED_LOG_PATHS.get()
    if log_file_path not in current_paths:
        _RELATED_LOG_PATHS.set((*current_paths, log_file_path))


def get_related_log_paths() -> list[Path]:
    """
    現在の tgbt 呼び出しに関連するログパス一覧を返す。
    """
    return list(_RELATED_LOG_PATHS.get())


def get_exit_code(exc_obj: BaseException) -> int:
    """
    Typer/SystemExit 系の例外からプロセス終了コードを推定する。
    """
    if isinstance(exc_obj, typer.Exit):
        return int(exc_obj.exit_code)

    if isinstance(exc_obj, typer.Abort):
        return 1

    if isinstance(exc_obj, SystemExit):
        if isinstance(exc_obj.code, int):
            return exc_obj.code
        if exc_obj.code is None:
            return 0
        return 1

    if isinstance(exc_obj, KeyboardInterrupt):
        return 130

    return 1


def write_tgbt_call_log(
    argv: list[str],
    exit_code: int,
    exc_obj: BaseException | None,
    exc_tb: TracebackType | None,
) -> Path | None:
    """
    tgbt コマンド呼び出し自体のログを保存する。

    ログ保存に失敗しても、本来の CLI 終了挙動を壊さないため例外は外へ出さない。
    """
    try:
        log_dir = TGBT_PATH.tgbt_logs_tgbt_call
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file_path = log_dir / f"{time.time_ns()}.json"

        error = None
        if exc_obj is not None and exit_code != 0:
            error = {
                "type": type(exc_obj).__name__,
                "message": str(exc_obj),
                "traceback": (
                    "".join(traceback.format_exception(type(exc_obj), exc_obj, exc_tb))
                    if exc_tb is not None
                    else None
                ),
            }

        log_file_path.write_text(
            json.dumps(
                {
                    "command": {
                        "argv": argv,
                        "python_argv": sys.argv,
                        "cwd": str(Path.cwd()),
                        "repo_root": str(TGBT_PATH.repo_root),
                    },
                    "result": {
                        "is_ok": exit_code == 0,
                        "exit_code": exit_code,
                        "error": error,
                    },
                    "related": {
                        "log_file_paths": [
                            str(path) for path in get_related_log_paths()
                        ],
                    },
                    "timestamp": {
                        "epoch_ns": time.time_ns(),
                        "iso": datetime.now().isoformat(),
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return log_file_path
    except Exception:
        return None
