"""Pick-quality PQ8: night picks on their own >= 2% cash ex-dividend day. Spec: pick_quality_log.md (PQ8)."""
from __future__ import annotations

import json
import pickle
import sys

import numpy as np
import pandas as pd

from . import book as B


def divs(files=("divs_all.json", "divs_2024_26.json")):
    rows = []
    for f in files:
        try:
            rows += json.load(open(f"data/research/program/ib/{f}"))
        except FileNotFoundError:
            pass
    D = pd.DataFrame(rows)
    D["ex"] = pd.to_datetime(D.ex_date)
    return D.groupby(["symbol", "ex"]).rate.sum()


def tag(N, dv, a, b):
    rows = []
    for d, nd in N.items():
        if not (pd.Timestamp(a) <= d <= pd.Timestamp(b)):
            continue
        c = B.cost_bps("tier", np.asarray(nd.price), np.asarray(nd.adv))
        for j, s in enumerate(nd.syms):
            r = dv.get((s, d), 0.0)
            p0 = float(nd.price[j]) / (1 + float(nd.day_ret[j])) if nd.day_ret[j] > -1 else np.nan
            y = r / p0 if p0 and np.isfinite(p0) else 0.0
            rows.append((d, s, y, float(nd.ret[j]) - 2 * c[j] / 1e4))
    return pd.DataFrame(rows, columns=["d", "s", "y", "net"])


def main(mode):
    N = pickle.load(open("data/research/program/cache_rawprice.pkl", "rb"))["raw"][0.10]
    dv = divs()
    if mode == "counts":
        T = tag(N, dv, "2021-01-01", "2026-09-30")
        T["ex"] = T.y >= 0.02
        print(T.groupby(T.d.dt.year).ex.agg(["sum", "mean"]).rename(columns={"sum": "ex-div picks", "mean": "share"}).round(3))
        print("2025-26 examples:", T[T.ex & (T.d >= "2025-01-01")].s.value_counts().head(15).to_dict())
    else:
        T = tag(N, dv, "2021-01-01", "2023-12-31")
        ex = T.y >= 0.02
        g, rest = T[ex], T[~ex]
        diff = g.net.mean() - rest.net.mean()
        print(f"2021-23: ex-div picks {ex.sum()} (median yield {g.y.median():.1%}); net {g.net.mean() * 1e4:+.1f}bp vs rest "
              f"{rest.net.mean() * 1e4:+.1f}bp, diff {diff * 1e4:+.1f}bp; by year "
              + " ".join(f"{y}: {(g[g.d.dt.year == y].net.mean() - rest[rest.d.dt.year == y].net.mean()) * 1e4:+.0f} (n {(g.d.dt.year == y).sum()})"
                         for y in (2021, 2022, 2023)))


if __name__ == "__main__":
    main(sys.argv[1])
