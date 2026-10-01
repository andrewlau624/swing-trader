"""Study Lab-BI: short announcement-gap stocks (Lab-BH's events) hedged with SPY, judged ONLY on 2017-2021
(round1_prose.md Lab Round 33). Daily bars, completed regular sessions (pre-23/5): raw for the filters, adjusted
for returns. Entry = day 1's opening cross; exit = day 20's closing cross.

  python -m daytrade.research.bi_replay
"""
from __future__ import annotations

import datetime as dt
import json
import math
import random
from collections import defaultdict

import numpy as np
import pandas as pd

from ..settings import DATA
from . import as_replay as A
from . import bh_replay as BH

OUT = DATA / "research" / "bi"
START, END = dt.date(2017, 1, 3), dt.date(2021, 12, 31)
FETCH_FROM, FETCH_TO = dt.date(2016, 10, 1), dt.date(2022, 2, 15)
SPLIT = "2020-01-01"
H = 20
COSTS = {"1x": (10, 0.5, 0.005), "2x": (20, 1.0, 0.010)}   # stock bp/side, SPY bp/side, borrow per year


def bars(symbols, adjustment, path):
    if path.exists():
        return pd.read_parquet(path)
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from swingtrader.daily.marketdata import trade_date
    data, _ = A._clients()
    parts = []
    cols = ["symbol", "timestamp", "open", "high", "low", "close", "volume"]
    for i in range(0, len(symbols), 300):
        for attempt in range(4):
            try:
                df = data.get_stock_bars(StockBarsRequest(symbol_or_symbols=symbols[i:i + 300], timeframe=TimeFrame.Day,
                                                          start=pd.Timestamp(FETCH_FROM, tz="UTC"), end=pd.Timestamp(FETCH_TO, tz="UTC"),
                                                          feed="sip", adjustment=adjustment)).df
                break
            except Exception as exc:
                A.log(f"retry {attempt} {type(exc).__name__}"); import time; time.sleep(10)
        else:
            continue
        if df is not None and len(df):
            parts.append(df.reset_index()[cols])
        A.log(f"{adjustment} {min(i + 300, len(symbols))}/{len(symbols)}")
    x = pd.concat(parts)
    x["date"] = trade_date(x["timestamp"])
    x = x.drop(columns="timestamp")
    OUT.mkdir(parents=True, exist_ok=True)
    x.to_parquet(path)
    return x


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    raw = bars(sorted(A.universe()), "raw", OUT / "raw.parquet")
    BH.A.START = START                                   # the event scan's date floor
    ev = BH.events(raw)
    ev = ev[(ev.day0 >= pd.Timestamp(START)) & (ev.day0 <= pd.Timestamp(END))]
    A.log(f"events 2017-2021: {len(ev)}")
    adj = bars(sorted(set(ev.sym) | {"SPY"}), "all", OUT / "adjusted.parquet")
    px = {s: g.set_index("date").sort_index() for s, g in adj.groupby("symbol")}
    spy = px["SPY"]; si = {t: i for i, t in enumerate(spy.index)}
    etb = set(json.loads((DATA / "research" / "ba" / "etb.json").read_text()))

    def hedged(g, k):                                       # short g from day k+1 open to day k+H close, long SPY
        j = min(k + H, len(g) - 1)
        t1, tH = g.index[k + 1], g.index[j]
        if t1 not in si or tH not in si:
            return None
        ret = g.close.iat[j] / g.open.iat[k + 1] - 1
        mkt = spy.close.iat[si[tH]] / spy.open.iat[si[t1]] - 1
        return (mkt - ret) * 1e4, j - k

    rows = []
    for r in ev.itertuples(index=False):
        g = px.get(r.sym)
        if g is None or r.day0 not in g.index:
            continue
        k = g.index.get_loc(r.day0)
        if k + 1 >= len(g):
            continue
        h = hedged(g, k)
        if h:
            rows.append({"sym": r.sym, "day": str(r.day0.date()), "gross": h[0], "days": h[1], "volx": r.volx,
                         "etb": r.sym in etb})
    t = pd.DataFrame(rows)
    res = {"events": len(t), "etb_share": float(t.etb.mean())}
    for name, part in (("Lab-BI1", t), ("Lab-BI2", t[t.etb])):
        v = {"n": len(part)}
        for mult, (c, cs, borrow) in COSTS.items():
            net = part.gross - 2 * c - 2 * cs - borrow * part.days / 252 * 1e4
            v[mult] = {h: float(net[mask].mean()) for h, mask in (("all", net.index == net.index),
                                                                  ("h1", part.day < SPLIT), ("h2", part.day >= SPLIT))}
            if mult == "1x":
                n1 = net.values
        m = n1.mean()
        cl = defaultdict(float)
        for mo, x in zip(part.day.str[:7], n1):
            cl[mo] += x - m
        v["t_month"] = float(m / (math.sqrt(sum(z * z for z in cl.values())) / len(n1)))
        v["median_1x"] = float(np.median(n1))
        v["without_top20"] = float(np.sort(n1)[:-20].mean())
        v["by_year_1x"] = {y: float(x.mean()) for y, x in pd.Series(n1, index=part.day.str[:4]).groupby(level=0)}
        # placebo: same stocks, random non-event dates, same short+hedge, 1x costs
        evd = defaultdict(set)
        for r in ev.itertuples(index=False):
            evd[r.sym].add(r.day0)
        pool = {}
        for s in part.sym.unique():
            g = px[s]; idx = g.index
            bad = set()
            for e in evd[s]:
                if e in idx:
                    q = idx.get_loc(e); bad |= set(idx[max(0, q - 5):q + 6])
            opts = []
            for k in range(1, len(idx) - H - 1):
                if idx[k] in bad or not (pd.Timestamp(START) <= idx[k] <= pd.Timestamp(END)):
                    continue
                h = hedged(g, k)
                if h:
                    opts.append(h[0] - 2 * 10 - 2 * 0.5 - 0.005 * h[1] / 252 * 1e4)
            pool[s] = opts or [0.0]
        rng = random.Random(53)
        means = [np.mean([rng.choice(pool[s]) for s in part.sym]) for _ in range(1000)]
        v["placebo_pct"] = float(np.mean(np.array(means) < m) * 100)
        v["placebo_mean_bp"] = float(np.mean(means))
        v["verdict"] = ("PASS (to paper)" if v["2x"]["h1"] > 0 and v["2x"]["h2"] > 0 and v["t_month"] >= 2
                        and v["placebo_pct"] >= 95 and v["without_top20"] > 0 else "DEAD")
        res[name] = v
        print(name, v["verdict"], json.dumps({k: v[k] for k in ("n", "1x", "2x", "t_month", "median_1x", "without_top20",
                                                               "placebo_pct", "by_year_1x")}, default=float), flush=True)
    t.to_csv(OUT / "events.csv", index=False)
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    run()
