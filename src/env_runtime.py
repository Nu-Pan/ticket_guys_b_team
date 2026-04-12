"""`tgbt env` 向けの runtime 生成と合法性判定を扱う。"""

from dataclasses import dataclass
import tomllib
from pathlib import Path

from . import state_io


CODEX_PROFILE_NAME = "tgbt-worker"


@dataclass(frozen=True)
class EnvIssue:
    """`tgbt env` の issue object を表す。"""

    code: str
    severity: str
    subject: str
    path: str
    message: str
    repair_policy: str

    def to_record(self) -> dict[str, object]:
        """audit log 向けの辞書表現を返す。"""

        return {
            "code": self.code,
            "severity": self.severity,
            "subject": self.subject,
            "path": self.path,
            "message": self.message,
            "repair_policy": self.repair_policy,
        }


@dataclass(frozen=True)
class EnvRepairAction:
    """`tgbt env` の repair action object を表す。"""

    subject: str
    path: str
    action_type: str
    result: str
    message: str

    def to_record(self) -> dict[str, object]:
        """audit log 向けの辞書表現を返す。"""

        return {
            "subject": self.subject,
            "path": self.path,
            "action_type": self.action_type,
            "result": self.result,
            "message": self.message,
        }


@dataclass(frozen=True)
class EnvLegalityReport:
    """env の合法性判定結果。"""

    blocking_issues: list[EnvIssue]
    diagnostics: list[EnvIssue]

    @property
    def is_legal(self) -> bool:
        """blocking issue がないかを返す。"""

        return not self.blocking_issues


def render_runtime_instructions(repo_root: Path) -> str:
    """worker runtime 指示の canonical content を返す。"""

    source_path = repo_root / "docs" / "spec" / "codex_worker_instructions.md"
    return source_path.read_text(encoding="utf-8")


def render_runtime_config(repo_root: Path) -> str:
    """repo-local Codex config の canonical content を返す。"""

    instructions_path = state_io.absolute_path_string(
        state_io.runtime_instructions_path(repo_root)
    )
    return (
        f"[profiles.{CODEX_PROFILE_NAME}]\n"
        f'model_instructions_file = "{instructions_path}"\n'
    )


def regenerate_repo_local_runtime(repo_root: Path) -> list[EnvRepairAction]:
    """repo-local runtime file を正本契約どおり再生成する。"""

    config_path = state_io.repo_local_codex_config_path(repo_root)
    instructions_path = state_io.runtime_instructions_path(repo_root)
    state_io.write_text_atomically(
        config_path,
        render_runtime_config(repo_root),
        create_only=False,
    )
    state_io.write_text_atomically(
        instructions_path,
        render_runtime_instructions(repo_root),
        create_only=False,
    )
    return [
        EnvRepairAction(
            subject="repo_local_codex_config",
            path=state_io.absolute_path_string(config_path),
            action_type="create_or_replace_file",
            result="updated",
            message="regenerated repo-local Codex config",
        ),
        EnvRepairAction(
            subject="runtime_instructions",
            path=state_io.absolute_path_string(instructions_path),
            action_type="create_or_replace_file",
            result="updated",
            message="regenerated runtime instructions from worker spec",
        ),
    ]


