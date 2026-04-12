"""`tgbt env` 向けの runtime 生成と合法性判定を扱う。"""

from collections.abc import Mapping
from dataclasses import dataclass
import tomllib
from pathlib import Path

from .codex_common import VALID_REASONING_EFFORTS
from . import state_io


DEFAULT_PROFILE_MODEL = "gpt-5.2-codex"
PROFILE_DRAFTING = "tgbt-drafting"
PROFILE_WORKER = "tgbt-worker"
PROFILE_REVIEW = "tgbt-review"
RUNTIME_INSTRUCTIONS_TEMPLATE = """# tgbt Codex Runtime Instructions

- Treat the task instruction passed from `tgbt` as the highest-priority work instruction.
- Treat repository documents under `docs/` as authoritative when reading repository-local documentation.
- Do not use skills.
- Do not use sub agents.
- Do not rely on `~/.codex` or repository-root `.codex/`.
- Treat the repo-local runtime under `.tgbt/` as the authoritative Codex CLI configuration.
- `AGENTS.md` may be read as bootstrap context, but it is not the authoritative source for runtime instructions.
"""


@dataclass(frozen=True)
class CodexProfileSpec:
    """repo-local runtime が要求する Codex profile 定義。"""

    name: str
    model: str
    model_reasoning_effort: str
    approval_policy: str
    sandbox_mode: str


PROFILE_SPECS = (
    CodexProfileSpec(
        name=PROFILE_DRAFTING,
        model=DEFAULT_PROFILE_MODEL,
        model_reasoning_effort="high",
        approval_policy="never",
        sandbox_mode="read-only",
    ),
    CodexProfileSpec(
        name=PROFILE_WORKER,
        model=DEFAULT_PROFILE_MODEL,
        model_reasoning_effort="high",
        approval_policy="never",
        sandbox_mode="workspace-write",
    ),
    CodexProfileSpec(
        name=PROFILE_REVIEW,
        model=DEFAULT_PROFILE_MODEL,
        model_reasoning_effort="high",
        approval_policy="never",
        sandbox_mode="read-only",
    ),
)
PROFILE_SPECS_BY_NAME = {profile.name: profile for profile in PROFILE_SPECS}
CALL_PURPOSE_TO_PROFILE_NAME = {
    "plan_drafting": PROFILE_DRAFTING,
    "ticket_planning": PROFILE_DRAFTING,
    "ticket_execution": PROFILE_WORKER,
    "followup_planning": PROFILE_REVIEW,
}


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


def resolve_profile_name_for_call_purpose(call_purpose: str) -> str:
    """`call_purpose` から canonical profile 名を解決する。"""

    try:
        return CALL_PURPOSE_TO_PROFILE_NAME[call_purpose]
    except KeyError as error:
        raise ValueError(f"unsupported call_purpose: {call_purpose}") from error


def resolve_profile_spec_for_call_purpose(call_purpose: str) -> CodexProfileSpec:
    """`call_purpose` に対応する profile 定義を返す。"""

    profile_name = resolve_profile_name_for_call_purpose(call_purpose)
    return PROFILE_SPECS_BY_NAME[profile_name]


def render_runtime_instructions(repo_root: Path) -> str:
    """runtime 指示の canonical content を返す。"""

    del repo_root
    return RUNTIME_INSTRUCTIONS_TEMPLATE


def render_runtime_config(repo_root: Path) -> str:
    """repo-local Codex config の canonical content を返す。"""

    instructions_path = state_io.absolute_path_string(
        state_io.runtime_instructions_path(repo_root)
    )
    blocks: list[str] = []
    for profile in PROFILE_SPECS:
        blocks.append(
            "\n".join(
                (
                    f"[profiles.{profile.name}]",
                    f'model = "{profile.model}"',
                    f'model_reasoning_effort = "{profile.model_reasoning_effort}"',
                    f'approval_policy = "{profile.approval_policy}"',
                    f'sandbox_mode = "{profile.sandbox_mode}"',
                    f'model_instructions_file = "{instructions_path}"',
                )
            )
        )
    return "\n\n".join(blocks) + "\n"


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
            message="regenerated shared runtime instructions for tgbt Codex invocations",
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
                message="repository root .codex/ exists and is ignored by tgbt repo-local runtime profiles",
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
                    message=".tgbt/instructions.md does not match the canonical runtime instructions generated by tgbt env",
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
        semantic_issues = _validate_runtime_config(
            config_path=config_path,
            actual_config=actual_config,
        )
        if actual_config != expected_config and not semantic_issues:
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
        blocking_issues.extend(semantic_issues)

    return EnvLegalityReport(
        blocking_issues=blocking_issues,
        diagnostics=diagnostics,
    )


def reconcile_repo_local_runtime(repo_root: Path) -> list[EnvRepairAction]:
    """`tgbt env` が自動修正できる runtime file を再生成する。"""

    return regenerate_repo_local_runtime(repo_root)


def require_legal_live_runtime(repo_root: Path) -> None:
    """live 実行前に repo-local runtime の blocking issue 不在を保証する。"""

    report = evaluate_env_legality(repo_root)
    if report.is_legal:
        return

    issue_summary = "; ".join(issue.message for issue in report.blocking_issues)
    raise RuntimeError(
        "repo-local Codex runtime is illegal; run `tgbt env` first: "
        + issue_summary
    )


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

    expected_path = state_io.absolute_path_string(config_path.parents[1] / "instructions.md")
    for profile in PROFILE_SPECS:
        issues.extend(
            _validate_profile_config(
                config_path=config_path,
                profile_payload=profiles.get(profile.name),
                profile_spec=profile,
                expected_instructions_path=expected_path,
            )
        )
    return issues


def _validate_profile_config(
    *,
    config_path: Path,
    profile_payload: object,
    profile_spec: CodexProfileSpec,
    expected_instructions_path: str,
) -> list[EnvIssue]:
    """required profile 1 件の意味論を検証する。"""

    if not isinstance(profile_payload, Mapping):
        return [
            _build_issue(
                code="missing_repo_local_codex_profile",
                severity="blocking",
                subject="repo_local_codex_config",
                path=config_path,
                message=(
                    ".tgbt/.codex/config.toml does not define "
                    f"profiles.{profile_spec.name}"
                ),
                repair_policy="auto_repair",
            )
        ]

    issues: list[EnvIssue] = []
    expected_values = {
        "model": profile_spec.model,
        "model_reasoning_effort": profile_spec.model_reasoning_effort,
        "approval_policy": profile_spec.approval_policy,
        "sandbox_mode": profile_spec.sandbox_mode,
        "model_instructions_file": expected_instructions_path,
    }
    for field_name, expected_value in expected_values.items():
        if profile_payload.get(field_name) != expected_value:
            issues.append(
                _build_issue(
                    code=f"incorrect_profile_{field_name}",
                    severity="blocking",
                    subject="repo_local_codex_config",
                    path=config_path,
                    message=(
                        f"profiles.{profile_spec.name}.{field_name} does not match "
                        "the canonical tgbt runtime profile"
                    ),
                    repair_policy="auto_repair",
                )
            )

    reasoning_effort = profile_payload.get("model_reasoning_effort")
    if reasoning_effort not in VALID_REASONING_EFFORTS:
        issues.append(
            _build_issue(
                code="invalid_profile_model_reasoning_effort",
                severity="blocking",
                subject="repo_local_codex_config",
                path=config_path,
                message=(
                    f"profiles.{profile_spec.name}.model_reasoning_effort must be one "
                    "of minimal|low|medium|high|xhigh"
                ),
                repair_policy="auto_repair",
            )
        )
    return issues
