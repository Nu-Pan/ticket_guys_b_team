#!/usr/bin/env python3
"""Summarize the current docs tree for refactor work."""

import sys
from pathlib import Path


def first_heading(markdown_path: Path) -> str:
    """Return the first H1 heading in a markdown file when present."""
    try:
        for raw_line in markdown_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if line.startswith("# "):
                return line[2:].strip()
    except UnicodeDecodeError:
        return "<non-utf8>"
    return "<no-h1>"


def main() -> int:
    """Print an inventory of docs files and routing candidates."""
    if len(sys.argv) != 2:
        print("Usage: summarize_docs_tree.py <docs-path>", file=sys.stderr)
        return 2

    docs_root = Path(sys.argv[1]).resolve()
    if not docs_root.exists():
        print(f"[ERROR] Path not found: {docs_root}", file=sys.stderr)
        return 2
    if not docs_root.is_dir():
        print(f"[ERROR] Not a directory: {docs_root}", file=sys.stderr)
        return 2

    markdown_files = sorted(docs_root.rglob("*.md"))
    print(f"Docs root: {docs_root}")
    print(f"Markdown files: {len(markdown_files)}")

    empty_files: list[Path] = []
    print("\nFiles:")
    for path in markdown_files:
        relative = path.relative_to(docs_root)
        size = path.stat().st_size
        if size == 0:
            empty_files.append(relative)
        heading = first_heading(path)
        print(f"- {relative} | {size} bytes | H1: {heading}")

    print("\nRouting candidates:")
    for path in markdown_files:
        relative = path.relative_to(docs_root)
        parts = relative.parts
        if len(parts) == 1 or relative.name.lower() == "routing.md":
            print(f"- {relative}")

    print("\nEmpty files:")
    if empty_files:
        for relative in empty_files:
            print(f"- {relative}")
    else:
        print("- <none>")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
