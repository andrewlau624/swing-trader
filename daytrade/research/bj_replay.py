"""Study Lab-BJ: calendar-month return seasonality (daytrade/plans/seasonality.md, round1_prose.md Lab Round 34).
Monthly SIP bars: adjusted (splits + dividends) for returns, raw for the $5 price filter. Month-end closes are the
closing cross of each month's last regular session.

  python -m daytrade.research.bj_replay
"""
from __future__ import annotations

import json
import math
import random

import numpy as np
import pandas as pd

from ..settings import DATA
from . import as_replay as A

OUT = DATA / "research" / "bj"
TOP, UNIV = 20, 500
TEST_FROM, SPLIT = "2021-01", "2024-01"


def monthly(adjustment):
    p = OUT / f"monthly_{adjustment}.parquet"
    if p.exists():
        return pd.read_parquet(p)
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
    data, _ = A._clients()
    syms = sorted(A.universe())
    parts = []
    for i in range(0, len(syms), 500):
        for attempt in range(4):
            try:
                df = data.get_stock_bars(StockBarsRequest(symbol_or_symbols=syms[i:i + 500], timeframe=TimeFrame(1, TimeFrameUnit.Month),
                                                          start=pd.Timestamp("2015-11-01", tz="UTC"), end=pd.Timestamp("2026-10-01", tz="UTC"),
                                                          feed="sip", adjustment=adjustment)).df
                break
            except Exception as exc:
                A.log(f"retry {attempt} {type(exc).__name__}"); import time; time.sleep(10)
        else:
            continue
        if df is not None and len(df):
            parts.append(df.reset_index()[["symbol", "timestamp", "close", "volume"]])
        A.log(f"monthly {adjustment} {min(i + 500, len(syms))}/{len(syms)}")
    x = pd.concat(parts)
    x["month"] = x.timestamp.dt.tz_convert("America/New_York").dt.strftime("%Y-%m")
    x = x.drop(columns="timestamp")
    OUT.mkdir(parents=True, exist_ok=True)
    x.to_parquet(p)
    return x


def run():
    adj, raw = monthly("all"), monthly("raw")
    C = adj.pivot_table(index="month", columns="symbol", values="close")
    V = adj.pivot_table(index="month", columns="symbol", values="volume")
    RAW = raw.pivot_table(index="month", columns="symbol", values="close").reindex(index=C.index, columns=C.columns)
    R = C / C.shift(1) - 1                       # month m's return (close m-1 -> close m)
    DV = (C * V).rolling(12, min_periods=10).mean()
    months = [m for m in C.index if m >= TEST_FROM]
    rows, missing = [], 0
    for m in months:
        k = C.index.get_loc(m)
        prev = C.index[k - 1]
        elig = RAW.loc[prev][RAW.loc[prev] >= 5].index
        dv = DV.loc[prev, elig].dropna().sort_values(ascending=False)
        univ = list(dv.index[:UNIV])
        cal = m[5:]
        past = [mm for mm in C.index[:k] if mm[5:] == cal][-5:]
        sig = R.loc[past, univ].mean(skipna=True) if past else pd.Series(dtype=float)
        nobs = R.loc[past, univ].notna().sum() if past else pd.Series(dtype=float)
        sig = sig[nobs >= 3].dropna()
        picks = list(sig.sort_values(ascending=False).index[:TOP])
        r_univ = R.loc[m, univ]
        missing += int(r_univ[picks].isna().sum())
        port = r_univ[picks].fillna(0.0).mean()          # a pick without a month-m bar (delisted) counts as 0
        bench = r_univ.mean(skipna=True)
        rows.append({"month": m, "port": port, "bench": bench, "n_univ": len(univ), "n_sig": len(sig),
                     "picks": picks, "univ_ret": r_univ.fillna(0.0).to_dict()})
    t = pd.DataFrame(rows)
    res = {"months": len(t), "missing_pick_months": missing}
    for mult, c in (("1x", 10), ("2x", 20)):
        t[f"ex_{mult}"] = (t.port - t.bench) * 1e4 - 2 * c
        res[mult] = {h: float(p[f"ex_{mult}"].mean()) for h, p in (("all", t), ("h1", t[t.month < SPLIT]), ("h2", t[t.month >= SPLIT]))}
    x = t.ex_1x.values
    res["t"] = float(x.mean() / (x.std(ddof=1) / math.sqrt(len(x))))
    res["without_best5"] = float(np.sort(x)[:-5].mean())
    res["by_year_1x"] = {y: float(g.ex_1x.mean()) for y, g in t.groupby(t.month.str[:4])}
    res["port_annual_gross"] = float((1 + t.port).prod() ** (12 / len(t)) - 1)
    res["bench_annual"] = float((1 + t.bench).prod() ** (12 / len(t)) - 1)
    rng = random.Random(59)
    means = []
    for _ in range(1000):
        sims = [np.mean(rng.sample(list(r.univ_ret.values()), TOP)) * 1e4 - (r.bench * 1e4) - 20 for r in t.itertuples()]
        means.append(np.mean(sims))
    res["placebo_pct"] = float(np.mean(np.array(means) < x.mean()) * 100)
    res["placebo_mean_bp"] = float(np.mean(means))
    a2 = res["2x"]
    res["verdict"] = ("PASS (to paper)" if a2["h1"] > 0 and a2["h2"] > 0 and res["t"] >= 2 and res["placebo_pct"] >= 95
                      and res["without_best5"] > 0 else "DEAD")
    t.drop(columns=["univ_ret"]).to_csv(OUT / "months.csv", index=False)
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    run()
