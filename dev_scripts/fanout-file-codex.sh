#!/usr/bin/env bash

set -u
set -o pipefail

readonly SCRIPT_NAME="$(basename "$0")"
readonly TGBT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
readonly LOG_DIR="${TGBT_ROOT}/dev_scripts/logs/fanout-file-codex"

usage() {
    cat <<USAGE
Usage:
  ${SCRIPT_NAME} [--dangerously-bypass-approvals-and-sandbox] <target-dir> <file-pattern>
  ${SCRIPT_NAME} [--dangerously-bypass-approvals-and-sandbox] <target-dir> <file-pattern> -

Options:
  --dangerously-bypass-approvals-and-sandbox
                    Pass Codex CLI's same-named option. Use only when this
                    script is running against a tightly scoped target set.

Arguments:
  <target-dir>      Directory to enumerate recursively.
  <file-pattern>    Glob pattern matched against each relative file path.
                    A basename match is also accepted for simple patterns.
  -                 Read the prompt from stdin. Without this argument, an
                    editor is opened for prompt input.
USAGE
}

fail() {
    printf 'error: %s\n' "$*" >&2
    exit 1
}

choose_editor() {
    if [[ -n "${EDITOR:-}" ]]; then
        printf '%s\n' "$EDITOR"
        return 0
    fi

    if command -v code >/dev/null 2>&1; then
        printf '%s\n' 'code --wait'
        return 0
    fi

    local editor
    for editor in vim vi; do
        if command -v "$editor" >/dev/null 2>&1; then
            printf '%s\n' "$editor"
            return 0
        fi
    done

    return 1
}

strip_html_comments() {
    awk '
        {
            line = $0
            while (line != "") {
                if (in_comment) {
                    end = index(line, "-->")
                    if (end == 0) {
                        line = ""
                    } else {
                        line = substr(line, end + 3)
                        in_comment = 0
                    }
                } else {
                    start = index(line, "<!--")
                    if (start == 0) {
                        print line
                        line = ""
                    } else {
                        before = substr(line, 1, start - 1)
                        rest = substr(line, start + 4)
                        end = index(rest, "-->")
                        if (end == 0) {
                            print before
                            line = ""
                            in_comment = 1
                        } else {
                            line = before substr(rest, end + 3)
                        }
                    }
                }
            }
        }
    '
}

read_prompt_from_editor() {
    local tmp_file
    tmp_file="$(mktemp)" || return 1

    cat >"$tmp_file" <<'TEMPLATE'
<!--
fanout-file-codex.sh に渡すプロンプトを Markdown で入力してください。
このコメント部分は実行前に削除されます。
入力が完了したらエディタを閉じてください。
-->
# 指示

TEMPLATE

    local editor
    editor="$(choose_editor)" || {
        rm -f "$tmp_file"
        fail 'no editor found; set $EDITOR or pass - and provide the prompt on stdin'
    }

    # Intentionally allow EDITOR to contain arguments such as "code --wait".
    # shellcheck disable=SC2086
    $editor "$tmp_file" || {
        local status=$?
        rm -f "$tmp_file"
        return "$status"
    }

    strip_html_comments <"$tmp_file"
    rm -f "$tmp_file"
}

prompt_is_effectively_empty() {
    local prompt="$1"

    # エディタ入力用テンプレートの誘導見出しだけが残った状態は、未入力として扱う。
    ! printf '%s\n' "$prompt" | awk '
        /^[[:space:]]*$/ {
            next
        }
        $0 == "# 指示" {
            next
        }
        {
            found = 1
        }
        END {
            exit found ? 0 : 1
        }
    '
}

collect_files() {
    local target_root="$1"
    local file_pattern="$2"

    local path
    while IFS= read -r -d '' path; do
        local rel_path="${path#"${target_root}/"}"
        local base_name="${rel_path##*/}"
        if [[ "$rel_path" == $file_pattern || "$base_name" == $file_pattern ]]; then
            printf '%s\0' "$path"
        fi
    done < <(find "$target_root" -type f -print0 | sort -z)
}

