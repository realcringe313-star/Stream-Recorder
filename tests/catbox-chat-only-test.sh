#!/usr/bin/env bash
# Catbox is for compact chat JSON only. It must not return as a video or
# thumbnail host, and the chat uploader must reject missing files.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPLOADER="$ROOT/scripts/catbox/upload_to_catbox.sh"
PUBLISHER="$ROOT/scripts/chat/publish-catbox.py"

[[ -x "$UPLOADER" || -f "$UPLOADER" ]] || { echo 'RED: Catbox chat uploader missing'; exit 1; }
[[ -f "$PUBLISHER" ]] || { echo 'RED: Catbox chat publisher missing'; exit 1; }
[[ ! -e "$ROOT/.github/workflows/catbox-mirror.yml" ]] || { echo 'RED: video Catbox mirror returned'; exit 1; }
[[ ! -e "$ROOT/.github/workflows/thumbnail-gen.yml" ]] || { echo 'RED: thumbnail cloud generator returned'; exit 1; }

if bash -c 'source "$1"; upload_chat_to_catbox "$2"' _ "$UPLOADER" "$ROOT/does-not-exist.json"; then
  echo 'RED: Catbox uploader accepted a missing file'
  exit 1
fi

echo 'GREEN: Catbox is chat-only; thumbnails are Discord-only'
