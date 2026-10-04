"""Contest hunt T3: pre-earnings long straddle t-3 -> t-1 (round1_prose.md, N 798 -> 800).

  PYTHONPATH=. .venv/bin/python -m research.sim.contest_straddle bars     # Alpaca raw daily bars for the event names
  PYTHONPATH=. .venv/bin/python -m research.sim.contest_straddle fetch    # OPRA NBBO, 15:49-15:53 window per session
  PYTHONPATH=. .venv/bin/python -m research.sim.contest_straddle run

Per-trade gates first (judge mean return on premium > 0, bootstrap P <= 5%, select > 0, ex-best-5 > 0); the money
simulation with concurrent positions is only worth building if those pass.
"""
import os
import sys

import numpy as np
import pandas as pd
from dotenv import dotenv_values

from research.sim.contest_options import FEE, CAP_USD, ET, SELECT_END, boot_mean

EARN = "data/research/contest/earnings.parquet"
BARS = "data/research/contest/straddle_raw_bars.parquet"
OUT = "data/research/contest/opra_t3"
MIN_MCAP = 2e9
STRIKE_STEPS = (0.5, 1.0, 2.5, 5.0)
Q_MIN = 381                                   # the 15:51 record (end of minute 381 after 09:30)


def events():
    e = pd.read_parquet(EARN)
    e = e[(e.mcap >= MIN_MCAP) & (e.date >= "2023-01-01") & e.symbol.str.fullmatch(r"[A-Z]{1,5}")]
    return e.drop_duplicates(["symbol", "date"])


def fetch_bars():
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    env = dotenv_values(".env")
    c = StockHistoricalDataClient(env["ALPACA_API_KEY"], env["ALPACA_SECRET_KEY"])
    syms = sorted(events().symbol.unique()) + ["SPY"]
    out = []
    for i in range(0, len(syms), 200):
        df = c.get_stock_bars(StockBarsRequest(symbol_or_symbols=syms[i:i + 200], timeframe=TimeFrame.Day,
                                               start=pd.Timestamp("2022-12-01"), end=pd.Timestamp("2026-10-01"),
                                               feed="sip", adjustment="raw")).df.reset_index()
        out.append(df[["symbol", "timestamp", "close"]])
        print(i, flush=True)
    b = pd.concat(out)
    b["day"] = b.timestamp.dt.tz_convert(ET).dt.tz_localize(None).dt.normalize()
    b[["symbol", "day", "close"]].to_parquet(BARS)


def third_friday(y, m):
    d = pd.Timestamp(y, m, 15)
    return d + pd.Timedelta(days=(4 - d.weekday()) % 7)


def plan():
    """Event rows with entry / exit sessions, raw t-4 close, candidate expiries and strikes."""
    b = pd.read_parquet(BARS)
    cal = pd.DatetimeIndex(sorted(b[b.symbol == "SPY"].day.unique()))
    px = b.set_index(["symbol", "day"]).close
    rows = []
    for r in events().itertuples():
        t = pd.Timestamp(r.date)
        if t not in cal:
            continue
        i = cal.get_loc(t)
        if i < 4:
            continue
        d4, d3, d1 = cal[i - 4], cal[i - 3], cal[i - 1]
        p = px.get((r.symbol, d4))
        if p is None or not np.isfinite(p) or p <= 0:
            continue
        fri = t + pd.Timedelta(days=(4 - t.weekday()) % 7)
        tf = third_friday(t.year, t.month)
        if tf < t:
            tf = third_friday(t.year + (t.month == 12), t.month % 12 + 1)
        exps = sorted({fri, tf})
        ks = sorted({round(round(p / s) * s, 2) for s in STRIKE_STEPS if round(p / s) * s > 0})
        rows.append((r.symbol, t, d3, d1, p, r.mcap, exps, ks))
    return pd.DataFrame(rows, columns=["sym", "t", "d_in", "d_out", "px", "mcap", "exps", "ks"])


def osi(root, exp, cp, k):
    return f"{root:<6}{pd.Timestamp(exp):%y%m%d}{cp}{int(round(k * 1000)):08d}"


def contracts(r):
    return [osi(r.sym, e, cp, k) for e in r.exps for k in r.ks for cp in "CP"]


