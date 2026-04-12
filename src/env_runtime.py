"""`tgbt env` 向けの runtime 生成と合法性判定を扱う。"""

from dataclasses import dataclass
import tomllib
from pathlib import Path

from . import state_io


CODEX_PROFILE_NAME = "tgbt-worker"


@dataclass(frozen=True)
class EnvLegalityReport:
    """env の合法性判定結果。"""

    blocking_issues: list[str]
    diagnostics: list[str]

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


def regenerate_repo_local_runtime(repo_root: Path) -> list[str]:
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
        state_io.absolute_path_string(config_path),
        state_io.absolute_path_string(instructions_path),
    ]


def evaluate_env_legality(repo_root: Path) -> EnvLegalityReport:
    """`tgbt env` のゴール条件に照らして合法性を判定する。"""

    blocking_issues: list[str] = []
    diagnostics: list[str] = []
    agents_path = state_io.agents_md_path(repo_root)
    if not agents_path.exists():
        diagnostics.append("AGENTS.md was not found")

    if state_io.repo_root_codex_dir(repo_root).exists():
        diagnostics.append(
            "repository root .codex/ exists and is ignored by tgbt worker runtime"
        )

    instructions_path = state_io.runtime_instructions_path(repo_root)
    expected_instructions = render_runtime_instructions(repo_root)
    if not instructions_path.exists():
        blocking_issues.append(".tgbt/instructions.md was not found")
    else:
        actual_instructions = instructions_path.read_text(encoding="utf-8")
        if actual_instructions != expected_instructions:
            blocking_issues.append(
                ".tgbt/instructions.md does not match the generated runtime instructions"
            )

    config_path = state_io.repo_local_codex_config_path(repo_root)
    expected_config = render_runtime_config(repo_root)
    if not config_path.exists():
        blocking_issues.append(".tgbt/.codex/config.toml was not found")
    else:
        actual_config = config_path.read_text(encoding="utf-8")
        if actual_config != expected_config:
            blocking_issues.append(
                ".tgbt/.codex/config.toml does not match the generated runtime config"
            )
        else:
            blocking_issues.extend(
                _validate_runtime_config(
                    repo_root=repo_root,
                    actual_config=actual_config,
                )
            )

    return EnvLegalityReport(
        blocking_issues=blocking_issues,
        diagnostics=diagnostics,
    )


def reconcile_repo_local_runtime(repo_root: Path) -> list[str]:
    """`tgbt env` が自動修正できる runtime file を再生成する。"""

    return regenerate_repo_local_runtime(repo_root)


def _validate_runtime_config(*, repo_root: Path, actual_config: str) -> list[str]:
    """runtime config の最低限の意味論を検証する。"""

    issues: list[str] = []
    try:
        payload = tomllib.loads(actual_config)
    except tomllib.TOMLDecodeError:
        return [".tgbt/.codex/config.toml is not valid TOML"]

    profiles = payload.get("profiles")
    if not isinstance(profiles, dict):
        return [".tgbt/.codex/config.toml does not define [profiles]"]

    worker_profile = profiles.get(CODEX_PROFILE_NAME)
    if not isinstance(worker_profile, dict):
        return [".tgbt/.codex/config.toml does not define profiles.tgbt-worker"]

    expected_path = state_io.absolute_path_string(state_io.runtime_instructions_path(repo_root))
    if worker_profile.get("model_instructions_file") != expected_path:
        issues.append(
            "profiles.tgbt-worker.model_instructions_file does not point to .tgbt/instructions.md"
        )
    return issues
