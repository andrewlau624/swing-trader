"""Pick-quality PQ2: why the stock fell (headline category before the 15:50 decision). Explore on 2021-23 only.

    PYTHONPATH=. .venv/bin/python -m research.sim.pq2 explore
Spec: research/drafts/pick_quality_log.md (PQ2).
"""
from __future__ import annotations

import pickle
import re
import sys

import numpy as np
import pandas as pd

from . import book as B

CATS = [("OFFERING", r"offering|\bpriced\b|pricing|dilut|registered direct|\bATM\b|private placement"),
        ("EARNINGS", r"earnings|results|quarter|\bQ[1-4]\b|\bEPS\b|revenue|guidance|outlook|forecast"),
        ("DOWNGRADE", r"downgrade|cut to|lowers price target|price target cut"),
        ("BIOTECH", r"\bFDA\b|trial|\bCRL\b|phase|endpoint|PDUFA"),
        ("LEGAL", r"lawsuit|investigation|\bSEC\b|subpoena|class action|fraud|short seller|short report")]
CRE = [(k, re.compile(p, re.I)) for k, p in CATS]


def news(a, b):
    ms = pd.period_range(a, b, freq="M")
    fr = []
    for m in ms:
        f = f"data/research/jump/news/{m}.parquet"
        try:
            x = pd.read_parquet(f, columns=["created_at", "headline", "symbols"])
        except Exception:
            continue
        fr.append(x)
    X = pd.concat(fr)
    X["t"] = pd.to_datetime(X.created_at, utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    X = X.explode("symbols").rename(columns={"symbols": "sym"}).dropna(subset=["sym"])
    return X[["sym", "t", "headline"]]


def categorize(hs):
    if not len(hs):
        return "NONE"
    for k, c in CRE:
        if any(c.search(h or "") for h in hs):
            return k
    return "OTHER"


def explore():
    N = pickle.load(open("data/research/program/cache_rawprice.pkl", "rb"))["raw"][0.10]
    X = news("2020-12", "2023-12")
    by = {s: g.sort_values("t") for s, g in X.groupby("sym")}
    days = sorted(d for d in N if pd.Timestamp("2021-01-01") <= d <= pd.Timestamp("2023-12-31"))
    alld = sorted(N)
    prev = {d: alld[i - 1] if i else d - pd.Timedelta(days=1) for i, d in enumerate(alld)}
    rows = []
    for d in days:
        nd = N[d]
        c = B.cost_bps("tier", np.asarray(nd.price), np.asarray(nd.adv))
        lo, hi = prev[d] + pd.Timedelta(hours=16), d + pd.Timedelta(hours=15, minutes=50)
        for j, s in enumerate(nd.syms):
            g = by.get(s)
            hs = list(g.headline[(g.t >= lo) & (g.t <= hi)]) if g is not None else []
            rows.append((d, s, categorize(hs), float(nd.ret[j]) - 2 * c[j] / 1e4))
    T = pd.DataFrame(rows, columns=["d", "sym", "cat", "net"])
    T.to_pickle("data/research/program/pq2_select.pkl")
    mu = T.net.mean()
    print(f"picks {len(T)}, pool mean net {mu * 1e4:+.1f}bp")
    for k, g in T.groupby("cat"):
        nm = g.groupby("d").net.mean()
        t = (g.net.mean() - mu) / (g.net.std() / np.sqrt(len(g)))
        yrs = " ".join(f"{y}: {(gg.net.mean() - T[T.d.dt.year == y].net.mean()) * 1e4:+.0f}" for y, gg in g.groupby(g.d.dt.year))
        print(f"  {k:9s} n {len(g):5d} ({len(g) / len(T):.0%})  net {g.net.mean() * 1e4:+6.1f}bp  vs pool {(g.net.mean() - mu) * 1e4:+6.1f}bp "
              f"t {t:+.2f} | vs that year's pool: {yrs}")


if __name__ == "__main__":
    explore()
