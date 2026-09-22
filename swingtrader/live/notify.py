"""Email alerts via Resend.

Two rules, both load-bearing:

1. **A notification failure must never stop trading.** Every call is wrapped;
   the worst case is a logged warning and a silent run. An alerting bug that
   takes down the trader is strictly worse than no alerting.
2. **Never send twice for the same event.** Alerts are keyed by a digest of
   their content and recorded, so re-running a cycle does not re-notify.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from pathlib import Path

from ..config import get_env

ENDPOINT = "https://api.resend.com/emails"


def _fmt_money(v: float) -> str:
    return f"${v:,.2f}"


class Notifier:
    def __init__(self, state_dir: Path, enabled: bool = True):
        self.api_key = get_env("RESEND_API_KEY")
        self.to = get_env("NOTIFY_EMAIL")
        self.sender = get_env("NOTIFY_FROM", "onboarding@resend.dev")
        self.seen_path = state_dir / "notified.json"
        self.enabled = bool(enabled and self.api_key and self.to)
        self.reason = ""
        if not self.api_key:
            self.reason = "RESEND_API_KEY not set"
        elif not self.to:
            self.reason = "NOTIFY_EMAIL not set"
        try:
            self._seen = set(json.loads(self.seen_path.read_text()))
        except Exception:
            self._seen = set()

    def _remember(self, key: str) -> None:
        self._seen.add(key)
        # keep the file small; only recent keys matter for dedupe
        keep = list(self._seen)[-500:]
        self._seen = set(keep)
        try:
            self.seen_path.parent.mkdir(parents=True, exist_ok=True)
            self.seen_path.write_text(json.dumps(keep))
        except Exception:
            pass

    def send(self, subject: str, html: str, dedupe_key: str | None = None) -> str:
        """Returns a short status string; never raises."""
        if not self.enabled:
            return f"email skipped ({self.reason})"
        key = dedupe_key or hashlib.sha256((subject + html).encode()).hexdigest()[:16]
        if key in self._seen:
            return "email skipped (already sent)"
        try:
            import requests
            r = requests.post(
                ENDPOINT,
                headers={"Authorization": f"Bearer {self.api_key}",
                         "Content-Type": "application/json"},
                json={"from": self.sender, "to": [self.to],
                      "subject": subject, "html": html},
                timeout=15,
            )
            if r.status_code >= 300:
                return f"email FAILED {r.status_code}: {r.text[:160]}"
            self._remember(key)
            return f"email sent -> {self.to}"
        except Exception as exc:
            return f"email FAILED {type(exc).__name__}: {str(exc)[:120]}"

    # ------------------------------------------------------------- templates
    def activity(self, *, equity: float, actions: list[str], fills: list,
                 positions: dict, pending: dict, slippage: dict | None,
                 warnings: list[str], log_tail: list[str],
                 shadow: dict | None = None, dedupe_key: str | None = None) -> str:
        """The one alert that matters: something happened, here is everything."""
        when = dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
        n_fill, n_act = len(fills), len(actions)
        # one prefix, not two -- the warning path used to prepend a second
        # "[swing-trader]" and produce a doubled subject line
        prefix = "[swing-trader] ⚠" if warnings else "[swing-trader]"
        subject = f"{prefix} {n_act} order(s), {n_fill} fill(s) — {_fmt_money(equity)}"

        def rows(hdr, body):
            return (f"<h3 style='margin:18px 0 6px;font:600 13px system-ui'>{hdr}</h3>"
                    f"<div style='font:12px ui-monospace,Menlo,monospace;"
                    f"white-space:pre-wrap;background:#f6f8fa;padding:10px;"
                    f"border-radius:6px'>{body}</div>")

        h = [f"<div style='font:14px system-ui;max-width:760px'>",
             f"<h2 style='margin:0 0 4px'>swing-trader</h2>",
             f"<div style='color:#57606a;font-size:12px'>{when} · equity "
             f"<b>{_fmt_money(equity)}</b></div>"]

        if warnings:
            h.append("<div style='background:#fff1e5;border-left:3px solid #d1242f;"
                     "padding:8px 10px;margin:12px 0;font-size:13px'><b>Warnings</b><br>"
                     + "<br>".join(warnings) + "</div>")

        if actions:
            h.append(rows("Orders this run", "\n".join(actions)))
        if fills:
            body = "\n".join(
                f"{f.side.upper():4} {f.qty:>6.0f} {f.symbol:<6} @ {f.fill_px:>9.4f}  "
                f"ref {f.ref_px:>9.4f}  slippage {f.slippage_bps:+7.1f} bps"
                for f in fills)
            h.append(rows("Fills", body))

        if slippage and slippage.get("n"):
            verdict = ("holding up vs the 20bps the backtest assumed"
                       if slippage["mean"] <= 25 else
                       "WORSE than the 20bps the backtest assumed — edge shrinks")
            h.append(rows("Measured slippage (the number this all rests on)",
                          f"n={slippage['n']}  mean {slippage['mean']:+.1f} bps  "
                          f"median {slippage['median']:+.1f}  p90 {slippage['p90']:+.1f}\n"
                          f"{verdict}"))

        if positions:
            body = "\n".join(
                f"{s:<6} {float(p.get('qty',0)):>6.0f} sh @ {float(p.get('entry_px',0)):>8.2f}  "
                f"stop {float(p.get('stop_px',0)):>8.2f}  held {int(p.get('bars_held',0)):>2}d"
                for s, p in positions.items())
            h.append(rows(f"Open positions ({len(positions)})", body))
        else:
            h.append(rows("Open positions", "flat"))
        if pending:
            h.append(rows(f"Working orders ({len(pending)})",
                          "\n".join(f"{s:<6} {v.get('qty',0)} sh  ref {v.get('ref_px',0):.2f}"
                                    for s, v in pending.items())))
        if shadow:
            h.append(rows("Momentum book (shadow, no orders)",
                          f"holding {shadow.get('holding',0)}  "
                          f"closed {shadow.get('closed',0)}"))
        if log_tail:
            h.append(rows("Run log", "\n".join(log_tail[-40:])))
        h.append("</div>")
        return self.send(subject, "".join(h), dedupe_key=dedupe_key)

    def alert(self, subject: str, body: str) -> str:
        return self.send(f"[swing-trader] {subject}",
                         f"<pre style='font:12px ui-monospace'>{body}</pre>")
