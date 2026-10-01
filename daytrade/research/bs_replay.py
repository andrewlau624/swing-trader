"""Study Lab-BS: sector-ETF 12-1 momentum rotation (round1_prose.md Lab Round 41). Monthly adjusted SIP bars.

  python -m daytrade.research.bs_replay
"""
from __future__ import annotations

import json
import math
import random

import numpy as np
import pandas as pd

from ..settings import DATA
from . import as_replay as A

OUT = DATA / "research" / "bs"
ETFS = ["XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY"]
TOP, TEST_FROM, SPLIT = 3, "2017-01", "2022-01"


def run(etfs=None, top=None, bench="ew", out=None, cost=(5, 10)):
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
    etfs = etfs or ETFS
    top = top or TOP
    out = out or OUT
    data, _ = A._clients()
    df = data.get_stock_bars(StockBarsRequest(symbol_or_symbols=etfs + ["SPY"], timeframe=TimeFrame(1, TimeFrameUnit.Month),
                                              start=pd.Timestamp("2015-10-01", tz="UTC"), end=pd.Timestamp("2026-09-30T23:00", tz="UTC"),
                                              feed="sip", adjustment="all")).df.reset_index()
    df["month"] = df.timestamp.dt.tz_convert("America/New_York").dt.strftime("%Y-%m")
    C = df.pivot_table(index="month", columns="symbol", values="close")
    R = C / C.shift(1) - 1
    MOM = C.shift(1) / C.shift(12) - 1
    rows = []
    for m in [m for m in C.index if m >= TEST_FROM]:
        prev = C.index[C.index.get_loc(m) - 1]
        sc = MOM.loc[prev, etfs].dropna()
        avail = list(sc.index)
        picks = list(sc.sort_values(ascending=False).index[:top])
        if len(avail) < top + 1:
            continue                      # no full 12-1 signal yet (SIP history starts 2016-01)
        rows.append({"month": m, "port": float(R.loc[m, picks].mean()),
                     "bench": float(R.loc[m, "SPY"]) if bench == "spy" else float(R.loc[m, avail].mean()),
                     "spy": float(R.loc[m, "SPY"]), "univ": R.loc[m, avail].values})
    t = pd.DataFrame(rows)
    res = {"months": len(t)}
    for mult, c in (("1x", cost[0]), ("2x", cost[1])):
        t[f"ex_{mult}"] = (t.port - t.bench) * 1e4 - 2 * c
        res[mult] = {h: float(p[f"ex_{mult}"].mean()) for h, p in (("all", t), ("h1", t[t.month < SPLIT]), ("h2", t[t.month >= SPLIT]))}
    x = t.ex_1x.values
    res["t"] = float(x.mean() / (x.std(ddof=1) / math.sqrt(len(x))))
    res["without_best5"] = float(np.sort(x)[:-5].mean())
    res["cagr"] = {k: float((1 + v).prod() ** (12 / len(t)) - 1) for k, v in (("port_1x", t.port - 2 * cost[0] / 1e4), ("bench", t.bench), ("spy", t.spy))}
    res["by_year_1x"] = {y: float(g.ex_1x.mean()) for y, g in t.groupby(t.month.str[:4])}
    rng = random.Random(79)
    means = [np.mean([(np.mean(rng.sample(list(u), top)) - b) * 1e4 - 2 * cost[0] for u, b in zip(t.univ, t.bench)]) for _ in range(1000)]
    res["placebo_pct"] = float(np.mean(np.array(means) < x.mean()) * 100)
    a2 = res["2x"]
    res["verdict"] = ("PASS (to paper)" if a2["h1"] > 0 and a2["h2"] > 0 and res["t"] >= 2 and res["placebo_pct"] >= 95
                      and res["without_best5"] > 0 else "DEAD")
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))


BX_ETFS = ["XBI", "XHB", "XRT", "KRE", "KIE", "XME", "XOP", "OIH", "SMH", "IGV", "ITA", "IYT", "XPH", "IHI", "XHS",
           "GDX", "IYR", "IYZ", "JETS", "TAN"]


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "bx":   # Study Lab-BX (Lab Round 46)
        run(etfs=BX_ETFS, top=5, bench="spy", out=DATA / "research" / "bx", cost=(5, 10))
    else:
        run()
