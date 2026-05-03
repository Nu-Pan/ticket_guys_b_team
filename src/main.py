# std
import sys
from types import TracebackType
from typing import Annotated

# pip
import typer

# local
from sub_commands.plan.tgbt_plan import tgbt_plan_impl
from sub_commands.run.tgbt_run import tgbt_run_impl
from util.tgbt_call_log import (
    get_exit_code,
    reset_related_log_paths,
    write_tgbt_call_log,
)
from util.tgbt_repo_lock import TGBTRepoLock

# NOTE: `bin/tgbt` はこのファイルを直接実行するため、
# local import は絶対 import にする。
_app = typer.Typer(
    name="tgbt",
    help="ticket_guys_b_team command line interface.",
    no_args_is_help=True,
)


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

    # help だけの呼び出しは repo lock 対象外とする。
    if is_help_only:
        _run_app_with_tgbt_call_log()
    else:
        with TGBTRepoLock():
            _run_app_with_tgbt_call_log()


def _run_app_with_tgbt_call_log() -> None:
    """
    Typer app を実行し、tgbt 呼び出しログを保存する。
    """
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
