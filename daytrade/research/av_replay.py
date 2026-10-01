"""Study Lab-AV: Study Lab-AT's opening imbalance (daytrade/plans/open_imbalance.md) on historical SIP ticks,
QQQ and SPY, 2022-01-03 .. 2026-09-30 (round1_prose.md Lab Round 20). The lab's OpenImbalance strategy code
runs through the lab's engine.

Every read is inside the regular session (from the calendar): SIP NBBO and trades 09:30:00-09:34:59,
SIP NBBO 09:35:00-09:35:05 and 10:05:00-10:05:05 (the fills), SIP minute bars 09:35-10:06 (the stop).
Quotes in the window are thinned to the last quote of each second: the strategy samples the last
known quote once per second, so this changes nothing it computes.

  python -m daytrade.research.av_replay fetch    # resumable, ~3 h
  python -m daytrade.research.av_replay run
"""
from __future__ import annotations

import datetime as dt
import json
import pickle
import random
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

from ..engine import Engine
from ..events import Bar, Quote, Trade
from ..fills import SimBroker
from ..session import session_times
from ..settings import DATA, Limits
from ..strategies.open_imbalance import OpenImbalance
from . import as_replay as A

OUT = DATA / "research" / "av"
SYMS = ("QQQ", "SPY")
START, END, SPLIT = A.START, A.END, A.SPLIT
log = A.log


def _get(kind, data, start, end):
    from alpaca.data.requests import StockBarsRequest, StockQuotesRequest, StockTradesRequest
    from alpaca.data.timeframe import TimeFrame
    import time
    for attempt in range(5):
        try:
            if kind == "q":
                r = data.get_stock_quotes(StockQuotesRequest(symbol_or_symbols=list(SYMS), start=start, end=end, feed="sip"))
            elif kind == "t":
                r = data.get_stock_trades(StockTradesRequest(symbol_or_symbols=list(SYMS), start=start, end=end, feed="sip"))
            else:
                r = data.get_stock_bars(StockBarsRequest(symbol_or_symbols=list(SYMS), timeframe=TimeFrame.Minute,
                                                         start=start, end=end, feed="sip", adjustment="raw"))
            df = r.df
            return df.reset_index() if df is not None and len(df) else pd.DataFrame()
        except Exception as exc:
            log(f"{kind} retry {attempt}: {type(exc).__name__} {str(exc)[:80]}"); time.sleep(5 * (attempt + 1))
    raise RuntimeError("tick data unavailable")


def fetch_day(o, c):
    data, _ = A._clients()
    U = dt.timezone.utc
    t0, t1 = o.astimezone(U), (o + dt.timedelta(minutes=5)).astimezone(U)
    q = _get("q", data, t0, t1)
    if len(q):
        q["sec"] = q["timestamp"].dt.floor("s")
        q = q.sort_values("timestamp").groupby(["symbol", "sec"]).tail(1)
    tr = _get("t", data, t0, t1)
    fills = pd.concat([_get("q", data, (o + dt.timedelta(minutes=m)).astimezone(U),
                            (o + dt.timedelta(minutes=m, seconds=5)).astimezone(U)) for m in (5, 35)])
    bars = _get("b", data, (o + dt.timedelta(minutes=5)).astimezone(U), (o + dt.timedelta(minutes=36)).astimezone(U))
    keepq = ["symbol", "timestamp", "bid_price", "ask_price", "bid_size", "ask_size"]
    return {"q": q[keepq] if len(q) else q, "t": tr[["symbol", "timestamp", "price", "size"]] if len(tr) else tr,
            "f": fills[keepq] if len(fills) else fills, "b": bars, "open": o, "close": c}


def fetch() -> None:
    from swingtrader.daily.brokers import regular_sessions
    cal = regular_sessions(START, END + dt.timedelta(days=7))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sessions.pkl").write_bytes(pickle.dumps(cal))
    (OUT / "days").mkdir(exist_ok=True)
    todo = [(o, c) for o, c in cal if o.date() <= END and not (OUT / "days" / f"{o.date()}.pkl").exists()]

    def one(oc):
        o, c = oc
        rec = fetch_day(o, c)
        (OUT / "days" / f"{o.date()}.pkl").write_bytes(pickle.dumps(rec))
        return o.date(), len(rec["q"]), len(rec["t"])

    with ThreadPoolExecutor(3) as ex:
        for i, (day, nq, nt) in enumerate(ex.map(one, todo)):
            if i % 20 == 0:
                log(f"{day}: {nq} quote-seconds, {nt} trades ({i + 1}/{len(todo)})")


