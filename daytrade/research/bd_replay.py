"""Study Lab-BD: the early closing imbalance on QQQ / TQQQ every day (cheap instruments). Data: Lab-AZ's NOII files;
Alpaca SIP NBBO at close-5:29 (entry) and the official close (exit, the closing cross).

  python -m daytrade.research.bd_replay build     # daily rows for QQQ/TQQQ: r, entry quotes, close
  python -m daytrade.research.bd_replay run       # the registered test (after registration)
"""
from __future__ import annotations

import datetime as dt
import json
import pickle
import random
import sys

import numpy as np
import pandas as pd

from ..settings import DATA
from . import as_replay as A
from . import az_replay as Z

OUT = DATA / "research" / "bd"
SYMS = ("QQQ", "TQQQ")


def build():
    from alpaca.data.requests import StockBarsRequest, StockQuotesRequest
    from alpaca.data.timeframe import TimeFrame
    from swingtrader.daily.marketdata import trade_date
    data, _ = A._clients()
    cal = pickle.loads((Z.OUT / "sessions.pkl").read_bytes())
    rows = []
    for o, cl in cal:
        f = Z.OUT / "imbalance" / f"{o.date()}.parquet"
        if o.date() > Z.END or not f.exists():
            continue
        df = pd.read_parquet(f)
        t = (cl - dt.timedelta(minutes=5, seconds=30)).astimezone(dt.timezone.utc)
        df = df[(df.ts_event <= t) & df.symbol.isin(SYMS)]
        last = df.sort_values("ts_event").groupby("symbol").tail(1).set_index("symbol")
        q = data.get_stock_quotes(StockQuotesRequest(symbol_or_symbols=list(SYMS), start=t + dt.timedelta(seconds=1),
                                                     end=t + dt.timedelta(seconds=4), feed="sip")).df
        q = q.reset_index() if q is not None and len(q) else pd.DataFrame()
        for s in SYMS:
            if s not in last.index or not len(q):
                continue
            r0 = last.loc[s]
            sg = 1 if r0.side == "B" else -1 if r0.side == "A" else 0
            r = sg * float(r0.total_imbalance_qty) / float(r0.paired_qty) if r0.paired_qty > 0 else 0.0
            qs = q[(q.symbol == s) & (q.bid_price > 0) & (q.ask_price >= q.bid_price)]
            if len(qs):
                rows.append({"day": str(o.date()), "sym": s, "r": r, "bid": float(qs.iloc[0].bid_price),
                             "ask": float(qs.iloc[0].ask_price)})
    x = pd.DataFrame(rows)
    bars = data.get_stock_bars(StockBarsRequest(symbol_or_symbols=list(SYMS), timeframe=TimeFrame.Day,
                                                start=pd.Timestamp(Z.START, tz="UTC"),
                                                end=pd.Timestamp(Z.END + dt.timedelta(days=1), tz="UTC"),
                                                feed="sip", adjustment="raw")).df.reset_index()
    bars["day"] = trade_date(bars["timestamp"]).dt.strftime("%Y-%m-%d")
    closes = bars.set_index(["symbol", "day"])["close"]
    x["close"] = [float(closes.get((s, d), np.nan)) for s, d in zip(x.sym, x.day)]
    x["mid"] = (x.bid + x.ask) / 2
    x["fwd_bp"] = (x.close / x.mid - 1) * 1e4
    x["spread_bp"] = (x.ask - x.bid) / x.mid * 1e4
    OUT.mkdir(parents=True, exist_ok=True)
    x.to_parquet(OUT / "daily.parquet")
    A.log(f"rows {len(x)}")



HI, LO = 0.2585, -0.2824          # H1 80th / 20th pct of QQQ's r (registered)


def trades(x, mult):
    x = x[(x.sym == "QQQ") & x.close.notna()].copy()
    x["side"] = np.where(x.r >= HI, 1, np.where(x.r <= LO, -1, 0))
    x = x[x.side != 0]
    half = (x.ask - x.bid) / 2
    extra = 0.5 if mult == 1 else 1.0
    entry = np.where(x.side > 0, x.ask + (half if mult == 2 else 0), x.bid - (half if mult == 2 else 0))
    entry = entry * (1 + x.side * extra / 1e4)
    exit_ = x.close * (1 - x.side * extra / 1e4)
    x["net_bp"] = x.side * (exit_ / entry - 1) * 1e4
    x["gross_bp"] = x.side * x.fwd_bp
    x["cost_bp"] = x.gross_bp - x.net_bp
    return x


def run():
    x = pd.read_parquet(OUT / "daily.parquet")
    res = {}
    for label, part in (("H2 (holdout, judged)", x[x.day >= "2024-06-01"]), ("H1 (in-sample)", x[x.day < "2024-06-01"])):
        t1, t2 = trades(part, 1), trades(part, 2)
        n = part[part.sym == "QQQ"].day.nunique()
        xs = np.sort(t1.net_bp.values)
        rng = random.Random(37)
        means = [np.mean([(g if rng.random() < 0.5 else -g) - c for g, c in zip(t1.gross_bp, t1.cost_bp)]) for _ in range(1000)]
        res[label] = {"n": len(t1), "days": n, "gross": float(t1.gross_bp.mean()),
                      "1x": A.summary(t1.to_dict("records"), n), "2x": A.summary(t2.to_dict("records"), n),
                      "without_top20": float(xs[:-20].mean()) if len(xs) > 40 else None,
                      "placebo_pct": float(np.mean(np.array(means) < t1.net_bp.mean()) * 100),
                      "by_side_1x": {int(k): [float(g.net_bp.mean()), len(g)] for k, g in t1.groupby("side")},
                      "by_year_1x": {y: float(g.net_bp.mean()) for y, g in t1.groupby(t1.day.str[:4])},
                      "median_spread_bp": float(t1.spread_bp.median())}
        if label.startswith("H2"):
            t1.to_csv(OUT / "trades_H2_1x.csv", index=False)
    h = res["H2 (holdout, judged)"]
    res["verdict"] = ("PASS (to paper)" if h["2x"]["mean_bp"] > 0 and h["1x"]["t_day"] >= 2.0
                      and h["placebo_pct"] >= 95 and (h["without_top20"] or -1) > 0 else "DEAD")
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    {"build": build, "run": run}[sys.argv[1]]()
