#!/usr/bin/env bash
# Install the three-a-day schedule, using whatever this box actually supports.
#
# Prefers a systemd user timer (clean timezone handling, survives logout with
# lingering). Falls back to cron when there is no systemd user session -- which
# is the normal situation after `su - user` from root, because that gives you a
# shell but no D-Bus session and no XDG_RUNTIME_DIR.
set -uo pipefail
APP="$(cd "$(dirname "$0")/.." && pwd)"
USER_="$(whoami)"
UID_="$(id -u)"

have_systemd_user() {
  command -v systemctl >/dev/null 2>&1 || return 1
  # a user bus needs XDG_RUNTIME_DIR; try to supply it if the dir exists
  if [[ -z "${XDG_RUNTIME_DIR:-}" && -d "/run/user/$UID_" ]]; then
    export XDG_RUNTIME_DIR="/run/user/$UID_"
    export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$UID_/bus"
  fi
  systemctl --user show-environment >/dev/null 2>&1
}

install_systemd() {
  echo "installing systemd user timer..."
  mkdir -p "$HOME/.config/systemd/user"
  sed -e "s|__USER__|$USER_|g" -e "s|__APP_DIR__|$APP|g" \
      "$APP/deploy/swing-trader.service.in" > "$HOME/.config/systemd/user/swing-trader.service"
  cp "$APP/deploy/swing-trader.timer.in" "$HOME/.config/systemd/user/swing-trader.timer"
  systemctl --user daemon-reload
  systemctl --user enable --now swing-trader.timer
  if ! loginctl show-user "$USER_" -p Linger 2>/dev/null | grep -q "Linger=yes"; then
    echo ""
    echo "  WARNING: lingering is OFF, so this timer stops when you log out of SSH."
    echo "  Fix it as root:   sudo loginctl enable-linger $USER_"
  fi
  echo ""
  systemctl --user list-timers swing-trader.timer --no-pager || true
}

install_cron() {
  echo "installing cron entries..."
  local tmp; tmp="$(mktemp)"
  crontab -l 2>/dev/null | grep -v 'run-live.sh' \
    | grep -vE '^CRON_TZ=America/New_York|^# swing-trader' > "$tmp" || true

  if [[ "$(uname -s)" == "Darwin" ]]; then
    # macOS cron ignores CRON_TZ entirely, so ET times must be converted to
    # local clock times or the runs fire hours off. Compute the offset rather
    # than hardcoding it, so this stays correct across DST and machines.
    echo "# swing-trader - macOS cron ignores CRON_TZ, so these are LOCAL times" >> "$tmp"
    python3 - "$APP" >> "$tmp" <<'PYEOF'
import sys, datetime as dt
from zoneinfo import ZoneInfo
app = sys.argv[1]
et, local = ZoneInfo("America/New_York"), dt.datetime.now().astimezone().tzinfo
today = dt.date.today()
notes = {(9,5):"decide + submit market-on-open",
         (9,47):"reconcile fills, arm stops",
         (15,52):"pre-close sweep"}
for (h, m), note in notes.items():
    t = dt.datetime.combine(today, dt.time(h, m), tzinfo=et).astimezone(local)
    print(f"{t.minute:2d} {t.hour} * * 1-5 {app}/scripts/run-live.sh  # {h:02d}:{m:02d} ET - {note}")
PYEOF
  else
    echo "# swing-trader - times below are US/Eastern via CRON_TZ" >> "$tmp"
    echo "CRON_TZ=America/New_York" >> "$tmp"
    {
      echo " 5 9 * * 1-5 $APP/scripts/run-live.sh   # decide + submit market-on-open"
      echo "47 9 * * 1-5 $APP/scripts/run-live.sh   # reconcile fills, arm stops"
      echo "52 15 * * 1-5 $APP/scripts/run-live.sh  # pre-close sweep"
    } >> "$tmp"
  fi

  crontab "$tmp" && rm -f "$tmp"
  echo ""
  crontab -l | grep -A4 'swing-trader'
  echo ""
  echo "  server timezone : $(date +%Z) ($(date '+%H:%M'))"
  echo "  US/Eastern now  : $(TZ=America/New_York date '+%H:%M %Z')"
  if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "  If CRON_TZ is unsupported here, those fire at the listed times in SERVER"
    echo "  time instead. Every run stamps ET in the log, so confirm after the first"
    echo "  fire with:  make logs"
  fi
}

case "$(uname -s)" in
  Linux)
    if have_systemd_user; then
      install_systemd
    else
      echo "systemd user session unavailable - 'systemctl --user' cannot reach a bus."
      echo "  Usually because this shell came from 'su - $USER_' rather than a real login."
      echo "  Falling back to cron, which needs no session and works fine."
      echo ""
      echo "  To use systemd instead, as root run:"
      echo "      loginctl enable-linger $USER_"
      echo "  then reconnect with:  ssh $USER_@<host>     (not 'su - $USER_')"
      echo "  and re-run: make persist"
      echo ""
      install_cron
    fi
    ;;
  *) install_cron ;;
esac
echo ""
echo "installed. check it with:  make persist-status"
