"""Study Lab-BL: distance-method stock pairs (round1_prose.md Lab Round 36). Daily adjusted SIP closes (closing crosses);
the universe per period from Lab-BJ's monthly bars (raw price >= $5, top 100 by formation dollar volume).

  python -m daytrade.research.bl_replay
"""
from __future__ import annotations

import itertools
import json
import math
import random

import numpy as np
import pandas as pd

from ..settings import DATA
from . import as_replay as A
from .bj_replay import monthly

OUT = DATA / "research" / "bl"
NPAIR, UNIV, OPEN_SD = 20, 100, 2.0
COSTS = {"1x": 10, "2x": 20}
SPLIT = "2022-01"


def periods():
    out = []
    for y in range(2017, 2027):
        for m in (1, 7):
            start = pd.Timestamp(y, m, 1)
            if start > pd.Timestamp("2026-09-01"):
                break
            out.append((start - pd.DateOffset(months=12), start, min(start + pd.DateOffset(months=6), pd.Timestamp("2026-10-01"))))
    return out


def universes():
    adj, raw = monthly("all"), monthly("raw")
    C = adj.pivot_table(index="month", columns="symbol", values="close")
    V = adj.pivot_table(index="month", columns="symbol", values="volume")
    RAW = raw.pivot_table(index="month", columns="symbol", values="close").reindex(index=C.index, columns=C.columns)
    out = {}
    for f0, t0, _ in periods():
        ms = [m for m in C.index if f0.strftime("%Y-%m") <= m < t0.strftime("%Y-%m")]
        if len(ms) < 10:
            continue
        dv = (C.loc[ms] * V.loc[ms]).mean()
        ok = RAW.loc[ms[-1]] >= 5
        out[str(t0.date())] = list(dv[ok[ok].index].dropna().sort_values(ascending=False).index[:UNIV])
    return out


def daily(symbols):
    p = OUT / "daily.parquet"
    if p.exists():
        return pd.read_parquet(p)
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from swingtrader.daily.marketdata import trade_date
    data, _ = A._clients()
    parts = []
    for i in range(0, len(symbols), 200):
        df = data.get_stock_bars(StockBarsRequest(symbol_or_symbols=symbols[i:i + 200], timeframe=TimeFrame.Day,
                                                  start=pd.Timestamp("2016-01-01", tz="UTC"), end=pd.Timestamp("2026-10-01", tz="UTC"),
                                                  feed="sip", adjustment="all")).df.reset_index()
        df["date"] = trade_date(df["timestamp"])
        parts.append(df.pivot_table(index="date", columns="symbol", values="close"))
        A.log(f"daily {min(i + 200, len(symbols))}/{len(symbols)}")
    x = pd.concat(parts, axis=1).sort_index()
    OUT.mkdir(parents=True, exist_ok=True)
    x.to_parquet(p)
    return x


def trade_period(P, f0, t0, t1, univ, cost_bp, pairs=None):
    form = P.loc[(P.index >= f0) & (P.index < t0), univ].dropna(axis=1)
    trd = P.loc[(P.index >= t0) & (P.index < t1), form.columns].ffill()
    if len(form) < 150 or len(trd) < 5:
        return pd.Series(dtype=float), []
    N = form / form.iloc[0]
    if pairs is None:
        cols = list(N.columns)
        X = N.values
        ssd = []
        for i, j in itertools.combinations(range(len(cols)), 2):
            ssd.append((float(((X[:, i] - X[:, j]) ** 2).sum()), cols[i], cols[j]))
        pairs = [(a, b) for _, a, b in sorted(ssd)[:NPAIR]]
    daily_ret = pd.Series(0.0, index=trd.index)
    for a, b in pairs:
        if a not in trd or b not in trd:
            continue
        sd = float((N[a] - N[b]).std())
        na, nb = trd[a] / form[a].iloc[0], trd[b] / form[b].iloc[0]
        spread = (na - nb).values
        ra, rb = trd[a].pct_change().fillna(0).values, trd[b].pct_change().fillna(0).values
        pos = 0                              # +1: long a / short b; -1: short a / long b
        r = np.zeros(len(trd))
        for k in range(1, len(trd)):
            r[k] = pos * (ra[k] - rb[k]) / 2  # $1 each leg on 1/NPAIR of capital -> pair return on its $2 gross
            if pos == 0 and abs(spread[k]) > OPEN_SD * sd:
                pos = -1 if spread[k] > 0 else 1
                r[k] -= 2 * cost_bp / 1e4 / 2
            elif pos != 0 and (np.sign(spread[k]) != np.sign(spread[k - 1]) or k == len(trd) - 1):
                pos = 0
                r[k] -= 2 * cost_bp / 1e4 / 2
        daily_ret += pd.Series(r, index=trd.index) / NPAIR
    return daily_ret, pairs


def run():
    univs = universes()
    syms = sorted({s for u in univs.values() for s in u})
    P = daily(syms)
    res = {"periods": len(univs)}
    series = {}
    for tier, c in COSTS.items():
        parts = []
        for f0, t0, t1 in periods():
            u = univs.get(str(t0.date()))
            if u:
                r, _ = trade_period(P, f0, t0, t1, u, c)
                parts.append(r)
        series[tier] = pd.concat(parts).sort_index()
    for tier, s in series.items():
        mo = (1 + s).groupby(s.index.to_period("M")).prod() - 1
        res[tier] = {"all": float(mo.mean() * 1e4), "h1": float(mo[mo.index < pd.Period(SPLIT)].mean() * 1e4),
                     "h2": float(mo[mo.index >= pd.Period(SPLIT)].mean() * 1e4),
                     "cagr": float((1 + s).prod() ** (252 / len(s)) - 1), "max_dd": float(((1 + s).cumprod() / (1 + s).cumprod().cummax() - 1).min())}
        if tier == "1x":
            x = mo.values
            res["t"] = float(x.mean() / (x.std(ddof=1) / math.sqrt(len(x))))
            res["without_best3"] = float(np.sort(x)[:-3].mean() * 1e4)
            res["by_year_1x_pct"] = {str(y): float(((1 + g).prod() - 1) * 100) for y, g in mo.groupby(mo.index.year)}
            actual = x.mean()
    rng = random.Random(61)
    pmeans = []
    for _ in range(200):
        parts = []
        for f0, t0, t1 in periods():
            u = univs.get(str(t0.date()))
            if u:
                cols = [c for c in u if c in P.columns]
                rp = [tuple(rng.sample(cols, 2)) for _ in range(NPAIR)]
                r, _ = trade_period(P, f0, t0, t1, u, COSTS["1x"], pairs=rp)
                parts.append(r)
        s = pd.concat(parts)
        pmeans.append(((1 + s).groupby(s.index.to_period("M")).prod() - 1).mean())
    res["placebo_pct"] = float(np.mean(np.array(pmeans) < actual) * 100)
    res["placebo_mean_bp"] = float(np.mean(pmeans) * 1e4)
    a2 = res["2x"]
    res["verdict"] = ("PASS (to paper)" if a2["h1"] > 0 and a2["h2"] > 0 and res["t"] >= 2 and res["without_best3"] > 0
                      and res["placebo_pct"] >= 95 else "DEAD")
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    run()
