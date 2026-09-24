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


def momentum_top(closes: pd.DataFrame, today: pd.Timestamp, k: int,
                 lookback: int = 252, skip: int = 21) -> list[str]:
    """Top-k ETFs by 12-1 month momentum, ranked at the last month-end BEFORE
    today and held for the month (research: h5a.py, "top-3 by 12m momentum").
    Replaces a hand-picked tech list: same idea, chosen by rule, so it rotates
    on its own if tech stops leading. closes: session-date index, one column
    per ETF, bars strictly before today."""
    if closes is None or closes.empty or not isinstance(closes.index, pd.DatetimeIndex):
        return []                     # no data today: hold nothing rather than crash
    c = closes[closes.index < today]
    mom = c.shift(skip) / c.shift(lookback) - 1
    month_ends = mom.groupby([mom.index.year, mom.index.month]).tail(1)
    month_ends = month_ends[month_ends.index.to_period("M") < today.to_period("M")]
    if month_ends.empty:
        return []
    last = month_ends.iloc[-1].dropna()
    return sorted(last.sort_values(ascending=False).index[:k])


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


def prev_close_mismatch(rows: pd.DataFrame, tol: float = 0.03) -> pd.Series:
    """True where yesterday's close from our daily bars disagrees with the
    quote feed's own previous close. That is a split or other corporate action
    our bars have not absorbed yet, and it fakes the day's move: a 1:10 split
    reads as -90%. The research data had exactly these (a -94% "day" followed
    by +1,250% "overnight"). Rows without a feed value are never flagged."""
    if "feed_prev_close" not in rows:
        return pd.Series(False, index=rows.index)
    fp = rows["feed_prev_close"].astype(float)
    bad = (fp / rows["prev_close"].astype(float) - 1.0).abs() > tol
    return bad & np.isfinite(fp) & (fp > 0)


def night_exit_cost(fills: list[dict], opens: dict, window: int = 30) -> tuple[int, float]:
    """Mean cost of the last `window` night-leg SELLS against the official
    opening print, in bps per side (+ = sold below the open). The whole night
    edge is in the open auction (RESULTS.md addendum 10), and every 5bp/side
    here costs ~8pp/yr; it is gone near 28bp (addendum 14). `opens` maps
    (sym, 'YYYY-MM-DD') -> official open. Returns (n measured, mean bps)."""
    sells = [f for f in fills if f.get("leg") == "night" and f.get("side") == "sell"]
    costs = []
    for f in sells[-window:]:
        o = opens.get((f["sym"], str(f.get("filled_at", ""))[:10]))
        if o and o > 0 and f.get("fill_px"):
            costs.append(-(float(f["fill_px"]) / o - 1.0) * 1e4)
    return len(costs), (float(np.mean(costs)) if costs else float("nan"))


def dedupe_correlated(picks: pd.DataFrame, rets: dict, max_corr: float = 0.9) -> tuple[pd.DataFrame, list]:
    """One position per underlying bet. Walk the picks most-beaten first and
    drop any whose last-20-day returns correlate above max_corr with one
    already kept. Seven 2x SpaceX ETFs from seven issuers are one bet, not
    seven; so are a stock and its own leveraged ETF. No name parsing, so new
    products are handled as they launch. Returns (kept, [(dropped, kept_as)])."""
    kept, dropped, series = [], [], []
    for sym in picks.index:
        r = np.asarray(rets.get(sym) or [], dtype=float)
        dup = None
        if len(r) >= 10 and np.std(r) > 0:
            for k, rk in series:
                n = min(len(r), len(rk))
                if n >= 10 and np.std(rk[-n:]) > 0 and np.corrcoef(r[-n:], rk[-n:])[0, 1] > max_corr:
                    dup = k; break
        if dup is None:
            kept.append(sym)
            if len(r) >= 10:
                series.append((sym, r))
        else:
            dropped.append((sym, dup))
    return picks.loc[kept], dropped


def night_sizing(picks: pd.DataFrame, *, vol_min: float, crowd_n: int,
                 max_name_pct: float) -> tuple[pd.DataFrame, float]:
    """Filter and size the night leg (research: h1.py / h1port.py, rule R6).

    - drop names whose 20-day volatility is under `vol_min`: in quiet names a
      -8% day is news, not overreaction (-33bp/trade, t -8)
    - count the day's raw signals BEFORE that filter; on days with more than
      `crowd_n` of them the selloff is market-wide and the bounce is weak
      (-9bp vs +25bp on ordinary days), so exposure scales by crowd_n / n.
    Returns (kept picks, fraction of the leg per name)."""
    n_raw = len(picks)
    kept = picks[picks["vol20"] >= vol_min] if "vol20" in picks else picks
    if kept.empty:
        return kept, 0.0
    per = min(1.0 / len(kept), max_name_pct) * min(1.0, crowd_n / max(n_raw, 1))
    return kept, per


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
