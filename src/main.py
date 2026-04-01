"""`ticket_guys_b_team` の CLI エントリポイント。"""

from pathlib import Path
import sys
from typing import Annotated

import typer


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import src.plan_service as plan_service
    from src.codex_common import CodexCliMode
else:
    from . import plan_service
    from .codex_common import CodexCliMode


# CLI の公開形をここで固定する。
app = typer.Typer(
    name="tgbt",
    help="ticket_guys_b_team command line interface.",
    no_args_is_help=True,
)


def _raise_not_implemented(*, command_name: str, impact: str, next_step: str) -> None:
    """未実装コマンドの共通エラー出力を行って終了する。

    Args:
        command_name: 未実装として扱うコマンド名。
        impact: 今回の呼び出しで起きていない影響範囲。
        next_step: 次に取るべき行動。
    """

    # NOTE: 未実装コマンドを成功扱いにすると利用者が state mutation 済みと誤認する。
    typer.echo(f"ERROR: {command_name} command is not implemented yet", err=True)
    typer.echo(f"Impact: {impact}", err=True)
    typer.echo(f"Next: {next_step}", err=True)
    raise typer.Exit(code=1)


def _raise_command_error(error: plan_service.PlanCommandError) -> None:
    """業務コマンドのエラーを CLI 向けに整形して終了する。"""

    typer.echo(f"ERROR: {error.cause}", err=True)
    typer.echo(f"Impact: {error.impact}", err=True)
    typer.echo(f"Next: {error.next_step}", err=True)
    raise typer.Exit(code=1)


@app.command()
def plan(
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
    """Plan 草案の生成または更新を受け付ける。"""

    try:
        result = plan_service.create_or_update_plan(
            request_text=request_text,
            plan_id=plan_id,
            codex_cli_mode=codex_cli_mode,
        )
    except plan_service.PlanCommandError as error:
        _raise_command_error(error)
    else:
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
    _raise_not_implemented(
        command_name="run",
        impact="no plan or ticket state mutation was performed",
        next_step="implement run orchestration before retrying this command",
    )


def main() -> None:
    """CLI アプリケーションを起動する。"""

    app(prog_name="tgbt")


if __name__ == "__main__":
    main()
