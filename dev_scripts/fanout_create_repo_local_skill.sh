#!/usr/bin/env bash

set -u
set -o pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
readonly TGBT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd -P)"
readonly LOG_DIR="${TGBT_ROOT}/dev_scripts/logs/fanout-file-codex"

readonly USER_PROMPT='$create-repo-local-skill を使用してください'

compose_prompt() {
    local target_dir="$1"

    printf '`%s` だけを対象に、以下に述べる作業を行ってください。\n\n%s\n' \
        "$target_dir" \
        "$USER_PROMPT"
}

main() {
    local skills_root="${TGBT_ROOT}/.agents/skills"
    [[ -d "$skills_root" ]] || {
        printf 'error: skills directory does not exist: %s\n' "$skills_root" >&2
        return 1
    }

    mkdir -p "$LOG_DIR" || return 1

    local timestamp
    timestamp="$(date '+%Y%m%d-%H%M%S')"
    local log_file="${LOG_DIR}/${timestamp}.log"

    exec > >(tee "$log_file") 2>&1

    printf 'fanout_create_repo_local_skill started\n'
    printf 'target_dir: %s\n' "$skills_root"
    printf 'dangerously_bypass_approvals_and_sandbox: true\n'
    printf 'log_file: %s\n\n' "$log_file"

    local skill_dirs=()
    local skill_dir
    while IFS= read -r -d '' skill_dir; do
        skill_dirs+=("$skill_dir")
    done < <(find "$skills_root" -mindepth 1 -maxdepth 1 -type d -print0 | sort -z)

    if (( ${#skill_dirs[@]} == 0 )); then
        printf 'fanout_create_repo_local_skill completed\n'
        printf 'matched_skills: 0\n'
        printf 'log_file: %s\n' "$log_file"
        return 0
    fi

    printf 'matched_skills: %d\n\n' "${#skill_dirs[@]}"

    local failure_count=0
    local index=0
    for skill_dir in "${skill_dirs[@]}"; do
        index=$((index + 1))
        printf '===== [%d/%d] %s =====\n' "$index" "${#skill_dirs[@]}" "$skill_dir"

        local codex_prompt
        codex_prompt="$(compose_prompt "$skill_dir")"

        if codex exec -C "$TGBT_ROOT" --dangerously-bypass-approvals-and-sandbox "$codex_prompt"; then
            printf '===== success: %s =====\n\n' "$skill_dir"
        else
            local status=$?
            failure_count=$((failure_count + 1))
            printf '===== failure: %s (exit %d) =====\n\n' "$skill_dir" "$status"
        fi
    done

    printf 'fanout_create_repo_local_skill completed\n'
    printf 'total_skills: %d\n' "${#skill_dirs[@]}"
    printf 'failed_skills: %d\n' "$failure_count"
    printf 'log_file: %s\n' "$log_file"

    if (( failure_count > 0 )); then
        return 1
    fi
}

main "$@"
