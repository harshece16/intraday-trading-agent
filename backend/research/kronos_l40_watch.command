#!/bin/bash
# Live view of the Kronos look L40: the run of record on the PC (over SSH) and tomorrow's shadow on this Mac. Read-only.
PC="ssh -i $HOME/.ssh/trader_sahab_pc -o BatchMode=yes -o ConnectTimeout=6 harsh@192.168.88.3"
SHADOW=/Users/harshgupta/Projects/webapp/backend/data/kronos_shadow_latest.txt
SHPID=/Users/harshgupta/Projects/webapp/backend/data/kronos_shadow.pid
while true; do
  clear
  echo "KRONOS LOOK L40 — run of record on the PC (RTX 3060 Ti, three samples a forecast)      $(date '+%a %d %b %H:%M:%S')"
  echo "prereg: docs/research/prereg-kronos-feature-ic.md (amendment 4)   branch: research/kronos-l40-run   PR #200"
  echo "------------------------------------------------------------------------------------"
  $PC 'powershell -NoProfile -ExecutionPolicy Bypass -File tail.ps1 -N 14 -Task KronosPass' 2>/dev/null | grep -v "symlink\|warnings.warn\|Xet Storage\|UserWarning\|^gpu line" | cut -c1-120 || echo "PC not reachable right now"
  echo
  echo "------------------------------------------------------------------------------------"
  if [ -f "$SHPID" ] && kill -0 "$(cat $SHPID)" 2>/dev/null; then
    echo "SHADOW on this Mac for the live session: waiting for 09:45, then a forecast for the day's list every 5 minutes until 14:15 (display only)"
  else
    echo "SHADOW on this Mac: not running"
  fi
  [ -f "$SHADOW" ] && head -32 "$SHADOW"
  echo
  echo "refreshes every 30 s — close this window any time; nothing runs in it"
  sleep 30
done
