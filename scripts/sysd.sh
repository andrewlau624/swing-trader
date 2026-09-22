#!/usr/bin/env bash
# Run `systemctl --user` with the session environment supplied.
#
# A shell reached via `su - user` has no XDG_RUNTIME_DIR or DBUS address, so
# systemctl --user reports "Failed to connect to bus" even when the units are
# installed and the timer is running. Supplying them makes every caller agree
# about whether the timer exists -- the installer once said "installed" while
# persist-status said "not installed", both correct from where they stood.
[[ -z "${XDG_RUNTIME_DIR:-}" && -d "/run/user/$(id -u)" ]] && \
  export XDG_RUNTIME_DIR="/run/user/$(id -u)"
[[ -z "${DBUS_SESSION_BUS_ADDRESS:-}" && -S "${XDG_RUNTIME_DIR:-/nonexistent}/bus" ]] && \
  export DBUS_SESSION_BUS_ADDRESS="unix:path=${XDG_RUNTIME_DIR}/bus"
exec systemctl --user "$@"