def fetch(dry):
    import databento as db
    client = db.Historical(dotenv_values(".env")["DATABENTO_API_KEY"])
    pl = plan()
    need = {}
    for r in pl.itertuples():
        for d in (r.d_in, r.d_out):
            need.setdefault(d, set()).update(contracts(r))
    os.makedirs(OUT, exist_ok=True)
    jobs = []
    for d, syms in sorted(need.items()):
        syms = sorted(syms)
        for j in range(0, len(syms), 1500):
            path = f"{OUT}/{d:%Y-%m-%d}_{j // 1500}.parquet"
            if os.path.exists(path):
                continue
            start = pd.Timestamp(d).tz_localize(ET) + pd.Timedelta(hours=15, minutes=49)
            jobs.append((syms[j:j + 1500], start.tz_convert("UTC").isoformat(),
                         (start + pd.Timedelta(minutes=5)).tz_convert("UTC").isoformat(), path))
    sample = jobs[:: max(1, len(jobs) // 15)]
    def cost(j):
        try:
            return client.metadata.get_cost(dataset="OPRA.PILLAR", symbols=j[0], stype_in="raw_symbol",
                                            schema="cbbo-1m", start=j[1], end=j[2])
        except Exception:                           # 422 when no symbol in the chunk resolves
            return 0.0
    est = sum(cost(j) for j in sample)
    total = est / max(len(sample), 1) * len(jobs)
    print(f"{len(pl)} events, {len(jobs)} requests, estimated ${total:.2f}", flush=True)
    if total > CAP_USD or dry:
        sys.exit(0 if dry else f"ABORT: ${total:.2f} > cap")

    def one(job):
        syms, start, end, path = job
        try:
            df = client.timeseries.get_range(dataset="OPRA.PILLAR", symbols=syms, stype_in="raw_symbol",
                                             schema="cbbo-1m", start=start, end=end).to_df().reset_index()
        except Exception as exc:                    # one bad day must not stop the pull; rerun fills gaps
            print(f"{path}: {type(exc).__name__} {str(exc)[:120]}", flush=True)
            return
        keep = [k for k in ("ts_recv", "symbol", "bid_px_00", "ask_px_00") if k in df.columns]
        df[keep].rename(columns=lambda k: k.replace("_00", "")).to_parquet(path)

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(one, jobs))
    print("done", flush=True)


def fetch_windows(need, out, hm, tag=""):
    """need: {day: set(symbols)} -> one 5-minute window per day starting at hm=(h, m) ET, chunks of 1500."""
    import databento as db
    client = db.Historical(dotenv_values(".env")["DATABENTO_API_KEY"])
    os.makedirs(out, exist_ok=True)
    jobs = []
    for d, syms in sorted(need.items()):
        syms = sorted(syms)
        for j in range(0, len(syms), 1500):
            path = f"{out}/{d:%Y-%m-%d}{tag}_{j // 1500}.parquet"
            if os.path.exists(path):
                continue
            st = pd.Timestamp(d).tz_localize(ET) + pd.Timedelta(hours=hm[0], minutes=hm[1])
            jobs.append((syms[j:j + 1500], st.tz_convert("UTC").isoformat(),
                         (st + pd.Timedelta(minutes=5)).tz_convert("UTC").isoformat(), path))

    def one(job):
        syms, start, end, path = job
        try:
            df = client.timeseries.get_range(dataset="OPRA.PILLAR", symbols=syms, stype_in="raw_symbol",
                                             schema="cbbo-1m", start=start, end=end).to_df().reset_index()
        except Exception as exc:
            print(f"{path}: {type(exc).__name__} {str(exc)[:120]}", flush=True)
            return
        keep = [k for k in ("ts_recv", "symbol", "bid_px_00", "ask_px_00") if k in df.columns]
        df[keep].rename(columns=lambda k: k.replace("_00", "")).to_parquet(path)

    print(f"{out}: {len(jobs)} windows", flush=True)
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(one, jobs))


