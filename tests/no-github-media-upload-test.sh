#!/usr/bin/env bash
# GitHub can suspend an account for using Releases as permanent media hosting.
# The old mirror workflow uploaded every recording as an MP4 release asset.
# Keep that capability removed unless the owner deliberately redesigns it.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

fail=0
for path in \
  "$ROOT/.github/workflows/github-release-mirror.yml" \
  "$ROOT/scripts/github-release-upload.py"
do
  if [[ -e "$path" ]]; then
    echo "RED: forbidden GitHub media-upload file exists: ${path#$ROOT/}"
    fail=1
  fi
done

if grep -RInE 'uploads\.github\.com|releases/[^ ]*/assets' \
  "$ROOT/.github/workflows" "$ROOT/scripts" 2>/dev/null; then
  echo "RED: workflow/script still contains a GitHub Release upload endpoint"
  fail=1
fi

if (( fail )); then
  exit 1
fi
echo 'GREEN: GitHub media storage and MP4 Release uploads are disabled'
