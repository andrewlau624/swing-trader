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
    return f"{root:<6}{exp:%y%m%d}{cp}{int(round(k * 1000)):08d}"


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


def quotes():
    """{(symbol, day): (bid, ask)} at the 15:51 record (last record stamped <= end of minute Q_MIN)."""
    fs = [f"{OUT}/{f}" for f in os.listdir(OUT) if f.endswith(".parquet")]
    q = pd.concat([pd.read_parquet(f) for f in fs])
    ts = pd.to_datetime(q.ts_recv, utc=True).dt.tz_convert(ET)
    q["day"] = ts.dt.tz_localize(None).dt.normalize()
    q["sec"] = ts.dt.hour * 3600 + ts.dt.minute * 60 + ts.dt.second - 34200
    q = q[q.sec <= (Q_MIN + 1) * 60].sort_values("sec").groupby(["symbol", "day"]).last()
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


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "bars":
        fetch_bars()
    elif cmd == "fetch":
        fetch("--dry" in sys.argv)
    else:
        main()
