"""Pick-quality PQ6: fails-to-deliver intensity (lagged >= 30 days) as a night-pick feature. Explore 2021-23 only."""
from __future__ import annotations

import glob
import pickle

import numpy as np
import pandas as pd

from . import book as B


def ftd():
    fr = []
    for f in sorted(glob.glob("data/research/jump/ftd/*.parquet")):
        x = pd.read_parquet(f, columns=["date", "sym", "qty", "file"]); fr.append(x)
    X = pd.concat(fr); X["date"] = pd.to_datetime(X.date)
    end = X.groupby("file").date.max()
    X["avail"] = X.file.map(end) + pd.Timedelta(days=30)
    return X


def main():
    N = pickle.load(open("data/research/program/cache_rawprice.pkl", "rb"))["raw"][0.10]
    X = ftd()
    files = X.groupby("file").avail.first().sort_values()
    mx = X.groupby(["file", "sym"]).qty.max()
    rows = []
    for d in sorted(N):
        if not (pd.Timestamp("2021-01-01") <= d <= pd.Timestamp("2023-12-31")):
            continue
        ok = files[files <= d]
        if not len(ok):
            continue
        fl = ok.index[-1]
        nd = N[d]
        c = B.cost_bps("tier", np.asarray(nd.price), np.asarray(nd.adv))
        for j, s in enumerate(nd.syms):
            q = mx.get((fl, s), np.nan)
            ratio = q * float(nd.price[j]) / float(nd.adv[j]) if np.isfinite(q) and nd.adv[j] > 0 else np.nan
            b = "NONE" if not np.isfinite(ratio) else ("HIGH" if ratio >= 0.01 else "LOW")
            rows.append((d, s, b, ratio, float(nd.ret[j]) - 2 * c[j] / 1e4))
    T = pd.DataFrame(rows, columns=["d", "sym", "b", "ratio", "net"])
    mu = T.net.mean()
    print(f"picks {len(T)}, pool net {mu * 1e4:+.1f}bp; bucket shares {T.b.value_counts(normalize=True).round(2).to_dict()}")
    for k, g in T.groupby("b"):
        rest = T[T.b != k]
        diff = g.net.mean() - rest.net.mean()
        t = diff / np.sqrt(g.net.var() / len(g) + rest.net.var() / len(rest))
        yrs = " ".join(f"{y}: {(g[g.d.dt.year == y].net.mean() - rest[rest.d.dt.year == y].net.mean()) * 1e4:+.0f}"
                       for y in (2021, 2022, 2023))
        print(f"  {k:5s} n {len(g):5d} net {g.net.mean() * 1e4:+6.1f}bp  vs rest {diff * 1e4:+6.1f}bp t {t:+.2f} | by year {yrs}")


if __name__ == "__main__":
    main()
