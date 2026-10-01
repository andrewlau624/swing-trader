"""Study Lab-BE: buy (short) in the Nasdaq opening cross after a big sell (buy) imbalance at 09:28, exit 10:00
(daytrade/plans/open_cross_reversal.md, round1_prose.md Lab Round 29).

Reads: Databento XNAS.ITCH `imbalance` opening-cross messages 09:27-09:28 ET (pre-open; the one pre-session input,
the indicative price of the official 09:30 cross); the official opening cross price (SIP raw daily open: the
09:30 auction print); Alpaca SIP NBBO at 10:00:00 (regular session) for the exit.

  python -m daytrade.research.be_replay fetch
  python -m daytrade.research.be_replay run
"""
from __future__ import annotations

import datetime as dt
import json
import pickle
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

from ..settings import DATA
from . import as_replay as A
from . import az_replay as Z

OUT = DATA / "research" / "be"
VARIANT = "BE"
BUDGET = 28.0       # measured $0.023/day x 1,190 ~ $27; lab total ~$92 + main BD/BE ~$16 < $125
TOP = 5


def fetch():
    import databento as db
    from swingtrader.config import get_env
    syms = Z.universe()
    cal = pickle.loads((Z.OUT / "sessions.pkl").read_bytes())
    d = OUT / "imbalance"; d.mkdir(parents=True, exist_ok=True)
    sp = OUT / "spent.json"
    lock = threading.Lock()
    st = {"spent": json.loads(sp.read_text())["usd"] if sp.exists() else 0.0, "stop": False}
    todo = [(o, c) for o, c in cal if o.date() <= Z.END and not (d / f"{o.date()}.parquet").exists()]

    def one(oc):
        o, _ = oc
        if st["stop"]:
            return
        s, e = (o - dt.timedelta(minutes=3)).astimezone(dt.timezone.utc), (o - dt.timedelta(minutes=2)).astimezone(dt.timezone.utc)
        cli = db.Historical(get_env("DATABENTO_API_KEY"))
        for attempt in range(6):
            try:
                cost = cli.metadata.get_cost(dataset="XNAS.ITCH", schema="imbalance", symbols=syms, start=s, end=e)
                with lock:
                    if st["spent"] + cost > BUDGET:
                        st["stop"] = True; A.log(f"STOP at {o.date()}: ${st['spent'] + cost:.2f}"); return
                    st["spent"] += cost
                df = cli.timeseries.get_range(dataset="XNAS.ITCH", schema="imbalance", symbols=syms, start=s, end=e).to_df()
                break
            except Exception as exc:
                A.log(f"{o.date()} retry {attempt}: {type(exc).__name__}"); time.sleep(10 * (attempt + 1))
        else:
            A.log(f"{o.date()} skipped"); return
        if len(df):
            df = df.reset_index()[["ts_event", "symbol", "ref_price", "cont_book_clr_price", "auct_interest_clr_price",
                                   "paired_qty", "total_imbalance_qty", "side", "auction_type"]]
            df = df[df.auction_type == "O"]
        df.to_parquet(d / f"{o.date()}.parquet")
        with lock:
            sp.write_text(json.dumps({"usd": round(st["spent"], 4)}))

    with ThreadPoolExecutor(6) as ex:
        list(ex.map(one, todo))
    A.log(f"imbalance done, spent ${st['spent']:.2f}")
    prices(cal)


def signals_for(df, o):
    t = (o - dt.timedelta(minutes=2)).astimezone(dt.timezone.utc)
    df = df[df.ts_event <= t]
    if not len(df):
        return []
    last = df.sort_values("ts_event").groupby("symbol").tail(1)
    last = last[(last.ref_price > 0) & (last.cont_book_clr_price > 0)]
    last = last.assign(d=last.cont_book_clr_price / last.ref_price - 1)
    lo = last[(last.side == "A") & (last.d < 0)].nsmallest(TOP, "d")
    hi = last[(last.side == "B") & (last.d > 0)].nlargest(TOP, "d")
    return [(s, 1, v) for s, v in zip(lo.symbol, lo.d)] + [(s, -1, v) for s, v in zip(hi.symbol, hi.d)]


