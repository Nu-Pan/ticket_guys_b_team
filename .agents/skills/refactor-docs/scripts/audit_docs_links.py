#!/usr/bin/env python3
"""Audit docs-related references in markdown files."""

import re
import sys
from pathlib import Path

MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
INLINE_CODE_RE = re.compile(r"`([^`]+)`")


def should_scan(markdown_path: Path, repo_root: Path) -> bool:
    """Return whether a markdown file should be scanned."""
    try:
        relative = markdown_path.resolve().relative_to(repo_root)
    except ValueError:
        return False

    if relative.parts and relative.parts[0] in {"memo", "oracle"}:
        return False
    if relative == Path("README.md") or relative == Path("AGENTS.md"):
        return False
    return True


def normalize_target(raw_target: str) -> str:
    """Strip common decorations from markdown targets."""
    target = raw_target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    return target.split("#", 1)[0].split("?", 1)[0].strip()


def resolve_target(markdown_path: Path, target: str, repo_root: Path) -> Path:
    """Resolve a markdown target to a filesystem path."""
    if target.startswith("/"):
        return (repo_root / target.lstrip("/")).resolve()
    if target.startswith(("docs/", ".agents/", "src/")):
        return (repo_root / target).resolve()
    return (markdown_path.parent / target).resolve()


def main() -> int:
    """Print docs-related link issues discovered in markdown files."""
    if len(sys.argv) != 2:
        print("Usage: audit_docs_links.py <repo-root-or-docs-path>", file=sys.stderr)
        return 2

    root = Path(sys.argv[1]).resolve()
    if not root.exists():
        print(f"[ERROR] Path not found: {root}", file=sys.stderr)
        return 2

    repo_root = root if (root / ".git").exists() else root.parent
    scan_root = repo_root if (repo_root / ".git").exists() else root
    markdown_files = sorted(scan_root.rglob("*.md"))

    missing_links: list[str] = []
    stale_inline_paths: list[str] = []
    docs_reference_files: set[str] = set()

    for markdown_path in markdown_files:
        if not should_scan(markdown_path, repo_root):
            continue
        relative_file = markdown_path.resolve().relative_to(repo_root)
        text = markdown_path.read_text(encoding="utf-8")

        for raw_target in MARKDOWN_LINK_RE.findall(text):
            target = normalize_target(raw_target)
            if not target or "://" in target or target.startswith(("mailto:", "#")):
                continue
            if "docs/" not in target and not target.startswith("docs") and "/docs/" not in target:
                continue
            docs_reference_files.add(str(relative_file))
            resolved = resolve_target(markdown_path, target, repo_root)
            if not resolved.exists():
                missing_links.append(f"{relative_file}: {target}")

        for code_value in INLINE_CODE_RE.findall(text):
            candidate = code_value.strip()
            if "docs/" not in candidate:
                continue
            docs_reference_files.add(str(relative_file))
            if " " in candidate or candidate.endswith("/"):
                continue
            if "*" in candidate or "..." in candidate:
                continue
            resolved = resolve_target(markdown_path, candidate, repo_root)
            if not resolved.exists():
                stale_inline_paths.append(f"{relative_file}: {candidate}")

    print(f"Scan root: {scan_root}")
    print(f"Markdown files scanned: {sum(1 for p in markdown_files if should_scan(p, repo_root))}")

    print("\nFiles that reference docs:")
    if docs_reference_files:
        for item in sorted(docs_reference_files):
            print(f"- {item}")
    else:
        print("- <none>")

    print("\nMissing markdown links:")
    if missing_links:
        for item in missing_links:
            print(f"- {item}")
    else:
        print("- <none>")

    print("\nStale inline code paths:")
    if stale_inline_paths:
        for item in stale_inline_paths:
            print(f"- {item}")
    else:
        print("- <none>")

    return 1 if missing_links or stale_inline_paths else 0


if __name__ == "__main__":
    raise SystemExit(main())
