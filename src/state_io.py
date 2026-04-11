"""永続化と state file 入出力を扱う。"""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import socket
import sys
import tempfile

import yaml


PLAN_SECTION_ORDER = (
    "目的",
    "スコープ外",
    "成果物",
    "制約",
    "受け入れ条件",
    "未確定事項",
    "想定リスク",
    "実行方針",
)
PLAN_STATUSES = {"draft", "running", "settled"}


class StateValidationError(ValueError):
    """state file の検証失敗を表す。"""


@dataclass(frozen=True)
class PlanDocument:
    """Plan file の正規化済み表現。"""

    metadata: dict[str, object]
    sections: dict[str, str]


@dataclass(frozen=True)
class CounterState:
    """`counters.json` の正規化済み表現。"""

    next_ticket_seq: int
    next_run_seq: int
    next_codex_call_seq: int
    updated_at: str


def get_repository_root() -> Path:
    """現在の process が対象にしている repository root を返す。"""

    try:
        return Path.cwd()
    except OSError as error:
        raise StateValidationError(
            f"failed to resolve current working directory: {error}"
        ) from error


def absolute_path_string(path: Path) -> str:
    """filesystem absolute path を文字列化する。"""

    return str(path if path.is_absolute() else path.resolve())


def artifacts_root(repo_root: Path) -> Path:
    """artifact 配下のルートパスを返す。"""

    return repo_root / ".tgbt"


def plans_dir(repo_root: Path) -> Path:
    """Plan 保存先を返す。"""

    return artifacts_root(repo_root) / "plans"


def codex_dir(repo_root: Path) -> Path:
    """Codex session record 保存先を返す。"""

    return artifacts_root(repo_root) / "codex"


def logs_dir(repo_root: Path) -> Path:
    """実行ログ保存先を返す。"""

    return artifacts_root(repo_root) / "logs"


def tickets_dir(repo_root: Path) -> Path:
    """Ticket 保存先を返す。"""

    return artifacts_root(repo_root) / "tickets"


def locks_dir(repo_root: Path) -> Path:
    """lock 保存先を返す。"""

    return artifacts_root(repo_root) / "system" / "locks"


def lock_path(repo_root: Path) -> Path:
    """repository lock の保存先を返す。"""

    return locks_dir(repo_root) / "repository.lock.json"


def counters_path(repo_root: Path) -> Path:
    """counters.json の保存先を返す。"""

    return artifacts_root(repo_root) / "system" / "counters.json"


def repo_local_codex_home(repo_root: Path) -> Path:
    """repo-local な `CODEX_HOME` の保存先を返す。"""

    return artifacts_root(repo_root) / ".codex"


def repo_local_codex_config_path(repo_root: Path) -> Path:
    """repo-local Codex config の保存先を返す。"""

    return repo_local_codex_home(repo_root) / "config.toml"


def runtime_instructions_path(repo_root: Path) -> Path:
    """worker runtime 指示の保存先を返す。"""

    return artifacts_root(repo_root) / "instructions.md"


def repo_root_codex_dir(repo_root: Path) -> Path:
    """repository 直下 `.codex/` の canonical path を返す。"""

    return repo_root / ".codex"


def agents_md_path(repo_root: Path) -> Path:
    """`AGENTS.md` の canonical path を返す。"""

    return repo_root / "AGENTS.md"


def plan_path(repo_root: Path, plan_id: str) -> Path:
    """Plan file のパスを返す。"""

    return plans_dir(repo_root) / f"{plan_id}.md"


def run_log_path(repo_root: Path, *, plan_id: str, run_id: str) -> Path:
    """run log の保存先を返す。"""

    return logs_dir(repo_root) / f"{plan_id}-{run_id}.jsonl"


def env_log_path(repo_root: Path) -> Path:
    """`tgbt env` の canonical log path を返す。"""

    return logs_dir(repo_root) / "env-latest.jsonl"


def ensure_plan_storage(repo_root: Path) -> None:
    """`plan` 実行に必要な directory を作成する。"""

    plans_dir(repo_root).mkdir(parents=True, exist_ok=True)
    tickets_dir(repo_root).mkdir(parents=True, exist_ok=True)
    codex_dir(repo_root).mkdir(parents=True, exist_ok=True)
    logs_dir(repo_root).mkdir(parents=True, exist_ok=True)
    locks_dir(repo_root).mkdir(parents=True, exist_ok=True)
    repo_local_codex_home(repo_root).mkdir(parents=True, exist_ok=True)


def ensure_env_storage(repo_root: Path) -> None:
    """`env` 実行に必要な directory を作成する。"""

    logs_dir(repo_root).mkdir(parents=True, exist_ok=True)
    locks_dir(repo_root).mkdir(parents=True, exist_ok=True)
    repo_local_codex_home(repo_root).mkdir(parents=True, exist_ok=True)


def current_timestamp() -> str:
    """ローカルタイムゾーン付きの ISO 8601 文字列を返す。"""

    return datetime.now().astimezone().isoformat(timespec="seconds")


