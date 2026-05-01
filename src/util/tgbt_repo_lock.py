# std
import fcntl
import os
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import TextIO

# local
from state.path import TGBT_PATH
from util.error import tgbt_error


class TGBTRepoLock:
    """
    同一リポジトリ上の tgbt 呼び出しを直列化する排他ロック。
    """

    def __init__(self) -> None:
        """
        ロック対象のファイルパスを初期化する。
        """
        self._lock_file_path = TGBT_PATH.tgbt_lock
        self._lock_file: TextIO | None = None

    def __enter__(self) -> "TGBTRepoLock":
        """
        repo 単位の排他ロックを取得する。
        """
        # `.tgbt` 配下の lock file を、OS の advisory lock の対象として使う。
        self._lock_file_path.parent.mkdir(parents=True, exist_ok=True)
        lock_file = self._lock_file_path.open("a+", encoding="utf-8")

        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            lock_file.close()
            raise tgbt_error(
                "同じリポジトリ上で tgbt が既に実行中です",
                """
                実行中の tgbt が終了してから、もう一度実行してください。
                """,
                actual={"lock_file_path": self._lock_file_path},
                exc_obj=SystemExit(1),
            )

        # ロックファイルの内容はデバッグ用であり、排他判定には使わない。
        lock_file.seek(0)
        lock_file.truncate()
        lock_file.write(
            f"pid={os.getpid()}\n"
            f"started_at={datetime.now().isoformat()}\n"
            f"repo_root={TGBT_PATH.repo_root}\n"
        )
        lock_file.flush()

        self._lock_file = lock_file
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_obj: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """
        repo 単位の排他ロックを解放する。
        """
        _ = (exc_type, exc_obj, exc_tb)

        # ファイルを close すると flock も解放される。
        if self._lock_file is not None:
            self._lock_file.close()
            self._lock_file = None
