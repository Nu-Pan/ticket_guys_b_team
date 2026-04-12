"""`tgbt env` の one-shot bootstrap repair を扱う。"""

from dataclasses import dataclass
from pathlib import Path

from . import env_runtime, state_io


ENV_IMPACT = "repo-local Codex runtime may remain illegal for tgbt"
ENV_AUDIT_SCHEMA_NAME = "env_audit"
ENV_AUDIT_SCHEMA_VERSION = 1


@dataclass
class EnvCommandError(Exception):
    """`tgbt env` の CLI 向け失敗情報。"""

    cause: str
    impact: str
    next_step: str
    updated_files: list[str]
    diagnostics: list[str]
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
    diagnostics: list[str]
    remaining_issues: list[str]
    log_path: str


def ensure_legal_env() -> EnvCommandResult:
    """`tgbt env` を one-shot reconcile として実行する。"""

    try:
        repo_root = state_io.get_repository_root()
        state_io.ensure_env_storage(repo_root)
        with state_io.repository_lock(repo_root, command_name="env", plan_id=None):
            state_io.invalidate_env_log(repo_root)
            return _ensure_legal_env_locked(repo_root)
    except FileExistsError as error:
        raise EnvCommandError(
            cause="repository lock is already held",
            impact=ENV_IMPACT,
            next_step=(
                "remove a stale repository lock after confirming no other tgbt process is running, then retry"
            ),
            updated_files=[],
            diagnostics=[],
            remaining_issues=[],
        ) from error
    except state_io.StateValidationError as error:
        raise EnvCommandError(
            cause=f"state validation failed: {error}",
            impact=ENV_IMPACT,
            next_step="restore a safe snapshot or fix the invalid state files before retrying",
            updated_files=[],
            diagnostics=[],
            remaining_issues=[],
        ) from error
    except OSError as error:
        raise EnvCommandError(
            cause=f"failed to persist env state: {error}",
            impact=ENV_IMPACT,
            next_step="check filesystem permissions and retry after restoring a safe snapshot if needed",
            updated_files=[],
            diagnostics=[],
            remaining_issues=[],
        ) from error


def _ensure_legal_env_locked(repo_root: Path) -> EnvCommandResult:
    """lock 取得後の `tgbt env` 本体フローを実行する。"""

    try:
        initial_report = env_runtime.evaluate_env_legality(repo_root)
    except Exception as error:
        log_path = _write_failure_log(
            repo_root=repo_root,
            events=[],
            failure_stage="observation",
            cause=f"bootstrap observation failed: {error}",
            diagnostics=[],
        )
        raise EnvCommandError(
            cause=f"bootstrap observation failed: {error}",
            impact=ENV_IMPACT,
            next_step="fix the bootstrap observation failure, then rerun `tgbt env`",
            updated_files=[],
            diagnostics=[],
            remaining_issues=[],
            log_path=log_path,
        ) from error

    repair_attempted = not initial_report.is_legal
    repair_actions: list[env_runtime.EnvRepairAction] = []
    if repair_attempted:
        try:
            repair_actions = env_runtime.reconcile_repo_local_runtime(repo_root)
        except Exception as error:
            log_path = _write_failure_log(
                repo_root=repo_root,
                events=[_build_observed_event(repo_root, initial_report)],
                failure_stage="repair",
                cause=f"bootstrap repair failed: {error}",
                diagnostics=initial_report.diagnostics,
            )
            raise EnvCommandError(
                cause=f"bootstrap repair failed: {error}",
                impact=ENV_IMPACT,
                next_step="fix the bootstrap repair failure, then rerun `tgbt env`",
                updated_files=[],
                diagnostics=_issue_messages(initial_report.diagnostics),
                remaining_issues=[],
                log_path=log_path,
            ) from error

    try:
        final_report = env_runtime.evaluate_env_legality(repo_root)
    except Exception as error:
        log_path = _write_failure_log(
            repo_root=repo_root,
            events=[
                _build_observed_event(repo_root, initial_report),
                _build_reconciled_event(
                    repo_root,
                    repair_attempted=repair_attempted,
                    repair_actions=repair_actions,
                ),
            ],
            failure_stage="validation",
            cause=f"bootstrap validation failed: {error}",
            diagnostics=initial_report.diagnostics,
        )
        raise EnvCommandError(
            cause=f"bootstrap validation failed: {error}",
            impact=ENV_IMPACT,
            next_step="fix the bootstrap validation failure, then rerun `tgbt env`",
            updated_files=_updated_files(repair_actions),
            diagnostics=_issue_messages(initial_report.diagnostics),
            remaining_issues=[],
            log_path=log_path,
        ) from error

    result_status = "already_legal" if not repair_attempted else "legalized"
    if not final_report.is_legal:
        result_status = "illegal"

    log_path = state_io.env_log_path(repo_root)
    state_io.write_jsonl_log(
        log_path,
        [
            _build_observed_event(repo_root, initial_report),
            _build_reconciled_event(
                repo_root,
                repair_attempted=repair_attempted,
                repair_actions=repair_actions,
            ),
            _build_validated_event(repo_root, final_report, outcome=result_status),
        ],
    )
    absolute_log_path = state_io.absolute_path_string(log_path)
    updated_files = _updated_files(repair_actions)

    if final_report.is_legal:
        return EnvCommandResult(
            status=result_status,
            updated_files=updated_files,
            diagnostics=_issue_messages(final_report.diagnostics),
            remaining_issues=[],
            log_path=absolute_log_path,
        )

    raise EnvCommandError(
        cause=(
            "bootstrap issues remain after one-shot reconcile: "
            + "; ".join(_issue_messages(final_report.blocking_issues))
        ),
        impact=ENV_IMPACT,
        next_step="fix the remaining issues reported by `tgbt env`, then rerun the command",
        updated_files=updated_files,
        diagnostics=_issue_messages(final_report.diagnostics),
        remaining_issues=_issue_messages(final_report.blocking_issues),
        log_path=absolute_log_path,
    )


