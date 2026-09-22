#!/usr/bin/env bash
# Stop the previous llm-trader deployment, wherever and however it is running.
#
# It could be any of: a systemd system unit, a systemd *user* unit, the
# supervise.sh restart loop, a bare nohup'd live.py, a cron entry, or a launchd
# job on macOS. This finds and stops all of them, then verifies nothing is left.
#
#   ./scripts/kill-old-trader.sh          # show what it would stop
#   ./scripts/kill-old-trader.sh --yes    # actually stop it
set -uo pipefail

APPLY=0
[[ "${1:-}" == "--yes" || "${1:-}" == "-y" ]] && APPLY=1
FOUND=0
say() { printf '%s\n' "$*"; }
run() { if [[ $APPLY -eq 1 ]]; then say "    -> $*"; eval "$@" >/dev/null 2>&1; else say "    would run: $*"; fi; }

say "=== searching for a running llm-trader ==="

# 1. systemd (system scope)
if command -v systemctl >/dev/null 2>&1; then
  for unit in llm-trader llm-trader.service llmtrader; do
    if systemctl list-units --all --no-legend 2>/dev/null | grep -q "^\s*${unit}"; then
      state=$(systemctl is-active "$unit" 2>/dev/null)
      say "  [systemd/system] $unit is $state"; FOUND=1
      run "sudo systemctl stop $unit"
      run "sudo systemctl disable $unit"
    fi
  done
  # 2. systemd (user scope) - no sudo needed
  for unit in llm-trader llm-trader.service llmtrader; do
    if systemctl --user list-units --all --no-legend 2>/dev/null | grep -q "^\s*${unit}"; then
      state=$(systemctl --user is-active "$unit" 2>/dev/null)
      say "  [systemd/user]   $unit is $state"; FOUND=1
      run "systemctl --user stop $unit"
      run "systemctl --user disable $unit"
    fi
  done
fi

# 3. supervise.sh / bare live.py processes
PIDS=$(pgrep -f "supervise\.sh|llmtrader|llm-trader" 2>/dev/null | tr '\n' ' ')
# only match the OLD project's live.py, never this repo's
OLD_LIVE=$(pgrep -f "live\.py.*--strategy" 2>/dev/null | tr '\n' ' ')
PIDS="$PIDS $OLD_LIVE"
PIDS=$(echo "$PIDS" | tr ' ' '\n' | sort -u | grep -v '^$' | tr '\n' ' ')
if [[ -n "${PIDS// /}" ]]; then
  say "  [process] pids:$PIDS"; FOUND=1
  for p in $PIDS; do
    ps -p "$p" -o pid=,command= 2>/dev/null | sed 's/^/      /'
  done
  run "kill $PIDS"
  if [[ $APPLY -eq 1 ]]; then
    sleep 3
    STILL=$(echo "$PIDS" | tr ' ' '\n' | while read -r p; do [[ -n "$p" ]] && kill -0 "$p" 2>/dev/null && echo "$p"; done | tr '\n' ' ')
    [[ -n "${STILL// /}" ]] && { say "    still alive, sending KILL: $STILL"; kill -9 $STILL 2>/dev/null; }
  fi
fi

# 4. cron entries pointing at the old project
if crontab -l >/dev/null 2>&1; then
  if crontab -l 2>/dev/null | grep -qiE "llm-trader|llmtrader|supervise\.sh"; then
    say "  [cron] entries referencing the old trader:"
    crontab -l 2>/dev/null | grep -inE "llm-trader|llmtrader|supervise\.sh" | sed 's/^/      /'
    FOUND=1
    if [[ $APPLY -eq 1 ]]; then
      crontab -l 2>/dev/null | grep -viE "llm-trader|llmtrader|supervise\.sh" | crontab -
      say "    -> removed those cron lines (other entries kept)"
    else
      say "    would remove those lines, keeping every other cron entry"
    fi
  fi
fi

# 5. launchd (macOS)
if command -v launchctl >/dev/null 2>&1; then
  JOBS=$(launchctl list 2>/dev/null | grep -iE "llm.?trader" | awk '{print $3}')
  if [[ -n "${JOBS// /}" ]]; then
    say "  [launchd] $JOBS"; FOUND=1
    for j in $JOBS; do run "launchctl remove $j"; done
  fi
fi

say ""
if [[ $FOUND -eq 0 ]]; then
  say "nothing found - no old trader is running here."
  say "if it runs on another host, run this script there (it is the SSH box that matters)."
  exit 0
fi

if [[ $APPLY -eq 0 ]]; then
  say "DRY RUN. Nothing was stopped. Re-run with --yes to apply:"
  say "    ./scripts/kill-old-trader.sh --yes"
  exit 0
fi

say "=== verifying ==="
sleep 2
LEFT=$(pgrep -f "supervise\.sh|llmtrader|live\.py.*--strategy" 2>/dev/null | tr '\n' ' ')
if [[ -n "${LEFT// /}" ]]; then
  say "STILL RUNNING: $LEFT"
  say "inspect with: ps -p ${LEFT// /,} -o pid,ppid,command"
  exit 1
fi
say "clean - no llm-trader processes remain."
say "NOTE: open Alpaca positions are NOT touched by this. Check them with:"
say "    make positions"
