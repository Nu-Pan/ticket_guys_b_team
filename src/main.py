# std
from typing import Annotated
import typer

# local
from cmd.init.service import tgbt_init
from cmd.plan.docs.service import tgbt_plan_docs
from agent_wrapper.agent_wrapper import CodexCliMode
from util.error import tgbt_raise


# type app を構築
app = typer.Typer(
    name="tgbt",
    help="ticket_guys_b_team command line interface.",
    no_args_is_help=True,
)
plan_app = typer.Typer(
    help="Plan-related commands.",
    no_args_is_help=True,
)
app.add_typer(plan_app, name="plan")


@app.command()
def init() -> None:
    """
    tgbt の作業対象リポジトリを tgbt 実行にとって合法な状態へ整える。
    リポジトリへ tgbt を組み込む時に１回だけ呼び出されることを想定。
    """
    # 実装を呼び出し
    tgbt_init()



@plan_app.command("docs")
def plan_docs(
    request_text: Annotated[
        str,
        typer.Argument(help="Plan generation request text."),
    ],
    plan_id: Annotated[
        str | None,
        typer.Option("--plan-id", help="Existing plan identifier to update."),
    ] = None,
    codex_cli_mode: Annotated[
        CodexCliMode,
        typer.Option("--codex-cli-mode", help="Codex CLI execution mode."),
    ] = CodexCliMode.LIVE,
) -> None:
    """
    docs 修正作業の計画書を作成する。
    plan_id 未指定の場合は新規に計画書を作成する。
    plan_id を指定された場合は既存計画書を更新する。
    """
    # 実装を呼び出し
    result = tgbt_plan_docs(
        request_text=request_text,
        plan_id=plan_id,
        codex_cli_mode=codex_cli_mode,
    )
    # 結果をダンプ
    typer.echo(f"Updated: {result.updated_path}")
    typer.echo(f"Plan revision: {result.plan_revision}")
    typer.echo(f"Status: {result.status}")
    typer.echo(f"Session record: {result.session_record_path}")


@app.command()
def run(
    plan_id: Annotated[
        str,
        typer.Option("--plan-id", help="Plan identifier to execute."),
    ],
    codex_cli_mode: Annotated[
        CodexCliMode,
        typer.Option("--codex-cli-mode", help="Codex CLI execution mode."),
    ] = CodexCliMode.LIVE,
) -> None:
    """指定した Plan を起点に run を実行する。"""

    _ = plan_id, codex_cli_mode
    tgbt_raise(
        "tgbt run は未実装です",
        "将来の作業として tgbt run を実装する必要があります",
    )


def main() -> None:
    # TODO
    #   repo lock はここで取る
    #   repo lock 取れなかったら失敗させる
    app(prog_name="tgbt")

if __name__ == "__main__":
    main()