def evaluate_env_legality(repo_root: Path) -> EnvLegalityReport:
    """`tgbt env` のゴール条件に照らして合法性を判定する。"""

    blocking_issues: list[EnvIssue] = []
    diagnostics: list[EnvIssue] = []
    agents_path = state_io.agents_md_path(repo_root)
    if not agents_path.exists():
        diagnostics.append(
            _build_issue(
                code="missing_agents_md",
                severity="diagnostic",
                subject="agents_md",
                path=agents_path,
                message="AGENTS.md was not found",
                repair_policy="observe_only",
            )
        )

    repo_root_codex_dir = state_io.repo_root_codex_dir(repo_root)
    if repo_root_codex_dir.exists():
        diagnostics.append(
            _build_issue(
                code="repo_root_codex_dir_present",
                severity="diagnostic",
                subject="repo_root_codex_dir",
                path=repo_root_codex_dir,
                message="repository root .codex/ exists and is ignored by tgbt worker runtime",
                repair_policy="observe_only",
            )
        )

    instructions_path = state_io.runtime_instructions_path(repo_root)
    expected_instructions = render_runtime_instructions(repo_root)
    if not instructions_path.exists():
        blocking_issues.append(
            _build_issue(
                code="missing_runtime_instructions",
                severity="blocking",
                subject="runtime_instructions",
                path=instructions_path,
                message=".tgbt/instructions.md was not found",
                repair_policy="auto_repair",
            )
        )
    else:
        actual_instructions = instructions_path.read_text(encoding="utf-8")
        if actual_instructions != expected_instructions:
            blocking_issues.append(
                _build_issue(
                    code="mismatched_runtime_instructions",
                    severity="blocking",
                    subject="runtime_instructions",
                    path=instructions_path,
                    message=".tgbt/instructions.md does not match the generated runtime instructions",
                    repair_policy="auto_repair",
                )
            )

    config_path = state_io.repo_local_codex_config_path(repo_root)
    expected_config = render_runtime_config(repo_root)
    if not config_path.exists():
        blocking_issues.append(
            _build_issue(
                code="missing_repo_local_codex_config",
                severity="blocking",
                subject="repo_local_codex_config",
                path=config_path,
                message=".tgbt/.codex/config.toml was not found",
                repair_policy="auto_repair",
            )
        )
    else:
        actual_config = config_path.read_text(encoding="utf-8")
        if actual_config != expected_config:
            blocking_issues.append(
                _build_issue(
                    code="mismatched_repo_local_codex_config",
                    severity="blocking",
                    subject="repo_local_codex_config",
                    path=config_path,
                    message=".tgbt/.codex/config.toml does not match the generated runtime config",
                    repair_policy="auto_repair",
                )
            )
        else:
            blocking_issues.extend(
                _validate_runtime_config(
                    config_path=config_path,
                    actual_config=actual_config,
                )
            )

    return EnvLegalityReport(
        blocking_issues=blocking_issues,
        diagnostics=diagnostics,
    )


def reconcile_repo_local_runtime(repo_root: Path) -> list[EnvRepairAction]:
    """`tgbt env` が自動修正できる runtime file を再生成する。"""

    return regenerate_repo_local_runtime(repo_root)


def _build_issue(
    *,
    code: str,
    severity: str,
    subject: str,
    path: Path,
    message: str,
    repair_policy: str,
) -> EnvIssue:
    """issue object を構築する。"""

    return EnvIssue(
        code=code,
        severity=severity,
        subject=subject,
        path=state_io.absolute_path_string(path),
        message=message,
        repair_policy=repair_policy,
    )


def _validate_runtime_config(*, config_path: Path, actual_config: str) -> list[EnvIssue]:
    """runtime config の最低限の意味論を検証する。"""

    issues: list[EnvIssue] = []
    try:
        payload = tomllib.loads(actual_config)
    except tomllib.TOMLDecodeError:
        return [
            _build_issue(
                code="invalid_repo_local_codex_config_toml",
                severity="blocking",
                subject="repo_local_codex_config",
                path=config_path,
                message=".tgbt/.codex/config.toml is not valid TOML",
                repair_policy="auto_repair",
            )
        ]

    profiles = payload.get("profiles")
    if not isinstance(profiles, dict):
        return [
            _build_issue(
                code="missing_repo_local_codex_profiles_table",
                severity="blocking",
                subject="repo_local_codex_config",
                path=config_path,
                message=".tgbt/.codex/config.toml does not define [profiles]",
                repair_policy="auto_repair",
            )
        ]

    worker_profile = profiles.get(CODEX_PROFILE_NAME)
    if not isinstance(worker_profile, dict):
        return [
            _build_issue(
                code="missing_repo_local_codex_worker_profile",
                severity="blocking",
                subject="repo_local_codex_config",
                path=config_path,
                message=".tgbt/.codex/config.toml does not define profiles.tgbt-worker",
                repair_policy="auto_repair",
            )
        ]

    expected_path = state_io.absolute_path_string(config_path.parents[1] / "instructions.md")
    if worker_profile.get("model_instructions_file") != expected_path:
        issues.append(
            _build_issue(
                code="incorrect_model_instructions_file",
                severity="blocking",
                subject="repo_local_codex_config",
                path=config_path,
                message="profiles.tgbt-worker.model_instructions_file does not point to .tgbt/instructions.md",
                repair_policy="auto_repair",
            )
        )
    return issues