def quotes(out=OUT, minute=Q_MIN):
    """{(symbol, day): (bid, ask)} at the last record stamped <= end of `minute` (minutes after 09:30)."""
    fs = [f"{out}/{f}" for f in os.listdir(out) if f.endswith(".parquet")]
    q = pd.concat([pd.read_parquet(f) for f in fs])
    ts = pd.to_datetime(q.ts_recv, utc=True).dt.tz_convert(ET)
    q["day"] = ts.dt.tz_localize(None).dt.normalize()
    q["sec"] = ts.dt.hour * 3600 + ts.dt.minute * 60 + ts.dt.second - 34200
    q = q[(q.sec <= (minute + 1) * 60) & (q.sec > (minute + 1) * 60 - 300)]
    q = q.sort_values("sec").groupby(["symbol", "day"]).last()
    return {k: (float(b), float(a)) for k, b, a in zip(q.index, q.bid_px, q.ask_px)}


def price(pl, Q):
    rows = []
    for r in pl.itertuples():
        best = None
        for e in r.exps:                                    # earliest listed expiry >= t
            ks = [k for k in r.ks
                  if all((Q.get((osi(r.sym, e, cp, k), r.d_in)) or (0, 0))[1] > 0 for cp in "CP")]
            if ks:
                best = (e, min(ks, key=lambda k: abs(k - r.px)))
                break
        if best is None:
            continue
        e, k = best
        legs = [osi(r.sym, e, cp, k) for cp in "CP"]
        cost = sum(Q[(s, r.d_in)][1] for s in legs)
        val = sum(max(0.0, (Q.get((s, r.d_out)) or (0.0, 0.0))[0] or 0.0) for s in legs)
        fees = FEE * 4 / 100
        rows.append((r.sym, r.t, r.d_in, r.d_out, r.mcap, e, k, r.px, cost, val, fees))
    p = pd.DataFrame(rows, columns=["sym", "t", "d_in", "d_out", "mcap", "exp", "k", "px", "cost", "val", "fees"])
    p["risk"] = p.cost + p.fees
    p["pnl"] = p.val - p.cost - p.fees
    p["r"] = p.pnl / p.risk
    return p


def main():
    pl = plan()
    p = price(pl, quotes())
    p.to_parquet("data/research/contest/t3_trades.parquet")
    print(f"events {len(pl)}, priced {len(p)}")
    for v, g in (("T3a", p), ("T3b", p[p.mcap < 10e9])):
        sel, jud = g[g.t < SELECT_END], g[g.t >= SELECT_END]
        pb = boot_mean({d: x.r.values for d, x in jud.groupby("d_out")})
        ex5 = jud.sort_values("pnl").iloc[:-5]
        print(f"{v}: sel n {len(sel)} r {sel.r.mean():+.4f} | judge n {len(jud)} r {jud.r.mean():+.4f} "
              f"median {jud.r.median():+.4f} win {(jud.pnl > 0).mean():.2f} P(<=0) {pb:.3f} "
              f"ex-best-5 r {(ex5.pnl / ex5.risk).mean():+.4f} | median premium ${100 * g.risk.median():.0f}, "
              f"share <= $115 {(100 * g.risk <= 115).mean():.2f}, <= $500 {(100 * g.risk <= 500).mean():.2f}")
        print("   by year:", g.groupby(g.t.dt.year).r.mean().round(4).to_dict())

# ------------------------------------------------------------------ T5: short earnings iron fly t-1 -> t+1
OUT5 = "data/research/contest/opra_t5"


def grid(p):
    return sorted({round(round(p / st) * st, 2) for st in STRIKE_STEPS if round(p / st) * st > 0})


def plan5():
    b = pd.read_parquet(BARS)
    cal = pd.DatetimeIndex(sorted(b[b.symbol == "SPY"].day.unique()))
    px = b.set_index(["symbol", "day"]).close
    rows = []
    for r in events().itertuples():
        t = pd.Timestamp(r.date)
        if t not in cal:
            continue
        i = cal.get_loc(t)
        if i < 2 or i + 1 >= len(cal):
            continue
        p = px.get((r.symbol, cal[i - 2]))
        if p is None or not np.isfinite(p) or p <= 0:
            continue
        t1 = cal[i + 1]
        fri = t1 + pd.Timedelta(days=(4 - t1.weekday()) % 7)
        tf = third_friday(t1.year, t1.month)
        if tf < t1:
            tf = third_friday(t1.year + (t1.month == 12), t1.month % 12 + 1)
        rows.append((r.symbol, t, cal[i - 1], t1, p, r.mcap, sorted({fri, tf}), grid(p), grid(p * 1.1), grid(p * 0.9)))
    return pd.DataFrame(rows, columns=["sym", "t", "d_in", "d_out", "px", "mcap", "exps", "ks", "kh", "kl"])


