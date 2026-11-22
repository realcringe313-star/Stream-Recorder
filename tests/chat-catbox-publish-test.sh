#!/usr/bin/env bash
# Chat Catbox publishing: only valid compact chat files are uploaded, the
# Catbox URL becomes chat_url, and a second run skips the duplicate upload.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/data/chat" "$TMP/scripts/catbox"
cp "$ROOT/scripts/catbox/upload_to_catbox.sh" "$TMP/scripts/catbox/"

VID=abcdefghijk
printf '%s' '{"messages":[{"t":1,"a":"Alice","m":"hello"}]}' > "$TMP/data/chat/$VID.json"
printf '%s' '{"messages":[]}' > "$TMP/data/chat/emptyvid001.json"
printf '%s' '[{"video_id":"abcdefghijk","chat_url":""}]' > "$TMP/data/recordings.json"

REPO_ROOT="$TMP" CATBOX_TEST_URL="https://files.catbox.moe/testchat.json" \
  "$PYTHON_BIN" "$ROOT/scripts/chat/publish-catbox.py" > "$TMP/first.log"
grep -q 'uploaded=1' "$TMP/first.log" || { echo 'RED: valid chat was not uploaded'; exit 1; }
grep -q 'https://files.catbox.moe/testchat.json' "$TMP/data/recordings.json" \
  || { echo 'RED: Catbox chat URL missing from recordings.json'; exit 1; }
if grep -q 'emptyvid001' "$TMP/data/recordings.json"; then
  echo 'RED: empty chat was published'; exit 1
fi

REPO_ROOT="$TMP" CATBOX_TEST_URL="https://files.catbox.moe/testchat.json" \
  "$PYTHON_BIN" "$ROOT/scripts/chat/publish-catbox.py" > "$TMP/second.log"
grep -q 'uploaded=0' "$TMP/second.log" && grep -q 'skipped=1' "$TMP/second.log" \
  || { echo 'RED: duplicate Catbox upload was not skipped'; exit 1; }

echo 'GREEN: chat Catbox publishing stores links and skips duplicates'
