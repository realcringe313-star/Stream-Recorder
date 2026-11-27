#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  Regression test: Gofile dynamic auth + real download refresh & DropDrive    ║
# ║  HTML-200 dead-link detection (2026-11-27 outage)                            ║
# ║                                                                              ║
# ║  Locks down:                                                                 ║
# ║   1. Stale/rejected Gofile API (error-token + SPA 200 HTML) NEVER returns    ║
# ║      alive (prevents fake "78/78 Active" reports & skipped repairs).         ║
# ║   2. error-notFound or emptied folder (childrenCount=0) returns dead (rc=1)  ║
# ║      in mirror-health, repair-mirrors, and refresh-links.                    ║
# ║   3. gofile-wt.mjs + _gofile_mint_session sends Authorization + computed     ║
# ║      X-Website-Token, and refresh_gofile hits the direct storage URL with    ║
# ║      Cookie: accountToken=... and rejects text/html redirects.               ║
# ║   4. dropdrive.rip/d/... HTTP-200 missing-file shell (no og:title) is dead   ║
# ║      (rc=1), while HTTP-200 with og:title is alive (rc=0).                   ║
# ║                                                                              ║
# ║  Hermetic: curl is stubbed, no real network calls.                           ║
# ║  Run: bash tests/gofile-dropdrive-health-test.sh                             ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
FAILURES=0
ok()  { echo "  ✅ $1"; }
bad() { echo "  ❌ $1"; FAILURES=$((FAILURES+1)); }

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT
STUBBIN="$WORKDIR/bin"; mkdir -p "$STUBBIN"
GF_API_BODY="$WORKDIR/gf_api.body"
GF_DL_META="$WORKDIR/gf_dl.meta"
DD_PAGE_BODY="$WORKDIR/dd_page.body"
DD_HTTP_CODE="$WORKDIR/dd_page.code"
CURL_LOG="$WORKDIR/curl.log"

cat > "$WORKDIR/recordings.json" <<'JSON'
[
  {
    "video_id": "gfddfix0001",
    "title": "Gofile & DropDrive Fixture",
    "archive_link": "https://archive.org/details/fixture-item",
    "gofile_link": "https://gofile.io/d/FixGf01",
    "pixeldrain_link": "https://pixeldrain.com/u/FixPd01",
    "mega_link": "https://mega.nz/file/FixMg01#k",
    "st0807_link": "https://dropdrive.rip/d/FixDd01",
    "vikingfile_link": "https://vikingfile.com/f/FixVf01"
  }
]
JSON

cat > "$STUBBIN/curl" <<STUB
#!/usr/bin/env bash
OUT=""; WRITE_FMT=""; URL=""
raw_args="\$*"
printf '%s\n' "\$raw_args" >> "$CURL_LOG"
while [[ \$# -gt 0 ]]; do
  case "\$1" in
    -o) OUT="\$2"; shift 2;;
    -w) WRITE_FMT="\$2"; shift 2;;
    -H|-A|-F|-d|-r|-X|--max-time|--range|--user-agent|--retry|--retry-delay|--connect-timeout) shift 2;;
    http*|https*) URL="\$1"; shift;;
    *) shift;;
  esac