compose_prompt() {
    local target_file="$1"
    local user_prompt="$2"

    printf '`%s` だけを対象に、以下に述べる作業を行ってください。\n\n%s\n' \
        "$target_file" \
        "$user_prompt"
}

main() {
    if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
        usage
        return 0
    fi

    local dangerously_bypass_approvals_and_sandbox=false
    while [[ "${1:-}" == --* ]]; do
        case "$1" in
            --dangerously-bypass-approvals-and-sandbox)
                dangerously_bypass_approvals_and_sandbox=true
                shift
                ;;
            --help)
                usage
                return 0
                ;;
            *)
                usage >&2
                return 2
                ;;
        esac
    done

    if (( $# != 2 && $# != 3 )); then
        usage >&2
        return 2
    fi

    local target_dir="$1"
    local file_pattern="$2"
    local prompt_mode="${3:-editor}"

    [[ -d "$target_dir" ]] || fail "target directory does not exist: ${target_dir}"
    if (( $# == 3 )) && [[ "$prompt_mode" != "-" ]]; then
        usage >&2
        return 2
    fi

    local target_root
    target_root="$(cd "$target_dir" && pwd -P)" || return 1
    cd "$TGBT_ROOT" || return 1

    local user_prompt
    if [[ "$prompt_mode" == "-" ]]; then
        user_prompt="$(cat)"
    else
        user_prompt="$(read_prompt_from_editor)" || fail 'failed to read prompt from editor'
    fi

    if prompt_is_effectively_empty "$user_prompt"; then
        fail 'prompt is empty'
    fi

    mkdir -p "$LOG_DIR" || return 1

    local timestamp
    timestamp="$(date '+%Y%m%d-%H%M%S')"
    local log_file="${LOG_DIR}/${timestamp}.log"

    exec > >(tee "$log_file") 2>&1

    printf 'fanout-file-codex started\n'
    printf 'target_dir: %s\n' "$target_root"
    printf 'file_pattern: %s\n' "$file_pattern"
    printf 'dangerously_bypass_approvals_and_sandbox: %s\n' "$dangerously_bypass_approvals_and_sandbox"
    printf 'log_file: %s\n\n' "$log_file"

    local files=()
    local file
    while IFS= read -r -d '' file; do
        files+=("$file")
    done < <(collect_files "$target_root" "$file_pattern")

    if (( ${#files[@]} == 0 )); then
        printf 'fanout-file-codex completed\n'
        printf 'matched_files: 0\n'
        printf 'log_file: %s\n' "$log_file"
        return 0
    fi

    printf 'matched_files: %d\n\n' "${#files[@]}"

    local failure_count=0
    local index=0
    for file in "${files[@]}"; do
        index=$((index + 1))
        printf '===== [%d/%d] %s =====\n' "$index" "${#files[@]}" "$file"

        local codex_prompt
        codex_prompt="$(compose_prompt "$file" "$user_prompt")"

        local codex_exec_args=("-C" "$TGBT_ROOT")
        if [[ "$dangerously_bypass_approvals_and_sandbox" == true ]]; then
            codex_exec_args+=("--dangerously-bypass-approvals-and-sandbox")
        else
            codex_exec_args+=("--add-dir" "$target_root" "-s" "workspace-write")
        fi

        if codex exec "${codex_exec_args[@]}" "$codex_prompt"; then
            printf '===== success: %s =====\n\n' "$file"
        else
            local status=$?
            failure_count=$((failure_count + 1))
            printf '===== failure: %s (exit %d) =====\n\n' "$file" "$status"
        fi
    done

    printf 'fanout-file-codex completed\n'
    printf 'total_files: %d\n' "${#files[@]}"
    printf 'failed_files: %d\n' "$failure_count"
    printf 'log_file: %s\n' "$log_file"

    if (( failure_count > 0 )); then
        return 1
    fi
}

main "$@"
