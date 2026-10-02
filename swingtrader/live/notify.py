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
import base64
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
            # insertion-ordered, not a set: set ordering is arbitrary, so
            # truncating it could drop RECENT dedupe keys and keep stale ones
            self._seen = list(dict.fromkeys(json.loads(self.seen_path.read_text())))
        except Exception:
            self._seen = []

    def _remember(self, key: str) -> None:
        if key not in self._seen:
            self._seen.append(key)
        # keep the file small; only recent keys matter for dedupe
        self._seen = self._seen[-500:]
        try:
            self.seen_path.parent.mkdir(parents=True, exist_ok=True)
            self.seen_path.write_text(json.dumps(self._seen))
        except Exception:
            pass

    def send(self, subject: str, html: str, dedupe_key: str | None = None,
             images: list[tuple[str, bytes]] | None = None) -> str:
        """Returns a short status string; never raises. images: (content_id, png bytes) pairs,
        referenced in the html as <img src="cid:content_id"> (Resend inline attachments)."""
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
                json={"from": self.sender, "to": [self.to], "subject": subject, "html": html,
                      **({"attachments": [{"filename": f"{cid}.png", "content_type": "image/png",
                                           "content_id": cid,
                                           "content": base64.b64encode(png).decode()}
                                          for cid, png in images]} if images else {})},
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
        from . import mail as M
        n_fill, n_act = len(fills), len(actions)
        # one prefix, not two -- the warning path used to prepend a second
        # "[swing-trader]" and produce a doubled subject line
        prefix = "[swing-trader] ⚠" if warnings else "[swing-trader]"
        subject = f"{prefix} {n_act} order(s), {n_fill} fill(s) — {_fmt_money(equity)}"
        B = []
        if warnings:
            B.append(M.action("Warning", f"{len(warnings)} warning(s)", lines=warnings, tone="warn"))
        if actions:
            B.append(M.code("\n".join(actions), "Orders this run"))
        if fills:
            B.append(M.code("\n".join(
                f"{f.side.upper():4} {f.qty:>6.0f} {f.symbol:<6} @ {f.fill_px:>9.4f}  "
                f"ref {f.ref_px:>9.4f}  slippage {f.slippage_bps:+7.1f} bps" for f in fills), "Fills"))
        if slippage and slippage.get("n"):
            verdict = ("holding up vs the 20bps the backtest assumed"
                       if slippage["mean"] <= 25 else
                       "WORSE than the 20bps the backtest assumed — edge shrinks")
            B.append(M.facts([("Fills measured", str(slippage["n"])), ("Mean", f"{slippage['mean']:+.1f} bps"),
                              ("Median", f"{slippage['median']:+.1f} bps"), ("p90", f"{slippage['p90']:+.1f} bps")],
                             "Measured slippage") + M.para(verdict, muted=True))
        B.append(M.code("\n".join(
            f"{s:<6} {float(p.get('qty',0)):>6.0f} sh @ {float(p.get('entry_px',0)):>8.2f}  "
            f"stop {float(p.get('stop_px',0)):>8.2f}  held {int(p.get('bars_held',0)):>2}d"
            for s, p in positions.items()) or "flat", f"Open positions ({len(positions)})"))
        if pending:
            B.append(M.code("\n".join(f"{s:<6} {v.get('qty',0)} sh  ref {v.get('ref_px',0):.2f}"
                                      for s, v in pending.items()), f"Working orders ({len(pending)})"))
        if shadow:
            B.append(M.para(f"Momentum book (shadow, no orders): holding {shadow.get('holding',0)}, "
                            f"closed {shadow.get('closed',0)}", muted=True))
        if log_tail:
            B.append(M.code("\n".join(log_tail[-40:]), "Run log"))
        h = [M.page("swing-trader", f"{n_act} order(s), {n_fill} fill(s)", f"equity {_fmt_money(equity)}", B)]
        return self.send(subject, "".join(h), dedupe_key=dedupe_key)

    def mail(self, subject: str, html: str, dedupe_key: str | None = None) -> str:
        """An email built with swingtrader.live.mail (the digest's look)."""
        return self.send(f"[swing-trader] {subject}", html, dedupe_key=dedupe_key)

    def alert(self, subject: str, body: str) -> str:
        """Plain-text fallback, still in the shared look."""
        from . import mail as M
        return self.mail(subject, M.page("Alert", subject, blocks=[M.code(body)]))
