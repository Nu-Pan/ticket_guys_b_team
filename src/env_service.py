"""`tgbt env` の one-shot bootstrap repair を扱う。"""

from dataclasses import dataclass

from . import env_runtime, state_io


ENV_IMPACT = "repo-local Codex runtime may remain illegal for tgbt"


@dataclass
class EnvCommandError(Exception):
    """`tgbt env` の CLI 向け失敗情報。"""

    cause: str
    impact: str
    next_step: str
    updated_files: list[str]
    remaining_issues: list[str]
    log_path: str | None = None

    def __str__(self) -> str:
        """例外メッセージを返す。"""

        return self.cause


@dataclass(frozen=True)
class EnvCommandResult:
    """`tgbt env` 成功時の出力。"""

    status: str
    updated_files: list[str]
    remaining_issues: list[str]
    log_path: str


def ensure_legal_env() -> EnvCommandResult:
    """`tgbt env` を one-shot reconcile として実行する。"""

    try:
        repo_root = state_io.get_repository_root()
        state_io.ensure_env_storage(repo_root)
        with state_io.repository_lock(repo_root, command_name="env", plan_id=None):
            initial_report = env_runtime.evaluate_env_legality(repo_root)
            updated_files: list[str] = []
            if not initial_report.is_legal:
                updated_files = env_runtime.reconcile_repo_local_runtime(repo_root)

            final_report = env_runtime.evaluate_env_legality(repo_root)
            log_path = state_io.env_log_path(repo_root)
            state_io.write_jsonl_log(
                log_path,
                [
                    {
                        "timestamp": state_io.current_timestamp(),
                        "event_type": "env_observed",
                        "issues": initial_report.issues,
                        "repo_root_codex_dir_exists": state_io.repo_root_codex_dir(
                            repo_root
                        ).exists(),
                    },
                    {
                        "timestamp": state_io.current_timestamp(),
                        "event_type": "env_reconciled",
                        "updated_files": updated_files,
                    },
                    {
                        "timestamp": state_io.current_timestamp(),
                        "event_type": "env_validated",
                        "goal_reached": final_report.is_legal,
                        "remaining_issues": final_report.issues,
                    },
                ],
            )

            if final_report.is_legal:
                return EnvCommandResult(
                    status="already_legal" if not updated_files else "legalized",
                    updated_files=updated_files,
                    remaining_issues=[],
                    log_path=state_io.absolute_path_string(log_path),
                )

            raise EnvCommandError(
                cause=(
                    "bootstrap issues remain after one-shot reconcile: "
                    + "; ".join(final_report.issues)
                ),
                impact=ENV_IMPACT,
                next_step=(
                    "fix the remaining issues reported by `tgbt env`, then rerun the command"
                ),
                updated_files=updated_files,
                remaining_issues=final_report.issues,
                log_path=state_io.absolute_path_string(log_path),
            )
    except FileExistsError as error:
        raise EnvCommandError(
            cause="repository lock is already held",
            impact=ENV_IMPACT,
            next_step=(
                "remove a stale repository lock after confirming no other tgbt process is running, then retry"
            ),
            updated_files=[],
            remaining_issues=[],
        ) from error
    except state_io.StateValidationError as error:
        raise EnvCommandError(
            cause=f"state validation failed: {error}",
            impact=ENV_IMPACT,
            next_step="restore a safe snapshot or fix the invalid state files before retrying",
            updated_files=[],
            remaining_issues=[],
        ) from error
    except OSError as error:
        raise EnvCommandError(
            cause=f"failed to persist env state: {error}",
            impact=ENV_IMPACT,
            next_step="check filesystem permissions and retry after restoring a safe snapshot if needed",
            updated_files=[],
            remaining_issues=[],
        ) from error
