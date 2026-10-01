"""Study Lab-BB: the early closing-imbalance size as a 15:54:30 signal, exit market-on-close
(daytrade/plans/close_imbalance.md, round1_prose.md Lab Round 26). Uses Lab-AZ's NOII files (Databento XNAS.ITCH).
Entry quotes: Alpaca SIP NBBO 1s after the decision. Exit: the official close (SIP regular daily close = the cross).

  python -m daytrade.research.bb_replay
"""
from __future__ import annotations

import datetime as dt
import json
import pickle
import random

import numpy as np
import pandas as pd

from ..settings import DATA
from . import as_replay as A
from . import az_replay as Z

OUT = DATA / "research" / "bb"
TOP = 5


def signals_for(df, cl):
    t = (cl - dt.timedelta(minutes=5, seconds=30)).astimezone(dt.timezone.utc)
    df = df[df.ts_event <= t]
    if not len(df):
        return []
    last = df.sort_values("ts_event").groupby("symbol").tail(1)
    sgn = np.where(last.side == "B", 1, np.where(last.side == "A", -1, 0))
    paired = last.paired_qty.astype(float)
    r = np.where(paired > 0, sgn * last.total_imbalance_qty.astype(float) / paired.where(paired > 0, 1), 0.0)
    x = pd.DataFrame({"sym": last.symbol.values, "r": r})
    longs = x[x.r > 0].nlargest(TOP, "r")
    shorts = x[x.r < 0].nsmallest(TOP, "r")
    return [(s, 1, v) for s, v in zip(longs.sym, longs.r)] + [(s, -1, v) for s, v in zip(shorts.sym, shorts.r)]


def fetch_prices():
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
        sig = signals_for(pd.read_parquet(f), cl)
        if not sig:
            continue
        t = (cl - dt.timedelta(minutes=5, seconds=29)).astimezone(dt.timezone.utc)
        q = data.get_stock_quotes(StockQuotesRequest(symbol_or_symbols=sorted({s for s, _, _ in sig}), start=t,
                                                     end=t + dt.timedelta(seconds=3), feed="sip")).df
        q = q.reset_index() if q is not None and len(q) else pd.DataFrame()
        for s, side, r in sig:
            qs = q[(q.symbol == s) & (q.bid_price > 0) & (q.ask_price >= q.bid_price)] if len(q) else q
            if len(qs):
                rows.append({"day": str(o.date()), "sym": s, "side": side, "dev": r,
                             "bid": float(qs.iloc[0].bid_price), "ask": float(qs.iloc[0].ask_price)})
    sig = pd.DataFrame(rows)
    syms = sorted(set(sig.sym))
    bars = data.get_stock_bars(StockBarsRequest(symbol_or_symbols=syms, timeframe=TimeFrame.Day,
                                                start=pd.Timestamp(Z.START, tz="UTC"),
                                                end=pd.Timestamp(Z.END + dt.timedelta(days=1), tz="UTC"),
                                                feed="sip", adjustment="raw")).df.reset_index()
    bars["day"] = trade_date(bars["timestamp"]).dt.strftime("%Y-%m-%d")
    closes = bars.set_index(["symbol", "day"])["close"]
    sig["close"] = [float(closes.get((s, d), np.nan)) for s, d in zip(sig.sym, sig.day)]
    OUT.mkdir(parents=True, exist_ok=True)
    sig.to_parquet(OUT / "signals.parquet")
    A.log(f"signals with quotes: {len(sig)}")


def run():
    if not (OUT / "signals.parquet").exists():
        fetch_prices()
    sig = pd.read_parquet(OUT / "signals.parquet")
    days = sorted(set(sig.day))
    cal = pickle.loads((Z.OUT / "sessions.pkl").read_bytes())
    n_days = sum(1 for o, _ in cal if Z.START <= o.date() <= Z.END)
    n1 = sum(1 for o, _ in cal if Z.START <= o.date() < Z.SPLIT)
    res = {"n_days": n_days, "n_h1": n1, "signal_days": len(days)}
    for name, lo in (("Lab-BB1", False), ("Lab-BB2", True)):
        t1, t2 = Z.trades(sig, 1, lo), Z.trades(sig, 2, lo)
        r1, r2 = t1.to_dict("records"), t2.to_dict("records")
        v = {k: {h: A.summary(x, m) for h, x, m in (("all", rr, n_days), ("h1", A.half(rr, 1), n1),
                                                     ("h2", A.half(rr, 2), n_days - n1))}
             for k, rr in (("1x", r1), ("2x", r2))}
        xs = np.sort(t1.net_bp.values)
        v["gross_bp"] = float(t1.gross_bp.mean())
        v["mean_spread_bp"] = float(((t1.ask - t1.bid) / ((t1.ask + t1.bid) / 2) * 1e4).mean())
        v["mean_without_top20"] = float(xs[:-20].mean()) if len(xs) > 40 else None
        v["by_side"] = {int(k): float(g.net_bp.mean()) for k, g in t1.groupby("side")}
        rng = random.Random(29)
        means = [np.mean([(g if rng.random() < 0.5 else -g) - c for g, c in zip(t1.gross_bp, t1.cost_bp)])
                 for _ in range(1000)]
        v["placebo_pct"] = float(np.mean(np.array(means) < t1.net_bp.mean()) * 100)
        a2 = v["2x"]
        v["verdict"] = ("PASS (to paper)" if a2["h1"]["mean_bp"] > 0 and a2["h2"]["mean_bp"] > 0
                        and v["1x"]["all"]["t_day"] >= 2.0 and v["placebo_pct"] >= 95
                        and (v["mean_without_top20"] or -1) > 0 else "DEAD")
        res[name] = v
        t1.to_csv(OUT / f"trades_{name}_1x.csv", index=False)
        print(name, v["verdict"], json.dumps({"n": len(t1), "net": v["1x"]["all"]["mean_bp"], "gross": v["gross_bp"],
                                              "t": v["1x"]["all"]["t_day"], "no_top20": v["mean_without_top20"],
                                              "placebo": v["placebo_pct"], "by_side": v["by_side"]}), flush=True)
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    run()
