"""Normalize one <tgbt-root>/oracle/docs/**/ROUTING.md file."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ROUTING_FILE = "ROUTING.md"
ENTRY_RE = re.compile(r"^# `([^`]+)`\s*$")
TODO_BODY = "- TODO: ルーティング本文を記述する"


def find_repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "AGENTS.md").is_file() and (candidate / "oracle" / "docs").is_dir():
            return candidate
    raise RuntimeError("Could not find <tgbt-root> containing AGENTS.md and oracle/docs/")


def resolve_target(repo_root: Path, raw_target: str) -> Path:
    target = Path(raw_target)
    if not target.is_absolute():
        target = repo_root / target
    target = target.resolve()

    oracle_docs = (repo_root / "oracle" / "docs").resolve()
    if target != oracle_docs and oracle_docs not in target.parents:
        raise ValueError("target directory must be under <tgbt-root>/oracle/docs")
    if not target.is_dir():
        raise ValueError(f"target directory does not exist: {target}")
    return target


def actual_entries(directory: Path) -> list[str]:
    child_dirs = sorted(path.name for path in directory.iterdir() if path.is_dir())
    markdown_files = sorted(
        path.name
        for path in directory.glob("*.md")
        if path.is_file() and path.name != ROUTING_FILE
    )
    return [*child_dirs, *markdown_files]


def parse_existing_bodies(routing_path: Path) -> dict[str, list[str]]:
    if not routing_path.is_file():
        return {}

    bodies: dict[str, list[str]] = {}
    current_entry: str | None = None
    current_body: list[str] = []

    def flush() -> None:
        nonlocal current_entry, current_body
        if current_entry is not None:
            body = trim_blank_edges(current_body)
            bodies[current_entry] = body if body else [TODO_BODY]
        current_entry = None
        current_body = []

    for line in routing_path.read_text(encoding="utf-8").splitlines():
        match = ENTRY_RE.match(line)
        if match:
            flush()
            current_entry = match.group(1)
            current_body = []
        elif current_entry is not None:
            current_body.append(line)

    flush()
    return bodies


def trim_blank_edges(lines: list[str]) -> list[str]:
    start = 0
    end = len(lines)
    while start < end and lines[start].strip() == "":
        start += 1
    while end > start and lines[end - 1].strip() == "":
        end -= 1
    return lines[start:end]


def render_routing(entries: list[str], existing_bodies: dict[str, list[str]]) -> str:
    chunks: list[str] = []
    for entry in entries:
        body = existing_bodies.get(entry, [TODO_BODY])
        chunks.append(f"# `{entry}`\n\n" + "\n".join(body))
    if not chunks:
        return ""
    return "\n\n".join(chunks) + "\n"


def normalize(target_dir: Path) -> tuple[Path, list[str], list[str]]:
    routing_path = target_dir / ROUTING_FILE
    before_entries = set(parse_existing_bodies(routing_path))
    entries = actual_entries(target_dir)
    after_entries = set(entries)

    body = render_routing(entries, parse_existing_bodies(routing_path))
    routing_path.write_text(body, encoding="utf-8")

    added = sorted(after_entries - before_entries)
    removed = sorted(before_entries - after_entries)
    return routing_path, added, removed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Normalize one <tgbt-root>/oracle/docs/**/ROUTING.md file."
    )
    parser.add_argument("target_dir", help="Directory under <tgbt-root>/oracle/docs")
    args = parser.parse_args()

    repo_root = find_repo_root()
    target_dir = resolve_target(repo_root, args.target_dir)
    routing_path, added, removed = normalize(target_dir)

    rel_path = routing_path.relative_to(repo_root).as_posix()
    print(f"normalized: {rel_path}")
    if added:
        print("added entries:")
        for entry in added:
            print(f"- {entry}")
    if removed:
        print("removed entries:")
        for entry in removed:
            print(f"- {entry}")
    if not added and not removed:
        print("entries unchanged")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
