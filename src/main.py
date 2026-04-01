"""`ticket_guys_b_team` の CLI エントリポイント。"""

import enum
from typing import Annotated

import typer


# CLI の公開形をここで固定する。
app = typer.Typer(
    name="tgbt",
    help="ticket_guys_b_team command line interface.",
    no_args_is_help=True,
)


class CodexCliMode(str, enum.Enum):
    """`run` コマンドの Codex CLI 実行モード。"""

    LIVE = "live"
    STUB = "stub"


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
) -> None:
    """Plan 草案の生成または更新を受け付ける。"""

    _ = request_text, plan_id
    _raise_not_implemented(
        command_name="plan",
        impact="no plan file or front matter was created or updated",
        next_step="implement plan persistence before retrying this command",
    )


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
