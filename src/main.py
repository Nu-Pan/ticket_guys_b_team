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


class ApprovalTarget(str, enum.Enum):
    """`approve` コマンドの遷移先。"""

    IN_REVIEW = "in_review"
    APPROVED = "approved"


class RunMode(str, enum.Enum):
    """`run` コマンドの実行モード。"""

    DRY_RUN = "dry-run"
    PRODUCTION = "production"


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

    # NOTE: 仕様確定前のため、現時点では CLI 形状だけを提供する。
    _ = request_text, plan_id


@app.command()
def approve(
    plan_id: Annotated[
        str,
        typer.Argument(help="Plan identifier to update."),
    ],
    target: Annotated[
        ApprovalTarget,
        typer.Option("--to", help="Transition target state."),
    ],
) -> None:
    """Plan の承認状態を変更する。"""

    # NOTE: 状態遷移ロジックは未実装で、引数契約のみ先に固定する。
    _ = plan_id, target


@app.command()
def ticket(
    plan_id: Annotated[
        str,
        typer.Argument(help="Approved plan identifier."),
    ],
) -> None:
    """承認済み Plan からチケット群を生成する。"""

    _ = plan_id


@app.command()
def run(
    ticket_id: Annotated[
        str,
        typer.Argument(help="Ticket identifier to execute."),
    ],
    mode: Annotated[
        RunMode,
        typer.Argument(help="Execution mode."),
    ] = RunMode.PRODUCTION,
    model: Annotated[
        str | None,
        typer.Argument(help="Model name for execution."),
    ] = None,
    reasoning_effort: Annotated[
        str | None,
        typer.Argument(help="Reasoning effort for execution."),
    ] = None,
) -> None:
    """指定した Ticket の実行を受け付ける。"""

    _ = ticket_id, mode, model, reasoning_effort


@app.command("review-queue")
def review_queue(
    plan_id: Annotated[
        str | None,
        typer.Option("--plan-id", help="Optional plan identifier filter."),
    ] = None,
) -> None:
    """`review_pending` なチケット一覧を表示する。"""

    _ = plan_id


@app.command()
def artifacts(
    plan_id: Annotated[
        str | None,
        typer.Option("--plan-id", help="Plan identifier for artifact lookup."),
    ] = None,
    ticket_id: Annotated[
        str | None,
        typer.Option("--ticket-id", help="Ticket identifier for artifact lookup."),
    ] = None,
) -> None:
    """Plan または Ticket に紐づく成果物を表示する。"""

    _validate_artifact_target(plan_id=plan_id, ticket_id=ticket_id)


def _validate_artifact_target(*, plan_id: str | None, ticket_id: str | None) -> None:
    """`artifacts` コマンドの入力形を検証する。

    Args:
        plan_id: Plan 単位で参照する場合の識別子。
        ticket_id: Ticket 単位で参照する場合の識別子。

    Raises:
        typer.BadParameter: 指定数が契約に反している場合。
    """

    # 成果物参照は plan_id / ticket_id のどちらか一方に限定する。
    if plan_id is None and ticket_id is None:
        raise typer.BadParameter("Specify either --plan-id or --ticket-id.")

    if plan_id is not None and ticket_id is not None:
        raise typer.BadParameter("Specify only one of --plan-id or --ticket-id.")


def main() -> None:
    """CLI アプリケーションを起動する。"""

    app(prog_name="tgbt")


if __name__ == "__main__":
    main()
