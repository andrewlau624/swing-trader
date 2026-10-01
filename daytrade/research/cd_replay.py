"""Study Lab-CD: volatility-managed market exposure (Moreira & Muir 2017) (round1_prose.md Lab Round 51).

  python -m daytrade.research.cd_replay
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .by_replay import stats
from .ca_replay import daily_ff


def monthly_book(d, c_scale, cost):
    m = d.groupby(d.index.to_period("M"))
    rv = m.mkt.apply(lambda x: float((x ** 2).sum()))
    mret = m.mkt.apply(lambda x: float((1 + x).prod() - 1))
    rf = m.rf.apply(lambda x: float((1 + x).prod() - 1))
    w = (c_scale / rv.shift(1)).clip(lower=0, upper=2.0)
    lev = (w - 1).clip(lower=0)
    ret = w * mret + (1 - w).clip(lower=0) * rf - lev * (rf + 0.005 / 12 + 0.009 / 12) - w.diff().abs().fillna(0) * cost
    return pd.DataFrame({"book": ret, "mkt": mret, "w": w}).dropna()


def run():
    d = daily_ff()
    m = d.groupby(d.index.to_period("M"))
    rv = m.mkt.apply(lambda x: float((x ** 2).sum()))
    pre = rv[(rv.index >= pd.Period("1927-01", "M")) & (rv.index <= pd.Period("1962-12", "M"))]
    c_scale = float(1.0 / (1.0 / pre).mean())          # mean(c / RV) = 1 over 1927-62 (before the cap)
    res = {"c_scale": c_scale}
    P = (("judged", "1963-07", "2015-12"), ("h1", "1963-07", "1989-12"), ("h2", "1990-01", "2015-12"),
         ("ref 2016-26", "2016-01", "2026-08"))
    for tier, cost in (("1x", 0.0005), ("2x", 0.0010)):
        b = monthly_book(d, c_scale, cost)
        res[tier] = {}
        for n, a, z in P:
            s = b[(b.index >= pd.Period(a, "M")) & (b.index <= pd.Period(z, "M"))]
            res[tier][n] = {"book": stats(s.book, 12) if False else _mstats(s.book), "market": _mstats(s.mkt), "mean_w": float(s.w.mean())}
    r1, r2 = res["1x"], res["2x"]
    ok = (r1["h1"]["book"]["sharpe"] > r1["h1"]["market"]["sharpe"] and r1["h2"]["book"]["sharpe"] > r1["h2"]["market"]["sharpe"]
          and r2["h1"]["book"]["cagr"] >= r2["h1"]["market"]["cagr"] and r2["h2"]["book"]["cagr"] >= r2["h2"]["market"]["cagr"]
          and r1["judged"]["book"]["max_dd"] > r1["judged"]["market"]["max_dd"] and 0.6 <= r1["judged"]["mean_w"] <= 1.6)
    res["verdict"] = "PASS" if ok else "DEAD"
    print(json.dumps(res, indent=1, default=str))


def _mstats(r):
    import math
    eq = (1 + r).cumprod()
    return {"cagr": float(eq.iloc[-1] ** (12 / len(r)) - 1), "sharpe": float(r.mean() / r.std(ddof=1) * math.sqrt(12)),
            "max_dd": float((eq / eq.cummax() - 1).min())}


if __name__ == "__main__":
    run()
