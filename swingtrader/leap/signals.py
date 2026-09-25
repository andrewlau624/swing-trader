"""Signals for the leap book (RESULTS.md addendum 24). Pure functions, no I/O.

research/sim/leap.py calls these, so the backtest and the shadow log share
one implementation. Two rules survived research; neither is a 5x machine:

  orb - SOXL opening-range breakout: the day's first break of the first
        `orm` minutes' range. Up -> long SOXL, down -> long SOXS (the cash
        account cannot short). Stop at the other side of the range, no
        target, out at 15:57. FRAGILE: ~0 in 2016-20, dies at 10bp/side or
        with a 1-minute fill delay.
  ibs - SOXL IBS < 0.2 on the last complete daily bar: hold SOXL next open
        -> following open. Positive 2016-20, 2021-23 and 2024-26.

Micro futures (addendum 25): no new signal. The daily book's noise-band leg
(daily.signals.noise_*) on MNQ passed; what a futures version needs on top
is whole-contract sizing, below. Never force one contract past max_lev: a
small account holding 1 MNQ is 12x at $5k, 61x at $1k.
"""
from __future__ import annotations

import numpy as np

from ..daily.signals import ibs

LAST_MINUTE = 387        # minutes from 09:30; 386 = 15:56 close, flat by 15:57


def orb_break(high: np.ndarray, low: np.ndarray, orm: int) -> tuple[int, int, float, float] | None:
    """(side, minute, entry level, stop) for the day's first range break
    among the minutes seen so far, or None. side +1 = above the range high."""
    if len(high) <= orm:
        return None
    hi, lo = float(np.max(high[:orm])), float(np.min(low[:orm]))
    up = np.where(high[orm:LAST_MINUTE] > hi)[0]
    dn = np.where(low[orm:LAST_MINUTE] < lo)[0]
    fu = up[0] if len(up) else None
    fd = dn[0] if len(dn) else None
    if fu is None and fd is None:
        return None
    if fd is None or (fu is not None and fu < fd):
        return 1, orm + int(fu), hi, lo
    return -1, orm + int(fd), lo, hi


def orb_fill(side: int, level: float, bar_open: float) -> float:
    """A stop order at `level`: filled at the level, or at the bar's open if
    it gapped through."""
    return max(level, bar_open) if side == 1 else min(level, bar_open)


def orb_stopped(side: int, stop: float, bar_high: float, bar_low: float) -> bool:
    return bar_low <= stop if side == 1 else bar_high >= stop


def ibs_entry(high: float, low: float, close: float, ibs_max: float) -> bool:
    v = ibs(high, low, close)
    return bool(np.isfinite(v) and v < ibs_max)


# ------------------------------------------------ micro futures (addendum 25)
FUTURES = {"MNQ": {"mult": 2.0, "tick": 0.25},     # $2 x Nasdaq-100 futures
           "MES": {"mult": 5.0, "tick": 0.25}}     # $5 x S&P 500 futures


def futures_contracts(equity: float, index_level: float, fut: str,
                      target_lev: float, max_lev: float = 2.0) -> int:
    """Whole contracts for `target_lev` x equity, never above `max_lev` x
    equity. 0 when even one contract would exceed max_lev (account too small)."""
    n = FUTURES[fut]["mult"] * index_level
    if not (equity > 0 and n > 0 and np.isfinite(index_level)):
        return 0
    return int(np.floor(min(target_lev, max_lev) * equity / n))
