"""Jump hunt collisions across finished data sets (written before any outcome; jump_ideas.md):

- V2: a small-sub Reddit velocity day (>= 3 posts, >= 5x the trailing 30-day mean) with NO Benzinga story on the
  ticker in the prior 30 days (Reddit ahead of the media). ADV$ < $20M; first per ticker in 30 days.
- C2: a ticker's first small-sub post after >= 365 days of silence, with an officer/director open-market buy in the
  30 days before it. First per ticker in 365 days.
- C11: an H17 trade-count spike (night panel, quiet price) on a day with the ticker's first Benzinga story in >= 90
  days (story fd = the spike day or the day before).

    PYTHONPATH=. .venv/bin/python -m research.sim.jump_combo v2|c2|c11
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from .jump_common import first_in, save, small_only


def _within(sym_dates: dict, sym: str, d: pd.Timestamp, lo_days: int, hi_days: int = 0) -> bool:
    a = sym_dates.get(sym)
    if a is None:
        return False
    return bool(((a >= (d - pd.Timedelta(days=lo_days)).to_datetime64()) & (a <= (d + pd.Timedelta(days=hi_days)).to_datetime64())).any())


def _news_dates() -> dict:
    from .jump_news import news
    L = news()[["sym", "fd"]].drop_duplicates()
    return {s: np.sort(g.fd.to_numpy()) for s, g in L.groupby("sym")}


def v2() -> pd.DataFrame:
    from .jump_reddit import SMALL, _velocity
    E = _velocity(SMALL)
    nd = _news_dates()
    E = E[[not _within(nd, r.sym, r.fd, 30) for r in E.itertuples()]]
    return small_only(first_in(E, 30), 20e6)


def c2() -> pd.DataFrame:
    from .jump_insider import buys
    from .jump_reddit import M, SMALL, _start
    X = M()[lambda d: d["sub"].isin(SMALL)].sort_values(["sym", "t"])
    prev = X.groupby("sym").t.shift(1)
    F = X[prev.isna() | ((X.t - prev).dt.days >= 365)][["sym", "fd"]]
    F = _start(F, 365)
    B = buys()
    B = B[B.insider & (B.usd >= 1e3)].dropna(subset=["sym"])
    bd = {s: np.sort(g.fd.to_numpy()) for s, g in B.groupby("sym")}
    E = F[[_within(bd, r.sym, r.fd, 30) for r in F.itertuples()]]
    return first_in(E, 365)


def c11() -> pd.DataFrame:
    from .jump_h17 import build
    from .jump_news import news
    E = build()
    L = news()[["sym", "fd"]].drop_duplicates().sort_values(["sym", "fd"])
    L["prev"] = L.groupby("sym").fd.shift(1)
    first = L[L.prev.isna() | ((L.fd - L.prev).dt.days >= 90)]
    fd = {s: np.sort(g.fd.to_numpy()) for s, g in first.groupby("sym")}
    return E[[_within(fd, r.sym, r.fd, 1) for r in E.itertuples()]]


if __name__ == "__main__":
    what = sys.argv[1]
    save(globals()[what](), what)
