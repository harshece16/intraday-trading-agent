#!/bin/bash
# Install (or remove) the launchd job that keeps Trader Sahab's backend running
# during market hours whenever this Mac is awake.
#
#   scripts/install_watchdog.sh            install and start
#   scripts/install_watchdog.sh --uninstall remove it
#   scripts/install_watchdog.sh --status    is it loaded, and what has it done
#
# This writes one file to ~/Library/LaunchAgents and registers it with launchd.
# Nothing else on the machine is touched, and uninstalling removes both.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LABEL="com.tradersahab.watchdog"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$HOME/Library/Logs/TraderSahab"

case "${1:-install}" in
  --status)
    if launchctl list | grep -q "$LABEL"; then
      echo "loaded:  yes"
      launchctl list | awk -v l="$LABEL" '$3 == l {print "  pid/last exit: "$1"/"$2}'
    else
      echo "loaded:  no"
    fi
    echo "plist:   $PLIST"
    echo "logs:    $LOG_DIR"
    [ -f "$LOG_DIR/watchdog.log" ] && { echo "--- last 10 watchdog lines ---"; tail -10 "$LOG_DIR/watchdog.log"; }
    exit 0
    ;;
  --uninstall)
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || launchctl unload "$PLIST" 2>/dev/null || true
    rm -f "$PLIST"
    echo "Removed $LABEL. Logs are kept in $LOG_DIR."
    echo "Any backend it started is still running; stop it yourself if you want it down."
    exit 0
    ;;
  install) ;;
  *) echo "usage: $0 [install|--uninstall|--status]" >&2; exit 2 ;;
esac

[ -x "$REPO/backend/.venv/bin/python" ] || {
  echo "No virtualenv at backend/.venv — create it first:" >&2
  echo "  cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
}

mkdir -p "$HOME/Library/LaunchAgents" "$LOG_DIR"
chmod +x "$REPO/scripts/sahab_watchdog.sh"
sed -e "s|__REPO__|$REPO|g" -e "s|__HOME__|$HOME|g" \
    "$REPO/scripts/com.tradersahab.watchdog.plist" > "$PLIST"

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST" 2>/dev/null || launchctl load "$PLIST"

echo "Installed $LABEL"
echo "  checks every 2 minutes, and again whenever the Mac wakes"
echo "  starts the backend only during a trading session (NSE holidays included)"
echo "  logs: $LOG_DIR/watchdog.log"
echo
echo "Check it with:  scripts/install_watchdog.sh --status"
echo "Remove it with: scripts/install_watchdog.sh --uninstall"
