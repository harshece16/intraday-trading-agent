#!/bin/bash
# Live view of the Kronos look L40 measurement pass. Read-only: it counts rows and reads the log.
W=/Users/harshgupta/Projects/webapp/.claude/worktrees/kronos-l40/backend
ROWS=$W/research/kronos_rows_l40.jsonl
LOG=$W/research/kronos_l40_run.log
PIDF=$W/research/kronos_l40_run.pid
DONE=$W/research/kronos_l40_run.done
TOTAL=43362
t0=$(date +%s); r0=""
while true; do
  clear
  now=$(date +%s)
  echo "KRONOS LOOK L40 — one measurement pass, 43,362 forecasts        $(date '+%a %d %b %H:%M:%S')"
  echo "prereg: docs/research/prereg-kronos-feature-ic.md   branch: research/kronos-l40-run   PR #200"
  echo "------------------------------------------------------------------------------------"
  if [ -f "$PIDF" ]; then
    wpid=$(python3 -c "import json;print(json.load(open('$PIDF'))['worker'])" 2>/dev/null)
    st=$(ps -o state= -p "$wpid" 2>/dev/null | tr -d ' ')
    cpu=$(ps -o pcpu= -p "$wpid" 2>/dev/null | tr -d ' ')
    mem=$(ps -o rss= -p "$wpid" 2>/dev/null | awk '{printf "%.1f GB", $1/1048576}')
    case "$st" in
      T*) state="PAUSED for the trading session (continues at 15:45)";;
      "") state="NOT RUNNING";;
      *)  state="running  cpu ${cpu}%  memory ${mem}";;
    esac
    echo "worker pid $wpid: $state"
  else
    echo "no pid file: the run has not been started"
  fi
  if [ -f "$ROWS" ]; then
    rows=$(wc -l < "$ROWS" | tr -d ' ')
    if [ -z "$r0" ]; then r0=$rows; t0=$now; fi
    pct=$(python3 -c "print('%.1f' % ($rows*100/$TOTAL))")
    echo "forecasts done: $rows of $TOTAL  ($pct%)"
    el=$((now - t0)); d=$((rows - r0))
    if [ $el -gt 120 ] && [ $d -gt 0 ]; then
      python3 - "$rows" "$TOTAL" "$d" "$el" <<'PY'
import sys, time
rows, total, d, el = map(int, sys.argv[1:])
rate = d / el * 60
left = (total - rows) / (d / el)
print("rate since this window opened: %.0f forecasts a minute" % rate)
print("computing time left: %.1f hours (the run is stopped 08:30-15:45 on trading days, add that)" % (left / 3600))
PY
    else
      echo "rate: measuring (needs two minutes of this window)"
    fi
  else
    echo "forecast rows: none yet — stage 0 runs first (regression test, revisions, lookahead, timing), about 25 minutes"
  fi
  echo
  echo "log (last lines):"
  [ -f "$LOG" ] && grep -v "NotOpenSSLWarning\|warnings.warn" "$LOG" | tail -6 | cut -c1-140
  SHADOW=/Users/harshgupta/Projects/webapp/backend/data/kronos_shadow_latest.txt
  SHPID=/Users/harshgupta/Projects/webapp/backend/data/kronos_shadow.pid
  echo
  echo "------------------------------------------------------------------------------------"
  if [ -f "$SHPID" ] && kill -0 "$(cat $SHPID)" 2>/dev/null; then
    echo "SHADOW for the live session: waiting for 09:45, then a forecast for the day's list every 5 minutes until 14:15 (display only, no trade uses it)"
  else
    echo "SHADOW for the live session: not running"
  fi
  [ -f "$SHADOW" ] && cat "$SHADOW" | head -40
  if [ -f "$DONE" ]; then
    echo; echo "=== FINISHED ==="; cat "$DONE"
    echo; echo "result: $W/../docs/research/data/kronos_l40_result.json"
  fi
  echo
  echo "refreshes every 30 s — close this window any time, the run is not attached to it"
  sleep 30
done
