#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  Regression test: 0807.st → DropDrive uploader contract (offline)            ║
# ║                                                                              ║
# ║  0807.st was rebranded to DropDrive (dropdrive.rip). upload_to_st0807 now   ║
# ║  delegates to upload_to_dropdrive → scripts/dropdrive_upload.py. The old    ║
# ║  curl/PoW chunk test exercised removed code AND, because nothing was        ║
# ║  stubbed anymore, really uploaded test files to dropdrive.rip on every CI   ║
# ║  run. This version stubs python3 so NOTHING leaves the runner.              ║
# ║  Locks:                                                                      ║
# ║   1. success → link captured into ST0807_LINKS, rc 0                         ║
# ║   2. failure (no link) → rc 1, nothing recorded, reason logged               ║
# ║   3. upload_to_st0807 is a thin alias of upload_to_dropdrive                 ║
# ║   4. DROPDRIVE_SKIP / ST0807_SKIP keep the service out of upload_to_clouds   ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
FAILURES=0
ok()  { echo "  ✅ $1"; }
bad() { echo "  ❌ $1"; FAILURES=$((FAILURES+1)); }

W=$(mktemp -d); trap 'rm -rf "$W"' EXIT
mkdir -p "$W/bin"; head -c 8192 /dev/zero > "$W/f.mp4"
cat > "$W/bin/python3" <<EOF
#!/usr/bin/env bash
echo "\$*" >> "$W/calls"
case "\$(cat "$W/mode")" in
  ok)   echo "  DropDrive: done"; echo "https://dropdrive.rip/d/TestLink1"; exit 0;;
  fail) echo "  DropDrive: HTTP 403 forbidden"; exit 1;;
esac
EOF
chmod +x "$W/bin/python3"

run() {
  echo "$1" > "$W/mode"; : > "$W/calls"
  (cd "$ROOT" && PATH="$W/bin:$PATH" bash -c '
     source scripts/upload-clouds.sh >/dev/null 2>&1
     ST0807_LINKS=()
     '"$2"' "'"$W/f.mp4"'" HD; rc=$?
     echo "RC=$rc LINKS=${ST0807_LINKS[*]:-}"' 2>&1)
}

echo "── 1: success → link recorded ──"
OUT=$(run ok upload_to_dropdrive)
grep -q 'RC=0 LINKS=HD|https://dropdrive.rip/d/TestLink1' <<<"$OUT" && ok "link captured" || bad "unexpected: $(grep RC= <<<"$OUT")"
grep -q 'dropdrive_upload.py' "$W/calls" && ok "delegates to dropdrive_upload.py" || bad "python uploader not called"

echo "── 2: failure → rc 1, nothing recorded, reason visible ──"
OUT=$(run fail upload_to_dropdrive)
grep -q 'RC=1 LINKS=$' <<<"$OUT" && ok "failure returns 1 with no link" || bad "unexpected: $(grep RC= <<<"$OUT")"
grep -q '403' <<<"$OUT" && ok "failure reason logged" || bad "failure reason hidden"

echo "── 3: legacy name still works ──"
OUT=$(run ok upload_to_st0807)
grep -q 'RC=0 LINKS=HD|https://dropdrive.rip/d/TestLink1' <<<"$OUT" && ok "upload_to_st0807 → DropDrive" || bad "alias broken"

echo "── 4: skip flags honoured ──"
grep -q 'DROPDRIVE_SKIP:-false}" != "true" && "${ST0807_SKIP:-false}" != "true"' "$ROOT/scripts/upload-clouds.sh" \
  && ok "DROPDRIVE_SKIP / ST0807_SKIP gate the upload" || bad "skip gate missing"

echo
if (( FAILURES > 0 )); then echo "RESULT: RED — $FAILURES assertion(s) failed"; exit 1; fi
echo "RESULT: GREEN — DropDrive uploader contract locked (offline)"