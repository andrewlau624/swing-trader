"""Shared harness for swing-signal research.

Reuses the validated engine in swingtrader.backtest unchanged. New entry gates
are injected the same way prior research did it: by replacing the module global
`swingtrader.backtest.overnight_share`, which the engine already calls when
`min_overnight_share` is set. A gate receives the history up to and including
the decision bar and returns a score; entry requires score >= threshold.

Nothing here is imported by the package.
"""
import os
import pickle
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from swingtrader import backtest as bt  # noqa: E402
from swingtrader.config import Config  # noqa: E402
from swingtrader.data import fetch_bars  # noqa: E402
from swingtrader.report import curve_stats, months_to_significance, trade_stats  # noqa: E402
from swingtrader.universe import all_assets  # noqa: E402

HERE = Path(__file__).resolve().parent
EXTRA = ["SPY", "BIL", "SGOV", "VIXY", "VXX", "QQQ", "IWM", "SMH", "XLK", "XLF",
         "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB", "XLC"]

_ORIG_OS = bt.overnight_share
_ORIG_SCAN = bt.scan_window


def bars(start=None, end=None, refresh=False):
    cfg = Config.load()
    start = start or cfg.data.start
    end = end or cfg.data.end
    pk = HERE / f"bars_{start}_{end}.pkl"
    if pk.exists() and not refresh:
        return pickle.loads(pk.read_bytes())
    u = all_assets()
    b = fetch_bars(u.symbols + EXTRA, start, end, feed=cfg.data.feed,
                   adjustment=cfg.data.adjustment, verbose=False)
    b = {s: d for s, d in b.items() if len(d) > 150}
    pk.write_bytes(pickle.dumps(b, protocol=4))
    return b


# ---------------------------------------------------------------- scan cache
_scan_cache: dict = {}


def _install_scan_cache():
    def cached_scan(form, cohort, sel, mode="reversion"):
        idx = [d.index for d in form.values() if len(d)]
        if not idx:
            return _ORIG_SCAN(form, cohort, sel, mode)
        lo = min(i[0] for i in idx)
        hi = max(i[-1] for i in idx)
        key = (str(lo), str(hi), cohort.price_min, cohort.price_max,
               cohort.min_iex_dollar_vol, cohort.min_annual_vol,
               sel.halflife_min, sel.halflife_max, sel.hurst_max,
               sel.max_abs_drift_t, sel.min_amplitude_pct,
               sel.max_efficiency_ratio, sel.top_n, mode)
        if key not in _scan_cache:
            _scan_cache[key] = _ORIG_SCAN(form, cohort, sel, mode)
        return _scan_cache[key]
    bt.scan_window = cached_scan


# ---------------------------------------------------------------- gates
def set_gate(fn):
    """Install a gate: fn(hist, window) -> float, entry needs >= threshold."""
    bt.overnight_share = fn


def reset_gate():
    bt.overnight_share = _ORIG_OS


# ---------------------------------------------------------------- run/summary
def run(b, label="run", cfgmod=None, cohort="highvol", stop=10.0, cash="BIL",
        control=None, **kw):
    cfg = Config.load()
    cfg.portfolio.equity = 100_000.0
    if cfgmod:
        cfgmod(cfg)
    t0 = time.time()
    res = bt.run(b, cfg, cohort, stop_pct=stop, cash_symbol=cash,
                 control=control, verbose=False, **kw)
    res._elapsed = time.time() - t0
    return summ(res, label), res


def uncapped(c):
    c.selection.top_n = 999
    c.portfolio.position_pct = 0.10


def summ(res, label, ref_dd=14.4):
    eq = res.equity
    if eq is None or len(eq) < 3:
        return f"{label:44s} no equity"
    cs = curve_stats(eq)
    ts = trade_stats(res.trades)
    dd = cs.get("max_drawdown_pct", float("nan"))
    cagr = cs.get("cagr_pct", float("nan"))
    rm = cagr * ref_dd / abs(dd) if dd and np.isfinite(dd) and dd < 0 else float("nan")
    h1 = curve_stats(eq[eq.index < "2024-01-01"]).get("cagr_pct", float("nan"))
    h2 = curve_stats(eq[eq.index >= "2024-01-01"]).get("cagr_pct", float("nan"))
    m2s = months_to_significance(res.trades, years=cs.get("years", 1.0) or 1.0)
    return (f"{label:44s} n={ts.get('n_trades',0):4d} "
            f"CAGR {cagr:6.1f} Sh {cs.get('sharpe',float('nan')):5.2f} "
            f"DD {dd:6.1f} rm {rm:6.1f} avg {ts.get('avg_pnl_pct',float('nan')):6.2f} "
            f"win {ts.get('win_rate_pct',float('nan')):4.1f} "
            f"| 21-23 {h1:6.1f} 24-26 {h2:6.1f} m2s {m2s:4.0f}")


