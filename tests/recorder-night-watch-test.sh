#!/usr/bin/env bash
# Regression: the 1:52 AM PKT missed-recording incident.
#
# The recorder's */5 GitHub schedule was throttled until 3:26 AM, so a live
# stream at 1:52 AM was never checked. Night watch must start early enough,
# keep itself alive from Stream Recorder completion events, and dispatch a
# one-hour wait so the chain has no schedule-sized gaps.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 - "$ROOT" <<'PY'
from pathlib import Path
import sys, yaml

root = Path(sys.argv[1])
path = root / '.github/workflows/recorder-night-watch.yml'
w = yaml.safe_load(path.read_text())
on = w.get('on', w.get(True, {}))

crons = [item['cron'] for item in on['schedule']]
assert '20 13 * * *' in crons, 'night watch must bootstrap at 6:20 PM PKT'
assert '20 19 * * *' in crons, 'night watch must bootstrap at 12:20 AM PKT'
assert '20 23 * * *' in crons, 'night watch must cover the late stream tail'

chain = on.get('workflow_run', {})
assert 'Stream Recorder' in chain.get('workflows', []), \
    'night watch must continue from Stream Recorder completion events'
assert 'completed' in chain.get('types', []), \
    'night watch continuation must trigger when a recorder run completes'

script = w['jobs']['watch']['steps'][0]['run']
assert 'stream-recorder.yml/dispatches' in script
assert '"wait_for_live":"true"' in script
assert '"wait_max_hours":"1"' in script
assert 'sleep 120' in script, 'fallback polling gap must be under two minutes'

watchdog = yaml.safe_load(
    (root / '.github/workflows/pinger-watchdog.yml').read_text()
)
won = watchdog.get('on', watchdog.get(True, {}))
producers = won.get('workflow_run', {}).get('workflows', [])
assert 'Stream Recorder' in producers
assert 'Recorder night watch' in producers

print('GREEN: night coverage starts before 1:52 AM and self-chains from recorder events')
PY
