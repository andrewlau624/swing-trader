"""Email reminders before the Schwab login expires.

Schwab refresh tokens die 7 days after `make schwab-login`, and nothing can
renew them without you. After that, real-money trading stops (paper keeps
running, and the 15:40 scan falls back to Alpaca data). So each login gets
four emails, one per stage:

    2 days left   ->  1 day left   ->  under 6 hours left   ->  expired

Keyed on the token's creation time: a fresh login restarts the sequence,
and re-running never re-sends. If the box was down and several stages passed,
only the most urgent is sent.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from .brokers import TOKEN_MAX_AGE_S, schwab_token_path

ET = ZoneInfo("America/New_York")
STAGES = [(48, "2days", "expires in 2 days"),
          (24, "1day", "expires TOMORROW"),
          (6, "today", "expires in a few HOURS"),
          (0, "expired", "has EXPIRED")]


def token_times(path: Path | None = None) -> tuple[float, dt.datetime] | None:
    p = path or schwab_token_path()
    if not p.exists():
        return None
    try:
        created = float(json.loads(p.read_text())["creation_timestamp"])
    except Exception:
        return None
    return created, dt.datetime.fromtimestamp(created + TOKEN_MAX_AGE_S, ET)


def _body(headline: str, expires: dt.datetime) -> str:
    return (f"<p>Your Schwab API login {headline} "
            f"(<b>{expires:%a %b %d, %I:%M %p} ET</b>).</p>"
            "<p>On the server, run:</p><pre>make schwab-login</pre>"
            "<p>Open the link it prints, log in with your Schwab <i>brokerage</i> login, "
            "then paste back the https://127.0.0.1/?code=... address you land on "
            "(the \"can't connect\" page is expected). Paste it within ~30 seconds.</p>"
            "<p>If it lapses: real-money trading stops and places nothing; paper keeps "
            "running; the 15:40 scan uses Alpaca data instead of Schwab.</p>")


def probe(path: Path | None = None) -> str | None:
    """Ask Schwab whether the login still works. Returns an error string if it
    was revoked -- Schwab allows ONE active login per app, so logging in on a
    second machine silently kills the first. Age alone cannot see that."""
    try:
        from .brokers import schwab_client
        r = schwab_client().get_account_numbers()
        r.raise_for_status()
        return None
    except Exception as exc:
        msg = str(exc)
        if "invalid_grant" in msg or "invalid, expired or revoked" in msg or "401" in msg:
            return msg[:200]
        return None           # network hiccup etc.: not evidence of revocation


def check(notifier, now: dt.datetime | None = None, path: Path | None = None,
          probe_fn=None) -> str:
    t = token_times(path)
    if t is None:
        return "no Schwab login on this machine"
    created, expires = t
    now = now or dt.datetime.now(ET)
    hours_left = (expires - now).total_seconds() / 3600
    if hours_left > 0:
        err = (probe_fn or (lambda: probe(path)))()
        if err:
            return "Schwab login REVOKED: " + notifier.send(
                "[swing-trader] Schwab login was REVOKED - run make schwab-login on the server",
                "<p>Schwab rejected the saved login before its 7 days were up. Most likely "
                "cause: you logged in on another machine. Schwab keeps only ONE active login "
                "per app, and the newest wins.</p><p>Real-money trading is stopped until you run "
                "<code>make schwab-login</code> <b>on the server</b>. Paper keeps running.</p>"
                f"<pre>{err}</pre>", dedupe_key=f"schwab-token:{int(created)}:revoked")
    due = [s for s in STAGES if hours_left <= s[0]]
    if not due:
        return f"Schwab login OK: {hours_left/24:.1f} days left (expires {expires:%a %b %d %I:%M %p} ET)"
    urgent = due[-1]
    key = lambda s: f"schwab-token:{int(created)}:{s[1]}"
    if key(urgent) in notifier._seen:
        return f"Schwab login {urgent[2]} - reminder already sent"
    status = notifier.send(f"[swing-trader] Schwab login {urgent[2]} - run make schwab-login",
                           _body(urgent[2], expires), dedupe_key=key(urgent))
    for s in due[:-1]:          # stages skipped while the box was down: never send stale ones
        notifier._remember(key(s))
    return f"Schwab login {urgent[2]}: {status}"


def confirm_login(notifier, path: Path | None = None) -> str:
    t = token_times(path)
    if t is None:
        return "no token to confirm"
    created, expires = t
    when = lambda h: (expires - dt.timedelta(hours=h)).strftime("%a %b %d %I:%M %p")
    html = (f"<p>Schwab API login renewed. It expires <b>{expires:%a %b %d, %I:%M %p} ET</b>.</p>"
            f"<p>Reminders will arrive around: {when(48)}, {when(24)}, {when(6)} ET.</p>"
            "<p>Tip: log in during the day, so the expiry, and the last reminder, "
            "fall at a time you are awake.</p>")
    return notifier.send(f"[swing-trader] Schwab login renewed - expires {expires:%a %b %d}",
                         html, dedupe_key=f"schwab-token:{int(created)}:renewed")
