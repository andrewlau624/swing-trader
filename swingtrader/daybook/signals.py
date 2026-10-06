"""Signal primitives for the intraday day book (mirror swingtrader.daily.signals:676-731).

No lookahead: sigma uses sessions strictly before the trade day; bounds use the day open
and prior close (both known at 09:30); decisions use only minute closes up to the decision.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class DaybookConfig:
    # instruments and their share of the intraday risk budget
    core: dict = field(default_factory=lambda: {"QQQ": 0.5, "SMH": 0.5})
    conviction: dict = field(default_factory=lambda: {"TQQQ": 0.0, "SOXL": 0.0})
    # signal
    lookback: int = 14
    step: int = 30            # decision every 30 minutes from the open
    first: int = 30           # first decision minute (10:00)
    last: int = 360           # last decision minute (15:30)
    # sizing
    target_vol: float = 0.02  # daily-return vol target per instrument
    max_lev: float = 3.5      # leverage cap per instrument
    conviction_strength: float = 0.341   # first-breakout strength (sigma units) for conviction
    conviction_mult: float = 2.0
    # risk
    max_daily_loss: float = 0.0   # 0 = off; fraction of equity, stop trading for the day
    # costs, bp per fill (per unit of position changed)
    cost_bps: float = 1.0
    # flatten minute: 389 = the 15:59 minute (live flattens at 15:57, before the 16:00 auction).
    # 390 = hold through the closing auction. Live/reference use <390.
    close_min: int = 389


def noise_sigma(history_moves: np.ndarray) -> np.ndarray:
    """history_moves: (days, NMIN) of |close_m/open_day - 1| for prior sessions."""
    return np.nanmean(history_moves, axis=0)


def noise_bounds(day_open: float, prev_close: float, sigma: np.ndarray):
    ub = max(day_open, prev_close) * (1.0 + sigma)
    lb = min(day_open, prev_close) * (1.0 - sigma)
    return ub, lb


def noise_decide(pos: int, price: float, ub: float, lb: float, vwap: float) -> int:
    if pos == 1 and price < max(ub, vwap):
        pos = 0
    elif pos == -1 and price > min(lb, vwap):
        pos = 0
    if pos == 0:
        if price > ub:
            pos = 1
        elif price < lb:
            pos = -1
    return pos


def breakout_strength(price: float, ub: float, lb: float, sigma: float):
    if not (np.isfinite(price) and sigma > 0):
        return 0, 0.0
    if price > ub:
        return 1, (price / ub - 1) / sigma
    if price < lb:
        return -1, (1 - price / lb) / sigma
    return 0, 0.0


def vol_leverage(daily_closes: np.ndarray, target_vol: float, max_lev: float) -> float:
    """Vol target from the prior <=14 daily returns (known pre-open)."""
    r = pd.Series(daily_closes).pct_change().dropna()
    if len(r) < 5:
        return 0.0
    sd = float(r.iloc[-14:].std())
    if not np.isfinite(sd) or sd <= 0:
        return 0.0
    return float(min(max_lev, target_vol / sd))