def fetch5():
    need = {}
    for r in plan5().itertuples():
        syms = [osi(r.sym, e, "C", k) for e in r.exps for k in r.ks + r.kh] + \
               [osi(r.sym, e, "P", k) for e in r.exps for k in r.ks + r.kl]
        for d in (r.d_in, r.d_out):
            need.setdefault(d, set()).update(syms)
    fetch_windows(need, OUT5, (15, 49))


def main5():
    Q = quotes(OUT5, Q_MIN)
    ok = lambda s, d: (Q.get((s, d)) or (0, 0))[1] > 0
    rows = []
    for r in plan5().itertuples():
        for e in r.exps:
            ks = [k for k in r.ks if ok(osi(r.sym, e, "C", k), r.d_in) and ok(osi(r.sym, e, "P", k), r.d_in)]
            kh = [k for k in r.kh if ok(osi(r.sym, e, "C", k), r.d_in)]
            kl = [k for k in r.kl if ok(osi(r.sym, e, "P", k), r.d_in)]
            if ks and kh and kl:
                k = min(ks, key=lambda x: abs(x - r.px))
                hi = min(kh, key=lambda x: abs(x - r.px * 1.1))
                lo = min(kl, key=lambda x: abs(x - r.px * 0.9))
                if not (lo < k < hi):
                    break
                legs = [(-1, osi(r.sym, e, "C", k)), (-1, osi(r.sym, e, "P", k)),
                        (1, osi(r.sym, e, "C", hi)), (1, osi(r.sym, e, "P", lo))]
                qi = [Q[(x, r.d_in)] for _, x in legs]
                qo = [Q.get((x, r.d_out)) for _, x in legs]
                if any(not (q[0] > 0) for (sg, _), q in zip(legs, qi) if sg < 0):
                    break                                    # no bid to sell into at entry (NaN/0): no trade
                if any(q is None or not (q[1] > 0) for (sg, _), q in zip(legs, qo) if sg < 0):
                    break                                    # cannot price the buy-back: skip, logged as unpriced
                cost = sum(a if sg > 0 else -b for (sg, _), (b, a) in zip(legs, qi))
                bid = lambda q: q[0] if q and q[0] > 0 else 0.0          # missing/NaN bid on a long wing = 0
                val = sum(bid(q) if sg > 0 else -q[1] for (sg, _), q in zip(legs, qo))
                fees = FEE * 8 / 100
                rows.append((r.sym, r.t, r.d_in, r.d_out, r.mcap, cost, val, fees,
                             max(hi - k, k - lo) + cost + fees))
                break
    p = pd.DataFrame(rows, columns=["sym", "t", "d_in", "d_out", "mcap", "cost", "val", "fees", "risk"])
    p["pnl"] = p.val - p.cost - p.fees
    p["r"] = p.pnl / p.risk
    p.to_parquet("data/research/contest/t5_trades.parquet")
    summary("T5 short earnings fly", p)


def summary(v, g, key="t"):
    sel, jud = g[g[key] < SELECT_END], g[g[key] >= SELECT_END]
    pb = boot_mean({d: x.r.values for d, x in jud.groupby("d_out")}) if len(jud) else 1.0
    ex5 = jud.sort_values("pnl").iloc[:-5]
    print(f"{v}: sel n {len(sel)} r {sel.r.mean():+.4f} | judge n {len(jud)} r {jud.r.mean():+.4f} "
          f"median {jud.r.median():+.4f} win {(jud.pnl > 0).mean():.2f} P(<=0) {pb:.3f} "
          f"ex-best-5 r {(ex5.pnl / ex5.risk).mean():+.4f} | median risk ${100 * g.risk.median():.0f}, "
          f"share <= $115 {(100 * g.risk <= 115).mean():.2f}, <= $500 {(100 * g.risk <= 500).mean():.2f}")
    print("   by year:", g.groupby(g[key].dt.year).r.mean().round(4).to_dict())


