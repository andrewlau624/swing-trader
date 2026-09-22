"""Rank range-bound candidates over ONE formation window.

Hard filters first (a candidate must clear every one), then a rank composite
to order the survivors. The composite is the mean of percentile ranks across
four quality dimensions rather than a weighted formula, because weights are
free parameters and every free parameter is another way to overfit.
"""
from __future__ import annotations

import pandas as pd

from .config import CohortCfg, SelectionCfg
from .metrics import describe
from .universe import passes_cohort


def metric_table(bars: dict[str, pd.DataFrame], cohort: CohortCfg) -> pd.DataFrame:
    """Metrics for every symbol that clears the cohort prefilter."""
    rows = []
    for sym, d in bars.items():
        if not passes_cohort(d, cohort):
            continue
        m = describe(d)
        m["symbol"] = sym
        rows.append(m)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).set_index("symbol")


def apply_filters(tbl: pd.DataFrame, sel: SelectionCfg,
                  mode: str = "reversion") -> pd.DataFrame:
    """Hard gates.

    mode="reversion" selects stocks that do NOT trend (short half-life, Hurst
    below 0.5, zero drift). mode="momentum" selects the opposite: persistent,
    trending names. The distinction matters because the exit rule has to agree
    with the selection -- applying a trailing (trend-following) exit to names
    screened for not trending is a contradiction, and it loses money.
    """
    if tbl.empty:
        return tbl
    if mode == "momentum":
        ok = (
            (tbl["hurst"] >= 0.55)                      # persistent, not mean-reverting
            & (tbl["drift_t"] >= 2.0)                   # genuine uptrend
            & (tbl["amplitude_pct"] >= sel.min_amplitude_pct)
            & (tbl["efficiency_ratio"] >= 0.15)         # goes somewhere, not chop
        )
        return tbl[ok.fillna(False)]
    ok = (
        tbl["halflife"].between(sel.halflife_min, sel.halflife_max)
        & (tbl["hurst"] <= sel.hurst_max)
        & (tbl["drift_t"].abs() <= sel.max_abs_drift_t)
        & (tbl["amplitude_pct"] >= sel.min_amplitude_pct)
        & (tbl["efficiency_ratio"] <= sel.max_efficiency_ratio)
    )
    return tbl[ok.fillna(False)]


def rank_momentum(tbl: pd.DataFrame, top_n: int) -> pd.DataFrame:
    if tbl.empty:
        return tbl
    t = tbl.copy()
    t["score"] = (t["drift_t"].rank(pct=True) + t["efficiency_ratio"].rank(pct=True)
                  + t["amplitude_pct"].rank(pct=True)) / 3.0
    return t.sort_values("score", ascending=False).head(top_n)


def rank(tbl: pd.DataFrame, top_n: int) -> pd.DataFrame:
    """Composite = mean percentile rank over four quality dimensions."""
    if tbl.empty:
        return tbl
    t = tbl.copy()
    # higher is better
    r_amp = t["amplitude_pct"].rank(pct=True)
    # lower is better
    r_eff = (-t["efficiency_ratio"]).rank(pct=True)
    r_drift = (-t["drift_t"].abs()).rank(pct=True)
    r_hurst = (-t["hurst"]).rank(pct=True)
    t["score"] = (r_amp + r_eff + r_drift + r_hurst) / 4.0
    return t.sort_values("score", ascending=False).head(top_n)


def scan_window(bars: dict[str, pd.DataFrame], cohort: CohortCfg,
                sel: SelectionCfg, mode: str = "reversion") -> pd.DataFrame:
    """Full pipeline for one formation window: prefilter -> gate -> rank."""
    tbl = apply_filters(metric_table(bars, cohort), sel, mode=mode)
    return (rank_momentum if mode == "momentum" else rank)(tbl, sel.top_n)
