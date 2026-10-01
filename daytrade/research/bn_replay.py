"""Study Lab-BN: SVXY in VIX term-structure contango, else BIL (round1_prose.md Lab Round 38). Cboe VIX / VIX3M daily
closes; Alpaca SIP daily adjusted OPENS (the opening crosses) for SVXY, BIL, SPY.

  python -m daytrade.research.bn_replay
"""
from __future__ import annotations

import json
import math
import random

import numpy as np
import pandas as pd
import requests

from ..settings import DATA
from . import as_replay as A

OUT = DATA / "research" / "bn"
START, END, SPLIT = "2018-03-01", "2026-09-30", "2022-01-01"


def cboe(sym):
    p = OUT / f"{sym}.csv"
    if not p.exists():
        r = requests.get(f"https://cdn.cboe.com/api/global/us_indices/daily_prices/{sym}_History.csv", timeout=30)
        r.raise_for_status()
        OUT.mkdir(parents=True, exist_ok=True)
        p.write_text(r.text)
    x = pd.read_csv(p)
    x["date"] = pd.to_datetime(x.DATE)
    return x.set_index("date").CLOSE


def opens():
    p = OUT / "opens.parquet"
    if p.exists():
        return pd.read_parquet(p)
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from swingtrader.daily.marketdata import trade_date
    data, _ = A._clients()
    df = data.get_stock_bars(StockBarsRequest(symbol_or_symbols=["SVXY", "BIL", "SPY"], timeframe=TimeFrame.Day,
                                              start=pd.Timestamp("2018-02-01", tz="UTC"), end=pd.Timestamp("2026-09-30T23:00", tz="UTC"),
                                              feed="sip", adjustment="all")).df.reset_index()
    df["date"] = trade_date(df["timestamp"])
    x = df.pivot_table(index="date", columns="symbol", values="open").sort_index()
    OUT.mkdir(parents=True, exist_ok=True)
    x.to_parquet(p)
    return x


def run():
    vix, v3 = cboe("VIX"), cboe("VIX3M")
    O = opens()
    O = O[(O.index >= pd.Timestamp(START) - pd.Timedelta(days=10)) & (O.index <= pd.Timestamp(END) + pd.Timedelta(days=5))]
    ratio = (vix / v3).reindex(O.index)
    # open-to-open return of day d -> d+1, the position set by the signal at day d-1's close
    r = O.shift(-1) / O - 1
    sig = (ratio.shift(1) < 1.0)                       # day d-1's close decides the position held from d's open
    d = pd.DataFrame({"svxy": r.SVXY, "bil": r.BIL, "spy": r.SPY, "in": sig}).dropna()
    d = d[(d.index >= pd.Timestamp(START)) & (d.index <= pd.Timestamp(END))]
    res = {"days": len(d), "in_share": float(d["in"].mean())}

    def series(inmask, c_bp):
        ret = np.where(inmask, d.svxy, d.bil)
        sw = np.abs(np.diff(np.r_[0, inmask.astype(int)]))
        return pd.Series(ret - sw * 2 * c_bp / 1e4 / 1, index=d.index)   # a switch = sell one + buy the other

    for tier, c in (("1x", 5), ("2x", 10)):
        s = series(d["in"].values, c)
        ex = s - d.bil
        mo = (1 + ex).groupby(ex.index.to_period("M")).prod() - 1
        eq = (1 + s).cumprod()
        res[tier] = {"cagr": float(eq.iloc[-1] ** (252 / len(s)) - 1), "max_dd": float((eq / eq.cummax() - 1).min()),
                     "ex_month_bp": float(mo.mean() * 1e4), "h1": float(mo[mo.index < pd.Period(SPLIT[:7])].mean() * 1e4),
                     "h2": float(mo[mo.index >= pd.Period(SPLIT[:7])].mean() * 1e4),
                     "switches_per_yr": float(np.abs(np.diff(d["in"].astype(int))).sum() / (len(d) / 252))}
        if tier == "1x":
            x = mo.values
            res["t"] = float(x.mean() / (x.std(ddof=1) / math.sqrt(len(x))))
            res["without_best5"] = float(np.sort(x)[:-5].mean() * 1e4)
            res["by_year_pct"] = {str(y): float(((1 + g).prod() - 1) * 100) for y, g in s.groupby(s.index.year)}
            actual = x.mean()
    for name, col in (("SVXY buy&hold", "svxy"), ("SPY", "spy")):
        eq = (1 + d[col]).cumprod()
        res[name] = {"cagr": float(eq.iloc[-1] ** (252 / len(d)) - 1), "max_dd": float((eq / eq.cummax() - 1).min())}
    rng = random.Random(71)
    inm = d["in"].values.astype(int)
    blocks = [inm[i:i + 21] for i in range(0, len(inm), 21)]
    pm = []
    for _ in range(1000):
        b = blocks[:]; rng.shuffle(b)
        m = np.concatenate(b)[:len(inm)].astype(bool)
        s = series(m, 5); ex = s - d.bil
        pm.append(((1 + ex).groupby(ex.index.to_period("M")).prod() - 1).mean())
    res["placebo_pct"] = float(np.mean(np.array(pm) < actual) * 100)
    a2 = res["2x"]
    res["verdict"] = ("PASS (to paper)" if a2["h1"] > 0 and a2["h2"] > 0 and res["t"] >= 2 and res["1x"]["max_dd"] > -0.5
                      and res["placebo_pct"] >= 95 and res["without_best5"] > 0 else "DEAD")
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    run()