# ------------------------------------------------------------------ replay
def events(rec):
    from zoneinfo import ZoneInfo
    tz = ZoneInfo(A.ET)
    ev = []
    for df in (rec["q"], rec["f"]):
        for r in df.itertuples(index=False):
            if r.bid_price > 0 and r.ask_price >= r.bid_price:
                ev.append(Quote(r.timestamp.tz_convert(tz).to_pydatetime(), r.symbol, float(r.bid_price),
                                float(r.ask_price), float(r.bid_size), float(r.ask_size)))
    for r in rec["t"].itertuples(index=False):
        ev.append(Trade(r.timestamp.tz_convert(tz).to_pydatetime(), r.symbol, float(r.price), float(r.size)))
    for r in rec["b"].itertuples(index=False):
        s = r.timestamp.tz_convert(tz).to_pydatetime()
        ev.append(Bar(s + dt.timedelta(minutes=1), r.symbol, float(r.open), float(r.high), float(r.low),
                      float(r.close), float(r.volume), s))
    ev.sort(key=lambda e: (e.ts, 0 if isinstance(e, Bar) else 1))
    return ev


class Sim2x(SimBroker):
    """2x costs: 1.0bp/side plus the half-spread again on quote fills; 2bp on bar (stop) fills."""
    def _try(self, o, ev):
        f = super()._try(o, ev)
        if f is not None and isinstance(ev, Quote) and o.kind == "market":
            half = (ev.ask - ev.bid) / 2
            f.price = f.price + half if o.side == "buy" else f.price - half
        return f


def mid_at(rec, sym, minute):
    f = rec["f"]
    if not len(f):
        return None
    t = f[(f.symbol == sym)]
    t = t[t.timestamp >= (rec["open"] + dt.timedelta(minutes=minute, seconds=1)).astimezone(dt.timezone.utc)]
    if not len(t):
        return None
    r = t.iloc[0]
    return (r.bid_price + r.ask_price) / 2, (r.ask_price - r.bid_price) / 2


def run() -> None:
    cal = pickle.loads((OUT / "sessions.pkl").read_bytes())
    trades = {"1x": [], "2x": []}
    flips, n1, n = [], 0, 0
    for o, c in cal:
        f = OUT / "days" / f"{o.date()}.pkl"
        if not (START <= o.date() <= END) or not f.exists():
            continue
        rec = pickle.loads(f.read_bytes())
        st = session_times(o.date(), cal, Limits())
        ev = events(rec)
        n += 1; n1 += o.date() < SPLIT
        for label, broker in (("1x", SimBroker(latency_s=1, cost_bp=1.0, extra_bp=0.5)),
                              ("2x", Sim2x(latency_s=1, cost_bp=2.0, extra_bp=1.0))):
            eng = Engine([OpenImbalance()], broker, equity=1e7, session=st,
                         limits=Limits(max_positions=99, daily_loss_pct=1e9), halt_path=OUT / "HALT-never")
            eng.run(ev)
            trades[label] += eng.trades
        for t in trades["1x"][-2:]:
            if t["day"] != str(o.date()):
                continue
            a, b = mid_at(rec, t["sym"], 5), mid_at(rec, t["sym"], 35)
            if a and b:
                gross = (b[0] / a[0] - 1) * 1e4 * (1 if t["side"] == "long" else -1)
                flips.append((t["net_bp"], gross, gross - t["net_bp"]))   # (net, gross mid-to-mid, cost)
        if n % 100 == 0:
            log(f"{o.date()}: {n} days, {len(trades['1x'])} trades")
    res = {}
    for label, tr in trades.items():
        res[label] = {"all": A.summary(tr, n), "h1": A.summary(A.half(tr, 1), n1), "h2": A.summary(A.half(tr, 2), n - n1),
                      "by_sym": {s: float(np.mean([t["net_bp"] for t in tr if t["sym"] == s] or [np.nan])) for s in SYMS},
                      "by_side": {s: float(np.mean([t["net_bp"] for t in tr if t["side"] == s] or [np.nan]))
                                  for s in ("long", "short")}}
    rng = random.Random(5)
    actual = float(np.mean([x[0] for x in flips])) if flips else float("nan")
    means = [np.mean([(g if rng.random() < 0.5 else -g) - cst for _, g, cst in flips]) for _ in range(1000)]
    res["placebo_pct"] = float(np.mean(np.array(means) < actual) * 100) if flips else float("nan")
    res["placebo_mean_bp"] = float(np.mean(means)) if flips else float("nan")
    res["gross_mid_bp"] = float(np.mean([g for _, g, _ in flips])) if flips else float("nan")
    a2 = res["2x"]
    res["verdict"] = ("PASS (to paper)" if a2["h1"]["mean_bp"] > 0 and a2["h2"]["mean_bp"] > 0
                      and res["1x"]["all"]["t_day"] >= 2.0 and res["placebo_pct"] >= 95 else "DEAD")
    res["n_days"], res["n_h1"] = n, n1
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str))
    pd.DataFrame(trades["1x"]).to_csv(OUT / "trades_1x.csv", index=False)
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    {"fetch": fetch, "run": run}[sys.argv[1]]()
