#!/usr/bin/env bash
# Catbox was removed completely on 2026-11-22. Thumbnail and storyboard assets
# now use Archive.org. Keep both the standalone workflow and upload code gone.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fail=0

for path in \
  "$ROOT/.github/workflows/catbox-mirror.yml" \
  "$ROOT/scripts/catbox/upload_to_catbox.sh"
do
  if [[ -e "$path" ]]; then
    echo "RED: forbidden Catbox file exists: ${path#$ROOT/}"
    fail=1
  fi
done

if grep -RIni 'catbox' "$ROOT/.github/workflows" "$ROOT/scripts" 2>/dev/null; then
  echo "RED: production workflows/scripts still reference Catbox"
  fail=1
fi

if (( fail )); then exit 1; fi
echo 'GREEN: Catbox is completely removed; media-support assets use Archive.org'