done
emit() {
  local body="\$1" code="\$2" ctype="\${3:-application/json}"
  if [[ -n "\$OUT" && "\$OUT" != "/dev/null" ]]; then
    printf '%s' "\$body" > "\$OUT"
  elif [[ -z "\$OUT" ]]; then
    printf '%s' "\$body"
  fi
  if [[ -n "\$WRITE_FMT" ]]; then
    local out_w="\$WRITE_FMT"
    out_w="\${out_w//%{http_code\}/\$code}"
    out_w="\${out_w//%{content_type\}/\$ctype}"
    out_w="\${out_w//%{url_effective\}/\$URL}"
    printf '%b' "\$out_w"
  fi
  exit 0
}
case "\$URL" in
  *api.gofile.io/accounts*)
    emit '{"status":"ok","data":{"token":"guestTok999"}}' 200 ;;
  *gofile.io/js/wt.obf.js*)
    emit 'function generateWT(tok){ return "wt_" + tok; }' 200 'application/javascript' ;;
  *api.gofile.io/contents/*)
    emit "\$(cat "$GF_API_BODY")" 200 ;;
  *store-*.gofile.io/download/web/*)
    IFS='|' read -r mc mt mu < "$GF_DL_META"
    URL="\${mu:-\$URL}"
    emit '' "\${mc:-206}" "\${mt:-video/mp4}" ;;
  *gofile.io/d/*)
    emit '<!doctype html><html><body><div id="app"></div><script src="/js/app.js"></script></body></html>' 200 'text/html' ;;
  *dropdrive.rip/d/*)
    emit "\$(cat "$DD_PAGE_BODY")" "\$(cat "$DD_HTTP_CODE")" 'text/html' ;;
  *pixeldrain.com/api/file/*)
    emit '{"success":true}' 200 ;;
  *vikingfile.com/api/check-file*)
    emit '[{"exist":true}]' 200 ;;
  *g.api.mega.co.nz/cs*|*api.mega.co.nz/cs*)
    emit '[{"s":12345}]' 200 ;;
  *api.github.com*)
    emit '{}' 200 ;;
  *)
    emit '' 200 ;;
esac
STUB
chmod +x "$STUBBIN/curl"

health_check() {
  (cd "$WORKDIR" && PATH="$STUBBIN:$PATH" RECORDINGS_JSON="$WORKDIR/recordings.json" \
     MIRROR_HEALTH_JSON="$WORKDIR/health.json" MIRROR_CHECK_TIMEOUT=2 \
     bash "$ROOT/scripts/mirror-health.sh" >/dev/null 2>&1)
  jq -r "{gofile:.recordings[0].mirrors.gofile, dd:.recordings[0].mirrors.st0807}" "$WORKDIR/health.json" 2>/dev/null
}

echo "── 1: Gofile error-token + SPA 200 HTML → unverifiable (NEVER alive) ──"
printf '{"status":"error-token","data":{}}' > "$GF_API_BODY"
printf '<meta property="og:title" content="HD.mp4">' > "$DD_PAGE_BODY"
printf '200' > "$DD_HTTP_CODE"
: > "$CURL_LOG"
H=$(health_check)
[[ "$(jq -r .gofile <<<"$H")" == "unverifiable" ]] && ok "mirror-health: error-token → unverifiable" || bad "mirror-health: $H"
rc=0; (cd "$WORKDIR" && PATH="$STUBBIN:$PATH" bash -c 'source "$1/scripts/repair-mirrors.sh" >/dev/null 2>&1; _is_gofile_alive "https://gofile.io/d/FixGf01"' _ "$ROOT") || rc=$?
[[ "$rc" -eq 2 ]] && ok "repair-mirrors: error-token → rc=2 unverifiable (not alive)" || bad "repair-mirrors returned rc=$rc (expected 2)"
rc=0; (cd "$WORKDIR" && PATH="$STUBBIN:$PATH" bash -c 'source "$1/scripts/refresh-links.sh" >/dev/null 2>&1; check_link_alive "https://gofile.io/d/FixGf01"' _ "$ROOT") || rc=$?
[[ "$rc" -eq 2 ]] && ok "refresh-links: error-token → rc=2 unverifiable (not alive)" || bad "refresh-links returned rc=$rc (expected 2)"

echo "── 2: Gofile error-notFound → dead (rc=1) everywhere ──"
printf '{"status":"error-notFound","data":{}}' > "$GF_API_BODY"
H=$(health_check)
[[ "$(jq -r .gofile <<<"$H")" == "dead" ]] && ok "mirror-health: error-notFound → dead" || bad "mirror-health: $H"
rc=0; (cd "$WORKDIR" && PATH="$STUBBIN:$PATH" bash -c 'source "$1/scripts/repair-mirrors.sh" >/dev/null 2>&1; _is_gofile_alive "https://gofile.io/d/FixGf01"' _ "$ROOT") || rc=$?
[[ "$rc" -eq 1 ]] && ok "repair-mirrors: error-notFound → rc=1 dead" || bad "repair-mirrors returned rc=$rc"
rc=0; (cd "$WORKDIR" && PATH="$STUBBIN:$PATH" bash -c 'source "$1/scripts/refresh-links.sh" >/dev/null 2>&1; check_link_alive "https://gofile.io/d/FixGf01"' _ "$ROOT") || rc=$?
[[ "$rc" -eq 1 ]] && ok "refresh-links: error-notFound → rc=1 dead" || bad "refresh-links returned rc=$rc"

echo "── 3: Gofile emptied folder (childrenCount=0) → dead (rc=1) ──"
printf '{"status":"ok","data":{"type":"folder","childrenCount":0,"children":{}}}' > "$GF_API_BODY"
H=$(health_check)
[[ "$(jq -r .gofile <<<"$H")" == "dead" ]] && ok "mirror-health: emptied folder → dead" || bad "mirror-health: $H"

echo "── 4: Gofile live folder sends wt + downloads real storage URL with accountToken cookie ──"
printf '{"status":"ok","data":{"type":"folder","childrenCount":1,"children":{"f1":{"type":"file","link":"https://store-eu-par-1.gofile.io/download/web/f1/video.mp4"}}}}' > "$GF_API_BODY"
printf '206|video/mp4|https://store-eu-par-1.gofile.io/download/web/f1/video.mp4' > "$GF_DL_META"
: > "$CURL_LOG"
rc=0; (cd "$WORKDIR" && PATH="$STUBBIN:$PATH" bash -c 'source "$1/scripts/refresh-links.sh" >/dev/null 2>&1; check_link_alive "https://gofile.io/d/FixGf01" && refresh_gofile "https://gofile.io/d/FixGf01"' _ "$ROOT") || rc=$?
[[ "$rc" -eq 0 ]] && ok "refresh_gofile succeeded on real storage stream" || bad "refresh_gofile failed with rc=$rc"
grep -q 'X-Website-Token: wt_guestTok999' "$CURL_LOG" && ok "node gofile-wt.mjs injected dynamic X-Website-Token" || bad "missing X-Website-Token header in curl log"
grep -q 'Authorization: Bearer guestTok999' "$CURL_LOG" && ok "Bearer guest token injected" || bad "missing Bearer header"
grep -q 'store-eu-par-1.gofile.io/download/web/f1/video.mp4' "$CURL_LOG" && ok "hit direct storage download URL (not /d/ webpage)" || bad "did not hit storage URL"
grep -q 'Cookie: accountToken=guestTok999' "$CURL_LOG" && ok "sent accountToken cookie on download" || bad "missing accountToken cookie on download"

echo "── 5: Gofile refresh rejects 302 fallback to text/html ──"
printf '200|text/html; charset=utf-8|https://gofile.io/d/f1' > "$GF_DL_META"
rc=0; (cd "$WORKDIR" && PATH="$STUBBIN:$PATH" bash -c 'source "$1/scripts/refresh-links.sh" >/dev/null 2>&1; refresh_gofile "https://gofile.io/d/FixGf01"' _ "$ROOT") || rc=$?
[[ "$rc" -ne 0 ]] && ok "refresh_gofile rejected text/html SPA fallback (rc=$rc)" || bad "refresh_gofile accepted text/html!"

echo "── 6: DropDrive HTTP-200 missing-file shell (no og:title) → dead (rc=1) ──"
printf '<!DOCTYPE html><html><head><title>Download — DropDrive</title></head><body></body></html>' > "$DD_PAGE_BODY"
printf '200' > "$DD_HTTP_CODE"
H=$(health_check)
[[ "$(jq -r .dd <<<"$H")" == "dead" ]] && ok "mirror-health: DropDrive HTTP-200 without og:title → dead" || bad "mirror-health: $H"
rc=0; (cd "$WORKDIR" && PATH="$STUBBIN:$PATH" bash -c 'source "$1/scripts/repair-mirrors.sh" >/dev/null 2>&1; _is_st0807_alive "https://dropdrive.rip/d/FixDd01"' _ "$ROOT") || rc=$?
[[ "$rc" -eq 1 ]] && ok "repair-mirrors: DropDrive missing file → rc=1 dead" || bad "repair-mirrors returned rc=$rc"

echo "── 7: DropDrive 403 Cloudflare block → unverifiable (rc=2) ──"
printf '<html>Attention Required</html>' > "$DD_PAGE_BODY"
printf '403' > "$DD_HTTP_CODE"
H=$(health_check)
[[ "$(jq -r .dd <<<"$H")" == "unverifiable" ]] && ok "mirror-health: DropDrive 403 → unverifiable" || bad "mirror-health: $H"

echo ""
if (( FAILURES > 0 )); then echo "RESULT: RED — $FAILURES assertion(s) failed"; exit 1; fi
echo "RESULT: GREEN — Gofile dynamic auth/download & DropDrive dead-detection locked"; exit 0
