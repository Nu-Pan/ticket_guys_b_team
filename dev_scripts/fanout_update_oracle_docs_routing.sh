#!/usr/bin/env bash

set -u
set -o pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
readonly TGBT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd -P)"

"${SCRIPT_DIR}/fanout-file-codex.sh" \
    "${TGBT_ROOT}/oracle/docs" \
    "<dir>" \
    - <<'PROMPT'
$update-oracle-docs-routing を使用してください
PROMPT
