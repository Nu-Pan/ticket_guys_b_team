# std
from dataclasses import dataclass
from pathlib import Path
import typer

# tgbt
from state import io
from state.path import TGBT_PATH


def tgbt_init():
    """
    `tgbt init` の実装
    tgbt からの Codex CLI 呼び出しが、
    """

    # TODO
    # - `<repo-root>/.tgbt/.codex` を正しい状態にする
    # - `<repo-root>/AGENTS.md` を正しい状態にする
    # - `<repo-root>/AGENTS.md` 以外の `AGENTS.md` を削除
    # - `ROUTING.md` を正しい状態にする
    # - 既存の実行ログ類を削除

    io.ensure_env_storage(repo_root)
    with io.repository_lock(repo_root, command_name="env", plan_id=None):
        io.invalidate_env_log(repo_root)
        result = _ensure_legal_env_locked(repo_root)
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
