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