def prices(cal):
    from alpaca.data.requests import StockBarsRequest, StockQuotesRequest
    from alpaca.data.timeframe import TimeFrame
    from swingtrader.daily.marketdata import trade_date
    data, _ = A._clients()
    rows = []
    for o, _ in cal:
        f = OUT / "imbalance" / f"{o.date()}.parquet"
        if o.date() > Z.END or not f.exists():
            continue
        sig = signals_for(pd.read_parquet(f), o)
        if not sig:
            continue
        t = (o + dt.timedelta(minutes=30)).astimezone(dt.timezone.utc)
        q = data.get_stock_quotes(StockQuotesRequest(symbol_or_symbols=sorted({s for s, _, _ in sig}), start=t,
                                                     end=t + dt.timedelta(seconds=3), feed="sip")).df
        q = q.reset_index() if q is not None and len(q) else pd.DataFrame()
        for s, side, v in sig:
            qs = q[(q.symbol == s) & (q.bid_price > 0) & (q.ask_price >= q.bid_price)] if len(q) else q
            if len(qs):
                rows.append({"day": str(o.date()), "sym": s, "side": side, "d": v,
                             "bid": float(qs.iloc[0].bid_price), "ask": float(qs.iloc[0].ask_price)})
    x = pd.DataFrame(rows)
    bars = data.get_stock_bars(StockBarsRequest(symbol_or_symbols=sorted(set(x.sym)), timeframe=TimeFrame.Day,
                                                start=pd.Timestamp(Z.START, tz="UTC"),
                                                end=pd.Timestamp(Z.END + dt.timedelta(days=1), tz="UTC"),
                                                feed="sip", adjustment="raw")).df.reset_index()
    bars["day"] = trade_date(bars["timestamp"]).dt.strftime("%Y-%m-%d")
    opens = bars.set_index(["symbol", "day"])["open"]
    x["open"] = [float(opens.get((s, d), np.nan)) for s, d in zip(x.sym, x.day)]
    x.to_parquet(OUT / "signals.parquet")
    A.log(f"signals with exit quotes: {len(x)}")


def trades(x, mult, long_only):
    x = x.dropna(subset=["open"])
    if long_only:
        x = x[x.side > 0]
    x = x.copy()
    half = (x.ask - x.bid) / 2
    mid = (x.ask + x.bid) / 2
    c_in, c_out = (0.5, 0.5) if mult == 1 else (1.0, 1.0)
    entry = x.open * (1 + x.side * c_in / 1e4)
    ex = np.where(x.side > 0, x.bid - (half if mult == 2 else 0), x.ask + (half if mult == 2 else 0))
    ex = ex * (1 - x.side * c_out / 1e4)
    x["net_bp"] = x.side * (ex / entry - 1) * 1e4
    x["gross_bp"] = x.side * (mid / x.open - 1) * 1e4
    x["cost_bp"] = x.gross_bp - x.net_bp
    return x


def run():
    x = pd.read_parquet(OUT / "signals.parquet")
    cal = pickle.loads((Z.OUT / "sessions.pkl").read_bytes())
    n = sum(1 for o, _ in cal if Z.START <= o.date() <= Z.END)
    n1 = sum(1 for o, _ in cal if Z.START <= o.date() < Z.SPLIT)
    res = {"n_days": n, "spent": json.loads((OUT / "spent.json").read_text())}
    for name, lo in (("Lab-BE1", False), ("Lab-BE2", True)):
        t1, t2 = trades(x, 1, lo), trades(x, 2, lo)
        r1, r2 = t1.to_dict("records"), t2.to_dict("records")
        v = {k: {h: A.summary(rr_, m) for h, rr_, m in (("all", rr, n), ("h1", A.half(rr, 1), n1), ("h2", A.half(rr, 2), n - n1))}
             for k, rr in (("1x", r1), ("2x", r2))}
        xs = np.sort(t1.net_bp.values)
        rng = random.Random(41)
        means = [np.mean([(g if rng.random() < 0.5 else -g) - c for g, c in zip(t1.gross_bp, t1.cost_bp)]) for _ in range(1000)]
        v.update(gross_bp=float(t1.gross_bp.mean()), without_top20=float(xs[:-20].mean()) if len(xs) > 40 else None,
                 placebo_pct=float(np.mean(np.array(means) < t1.net_bp.mean()) * 100),
                 by_side={int(k): float(g.net_bp.mean()) for k, g in t1.groupby("side")},
                 by_year={y: float(g.net_bp.mean()) for y, g in t1.groupby(t1.day.str[:4])})
        a2 = v["2x"]
        v["verdict"] = ("PASS (to paper)" if a2["h1"]["mean_bp"] > 0 and a2["h2"]["mean_bp"] > 0 and v["1x"]["all"]["t_day"] >= 2
                        and v["placebo_pct"] >= 95 and (v["without_top20"] or -1) > 0 else "DEAD")
        res[name] = v
        t1.to_csv(OUT / f"trades_{name}_1x.csv", index=False)
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    {"fetch": fetch, "run": run}[sys.argv[1]]()