def parse_timestamp(value: object, *, field_name: str) -> datetime:
    """ISO 8601 文字列を検証して datetime に変換する。"""

    if not isinstance(value, str):
        raise StateValidationError(f"{field_name} must be a string")

    try:
        return datetime.fromisoformat(value)
    except ValueError as error:
        raise StateValidationError(f"{field_name} must be ISO 8601") from error


def load_markdown_with_front_matter(path: Path) -> tuple[dict[str, object], str]:
    """front matter 付き Markdown を読む。"""

    text = path.read_text(encoding="utf-8")
    lines = text.replace("\r\n", "\n").split("\n")

    if not lines or lines[0] != "---":
        raise StateValidationError("front matter must start with ---")

    end_index = None
    for index in range(1, len(lines)):
        if lines[index] == "---":
            end_index = index
            break

    if end_index is None:
        raise StateValidationError("front matter terminator --- was not found")

    payload = yaml.safe_load("\n".join(lines[1:end_index]))
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise StateValidationError("front matter must be a mapping")

    body = "\n".join(lines[end_index + 1 :]).lstrip("\n")
    return dict(payload), body


def parse_plan_sections(body: str) -> dict[str, str]:
    """Plan 本文を必須 section に分解する。"""

    lines = body.replace("\r\n", "\n").split("\n")
    headings: list[tuple[int, str]] = []

    for index, line in enumerate(lines):
        if line.startswith("# "):
            headings.append((index, line[2:].strip()))

    heading_names = [name for _, name in headings]
    expected_names = list(PLAN_SECTION_ORDER)
    if heading_names != expected_names:
        raise StateValidationError(
            "plan sections must exist exactly once and in the canonical order"
        )

    sections: dict[str, str] = {}
    for index, (start_line, title) in enumerate(headings):
        end_line = headings[index + 1][0] if index + 1 < len(headings) else len(lines)
        content = "\n".join(lines[start_line + 1 : end_line]).strip("\n")
        sections[title] = content

    return sections


def validate_plan_metadata(metadata: dict[str, object], *, expected_plan_id: str) -> None:
    """Plan front matter を検証する。"""

    required_fields = (
        "plan_id",
        "plan_revision",
        "title",
        "status",
        "created_at",
        "updated_at",
    )
    for field_name in required_fields:
        if field_name not in metadata:
            raise StateValidationError(f"missing required field: {field_name}")

    if metadata["plan_id"] != expected_plan_id:
        raise StateValidationError("plan_id does not match the target file")

    plan_revision = metadata["plan_revision"]
    if not isinstance(plan_revision, int) or plan_revision < 1:
        raise StateValidationError("plan_revision must be a positive integer")

    title = metadata["title"]
    if not isinstance(title, str) or not title.strip():
        raise StateValidationError("title must be a non-empty string")

    status = metadata["status"]
    if status not in PLAN_STATUSES:
        raise StateValidationError("status must be one of draft/running/settled")

    created_at = parse_timestamp(metadata["created_at"], field_name="created_at")
    updated_at = parse_timestamp(metadata["updated_at"], field_name="updated_at")
    if updated_at < created_at:
        raise StateValidationError("updated_at must be greater than or equal to created_at")


def load_plan_document(path: Path) -> PlanDocument:
    """Plan file を読み込み、正規化済み表現へ変換する。"""

    metadata, body = load_markdown_with_front_matter(path)
    validate_plan_metadata(metadata, expected_plan_id=path.stem)
    sections = parse_plan_sections(body)
    return PlanDocument(metadata=metadata, sections=sections)


def render_plan_document(metadata: dict[str, object], sections: dict[str, str]) -> str:
    """Plan file を canonical markdown へ render する。"""

    validate_plan_metadata(metadata, expected_plan_id=str(metadata["plan_id"]))

    ordered_sections: dict[str, str] = {}
    for section_name in PLAN_SECTION_ORDER:
        if section_name not in sections:
            raise StateValidationError(f"missing required section: {section_name}")
        ordered_sections[section_name] = sections[section_name]

    front_matter = yaml.safe_dump(
        metadata,
        allow_unicode=True,
        sort_keys=False,
    ).strip()

    body_parts: list[str] = []
    for section_name in PLAN_SECTION_ORDER:
        content = ordered_sections[section_name].strip("\n")
        if content:
            body_parts.append(f"# {section_name}\n{content}")
        else:
            body_parts.append(f"# {section_name}")

    body = "\n\n".join(body_parts)
    return f"---\n{front_matter}\n---\n\n{body}\n"


def load_ticket_metadata(path: Path) -> dict[str, object]:
    """Ticket front matter を読む。"""

    metadata, _ = load_markdown_with_front_matter(path)
    return metadata


def default_counter_state() -> CounterState:
    """初期 counters 値を返す。"""

    now = current_timestamp()
    return CounterState(
        next_ticket_seq=1,
        next_run_seq=1,
        next_codex_call_seq=1,
        updated_at=now,
    )


