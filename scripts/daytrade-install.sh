#!/usr/bin/env bash
# Install (or remove) the day-trading lab recorder as its own systemd user timer.
# It never touches the live bot's units (swing-trader, daily-trader, schwab-reminder).
set -euo pipefail
APP="$(cd "$(dirname "$0")/.." && pwd)"
UNIT_DIR="$HOME/.config/systemd/user"
if [[ "${1:-}" == "remove" ]]; then
  "$APP/scripts/sysd.sh" disable --now daytrade-recorder.timer 2>/dev/null || true
  "$APP/scripts/sysd.sh" stop daytrade-recorder.service 2>/dev/null || true
  rm -f "$UNIT_DIR/daytrade-recorder.service" "$UNIT_DIR/daytrade-recorder.timer"
  "$APP/scripts/sysd.sh" daemon-reload
  echo "daytrade recorder removed (the live bot's timers are untouched)"
  exit 0
fi
command -v systemctl >/dev/null || { echo "no systemd here: run 'make daytrade-record' from cron at 09:20 ET instead"; exit 1; }
mkdir -p "$UNIT_DIR" "$APP/logs/daytrade" "$APP/state/daytrade" "$APP/data/daytrade"
sed -e "s|__APP_DIR__|$APP|g" "$APP/deploy/daytrade-recorder.service.in" > "$UNIT_DIR/daytrade-recorder.service"
cp "$APP/deploy/daytrade-recorder.timer.in" "$UNIT_DIR/daytrade-recorder.timer"
"$APP/scripts/sysd.sh" daemon-reload
"$APP/scripts/sysd.sh" enable --now daytrade-recorder.timer
"$APP/scripts/sysd.sh" list-timers daytrade-recorder.timer --no-pager || true
