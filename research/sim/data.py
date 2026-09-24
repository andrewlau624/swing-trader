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


@lru_cache(maxsize=1)
def night_candidates() -> pd.DataFrame:
    """Every name at <= -8% and IBS < 0.1 at 15:50, with what was known then
    (p50, H50, L50, prev close, vol20, ret20) and what happened after
    (close_move: 15:50 -> close, ret: close -> next open). Candidates were
    chosen on the day's LOW, so a name that bounced into the close is in here
    (addendum 14's lookahead fix)."""
    x = pd.read_pickle(DATA / "night_trades.v2.pkl")
    x = x[x.ret.abs() <= 1]
    twin = x.groupby(["date", "day50", "ret"]).sym.transform("count")
    x = x[twin == 1].copy()
    x["C"] = x.p50 * (1 + x.close_move)          # the close auction price actually paid
    return x


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