def _write_failure_log(
    *,
    repo_root: Path,
    events: list[dict[str, object]],
    failure_stage: str,
    cause: str,
    diagnostics: list[env_runtime.EnvIssue],
) -> str | None:
    """`env_failed` を current invocation の audit artifact として保存する。"""

    log_path = state_io.env_log_path(repo_root)
    state_io.write_jsonl_log(
        log_path,
        [
            *events,
            _build_event(
                repo_root,
                event_type="env_failed",
                failure_stage=failure_stage,
                cause=cause,
                diagnostics=_issue_records(diagnostics),
            ),
        ],
    )
    return state_io.absolute_path_string(log_path)


def _build_observed_event(
    repo_root: Path,
    report: env_runtime.EnvLegalityReport,
) -> dict[str, object]:
    """`env_observed` record を構築する。"""

    return _build_event(
        repo_root,
        event_type="env_observed",
        blocking_issues=_issue_records(report.blocking_issues),
        diagnostics=_issue_records(report.diagnostics),
    )


def _build_reconciled_event(
    repo_root: Path,
    *,
    repair_attempted: bool,
    repair_actions: list[env_runtime.EnvRepairAction],
) -> dict[str, object]:
    """`env_reconciled` record を構築する。"""

    return _build_event(
        repo_root,
        event_type="env_reconciled",
        repair_attempted=repair_attempted,
        actions=[action.to_record() for action in repair_actions],
    )


def _build_validated_event(
    repo_root: Path,
    report: env_runtime.EnvLegalityReport,
    *,
    outcome: str,
) -> dict[str, object]:
    """`env_validated` record を構築する。"""

    return _build_event(
        repo_root,
        event_type="env_validated",
        outcome=outcome,
        goal_reached=report.is_legal,
        blocking_issues=_issue_records(report.blocking_issues),
        diagnostics=_issue_records(report.diagnostics),
    )


def _build_event(
    repo_root: Path,
    *,
    event_type: str,
    **payload: object,
) -> dict[str, object]:
    """共通 field を含む env audit event を構築する。"""

    event = {
        "schema_name": ENV_AUDIT_SCHEMA_NAME,
        "schema_version": ENV_AUDIT_SCHEMA_VERSION,
        "command_name": "env",
        "timestamp": state_io.current_timestamp(),
        "repo_root": state_io.absolute_path_string(repo_root),
        "event_type": event_type,
    }
    event.update(payload)
    return event


def _issue_records(issues: list[env_runtime.EnvIssue]) -> list[dict[str, object]]:
    """issue object 一覧を audit record 向けに変換する。"""

    return [issue.to_record() for issue in issues]


def _issue_messages(issues: list[env_runtime.EnvIssue]) -> list[str]:
    """CLI 表示用に issue message 一覧を返す。"""

    return [issue.message for issue in issues]


def _updated_files(repair_actions: list[env_runtime.EnvRepairAction]) -> list[str]:
    """更新済み file の absolute path 一覧を返す。"""

    return [action.path for action in repair_actions if action.result == "updated"]
