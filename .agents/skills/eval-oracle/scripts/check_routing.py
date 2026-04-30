"""Check oracle ROUTING.md entries against the filesystem."""

import re
import sys
from pathlib import Path


ROUTING_FILE = "ROUTING.md"
ROUTING_ENTRY_RE = re.compile(r"^# `([^`]+)`\s*$")


def find_repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "AGENTS.md").is_file() and (candidate / "oracle").is_dir():
            return candidate
    raise RuntimeError("Could not find repository root containing AGENTS.md and oracle/")


def routing_dirs(routing_root: Path) -> list[Path]:
    return sorted(
        [routing_root, *(path for path in routing_root.rglob("*") if path.is_dir())],
        key=lambda path: path.relative_to(routing_root).as_posix(),
    )


def routing_entries(routing_path: Path) -> set[str]:
    entries: set[str] = set()
    for line in routing_path.read_text(encoding="utf-8").splitlines():
        match = ROUTING_ENTRY_RE.match(line)
        if match:
            entries.add(match.group(1))
    return entries


def actual_routing_targets(directory: Path) -> set[str]:
    markdown_files = {
        path.name
        for path in directory.glob("*.md")
        if path.is_file() and path.name != ROUTING_FILE
    }
    child_directories = {path.name for path in directory.iterdir() if path.is_dir()}
    return markdown_files | child_directories


def main() -> int:
    repo_root = find_repo_root()
    routing_root = repo_root / "oracle" / "docs"
    if not routing_root.is_dir():
        raise RuntimeError("Could not find oracle/docs/")

    issues: list[str] = []

    for directory in routing_dirs(routing_root):
        routing_path = directory / ROUTING_FILE
        rel_dir = directory.relative_to(repo_root).as_posix()

        if not routing_path.is_file():
            issues.append(f"missing-routing: {rel_dir}/{ROUTING_FILE}")
            continue

        listed_entries = routing_entries(routing_path)
        actual_entries = actual_routing_targets(directory)

        for entry_name in sorted(listed_entries - actual_entries):
            issues.append(
                f"listed-missing-entry: {rel_dir}/{ROUTING_FILE} lists {entry_name}, "
                f"but {rel_dir}/{entry_name} does not exist"
            )

        for entry_name in sorted(actual_entries - listed_entries):
            issues.append(
                f"unlisted-entry: {rel_dir}/{entry_name} exists, "
                f"but is not listed in {rel_dir}/{ROUTING_FILE}"
            )

    if not issues:
        print("OK: oracle routing matches filesystem")
        return 0

    print("ROUTING issues found:")
    for issue in issues:
        print(f"- {issue}")
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