# ---------------------------------------------------------------- features
def vol_z(hist, window=20):
    """Today's volume vs its own trailing mean, in std units."""
    v = hist["volume"].astype(float)
    if len(v) < window + 1:
        return np.nan
    mu = v.iloc[-window - 1:-1].mean()
    sd = v.iloc[-window - 1:-1].std(ddof=1)
    if not sd or not np.isfinite(sd):
        return np.nan
    return float((v.iloc[-1] - mu) / sd)


def ibs(hist, window=None):
    """Internal bar strength of the last bar: (C-L)/(H-L). Low = closed near low."""
    b = hist.iloc[-1]
    rng = float(b["high"] - b["low"])
    if rng <= 0:
        return 0.5
    return float((b["close"] - b["low"]) / rng)


def close_loc_5(hist, window=5):
    """Mean close location over the last `window` bars, in [0,1]."""
    h = hist.iloc[-window:]
    rng = (h["high"] - h["low"]).replace(0, np.nan)
    return float(((h["close"] - h["low"]) / rng).mean())


def dist_52w_high(hist, window=252):
    """Close relative to the trailing high: 0 at a new high, -1 = -100%."""
    c = hist["close"].astype(float)
    w = c.iloc[-window:]
    if len(w) < 60:
        return np.nan
    hi = float(w.max())
    return float(c.iloc[-1] / hi - 1.0)


def overnight_share(hist, window=5):
    """Reference: the addendum-4 gate, for harness validation."""
    c, o = hist["close"].astype(float), hist["open"].astype(float)
    on = float(np.log(o / c.shift()).iloc[-window:].sum())
    tot = float(np.log(c / c.shift()).iloc[-window:].sum())
    if tot == 0 or not np.isfinite(tot) or not np.isfinite(on):
        return np.nan
    return on / tot


def z_of(hist, window=20):
    """Current z-score of close, computed inside the gate."""
    from swingtrader.metrics import zscore
    if len(hist) < window + 1:
        return np.nan
    z = zscore(hist["close"].astype(float), window)
    v = z.iloc[-1]
    return float(v) if np.isfinite(v) else np.nan


def z_turn_up(hist, window=20):
    """1 if the z-score rose vs yesterday (reversal under way), else 0."""
    from swingtrader.metrics import zscore
    if len(hist) < window + 2:
        return np.nan
    z = zscore(hist["close"].astype(float), window)
    return 1.0 if float(z.iloc[-1]) > float(z.iloc[-2]) else 0.0


def z_two_days(hist, window=20, entry=-2.0):
    """1 if z has been <= entry for two consecutive bars."""
    from swingtrader.metrics import zscore
    if len(hist) < window + 2:
        return np.nan
    z = zscore(hist["close"].astype(float), window)
    return 1.0 if (z.iloc[-2:] <= entry).all() else 0.0


def shock_share(hist, window=5):
    """Largest single-day decline as a share of the window's total decline.

    ~1 means the dip was one idiosyncratic down day (overreaction candidate);
    small means it ground down over many days (informed selling)."""
    c = hist["close"].astype(float)
    if len(c) < window + 1:
        return np.nan
    r = c.pct_change().iloc[-window:]
    tot = float(r.sum())
    if tot >= 0 or not np.isfinite(tot):
        return np.nan
    return float(r.min() / tot)


def down_days(hist, window=5):
    """Fraction of the last `window` bars that closed down."""
    c = hist["close"].astype(float)
    if len(c) < window + 1:
        return np.nan
    r = c.pct_change().iloc[-window:]
    return float((r < 0).mean())


def shock_sigma(hist, window=5):
    """Worst single-day decline in units of the window's daily-return sigma."""
    c = hist["close"].astype(float)
    if len(c) < window + 2:
        return np.nan
    r = c.pct_change().iloc[-window:]
    sd = float(r.std(ddof=1))
    if sd <= 0 or not np.isfinite(sd):
        return np.nan
    return float(-r.min() / sd)


def pin(fn, window):
    """Pin a feature's window: the engine passes overnight_window (5) as the
    second gate arg, which silently mis-windows 52w/z-score features."""
    return lambda hist, w: fn(hist, window)


def band(fn, lo, hi):
    """1.0 only if lo <= fn(hist) <= hi (a middle-band gate)."""
    def g(hist, w):
        v = fn(hist, w)
        if not np.isfinite(v):
            return np.nan
        return 1.0 if (lo <= v <= hi) else 0.0
    return g
    return lambda hist, w: fn(hist, window)


def combo(fn1, thr1, fn2, thr2):
    """1.0 only if both sub-gates pass; 0.0 otherwise."""
    def g(hist, w):
        a, c = fn1(hist, w), fn2(hist, w)
        if not (np.isfinite(a) and np.isfinite(c)):
            return np.nan
        return 1.0 if (a >= thr1 and c >= thr2) else 0.0
    return g


def make_market_gate(series, higher_is_better=True):
    """Gate on a date-indexed market series (e.g. SPY 5d return, VIXY z)."""
    def gate(hist, window=5):
        if not len(hist):
            return np.nan
        t = hist.index[-1]
        try:
            v = float(series.loc[t])
        except (KeyError, TypeError):
            return np.nan
        return v if higher_is_better else -v
    return gate


_install_scan_cache()
