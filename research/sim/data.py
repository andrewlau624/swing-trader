"""Point-in-time research data for the book simulator.

Everything here is a loader over the cached research data in
data/research/night/ (gitignored, ~3 GB). Nothing decides anything: the
decisions are made by swingtrader.daily.signals, the same functions the live
executor calls. The one cleaning step kept from research is the addendum-14
bad-bar filter (|overnight| > 100% and same-day identical-return twins), which
removes data errors, not trades.
"""
from __future__ import annotations

import os
import pickle
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "research" / "night"
ET = "America/New_York"


RAW_CLOSE = DATA / "raw_close.parquet"


@lru_cache(maxsize=2)
def night_candidates(raw: bool = False) -> pd.DataFrame:
    """Every name at <= -8% and IBS < 0.1 at 15:50, with what was known then
    (p50, H50, L50, prev close, vol20, ret20) and what happened after
    (close_move: 15:50 -> close, ret: close -> next open). Candidates were
    chosen on the day's LOW, so a name that bounced into the close is in here
    (addendum 14's lookahead fix).

    Prices here are SPLIT-ADJUSTED as of the fetch (adjustment='all'), so a name
    that later reverse-split shows a price far above what it traded at
    (addendum 30). raw=True adds raw_f (raw/adjusted close on that date),
    raw_p50 / raw_C (the prices the live executor actually saw and paid) and
    raw_src ('exact' | 'rebased' = raw close / our close, when the raw fetch's adjusted
    close is on a different basis | 'nearest' = factor from the symbol's nearest dated bar |
    'none' = no raw data, factor 1). Returns are unaffected."""
    x = pd.read_pickle(DATA / "night_trades.v2.pkl")
    x = x[x.ret.abs() <= 1]
    twin = x.groupby(["date", "day50", "ret"]).sym.transform("count")
    x = x[twin == 1].copy()
    x["C"] = x.p50 * (1 + x.close_move)          # the close auction price actually paid
    if raw:
        x = add_raw_factor(x, pd.read_parquet(RAW_CLOSE))
    return x


def add_raw_factor(x: pd.DataFrame, raw: pd.DataFrame) -> pd.DataFrame:
    """x: candidates (date, sym, p50, C). raw: symbol, date, raw_close, adj_close
    (both from the same source, so the ratio is the cumulative split/dividend
    factor on that date). Missing (sym, date): the factor of the symbol's nearest
    dated bar (factors are piecewise constant between corporate actions);
    unknown symbol: factor 1."""
    r = raw[["symbol", "date", "raw_close", "adj_close"]].dropna()
    r = r[(r.raw_close > 0) & (r.adj_close > 0)]
    r = r.assign(f=r.raw_close / r.adj_close, date=pd.to_datetime(r.date))
    x = x.copy()
    x["_i"] = np.arange(len(x))
    ex = x.merge(r[["symbol", "date", "f", "raw_close", "adj_close"]], left_on=["sym", "date"],
                 right_on=["symbol", "date"], how="left").set_index("_i").reindex(x["_i"])
    # a corporate action between this frame's fetch and the raw fetch puts the two adjusted
    # series on different bases (0.1% of candidates): then the factor is raw close / our close
    rebase = (np.abs(x["C"].values / ex["adj_close"].values - 1) > 0.2) if "C" in x else np.zeros(len(x), bool)
    ex = np.where(rebase, ex["raw_close"].values / x["C"].values if "C" in x else np.nan,
                  ex["f"].values).astype(float)
    src = np.where(np.isfinite(ex), np.where(rebase, "rebased", "exact"), "none").astype(object)
    miss = ~np.isfinite(ex)
    if miss.any():
        m = x.loc[miss, ["_i", "sym", "date"]].sort_values("date")
        rr = r[["symbol", "date", "f"]].rename(columns={"symbol": "sym"}).sort_values("date")
        near = pd.merge_asof(m, rr, on="date", by="sym", direction="nearest")
        near = near.set_index("_i")["f"]
        fill = near.reindex(x.loc[miss, "_i"]).values
        ex[miss] = fill
        src[miss] = np.where(np.isfinite(fill), "nearest", "none")
    f = np.where(np.isfinite(ex), ex, 1.0)
    x["raw_f"] = f
    x["raw_src"] = src
    x["raw_p50"] = x.p50 * f
    x["raw_C"] = x.C * f
    return x.drop(columns="_i")


@lru_cache(maxsize=1)
def panel() -> dict:
    """SIP daily panel {open, high, low, close, volume, ...}: session x symbol."""
    return pd.read_pickle(DATA / "panel.pkl")


@lru_cache(maxsize=1)
def etf() -> dict:
    e = pd.read_parquet(DATA / "etf_daily.parquet")
    e["date"] = e.timestamp.dt.tz_convert(ET).dt.normalize().dt.tz_localize(None)
    return {f: e.pivot(index="date", columns="symbol", values=f)
            for f in ["open", "high", "low", "close"]}


def minutes(sym: str) -> dict:
    """Minute matrices {open, high, low, close, volume}: session x minute 0..389."""
    sys.path.insert(0, str(DATA))
    from intra import load                      # noqa: E402  (research loader, pickled cache)
    return load(sym)


@lru_cache(maxsize=1)
def returns20() -> pd.DataFrame:
    """Daily close-to-close returns, used for the duplicate-bet correlation."""
    return panel()["close"].pct_change(fill_method=None)
