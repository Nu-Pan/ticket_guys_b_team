#!/usr/bin/env python3
"""Check oracle ROUTING.md file lists against the filesystem."""

from __future__ import annotations

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


def oracle_dirs(oracle_root: Path) -> list[Path]:
    return sorted(
        [oracle_root, *(path for path in oracle_root.rglob("*") if path.is_dir())],
        key=lambda path: path.relative_to(oracle_root).as_posix(),
    )


def routing_entries(routing_path: Path) -> set[str]:
    entries: set[str] = set()
    for line in routing_path.read_text(encoding="utf-8").splitlines():
        match = ROUTING_ENTRY_RE.match(line)
        if match:
            entries.add(match.group(1))
    return entries


def actual_markdown_files(directory: Path) -> set[str]:
    return {
        path.name
        for path in directory.glob("*.md")
        if path.is_file() and path.name != ROUTING_FILE
    }


def main() -> int:
    repo_root = find_repo_root()
    oracle_root = repo_root / "oracle"
    issues: list[str] = []

    for directory in oracle_dirs(oracle_root):
        routing_path = directory / ROUTING_FILE
        rel_dir = directory.relative_to(repo_root).as_posix()

        if not routing_path.is_file():
            issues.append(f"missing-routing: {rel_dir}/{ROUTING_FILE}")
            continue

        if directory == oracle_root:
            continue

        listed_files = routing_entries(routing_path)
        actual_files = actual_markdown_files(directory)

        for filename in sorted(listed_files - actual_files):
            issues.append(
                f"listed-missing-file: {rel_dir}/{ROUTING_FILE} lists {filename}, "
                f"but {rel_dir}/{filename} does not exist"
            )

        for filename in sorted(actual_files - listed_files):
            issues.append(
                f"unlisted-file: {rel_dir}/{filename} exists, "
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
