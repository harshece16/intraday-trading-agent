#!/bin/bash
# Keep Trader Sahab's backend running whenever the Mac is awake during a
# trading session. Run every couple of minutes by launchd (see
# com.tradersahab.watchdog.plist) — launchd also fires this right after the
# machine wakes, which is the case this exists for: the Mac sleeps at 10:40,
# wakes at 11:05, and the engine is back before the next candle closes.
#
# Deliberately conservative:
#   - It only ever STARTS the backend. It never stops one you started
#     yourself, and outside session hours it does nothing at all.
#   - "In session" comes from the app's own config and holidays.py, so there
#     is one source of truth for market hours and NSE holidays.
#   - A process that is listening but not answering is treated as wedged and
#     replaced, because a hung engine is worse than a dead one: it holds the
#     port while stops go unchecked.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$REPO/backend"
PY="$BACKEND/.venv/bin/python"
PORT="${SAHAB_PORT:-8000}"
LOG_DIR="${SAHAB_LOG_DIR:-$HOME/Library/Logs/TraderSahab}"
LOG="$LOG_DIR/watchdog.log"
SERVER_LOG="$LOG_DIR/backend.log"

# The dashboard is off by default: it only shows you what the engine is doing,
# and if it isn't up you find out the moment you open the browser. A missed
# trading session is the invisible failure, so the backend is what this
# guards. Set SAHAB_START_DASHBOARD=1 to have it keep the Vite server up too.
START_DASHBOARD="${SAHAB_START_DASHBOARD:-0}"
DASH_PORT="${SAHAB_DASH_PORT:-5500}"
DASH_LOG="$LOG_DIR/dashboard.log"

# Minutes either side of the session to stay up: early enough for the
# pre-market scan to seed the watchlist, late enough for the 15:15 square-off
# and the journal writes to finish.
WARMUP_MIN="${SAHAB_WARMUP_MIN:-20}"
COOLDOWN_MIN="${SAHAB_COOLDOWN_MIN:-20}"

mkdir -p "$LOG_DIR"
log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG"; }

if [ ! -x "$PY" ]; then
  log "no venv python at $PY — run: cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

# Ask the app itself whether this is a trading session. Exit 0 = yes.
in_session() {
  "$PY" - "$WARMUP_MIN" "$COOLDOWN_MIN" <<'PY' 2>/dev/null
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, ".")
import config
import holidays

warmup, cooldown = int(sys.argv[1]), int(sys.argv[2])
now = datetime.now(timezone(timedelta(hours=5, minutes=30)))
if now.weekday() >= 5 or holidays.is_holiday(now):
    sys.exit(1)
oh, om = (int(x) for x in config.MARKET_OPEN.split(":"))
ch, cm = (int(x) for x in config.MARKET_CLOSE.split(":"))
start = now.replace(hour=oh, minute=om, second=0, microsecond=0) - timedelta(minutes=warmup)
end = now.replace(hour=ch, minute=cm, second=0, microsecond=0) + timedelta(minutes=cooldown)
sys.exit(0 if start <= now <= end else 1)
PY
}

listening_pid() { lsof -ti ":$PORT" -sTCP:LISTEN 2>/dev/null | head -1; }

# Answers on /api/state, with the local dashboard key. A 200 means the event
# loop is alive; anything else (including a timeout) means it is not serving.
responds() {
  local key
  key=$("$PY" -c "import json;print(json.load(open('.dashboard_key.json'))['key'])" 2>/dev/null) || return 1
  [ -n "$key" ] || return 1
  curl -sf -m 10 -o /dev/null "http://127.0.0.1:$PORT/api/state?key=$key"
}

start_backend() {
  nohup "$PY" -m uvicorn app:app --port "$PORT" >> "$SERVER_LOG" 2>&1 &
  log "started backend on :$PORT (pid $!)"
}

# Vite binds IPv6 loopback only, so http://127.0.0.1:5500 is refused while
# http://localhost:5500 returns 200. Probing the IPv4 address makes a healthy
# dashboard look dead — which is how this check first got written, and it
# would have had the watchdog killing and restarting a working server every
# two minutes. Always probe the name, never the v4 address.
check_dashboard() {
  [ "$START_DASHBOARD" = "1" ] || return 0
  curl -sf -m 10 -o /dev/null "http://localhost:$DASH_PORT/" && return 0
  command -v npm >/dev/null 2>&1 || { log "dashboard requested but npm is not on PATH"; return 0; }
  # Don't fight for the port: if something else holds it, Vite would silently
  # move to 5501 and you'd have two servers and no idea which you're looking at.
  if lsof -ti ":$DASH_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    log "something holds :$DASH_PORT but doesn't serve — leaving it alone, check it by hand"
    return 0
  fi
  ( cd "$REPO/frontend" && nohup npm run dev >> "$DASH_LOG" 2>&1 & )
  log "started dashboard on :$DASH_PORT"
}

cd "$BACKEND" || { log "cannot cd to $BACKEND"; exit 1; }

if ! in_session; then
  exit 0                      # weekend, NSE holiday, or outside the session
fi

pid="$(listening_pid)"
if [ -z "$pid" ]; then
  log "nothing on :$PORT during market hours — starting"
  start_backend
  check_dashboard
  exit 0
fi

if responds; then
  check_dashboard
  exit 0                      # healthy; say nothing, this runs every 2 minutes
fi

# Listening but not answering. Give it one more chance before killing, so a
# single slow request during a heavy scan doesn't trigger a restart.
sleep 15
if responds; then
  log "pid $pid was slow to answer but recovered"
  exit 0
fi

log "pid $pid holds :$PORT but is not answering — restarting it"
kill "$pid" 2>/dev/null
for _ in $(seq 1 10); do
  [ -z "$(listening_pid)" ] && break
  sleep 1
done
[ -n "$(listening_pid)" ] && { log "pid $pid would not exit; sending SIGKILL"; kill -9 "$pid" 2>/dev/null; sleep 2; }
start_backend
check_dashboard
