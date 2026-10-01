"""Study Lab-AZ: Nasdaq closing-cross convergence from the NOII (daytrade/plans/close_cross.md,
round1_prose.md Lab Round 24).

Reads, all inside the regular session:
- Databento XNAS.ITCH `imbalance`, the closing cross's NOII from close-10:00 to close-5:00 ET each session
  (the calendar's close, so half days too).
- Alpaca SIP NBBO quotes in the 3 seconds after the decision (the entry).
- The SIP daily close (raw): the official closing-cross print, i.e. the market-on-close fill. It is a
  regular-session price by definition: the 16:00 cross.
Spend guard: every day is priced with metadata.get_cost before it is downloaded; the run stops once the
running total would pass BUDGET.

  python -m daytrade.research.az_replay fetch
  python -m daytrade.research.az_replay run
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

OUT = DATA / "research" / "az"
START, END, SPLIT = A.START, A.END, A.SPLIT
BUDGET = 60.0
DEV_MIN = 0.0010
log = A.log


def universe():
    return json.loads((OUT / "universe.json").read_text())


def fetch() -> None:
    import databento as db
    from swingtrader.config import get_env
    from swingtrader.daily.brokers import regular_sessions
    c = db.Historical(get_env("DATABENTO_API_KEY"))
    syms = universe()
    cal = regular_sessions(START, END + dt.timedelta(days=7))
    (OUT / "sessions.pkl").write_bytes(pickle.dumps(cal))
    d = OUT / "imbalance"; d.mkdir(parents=True, exist_ok=True)
    spent_p = OUT / "spent.json"
    spent = json.loads(spent_p.read_text())["usd"] if spent_p.exists() else 0.0
    for o, cl in cal:
        if o.date() > END:
            break
        f = d / f"{o.date()}.parquet"
        if f.exists():
            continue
        s, e = (cl - dt.timedelta(minutes=10)).astimezone(dt.timezone.utc), (cl - dt.timedelta(minutes=5)).astimezone(dt.timezone.utc)
        cost = c.metadata.get_cost(dataset="XNAS.ITCH", schema="imbalance", symbols=syms, start=s, end=e)
        if spent + cost > BUDGET:
            log(f"STOP: {o.date()} would take spend to ${spent + cost:.2f} > ${BUDGET}"); break
        df = c.timeseries.get_range(dataset="XNAS.ITCH", schema="imbalance", symbols=syms, start=s, end=e).to_df()
        if len(df):
            df = df.reset_index()[["ts_event", "symbol", "ref_price", "cont_book_clr_price", "auct_interest_clr_price",
                                   "paired_qty", "total_imbalance_qty", "side", "auction_type"]]
            df = df[df.auction_type == "C"]
        df.to_parquet(f)
        spent += cost
        spent_p.write_text(json.dumps({"usd": round(spent, 4)}))
        if o.day <= 3 or len(df) == 0:
            log(f"{o.date()}: {len(df)} records, spent ${spent:.2f}")
    log(f"imbalance done, spent ${spent:.2f}")
    fetch_prices(cal)


def signals_for(day, df, cl):
    t = (cl - dt.timedelta(minutes=5, seconds=30)).astimezone(dt.timezone.utc)
    df = df[df.ts_event <= t]
    if not len(df):
        return []
    last = df.sort_values("ts_event").groupby("symbol").tail(1)
    out = []
    for r in last.itertuples(index=False):
        if r.ref_price <= 0 or r.cont_book_clr_price <= 0:
            continue
        dev = r.cont_book_clr_price / r.ref_price - 1
        if dev >= DEV_MIN and r.side == "B":
            out.append((r.symbol, 1, dev))
        elif dev <= -DEV_MIN and r.side == "A":
            out.append((r.symbol, -1, dev))
    return out


def fetch_prices(cal) -> None:
    """Entry NBBO (first quote >= decision + 1s) for every signal, and SIP daily closes."""
    from alpaca.data.requests import StockQuotesRequest
    data, _ = A._clients()
    rows = []
    for o, cl in cal:
        f = OUT / "imbalance" / f"{o.date()}.parquet"
        if o.date() > END or not f.exists():
            continue
        sig = signals_for(o.date(), pd.read_parquet(f), cl)
        if not sig:
            continue
        t = (cl - dt.timedelta(minutes=5, seconds=29)).astimezone(dt.timezone.utc)
        q = data.get_stock_quotes(StockQuotesRequest(symbol_or_symbols=[s for s, _, _ in sig], start=t,
                                                     end=t + dt.timedelta(seconds=3), feed="sip")).df
        q = q.reset_index() if q is not None and len(q) else pd.DataFrame()
        for s, side, dev in sig:
            qs = q[(q.symbol == s) & (q.bid_price > 0) & (q.ask_price >= q.bid_price)] if len(q) else q
            if len(qs):
                r = qs.iloc[0]
                rows.append({"day": str(o.date()), "sym": s, "side": side, "dev": dev,
                             "bid": float(r.bid_price), "ask": float(r.ask_price)})
    sigs = pd.DataFrame(rows)
    syms = sorted(set(sigs.sym)) if len(sigs) else []
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from swingtrader.daily.marketdata import trade_date
    bars = data.get_stock_bars(StockBarsRequest(symbol_or_symbols=syms, timeframe=TimeFrame.Day,
                                                start=pd.Timestamp(START, tz="UTC"), end=pd.Timestamp(END + dt.timedelta(days=1), tz="UTC"),
                                                feed="sip", adjustment="raw")).df.reset_index()
    bars["day"] = trade_date(bars["timestamp"]).dt.strftime("%Y-%m-%d")
    closes = bars.set_index(["symbol", "day"])["close"]
    sigs["close"] = [float(closes.get((s, d), np.nan)) for s, d in zip(sigs.sym, sigs.day)]
    sigs.to_parquet(OUT / "signals.parquet")
    log(f"signals with entry quotes: {len(sigs)}")


def trades(sig, mult: int, long_only: bool):
    """net bp per trade at cost multiple 1 or 2."""
    s = sig.dropna(subset=["close"])
    if long_only:
        s = s[s.side > 0]
    half = (s.ask - s.bid) / 2
    mid = (s.ask + s.bid) / 2
    extra_in, extra_out = (0.5, 0.5) if mult == 1 else (1.0, 1.0)
    entry = np.where(s.side > 0, s.ask + (half if mult == 2 else 0), s.bid - (half if mult == 2 else 0))
    entry = entry * (1 + s.side * extra_in / 1e4)
    exit_ = s.close * (1 - s.side * extra_out / 1e4)
    net = s.side * (exit_ / entry - 1) * 1e4
    gross = s.side * (s.close / mid - 1) * 1e4
    return s.assign(net_bp=net.values, gross_bp=gross.values, cost_bp=(gross - net).values)


def run() -> None:
    sig = pd.read_parquet(OUT / "signals.parquet")
    cal = pickle.loads((OUT / "sessions.pkl").read_bytes())
    days = [o.date() for o, _ in cal if START <= o.date() <= END and (OUT / "imbalance" / f"{o.date()}.parquet").exists()]
    n1 = sum(1 for d in days if d < SPLIT)
    res = {"n_days": len(days), "n_h1": n1, "spent": json.loads((OUT / "spent.json").read_text())}
    for name, lo in (("Lab-AZ1", False), ("Lab-AZ2", True)):
        t1, t2 = trades(sig, 1, lo), trades(sig, 2, lo)
        r1, r2 = t1.to_dict("records"), t2.to_dict("records")
        v = {k: {h: A.summary(x, m) for h, x, m in (("all", rr, len(days)), ("h1", A.half(rr, 1), n1),
                                                     ("h2", A.half(rr, 2), len(days) - n1))}
             for k, rr in (("1x", r1), ("2x", r2))}
        v["gross_bp"] = float(t1.gross_bp.mean()) if len(t1) else None
        v["mean_spread_bp"] = float(((t1.ask - t1.bid) / ((t1.ask + t1.bid) / 2) * 1e4).mean()) if len(t1) else None
        rng = random.Random(23)
        means = [np.mean([(g if rng.random() < 0.5 else -g) - c for g, c in zip(t1.gross_bp, t1.cost_bp)])
                 for _ in range(1000)]
        v["placebo_pct"] = float(np.mean(np.array(means) < t1.net_bp.mean()) * 100) if len(t1) else None
        v["by_side"] = {int(k): float(g.net_bp.mean()) for k, g in t1.groupby("side")}
        a2 = v["2x"]
        v["verdict"] = ("PASS (to paper)" if len(t1) and a2["h1"]["mean_bp"] > 0 and a2["h2"]["mean_bp"] > 0
                        and v["1x"]["all"]["t_day"] >= 2.0 and v["placebo_pct"] >= 95 else "DEAD")
        res[name] = v
        t1.to_csv(OUT / f"trades_{name}_1x.csv", index=False)
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    {"fetch": fetch, "run": run, "prices": lambda: fetch_prices(pickle.loads((OUT / "sessions.pkl").read_bytes()))}[sys.argv[1]]()
