# std
import os
import sys
from types import TracebackType
from typing import Annotated
from uuid import uuid4

# pip
import typer

# local
from sub_commands.knowledge.tgbt_knowledge import tgbt_knowledge_search_impl
from sub_commands.plan.tgbt_plan import tgbt_plan_impl
from sub_commands.run.tgbt_run import tgbt_run_impl
from util.error import tgbt_error
from util.tgbt_call_log import (
    get_exit_code,
    reset_related_log_paths,
    write_tgbt_call_log,
)
from util.tgbt_repo_lock import TGBTRepoLock

_TGBT_ROOT_CALL_ID_ENV = "TGBT_ROOT_CALL_ID"

# NOTE: `bin/tgbt` はこのファイルを直接実行するため、
# local import は絶対 import にする。
_app = typer.Typer(
    name="tgbt",
    help="ticket_guys_b_team command line interface.",
    no_args_is_help=True,
)
_knowledge_app = typer.Typer(
    name="knowledge",
    help="tgbt knowledge system commands.",
    no_args_is_help=True,
)
_app.add_typer(_knowledge_app, name="knowledge")


@_knowledge_app.command("search")
def knowledge_search(
    question: Annotated[
        str,
        typer.Argument(
            help="Repository question to answer with the tgbt knowledge system.",
        ),
    ],
) -> None:
    """知識システムで repo についての質問に答える。"""
    # 実装を呼び出し
    tgbt_knowledge_search_impl(question)


@_app.command("plan")
def plan(
    instruction_source: Annotated[
        str | None,
        typer.Argument(
            help=(
                "Use '-' to read instruction text from stdin. "
                "Other text is inserted before opening the editor."
            ),
        ),
    ] = None,
    plan_id: Annotated[
        str | None,
        typer.Option(
            "--plan-id",
            help=(
                "Existing plan identifier to revise into a new plan. "
                "Use 'latest' for the newest plan."
            ),
        ),
    ] = None,
) -> None:
    """
    作業計画書を作成する。
    plan_id 未指定の場合は新規に計画書を作成する。
    plan_id を指定された場合は既存計画書から修正版計画書を新規作成する。
    """
    # 実装を呼び出し
    tgbt_plan_impl(
        instruction_source,
        plan_id=plan_id,
    )


@_app.command()
def run(
    plan_id: Annotated[
        str,
        typer.Option("--plan-id", help="Plan identifier to execute."),
    ],
) -> None:
    """指定した Plan を起点に run を実行する。"""
    # 現状の run 実装へ渡す値がまだ無いため、CLI 引数の未使用警告だけ避ける。
    _ = (plan_id,)
    tgbt_run_impl()


def main() -> None:
    """
    tgbt CLI の共通実行制御を行う。
    """
    # ヘルプ表示だけなら repo root 解決を要求しない。
    is_help_only = (
        len(sys.argv) == 1
        or "--help" in sys.argv[1:]
        or "-h" in sys.argv[1:]
    )

    # Codex CLI からの例外的な再入呼び出しでは、許可済み command だけを lock 外で通す。
    is_reentrant_call = _TGBT_ROOT_CALL_ID_ENV in os.environ
    if is_help_only:
        _run_app_with_tgbt_call_log()
    elif is_reentrant_call:
        if not _is_reentrant_command_allowed(sys.argv[1:]):
            raise tgbt_error(
                "再入 tgbt 呼び出しが許可されていないサブコマンドです",
                """
                tgbt から起動された Codex CLI が呼び出せる tgbt サブコマンドは、
                例外的に許可された `tgbt knowledge search` のみです。
                """,
                actual={"argv": ["tgbt", *sys.argv[1:]]},
                expect={"allowed": "tgbt knowledge search <question>"},
            )
        _run_app_with_tgbt_call_log()
    else:
        previous_root_call_id = os.environ.get(_TGBT_ROOT_CALL_ID_ENV)
        os.environ[_TGBT_ROOT_CALL_ID_ENV] = str(uuid4())
        try:
            with TGBTRepoLock():
                _run_app_with_tgbt_call_log()
        finally:
            if previous_root_call_id is None:
                os.environ.pop(_TGBT_ROOT_CALL_ID_ENV, None)
            else:
                os.environ[_TGBT_ROOT_CALL_ID_ENV] = previous_root_call_id


def _is_reentrant_command_allowed(argv: list[str]) -> bool:
    """再入 tgbt 呼び出しで実行を許可する command か判定する."""
    # 現時点で stack 的再入が許可されているのは知識検索だけ。
    return len(argv) >= 2 and argv[0] == "knowledge" and argv[1] == "search"


def _run_app_with_tgbt_call_log() -> None:
    """
    Typer app を実行し、tgbt 呼び出しログを保存する。
    """
    # 1 回の tgbt 呼び出しに紐づく関連ログ収集状態を初期化する。
    reset_related_log_paths()
    exit_code = 0
    exc_obj: BaseException | None = None
    exc_tb: TracebackType | None = None

    try:
        _app(prog_name="tgbt")
    except BaseException as error:
        exit_code = get_exit_code(error)
        exc_obj = error
        exc_tb = error.__traceback__
        raise
    finally:
        write_tgbt_call_log(
            argv=["tgbt", *sys.argv[1:]],
            exit_code=exit_code,
            exc_obj=exc_obj,
            exc_tb=exc_tb,
        )


if __name__ == "__main__":
    main()
