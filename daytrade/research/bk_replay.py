"""Study Lab-BK: short both legs of a 3x LETF pair, weekly rebalanced (daytrade/plans/letf_decay.md, Lab Round 35).
Adjusted SIP daily closes (the closing crosses), 2016-01 .. 2026-09.

  python -m daytrade.research.bk_replay
"""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd

from ..settings import DATA
from . import as_replay as A

OUT = DATA / "research" / "bk"
PAIRS = {"Lab-BK1": ("TQQQ", "SQQQ", "QQQ"), "Lab-BK2": ("UPRO", "SPXU", "SPY"), "ref QQQ+PSQ": ("QQQ", "PSQ", "QQQ")}
COSTS = {"1x": (5, 0.02, 0.04), "2x": (10, 0.05, 0.10)}
SPLIT = "2021-01-01"


def closes():
    p = OUT / "daily.parquet"
    if p.exists():
        return pd.read_parquet(p)
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from swingtrader.daily.marketdata import trade_date
    data, _ = A._clients()
    syms = sorted({s for v in PAIRS.values() for s in v})
    df = data.get_stock_bars(StockBarsRequest(symbol_or_symbols=syms, timeframe=TimeFrame.Day,
                                              start=pd.Timestamp("2016-01-01", tz="UTC"), end=pd.Timestamp("2026-10-01", tz="UTC"),
                                              feed="sip", adjustment="all")).df.reset_index()
    df["date"] = trade_date(df["timestamp"])
    x = df.pivot_table(index="date", columns="symbol", values="close").sort_index()
    OUT.mkdir(parents=True, exist_ok=True)
    x.to_parquet(p)
    return x


def simulate(px, bull, bear, c_bp, b_bull, b_bear):
    """Weekly: short 0.5 of equity in each leg at the week's last close; P&L to the next week's last close."""
    wk = px[[bull, bear]].dropna()
    last = wk.groupby(wk.index.to_period("W-FRI")).tail(1)
    rows = []
    for (d0, r0), (d1, r1) in zip(last.iloc[:-1].iterrows(), last.iloc[1:].iterrows()):
        rb, rr = r1[bull] / r0[bull] - 1, r1[bear] / r0[bear] - 1
        days = (d1 - d0).days
        pnl = -0.5 * rb - 0.5 * rr                                        # short both legs
        borrow = 0.5 * b_bull * days / 365 + 0.5 * b_bear * days / 365
        # rebalance turnover at d1: each leg's notional moved by its return; bring both back to 0.5
        turnover = 0.5 * abs(rb) + 0.5 * abs(rr) + abs(pnl)               # leg drift + equity change
        rows.append({"week": str(d1.date()), "net": pnl - borrow - turnover * c_bp / 1e4, "gross": pnl})
    return pd.DataFrame(rows)


def run():
    px = closes()
    res = {}
    for name, (bull, bear, idx) in PAIRS.items():
        v = {}
        for tier, (c, bb, br) in COSTS.items():
            w = simulate(px, bull, bear, c, bb, br)
            eq = (1 + w.net).cumprod()
            v[tier] = {h: float(p.net.mean() * 1e4) for h, p in (("all", w), ("h1", w[w.week < SPLIT]), ("h2", w[w.week >= SPLIT]))}
            v[tier]["cagr"] = float(eq.iloc[-1] ** (52 / len(w)) - 1)
            v[tier]["max_dd"] = float((eq / eq.cummax() - 1).min())
            v[tier]["worst_week"] = float(w.net.min())
            if tier == "1x":
                x = w.net.values
                v["t"] = float(x.mean() / (x.std(ddof=1) / math.sqrt(len(x))))
                v["without_best5"] = float(np.sort(x)[:-5].mean() * 1e4)
                v["gross_bp_week"] = float(w.gross.mean() * 1e4)
                v["by_year_1x_pct"] = {y: float(((1 + g.net).prod() - 1) * 100) for y, g in w.groupby(w.week.str[:4])}
                wi = px[idx].groupby(px.index.to_period("W-FRI")).last().pct_change().dropna()
                wi.index = [str(p.end_time.date()) for p in wi.index]
                j = w.set_index("week").net.reindex(wi.index).dropna()
                v["corr_index"] = float(np.corrcoef(j.values, wi.loc[j.index].values)[0, 1]) if len(j) > 10 else None
        a2 = v["2x"]
        v["verdict"] = ("PASS (to paper)" if a2["h1"] > 0 and a2["h2"] > 0 and v["t"] >= 2 and v["without_best5"] > 0
                        and v["1x"]["max_dd"] > -0.40 else "DEAD") if not name.startswith("ref") else "reference"
        res[name] = v
        print(name, v["verdict"], json.dumps({k: v[k] for k in ("t", "gross_bp_week", "without_best5", "corr_index")}, default=float),
              json.dumps(v["1x"], default=float), json.dumps(v["2x"], default=float), json.dumps(v["by_year_1x_pct"], default=float), flush=True)
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    run()
