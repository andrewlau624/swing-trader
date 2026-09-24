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


def exit_cost_by_route(fills: list[dict], opens: dict, window: int = 60) -> dict:
    """Open-sell quality per route (NASDAQ/NYSE/... = directed to the listing
    exchange's auction, AUTO = Schwab's routing, "" = broker OPG orders).
    Returns {route: (n, mean bps/side, auction hit rate)}. A fill within half
    a cent of the official open counts as an auction fill: that is the direct
    evidence the emulated market-on-open is reaching the auction."""
    sells = [f for f in fills if f.get("leg") == "night" and f.get("side") == "sell"][-window:]
    by: dict[str, list] = {}
    for f in sells:
        o = opens.get((f["sym"], str(f.get("filled_at", ""))[:10]))
        if not (o and o > 0 and f.get("fill_px")):
            continue
        px = float(f["fill_px"])
        by.setdefault(str(f.get("route") or ""), []).append(
            (-(px / o - 1.0) * 1e4, abs(px - o) <= 0.005))
    return {r: (len(v), float(np.mean([c for c, _ in v])), float(np.mean([h for _, h in v])))
            for r, v in by.items()}


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


def gap_scale(today, next_open, scale: float) -> float:
    """Night-leg exposure multiplier: `scale` when the position is held over
    more than one calendar night (weekend, holiday), else 1. Weekend nights
    earn the same per trade but swing harder (std 6.2% vs 5.5%, fatter left
    tail), and a crash's worst gaps land there: 2020-03-06 -> 03-09, five oil
    producers at -33..-53% after OPEC broke over the weekend (addendum 18)."""
    try:
        gap = (pd.Timestamp(next_open).date() - pd.Timestamp(today).date()).days
    except Exception:
        return 1.0
    return float(scale) if gap > 1 else 1.0


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


# Night sizing tilt (RESULTS.md addendum 16). OLS of the next-open return on
# (log vol20, day return), fitted on 2021-23 ONLY and judged on 2024-26: live
# book 41.3% -> 46.8% there, beating a shuffled-weight placebo (42.9%). The
# deeper the day's drop, the bigger the bounce; vol20 adds a little. These
# numbers are frozen: refitting on data that includes the holdout would
# erase the evidence that justified them.
NIGHT_TILT = {"mu": (0.0959, -0.1232), "sd": (0.4992, 0.0610),
              "beta_bp": (1.14, -11.54), "pred_sd_bp": 12.07}


def night_tilt(vol20, day_ret, k: float = 0.25) -> np.ndarray:
    """Per-name weights with mean 1 (so the leg's gross is unchanged):
    1 + k * predicted edge / its spread, clipped to [0.25, 2]. k = 0 -> equal."""
    vol20 = np.asarray(vol20, float); day_ret = np.asarray(day_ret, float)
    if k == 0 or len(vol20) == 0:
        return np.ones(len(vol20))
    t = NIGHT_TILT
    x = np.column_stack([np.log(np.maximum(vol20, 1e-3)), day_ret])
    x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
    z = (x - np.array(t["mu"])) / np.array(t["sd"])
    w = np.clip(1 + k * (z @ (np.array(t["beta_bp"]) / 1e4)) / (t["pred_sd_bp"] / 1e4), 0.25, 2.0)
    return w / w.mean()


# ------------------------------------------------------------ kill rules
# Pre-registered 2026-09-24, BEFORE any live results (RESULTS.md addendum 16).
# Written down now so that a losing leg is switched off by a rule, not kept
# alive by hope. Do not loosen these after seeing live numbers.
#   leg: (min round trips before judging, t-stat below which a losing leg dies)
KILL_MIN_TRADES = {"night": 100, "noise": 120, "ibs": 60}
KILL_T = -1.0
KILL_EXIT_COST_BPS = 25.0     # night open sells this far below the official open: edge gone (~28bp)
KILL_EXIT_COST_MIN_N = 30
HALT_DRAWDOWN = 0.25          # realised-P&L drawdown / equity; backtest worst is ~-20%


def kill_check(closed: list[dict], min_trades: dict = KILL_MIN_TRADES,
               t_max: float = KILL_T) -> dict[str, str]:
    """{leg: reason} for every leg whose live round trips (net of real fills)
    lose money with t < t_max once it has min_trades of them. Round trips
    booked out at an unknown price (`note`) are left out."""
    out = {}
    for leg, n_min in min_trades.items():
        r = np.array([c["ret"] for c in closed if c.get("leg") == leg and not c.get("note")], float)
        if len(r) < n_min:
            continue
        m, sd = float(r.mean()), float(r.std(ddof=1))
        t = m / (sd / np.sqrt(len(r))) if sd > 0 else 0.0
        if m < 0 and t < t_max:
            out[leg] = f"{len(r)} live round trips average {m*1e4:+.1f}bp (t {t:.2f} < {t_max})"
    return out


def realised_drawdown(closed: list[dict], equity: float) -> float:
    """Worst peak-to-trough of cumulative realised P&L, as a fraction of
    current equity. Built from P&L, not the equity log, so $1k deposits
    cannot hide a losing streak."""
    if not closed or equity <= 0:
        return 0.0
    cum = np.cumsum([float(c.get("pnl") or 0.0) for c in sorted(
        closed, key=lambda c: str(c.get("exit_date", "")))])
    return float(min(0.0, (cum - np.maximum.accumulate(np.r_[0.0, cum])[1:]).min()) / equity)


# Overnight leverage gate (addendum 16). 1.3x overnight gross adds ~+7pp/yr
# in both halves at backtest costs, and nearly nothing at pessimistic costs.
# So it switches on only once live fills PROVE the costs, and off again the
# moment they stop doing so.
LEVER_MIN_EXITS = 50          # night open sells scored against the official open
LEVER_MAX_EXIT_BPS = 10.0     # mean cost per side over those exits (backtest assumes 7.5)
LEVER_MAX_DD = 0.10           # no leverage while realised drawdown is deeper than this


def lever_ok(n_exits: int, exit_bps: float, killed: dict, drawdown: float,
             multiplier: float) -> tuple[bool, str]:
    """(on?, why). Every condition must hold on every check."""
    if killed:
        return False, f"a kill rule is active ({', '.join(killed)})"
    if multiplier < 2:
        return False, "not a margin account"
    if n_exits < LEVER_MIN_EXITS:
        return False, f"{n_exits}/{LEVER_MIN_EXITS} night exits measured"
    if not np.isfinite(exit_bps) or exit_bps > LEVER_MAX_EXIT_BPS:
        return False, f"night exits cost {exit_bps:+.1f}bp/side (need <= {LEVER_MAX_EXIT_BPS:g})"
    if drawdown < -LEVER_MAX_DD:
        return False, f"realised drawdown {drawdown:.0%} (limit -{LEVER_MAX_DD:.0%})"
    return True, f"{n_exits} exits at {exit_bps:+.1f}bp/side, drawdown {drawdown:.0%}"


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
