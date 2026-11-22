#!/usr/bin/env bash
# Catbox is intentionally limited to compact live-chat JSON archives.
# Videos and thumbnails must never be uploaded here.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NODE_BIN="${NODE_BIN:-node}"

upload_chat_to_catbox() {
    local file="${1:-}"
    [[ -f "$file" && -s "$file" ]] || return 1
    [[ "${CATBOX_SKIP:-false}" == "true" ]] && return 2

    # Test seam only: unit tests can provide a synthetic URL without network.
    if [[ -n "${CATBOX_TEST_URL:-}" ]]; then
        if [[ "$CATBOX_TEST_URL" =~ ^https://files\.catbox\.moe/[A-Za-z0-9._-]+$ ]]; then
            printf '%s\n' "$CATBOX_TEST_URL"
            return 0
        fi
        return 1
    fi

    "$NODE_BIN" "$SCRIPT_DIR/upload-chat.mjs" "$file"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    if [[ $# -ne 1 ]]; then
        echo "usage: $0 <chat-json-file>" >&2
        exit 2
    fi
    upload_chat_to_catbox "$1"
fi