def load_counter_state(repo_root: Path) -> CounterState:
    """`counters.json` を読み込む。"""

    path = counters_path(repo_root)
    if not path.exists():
        return default_counter_state()

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StateValidationError("counters.json must be valid JSON") from error

    if not isinstance(payload, dict):
        raise StateValidationError("counters.json must be a JSON object")

    next_ticket_seq = payload.get("next_ticket_seq")
    next_run_seq = payload.get("next_run_seq")
    next_codex_call_seq = payload.get("next_codex_call_seq")
    updated_at = payload.get("updated_at")
    if not isinstance(next_ticket_seq, int) or next_ticket_seq < 1:
        raise StateValidationError("next_ticket_seq must be a positive integer")
    if not isinstance(next_run_seq, int) or next_run_seq < 1:
        raise StateValidationError("next_run_seq must be a positive integer")
    if not isinstance(next_codex_call_seq, int) or next_codex_call_seq < 1:
        raise StateValidationError("next_codex_call_seq must be a positive integer")
    parse_timestamp(updated_at, field_name="updated_at")
    assert isinstance(updated_at, str)
    return CounterState(
        next_ticket_seq=next_ticket_seq,
        next_run_seq=next_run_seq,
        next_codex_call_seq=next_codex_call_seq,
        updated_at=updated_at,
    )


def write_counter_state(repo_root: Path, counter_state: CounterState) -> None:
    """`counters.json` を publish する。"""

    payload = {
        "next_ticket_seq": counter_state.next_ticket_seq,
        "next_run_seq": counter_state.next_run_seq,
        "next_codex_call_seq": counter_state.next_codex_call_seq,
        "updated_at": counter_state.updated_at,
    }
    write_text_atomically(
        counters_path(repo_root),
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        create_only=False,
    )


def allocate_codex_call_id(repo_root: Path) -> str:
    """`codex_call_id` を採番し、`counters.json` へ反映する。"""

    counter_state = load_counter_state(repo_root)
    codex_call_id = f"call-{counter_state.next_codex_call_seq:04d}"
    updated_state = CounterState(
        next_ticket_seq=counter_state.next_ticket_seq,
        next_run_seq=counter_state.next_run_seq,
        next_codex_call_seq=counter_state.next_codex_call_seq + 1,
        updated_at=current_timestamp(),
    )
    write_counter_state(repo_root, updated_state)
    return codex_call_id


def allocate_run_id(repo_root: Path) -> str:
    """`run_id` を採番し、`counters.json` へ反映する。"""

    counter_state = load_counter_state(repo_root)
    run_id = f"run-{counter_state.next_run_seq:04d}"
    updated_state = CounterState(
        next_ticket_seq=counter_state.next_ticket_seq,
        next_run_seq=counter_state.next_run_seq + 1,
        next_codex_call_seq=counter_state.next_codex_call_seq,
        updated_at=current_timestamp(),
    )
    write_counter_state(repo_root, updated_state)
    return run_id


def write_jsonl_log(path: Path, entries: list[dict[str, object]]) -> None:
    """JSONL 形式の execution log を保存する。"""

    content = "".join(
        json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n"
        for entry in entries
    )
    write_text_atomically(path, content, create_only=False)


def plan_drafting_session_record_relative_path(
    repo_root: Path,
    *,
    plan_id: str,
    plan_revision: int,
    codex_call_id: str,
) -> str:
    """`plan_drafting` session record の relative path を返す。"""

    path = codex_dir(repo_root) / (
        f"{plan_id}-rev-{plan_revision}-{codex_call_id}-plan_drafting.json"
    )
    return str(path.relative_to(repo_root))


def _fsync_directory(path: Path) -> None:
    """directory entry の durability を高める。"""

    directory_fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def write_text_atomically(path: Path, content: str, *, create_only: bool) -> None:
    """authoritative mutable file を atomic に publish する。"""

    path.parent.mkdir(parents=True, exist_ok=True)

    if create_only:
        file_descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        try:
            with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
        except Exception:
            if path.exists():
                path.unlink(missing_ok=True)
            raise

        _fsync_directory(path.parent)
        return

    temp_file_descriptor, temp_path_str = tempfile.mkstemp(
        prefix=f".{path.name}.tmp-",
        dir=path.parent,
        text=True,
    )
    temp_path = Path(temp_path_str)

    try:
        with os.fdopen(temp_file_descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(temp_path, path)
        _fsync_directory(path.parent)
    finally:
        temp_path.unlink(missing_ok=True)


@contextmanager
def repository_lock(
    repo_root: Path,
    *,
    command_name: str,
    plan_id: str | None,
) -> Iterator[None]:
    """repository-wide lock を保持する。"""

    locks_dir(repo_root).mkdir(parents=True, exist_ok=True)

    payload = {
        "command_name": command_name,
        "acquired_at": current_timestamp(),
        "plan_id": plan_id,
        "pid": os.getpid(),
        "hostname": socket.gethostname(),
        "command_line": " ".join(
            os.path.basename(arg) if index == 0 else arg
            for index, arg in enumerate(sys.argv)
        ),
    }
    content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    write_text_atomically(lock_path(repo_root), content, create_only=True)

    try:
        yield
    finally:
        lock_path(repo_root).unlink(missing_ok=True)
