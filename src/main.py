"""`ticket_guys_b_team` の CLI エントリポイント。"""

from pathlib import Path
import sys
from typing import Annotated

import typer



if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import src.env_service as env_service
    import src.plan_service as plan_service
    from src.codex_common import CodexCliMode
else:
    from . import env_service, plan_service
    from .codex_common import CodexCliMode


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


def _raise_not_implemented(*, command_name: str, impact: str, next_step: str) -> None:
    """未実装コマンドの共通エラー出力を行って終了する。"""

    typer.echo(f"ERROR: {command_name} command is not implemented yet", err=True)
    typer.echo(f"Impact: {impact}", err=True)
    typer.echo(f"Next: {next_step}", err=True)
    raise typer.Exit(code=1)


def _raise_plan_command_error(error: plan_service.PlanCommandError) -> None:
    """docs Plan エラーを CLI 向けに整形して終了する。"""

    typer.echo(f"ERROR: {error.cause}", err=True)
    typer.echo(f"Impact: {error.impact}", err=True)
    typer.echo(f"Next: {error.next_step}", err=True)
    raise typer.Exit(code=1)


def _raise_env_command_error(error: env_service.EnvCommandError) -> None:
    """env エラーを CLI 向けに整形して終了する。"""

    typer.echo(f"ERROR: {error.cause}", err=True)
    if error.updated_files:
        typer.echo("Updated files:", err=True)
        for path in error.updated_files:
            typer.echo(f"- {path}", err=True)
    if error.diagnostics:
        typer.echo("Diagnostics:", err=True)
        for message in error.diagnostics:
            typer.echo(f"- {message}", err=True)
    if error.remaining_issues:
        typer.echo("Remaining issues:", err=True)
        for issue in error.remaining_issues:
            typer.echo(f"- {issue}", err=True)
    if error.log_path is not None:
        typer.echo(f"Log: {error.log_path}", err=True)
    typer.echo(f"Impact: {error.impact}", err=True)
    typer.echo(f"Next: {error.next_step}", err=True)
    raise typer.Exit(code=1)


@app.command()
def env() -> None:
    """repo-local Codex runtime を one-shot で合法状態へ整える。"""

    try:
        result = env_service.ensure_legal_env()
    except env_service.EnvCommandError as error:
        _raise_env_command_error(error)
    else:
        typer.echo(f"Status: {result.status}")
        if result.updated_files:
            typer.echo("Updated files:")
            for path in result.updated_files:
                typer.echo(f"- {path}")
        if result.diagnostics:
            typer.echo("Diagnostics:")
            for message in result.diagnostics:
                typer.echo(f"- {message}")
        if result.remaining_issues:
            typer.echo("Remaining issues:")
            for issue in result.remaining_issues:
                typer.echo(f"- {issue}")
        typer.echo(f"Log: {result.log_path}")


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
    """docs 修正用 Plan 草案の生成または更新を受け付ける。"""

    try:
        result = plan_service.create_or_update_plan(
            request_text=request_text,
            plan_id=plan_id,
            codex_cli_mode=codex_cli_mode,
        )
    except plan_service.PlanCommandError as error:
        _raise_plan_command_error(error)
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
    app(prog_name="tgbt")

if __name__ == "__main__":
    main()
