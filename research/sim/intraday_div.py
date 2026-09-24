"""Addendum 20 research: diversify the intraday noise-area leg beyond QQQ + SMH.

    .venv/bin/python -m research.sim.intraday_div standalone   # each instrument alone, 2016-23 vs 2024-26
    .venv/bin/python -m research.sim.intraday_div book         # budget splits inside the full book

Same rule as the live leg (book.noise_days = signals.noise_*: 14-day sigma,
30-minute decisions, VWAP exit, 2% vol target). Costs per side are set per
instrument from typical quoted spreads (conservative, 1-3bp). Protocol:
candidates are picked on 2016-23 standalone numbers ONLY; 2024-26 is judged
once. At the book level a split is adopted only if both 2021-23 and 2024-26
improve over the shipped QQQ + SMH split.
"""
from __future__ import annotations

import copy
import sys

import numpy as np
import pandas as pd

from . import book as B
from . import data as D
from .validate import load_sim

COST = {"QQQ": 0.5, "SMH": 0.5, "SPY": 0.5, "IWM": 1.0, "TLT": 1.0, "GLD": 1.0,
        "XLE": 2.0, "USO": 2.5, "EEM": 3.0}
CANDS = ["SPY", "IWM", "TLT", "GLD", "XLE", "USO", "EEM"]
CAP = 1.5          # the shipped intraday budget (2x margin minus the IBS half)
_NZ: dict = {}


def nz(sym: str) -> pd.DataFrame:
    if sym not in _NZ:
        _NZ[sym] = B.noise_days(sym, cost=COST[sym])
    return _NZ[sym]


def leg(sym: str, cap: float = CAP) -> pd.Series:
    z = nz(sym)
    return np.minimum(z["lev"], cap) * z["ret"]


def st(r: pd.Series) -> str:
    c, s, d = B.stats(r)
    return f"{c*100:6.1f}%/{s:5.2f}/{d*100:4.0f}"


def standalone():
    spy = D.etf()["close"]["SPY"].pct_change(fill_method=None)
    base = (0.5 * leg("QQQ") + 0.5 * leg("SMH")).dropna()
    print(f"{'':10s} {'2016-23':>18s} {'2024-26':>18s} {'2025-26':>18s} corr(Q+S)  SPY-3%d bp  2022  2018Q4  COVID")
    rows = []
    for s in ["QQQ", "SMH", "Q+S"] + CANDS:
        r = base if s == "Q+S" else leg(s)
        r = r.dropna()
        j = pd.concat([r, base], axis=1, join="inner")
        corr = j.iloc[:, 0].corr(j.iloc[:, 1]) if s not in ("Q+S",) else 1.0
        sd = spy.reindex(r.index)
        crash = r[sd <= -0.03].mean() * 1e4
        y22 = (1 + r["2022"]).prod() - 1
        q18 = (1 + r["2018-10-01":"2018-12-24"]).prod() - 1
        cov = (1 + r["2020-02-19":"2020-03-23"]).prod() - 1
        print(f"{s:10s} {st(r[:'2023'])} {st(r['2024':])} {st(r['2025':])}   {corr:5.2f}   "
              f"{crash:+7.0f}  {y22*100:+5.1f}  {q18*100:+5.1f}  {cov*100:+5.1f}")
        rows.append((s, B.stats(r[:"2023"])[1]))
    # correlation matrix among candidates, in-sample
    M = pd.DataFrame({s: leg(s) for s in ["QQQ", "SMH"] + CANDS})[:"2023"].dropna()
    print("\ncorrelation 2016-23:\n", M.corr().round(2).to_string())
    # yearly
    Y = pd.DataFrame({s: leg(s) for s in ["QQQ", "SMH"] + CANDS}).fillna(0)
    Y["Q+S"] = 0.5 * Y.QQQ + 0.5 * Y.SMH
    print("\ncalendar-year return %:\n", ((1 + Y).groupby(Y.index.year).prod() - 1).mul(100).round(1).to_string())


def book():
    s = load_sim()
    for sym in CANDS:
        s.NZ[sym] = nz(sym)
    s07 = copy.copy(s); s07.N = B.night_days(max_corr=0.7)
    v5 = dict(tilt="live", night_cost="tier", weekend_scale=0.5)
    v7 = dict(v5, noise_cap=1.0, conviction_w=0.5)
    splits = {"QQQ+SMH (shipped)": {"QQQ": 0.5, "SMH": 0.5}}
    for x in CANDS:
        splits[f"QQQ+SMH+{x}"] = {"QQQ": 1 / 3, "SMH": 1 / 3, x: 1 / 3}
    for a, b in [("TLT", "GLD"), ("GLD", "XLE"), ("TLT", "XLE"), ("GLD", "IWM"), ("TLT", "IWM")]:
        splits[f"QQQ+SMH+{a}+{b}"] = {"QQQ": .25, "SMH": .25, a: .25, b: .25}
    splits["QQQ+GLD"] = {"QQQ": 0.5, "GLD": 0.5}
    splits["QQQ+TLT"] = {"QQQ": 0.5, "TLT": 0.5}
    for name, base in (("V5 (intraday 1.5x)", v5), ("V7 (intraday 1.0x + TQQQ conviction 0.5)", v7)):
        print(f"\n== {name}")
        print(f"{'':44s} {'2021-23':>16s} {'2024-26':>16s} {'full':>16s}")
        for lab, sp in splits.items():
            print(B.summary(s07.replay(B.Params(**base, noise=sp)), "  " + lab))


if __name__ == "__main__":
    {"standalone": standalone, "book": book}[sys.argv[1] if len(sys.argv) > 1 else "standalone"]()
