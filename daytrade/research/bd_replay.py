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


if __name__ == "__main__":
    {"build": build}[sys.argv[1]]()
