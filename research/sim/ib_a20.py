"""Index-beat A20: sell night picks in the pre-market instead of the open auction (explore on select nights only).

    PYTHONPATH=. .venv/bin/python -m research.sim.ib_a20 fetch [part]     # Alpaca SIP minutes 04:00-09:29, raw
    PYTHONPATH=. .venv/bin/python -m research.sim.ib_a20 explore
Spec: research/drafts/index_beat_log.md (A20), written before any pre-market bar was fetched.
"""
from __future__ import annotations

import os
import pathlib
import pickle
import sys
import time

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
PM = ROOT / "data/research/program/ib/pm1"
SELECT = (pd.Timestamp("2021-01-01"), pd.Timestamp("2023-12-31"))


def pool():
    rp = pickle.load(open(ROOT / "data/research/program/cache_rawprice.pkl", "rb"))
    return rp["raw"][0.10]


def next_day(N):
    from research.sim import data as D
    idx = D.etf()["close"].index
    return {d: idx[i + 1] for i, d in enumerate(idx[:-1])}


def fetch(part=0, nparts=2):
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from swingtrader.daily.marketdata import _clients
    c, _ = _clients()
    N = pool(); nx = next_day(N)
    PM.mkdir(parents=True, exist_ok=True)
    days = [d for d in sorted(N) if SELECT[0] <= d <= SELECT[1] and d in nx][part::nparts]
    for d in days:
        p = PM / f"{d.date()}.parquet"
        if p.exists():
            continue
        e = nx[d]
        st = (e + pd.Timedelta(hours=4)).tz_localize("America/New_York").tz_convert("UTC")
        en = (e + pd.Timedelta(hours=9, minutes=30)).tz_localize("America/New_York").tz_convert("UTC")
        syms = sorted(set(N[d].syms))
        df = None
        for _ in range(3):
            try:
                df = c.get_stock_bars(StockBarsRequest(symbol_or_symbols=syms, timeframe=TimeFrame.Minute, start=st,
                                                       end=en, feed="sip", adjustment="raw")).df
                break
            except Exception as exc:
                print("err", d.date(), str(exc)[:80], flush=True); time.sleep(5)
        (df.reset_index() if df is not None and len(df) else pd.DataFrame(columns=["symbol", "timestamp"])).to_parquet(p)
    print("DONE", part, flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "fetch":
        fetch(int(sys.argv[2]) if len(sys.argv) > 2 else 0)


def explore():
    from swingtrader.daily import signals as sg
    from research.sim.taxable_frontier import nw_t
    N = pool()
    rows = []
    for d in sorted(N):
        if not (SELECT[0] <= d <= SELECT[1]):
            continue
        p = PM / f"{d.date()}.parquet"
        if not p.exists():
            continue
        m = pd.read_parquet(p)
        nd = N[d]
        w = sg.night_tilt(nd.vol20, nd.day_ret, 0.25) * nd.frac
        if len(m):
            m["et"] = pd.to_datetime(m.timestamp).dt.tz_convert("America/New_York")
            m["hm"] = m.et.dt.hour * 100 + m.et.dt.minute
            m = m[m.hm <= 929]                       # pre-market only: never the 09:30 bar (the open cross)
            g = dict(tuple(m.groupby("symbol")))
        else:
            g = {}
        for j, s in enumerate(nd.syms):
            c, r = float(nd.close[j]), float(nd.ret[j])
            if not (np.isfinite(c) and np.isfinite(r) and c > 0):
                continue
            o = 1 + r
            x = g.get(s)
            v1 = v2 = 0.0
            f1 = f2 = False
            pmv = 0.0
            if x is not None and len(x):
                pmv = float((x.volume * x.vwap).sum())
                late = x[(x.hm >= 900) & (x.hm <= 928)]
                dv = float((late.volume * late.vwap).sum())
                if dv >= 1000:
                    vw = float((late.vwap * late.volume).sum() / late.volume.sum())
                    v1 = (vw / c * (1 - 10e-4)) / o - 1; f1 = True
                L = c * 1.03
                hit = x[x.high >= L + 0.01]
                if len(hit):
                    t0 = hit.hm.iloc[0]
                    after = x[x.hm >= t0]
                    if float((after.volume * after.vwap).sum()) >= 1000:
                        v2 = (L / c) / o - 1; f2 = True
            rows.append((d, s, w[j], r, v1, f1, v2, f2, pmv))
    T = pd.DataFrame(rows, columns=["d", "sym", "w", "ret", "v1", "f1", "v2", "f2", "pm_dollars"])
    print(f"select nights {T.d.nunique()}, picks {len(T)}; pre-market $ traded per pick: median ${T.pm_dollars.median():,.0f}, "
          f"share with >= $1k {(T.pm_dollars >= 1000).mean():.0%}")
    for v in ("v1", "v2"):
        f = "f" + v[1]
        bp = T[v] * 1e4
        night = T.groupby("d").apply(lambda g: (g[v] * g.w).sum() / g.w.sum() * 1e4)
        ex5 = night.drop(night.nlargest(5).index)
        print(f"{v.upper()}: filled {T[f].mean():.0%} of picks; improvement vs the open, equal-weight {bp.mean():+.1f}bp/pick "
              f"(filled only {bp[T[f]].mean():+.1f}bp); book-weighted per night {night.mean():+.1f}bp, NW t {nw_t(night / 1e4):+.2f}, "
              f"ex-top-5 nights {ex5.mean():+.1f}bp; by year " + " ".join(f"{y}: {gg.mean():+.1f}" for y, gg in night.groupby(night.index.year)))
    T.to_pickle(ROOT / "data/research/program/ib/a20_trades.pkl")


if __name__ == "__main__" and sys.argv[1] == "explore":
    explore()
