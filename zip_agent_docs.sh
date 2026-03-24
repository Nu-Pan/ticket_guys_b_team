#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="${1:-$script_dir}"
output_zip_arg="${2:-agent_docs.zip}"

if ! command -v zip >/dev/null 2>&1; then
  echo "error: 'zip' command is not installed" >&2
  exit 1
fi

repo_root="$(cd -- "$repo_root" && pwd)"

case "$output_zip_arg" in
  /*) output_zip="$output_zip_arg" ;;
  *)  output_zip="$repo_root/$output_zip_arg" ;;
esac

cd "$repo_root"

files=()

[[ -f "AGENTS.md" ]] && files+=("AGENTS.md")
[[ -f "README.md" ]] && files+=("README.md")

if [[ -d "doc" ]]; then
  while IFS= read -r file; do
    files+=("$file")
  done < <(find "doc" -type f -name "*.md" | LC_ALL=C sort)
fi

if [[ ${#files[@]} -eq 0 ]]; then
  echo "error: no target files found" >&2
  exit 1
fi

rm -f "$output_zip"
zip -q "$output_zip" "${files[@]}"

echo "created: $output_zip"
printf 'included:\n'
printf '  %s\n' "${files[@]}"
