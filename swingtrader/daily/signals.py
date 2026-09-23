"""Signals for the daily-cadence book. Pure functions, no I/O.

Each one is a port of the research code in research/daily-strategies/, and
tests/test_daily.py pins it to that behaviour. Three legs:

  ibs    - IBS < 0.2 on tech ETFs, decided on the last COMPLETE daily bar and
           held open -> next open. (research: etfport.py, "@nextopen")
  night  - stocks down >= 8% on the day, trading within 10% of the day's low,
           decided at ~15:40 ET from what is known THEN, bought at the close
           auction and sold at the next open auction. (research: t1550.py)
  noise  - QQQ "noise area" intraday momentum. (research: noise.py)

The night leg is the one where lookahead did the most damage in research:
computed from the final close it showed 58% CAGR, computed at 15:50 it showed
31%. Nothing here may be fed the closing print.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# ------------------------------------------------------------------ IBS leg
def ibs(high: float, low: float, close: float) -> float:
    """Internal bar strength: where the close sits in the day's range, 0..1."""
    rng = high - low
    if not np.isfinite(rng) or rng <= 0:
        return np.nan
    return (close - low) / rng


def ibs_targets(last_bars: dict[str, dict], ibs_max: float) -> list[str]:
    """ETFs to HOLD from the next open. `last_bars[sym]` is the last complete
    daily bar {high, low, close}. Re-evaluated every morning: a name still
    below the threshold stays held, one that recovered is sold."""
    out = []
    for sym, b in last_bars.items():
        v = ibs(b["high"], b["low"], b["close"])
        if np.isfinite(v) and v < ibs_max:
            out.append(sym)
    return sorted(out)


def equal_weights(symbols: list[str], leg_equity: float,
                  max_name_pct: float = 1.0) -> dict[str, float]:
    """Dollar allocation per name: 1/n of the leg, capped per name."""
    if not symbols:
        return {}
    per = leg_equity * min(1.0 / len(symbols), max_name_pct)
    return {s: per for s in symbols}


# ---------------------------------------------------------------- night leg
def loser_picks(rows: pd.DataFrame, *, day_ret_max: float, ibs_max: float,
                price_min: float, price_max: float) -> pd.DataFrame:
    """Rows: one per symbol with columns
         price       - latest trade at decision time (~15:40 ET)
         prev_close  - yesterday's official close
         high, low   - the day's range AS KNOWN AT DECISION TIME
       Returns the qualifying rows, most-beaten first, with day_ret and ibs.
    """
    if rows.empty:
        return rows.assign(day_ret=[], ibs=[])
    r = rows.copy()
    r["high"] = np.maximum(r["high"], r["price"])
    r["low"] = np.minimum(r["low"], r["price"])
    r["day_ret"] = r["price"] / r["prev_close"] - 1.0
    rng = (r["high"] - r["low"]).where(lambda x: x > 0)
    r["ibs"] = (r["price"] - r["low"]) / rng
    m = ((r["day_ret"] <= day_ret_max) & (r["ibs"] < ibs_max)
         & (r["price"] >= price_min) & (r["price"] <= price_max)
         & np.isfinite(r["day_ret"]) & np.isfinite(r["ibs"]))
    return r[m].sort_values("day_ret")


# ---------------------------------------------------------------- noise leg
NOISE_STEP = 30      # decisions at 10:00, 10:30, ... 15:30 (minutes from open)
NOISE_FIRST = 30


def noise_sigma(history_moves: np.ndarray) -> np.ndarray:
    """history_moves: (days, 390) array of |close_m / open_day - 1| for the
    previous `lookback` sessions. Returns sigma per minute-of-day."""
    return np.nanmean(history_moves, axis=0)


def noise_bounds(day_open: float, prev_close: float,
                 sigma: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    ub = max(day_open, prev_close) * (1.0 + sigma)
    lb = min(day_open, prev_close) * (1.0 - sigma)
    return ub, lb


def noise_decide(pos: int, price: float, ub: float, lb: float,
                 vwap: float) -> int:
    """One decision point. pos in {-1, 0, 1}. Exit when price falls back
    through the band or VWAP (whichever is tighter), then re-test for entry.
    Mirrors research/noise.py exactly, including re-entry on the same bar."""
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


def noise_leverage(daily_closes: pd.Series, target_vol: float,
                   max_lev: float) -> float:
    """Vol-targeted size from the prior 14 daily returns (known pre-open)."""
    r = daily_closes.pct_change().dropna().iloc[-14:]
    sd = float(r.std())
    if not np.isfinite(sd) or sd <= 0:
        return 0.0
    return float(min(max_lev, target_vol / sd))
