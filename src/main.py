# std
import sys
from typing import Annotated
import typer

# local
from sub_commands.init.tgbt_init import tgbt_init_impl
from sub_commands.plan.tgbt_plan import tgbt_plan_impl
from sub_commands.run.tgbt_run import tgbt_run_impl
from util.tgbt_call_log import (
    get_exit_code,
    reset_related_log_paths,
    write_tgbt_call_log,
)

# type app を構築
app = typer.Typer(
    name="tgbt",
    help="ticket_guys_b_team command line interface.",
    no_args_is_help=True,
)


@app.command()
def init() -> None:
    """
    tgbt の作業対象リポジトリを tgbt 実行にとって合法な状態へ整える。
    リポジトリへ tgbt を組み込む時に１回だけ呼び出されることを想定。
    必ず「カレントがリポジトリのルートである状態」でこのコマンドを実行する必要がある。
    """
    # 実装を呼び出し
    tgbt_init_impl()


@app.command("plan")
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
            help="Existing plan identifier to revise into a new plan.",
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


@app.command()
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
    # TODO
    #   repo lock はここで取る
    #   repo lock 取れなかったら失敗させる
    reset_related_log_paths()
    exit_code = 0
    exc_obj: BaseException | None = None
    exc_tb = None

    try:
        app(prog_name="tgbt")
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
