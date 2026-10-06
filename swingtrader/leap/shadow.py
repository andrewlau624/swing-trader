"""Leap book shadow log. Decides what the leap rules WOULD do and appends it
to logs/leap-shadow.jsonl. There is deliberately no broker, no order and no
account here: going live is a separate, reviewed change (NEXT.md).

The real-money book would live in its own Schwab account
(SCHWAB_LEAP_ACCOUNT_NUMBER) with its own state file (BOOK_FILE), so its
margin and positions never mix with the daily book's. Watch for wash sales:
the Roth book's intraday leg trades SOXL/SOXS too.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import numpy as np

from ..config import ROOT, Config
from . import signals as sg

BOOK_FILE = "book-leap-live.json"     # reserved for a future live book; unused in shadow
LOG = ROOT / "logs" / "leap-shadow.jsonl"


def decide(cfg: Config, minutes: dict, daily_bar: dict | None, today: dt.date) -> list[dict]:
    """minutes: {open, high, low, close} arrays for today so far (minute 0 =
    09:30). daily_bar: the last COMPLETE daily bar of the symbol {high, low, close}."""
    c = cfg.leap
    out = []
    b = sg.orb_break(np.asarray(minutes["high"]), np.asarray(minutes["low"]), c.orb_minutes)
    if b is not None:
        side, m, level, stop = b
        e = sg.orb_fill(side, level, float(minutes["open"][m]))
        out.append(dict(rule="orb", date=str(today), minute=m,
                        buy=c.symbol if side == 1 else c.inverse_symbol,
                        side=side, entry=e, stop=stop))
    if daily_bar and sg.ibs_entry(daily_bar["high"], daily_bar["low"], daily_bar["close"], c.ibs_max):
        out.append(dict(rule="ibs", date=str(today), buy=c.symbol, hold="next open -> following open"))
    return out


def log(decisions: list[dict], path: Path = LOG) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        for d in decisions:
            f.write(json.dumps(d) + "\n")


def forward(cfg: Config, path: Path = LOG, bars=None, today: dt.date | None = None, log_fn=print) -> list[dict]:
    """The robust leap rule, scored forward from daily bars once its exit prints: SOXL IBS < ibs_max on day d ->
    next open -> following open (research/sim/leap.py soxl_ibs, the same rule). The ORB rule is not scored here: it
    needs minute high/low and is ~0 in 2016-20 / dead at 10bp/side (addendum 24). `bars` = {sym: DataFrame} for tests."""
    import pandas as pd
    c = cfg.leap
    rows = [json.loads(x) for x in path.read_text().splitlines() if x.strip()] if path.exists() else []
    done = {r["date"] for r in rows if r.get("rule") == "ibs_fwd"}
    if bars is None:
        from ..daily import marketdata as md
        bars = md.sip_daily([c.symbol], pd.Timestamp(dt.date(2026, 10, 1)) - pd.Timedelta(days=5))
    b = bars[c.symbol].sort_index()
    b = b[b.index < pd.Timestamp(today)] if today else b
    new = []
    for i in range(len(b) - 2):
        d = b.index[i]
        if str(d.date()) in done or d < pd.Timestamp(START):
            continue
        h, lo, cl = (float(b[k].iloc[i]) for k in ("high", "low", "close"))
        if not sg.ibs_entry(h, lo, cl, c.ibs_max):
            continue
        o1, o2 = float(b["open"].iloc[i + 1]), float(b["open"].iloc[i + 2])
        new.append(dict(rule="ibs_fwd", date=str(d.date()), sym=c.symbol, ibs=round(sg.ibs(h, lo, cl), 4),
                        entry=o1, exit=o2, r_bp=round((o2 / o1 - 1) * 1e4, 1)))
    if new:
        log(new, path)
    allr = [r["r_bp"] for r in rows + new if r.get("rule") == "ibs_fwd"]
    log_fn(f"[leap] SOXL IBS forward: {len(allr)} trades" + (f", mean {np.mean(allr):+.1f}bp" if allr else ""))
    return rows + new


START = dt.date(2026, 10, 1)     # first signal day scored (forward only)


if __name__ == "__main__":
    # scoring only, never orders: runs whatever leap.enabled says (that switch is for a future live book)
    forward(Config.load())
