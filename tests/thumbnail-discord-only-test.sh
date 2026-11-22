#!/usr/bin/env bash
# Owner policy: thumbnails are attached to Discord from the temporary runner
# file. They must never be uploaded to Archive.org, MEGA, Gofile, Catbox, or git.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fail=0

[[ ! -e "$ROOT/.github/workflows/thumbnail-gen.yml" ]] || {
  echo 'RED: thumbnail storage workflow exists'; fail=1;
}
[[ ! -e "$ROOT/scripts/thumbnail-ai/generate_thumbnail.py" ]] || {
  echo 'RED: thumbnail storage generator exists'; fail=1;
}
if grep -qF 'upload_thumbnail_to_cloud || true' "$ROOT/scripts/upload-clouds.sh"; then
  echo 'RED: upload-clouds still invokes thumbnail cloud storage'; fail=1
fi
if ! grep -qF 'attachment://thumbnail.jpg' "$ROOT/scripts/discord-notify.sh"; then
  echo 'RED: Discord local-thumbnail attachment support missing'; fail=1
fi
(( fail )) && exit 1
echo 'GREEN: thumbnails are Discord-only and never stored'