# ------------------------------------------------------------------ T7: EV2-big insider buy -> long call, open -> close
OUT7 = "data/research/contest/opra_t7"


def plan7():
    from research.sim import goal_g12
    X = goal_g12.buys()
    I = X[X.insider & (X.usd > 0)].groupby(["sym", "fd"]).usd.sum().reset_index()
    allf = X[["sym", "fd"]].drop_duplicates().sort_values(["sym", "fd"])
    prev = {k: g.fd.values for k, g in allf.groupby("sym")}
    first = []
    for sm, fd in zip(I.sym, I.fd):
        d = prev[sm]
        j = np.searchsorted(d, np.datetime64(fd)) - 1
        first.append(j < 0 or (fd - pd.Timestamp(d[j])).days > 730)
    I = I[np.array(first) & (I.usd >= 5e5) & (I.fd >= "2022-12-20") & I.sym.str.fullmatch(r"[A-Z]{1,5}")]
    bars = __import__("research.sim.event_fetch", fromlist=["raw_bars"]).raw_bars(sorted(I.sym.unique()))
    rows = []
    for r in I.itertuples():
        b = bars.get(r.sym)
        if b is None or not len(b):
            continue
        idx = pd.DatetimeIndex(b.sort_index().index)
        i = idx.searchsorted(r.fd + pd.Timedelta(days=1))
        if i < 1 or i >= len(idx) or (idx[i] - r.fd).days > 7:
            continue
        d = idx[i]
        p = float(b.sort_index().close.iloc[i - 1])
        if p < 5:
            continue
        e0 = d + pd.Timedelta(days=5)
        fri = e0 + pd.Timedelta(days=(4 - e0.weekday()) % 7)
        tf = third_friday(e0.year, e0.month)
        if tf < e0:
            tf = third_friday(e0.year + (e0.month == 12), e0.month % 12 + 1)
        rows.append((r.sym, d, d, p, sorted({fri, tf}), grid(p)))
    return pd.DataFrame(rows, columns=["sym", "t", "d_out", "px", "exps", "ks"]).drop_duplicates(["sym", "t"])


def fetch7():
    pl = plan7()
    pl.to_parquet("data/research/contest/t7_plan.parquet")
    need = {}
    for r in pl.itertuples():
        need.setdefault(r.t, set()).update(osi(r.sym, e, "C", k) for e in r.exps for k in r.ks)
    fetch_windows(need, OUT7, (9, 33), "a")
    fetch_windows(need, OUT7, (15, 49), "b")


def main7():
    pl = pd.read_parquet("data/research/contest/t7_plan.parquet")
    Qa, Qb = quotes(OUT7, 5), quotes(OUT7, Q_MIN)
    rows = []
    for r in pl.itertuples():
        for e in r.exps:
            ks = [k for k in r.ks if (Qa.get((osi(r.sym, e, "C", k), r.t)) or (0, 0))[1] > 0]
            if not ks:
                continue
            s = osi(r.sym, e, "C", min(ks, key=lambda k: abs(k - r.px)))
            cost = Qa[(s, r.t)][1]
            val = (Qb.get((s, r.t)) or (0.0, 0.0))[0]
            rows.append((r.sym, r.t, r.t, cost, val, FEE * 2 / 100))
            break
    p = pd.DataFrame(rows, columns=["sym", "t", "d_out", "cost", "val", "fees"])
    p["risk"] = p.cost + p.fees
    p["pnl"] = p.val - p.cost - p.fees
    p["r"] = p.pnl / p.risk
    p.to_parquet("data/research/contest/t7_trades.parquet")
    print(f"T7 events {len(pl)}, priced {len(p)}")
    summary("T7 EV2-big call", p)



if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "bars":
        fetch_bars()
    elif cmd == "fetch":
        fetch("--dry" in sys.argv)
    elif cmd in ("fetch5", "run5", "fetch7", "run7"):
        {"fetch5": fetch5, "run5": main5, "fetch7": fetch7, "run7": main7}[cmd]()
    else:
        main()
