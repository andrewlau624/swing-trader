"""stock_noise helper: 1-minute SIP bars (adjustment='raw') for every symbol-year the stock_noise
universes need, plus daily bars raw + 'all' (split/dividend factors). Parallel and resumable.

    PYTHONPATH=. .venv/bin/python -m research.sim.stock_noise_fetch [--workers 8]

Same code path as data/research/night/fetch_m1.py (swingtrader.data._clients, StockBarsRequest,
feed='sip', one parquet per symbol-year) except adjustment='raw' and only regular-hours rows are
kept (09:30-15:59 ET) to save disk. Keys come from the environment exactly as _clients() loads them.
Output: data/research/program/stock_m1/{SYM}_{YYYY}.parquet, daily_raw.parquet, daily_all.parquet
"""
from __future__ import annotations

import os
import pickle
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd

from swingtrader.data import _clients

SP = str(__import__("pathlib").Path(__file__).resolve().parents[2]) + "/data/research/program"
OUT = f"{SP}/stock_m1"
UNIV = f"{SP}/stock_noise_univ.pkl"
END = pd.Timestamp("2026-09-21 23:00")
NMAX = 20                      # largest pre-registered N
CTRL = (41, 100, 10, 7)        # control: each January, 10 names drawn from ranks 41-100, seed 7


def control_draws(R: pd.DataFrame) -> dict:
    """month start -> the control names (drawn each January and at the first month)."""
    rng = np.random.default_rng(CTRL[3])
    out, pick = {}, None
    for d, row in R.iterrows():
        if pick is None or d.month == 1:
            pick = list(rng.choice(row.loc[CTRL[0]:CTRL[1]].values, CTRL[2], replace=False))
        out[d] = pick
    return out


def needed() -> set:
    u = pickle.load(open(UNIV, "rb"))
    R = u["rank"]
    ctrl = control_draws(R)
    need = set()
    for d, row in R.iterrows():
        names = list(row.loc[1:NMAX].values) + ctrl[d]
        for s in names:
            need.add((s, d.year))
            if d.month == 1:                  # sigma needs the previous 14 sessions
                need.add((s, d.year - 1))
    return need


def fetch_one(c, s, y):
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    p = f"{OUT}/{s.replace('.', '_')}_{y}.parquet"
    if os.path.exists(p):
        return s, y, -1
    a = pd.Timestamp(f"{y}-01-01"); b = min(pd.Timestamp(f"{y}-12-31 23:59"), END)
    for k in range(8):
        try:
            df = c.get_stock_bars(StockBarsRequest(symbol_or_symbols=[s], timeframe=TimeFrame.Minute,
                                                   start=a, end=b, feed="sip", adjustment="raw")).df
            break
        except Exception as e:  # noqa: BLE001
            print("err", s, y, str(e)[:120], flush=True); time.sleep(5 * (k + 1))
    else:
        return s, y, -2
    if len(df):
        df = df.reset_index()
        t = df.timestamp.dt.tz_convert("America/New_York")
        m = t.dt.hour * 60 + t.dt.minute - 570
        df = df[(m >= 0) & (m < 390)]
    df.to_parquet(p + ".tmp"); os.replace(p + ".tmp", p)
    return s, y, len(df)


def fetch_daily(c, syms):
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    for adj in ("raw", "all"):
        p = f"{OUT}/daily_{adj}.parquet"
        if os.path.exists(p):
            continue
        parts = []
        syms = sorted(syms)
        for i in range(0, len(syms), 50):
            df = c.get_stock_bars(StockBarsRequest(symbol_or_symbols=syms[i:i + 50], timeframe=TimeFrame.Day,
                                                   start=pd.Timestamp("2015-10-01"), end=END, feed="sip",
                                                   adjustment=adj)).df
            parts.append(df.reset_index())
        pd.concat(parts).to_parquet(p)
        print("daily", adj, flush=True)


# ------------------------------------------------------------------ quoted spreads (cost C2)
QWIN = ((11, 0), (14, 30))           # two 10-second windows per sampled session
QMONTHS = (2, 5, 8, 11)              # first session on/after the first Wednesday of these months


def quote_one(c, s, y, sessions):
    """median quoted spread (bps of mid) over the sampled windows of one symbol-year."""
    from alpaca.data.requests import StockQuotesRequest
    sp, nbbo = [], []
    for d in sessions:
        for hh, mm in QWIN:
            a = pd.Timestamp(d).tz_localize("America/New_York") + pd.Timedelta(hours=hh, minutes=mm)
            for k in range(6):
                try:
                    q = c.get_stock_quotes(StockQuotesRequest(symbol_or_symbols=[s], start=a,
                                                              end=a + pd.Timedelta(seconds=10), feed="sip",
                                                              limit=10000)).df
                    break
                except Exception as e:  # noqa: BLE001
                    print("qerr", s, y, str(e)[:80], flush=True); time.sleep(5 * (k + 1))
            else:
                continue
            if not len(q):
                continue
            b, x = q.bid_price.values, q.ask_price.values
            ok = (b > 0) & (x > b) & (x / b - 1 < 0.05)
            if ok.any():
                sp.append(float(np.median((x[ok] - b[ok]) / ((x[ok] + b[ok]) / 2) * 1e4)))
                nbbo.append(float((q.bid_exchange.values != q.ask_exchange.values).mean()))
    return s, y, (float(np.median(sp)) if sp else np.nan), len(sp), (float(np.mean(nbbo)) if nbbo else np.nan)


def quotes(workers=6):
    u = pickle.load(open(UNIV, "rb"))
    R = u["rank"]; ctrl = control_draws(R)
    need = set()
    for d, row in R.iterrows():
        for s in list(row.loc[1:NMAX].values) + ctrl[d]:
            need.add((s, d.year))
    days = pd.read_parquet(f"{OUT}/daily_raw.parquet")
    days["date"] = days.timestamp.dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
    have = days.groupby("symbol").date.apply(lambda x: pd.DatetimeIndex(sorted(x)))
    p = f"{OUT}/quote_spreads.parquet"
    done = pd.read_parquet(p) if os.path.exists(p) else pd.DataFrame(columns=["symbol", "year", "spread_bps", "n", "nbbo_share"])
    todo = [(s, y) for s, y in sorted(need) if not ((done.symbol == s) & (done.year == y)).any()]
    print("quote symbol-years", len(todo), flush=True)
    c, _ = _clients()
    rows = [tuple(r) for r in done.itertuples(index=False)]
    with ThreadPoolExecutor(workers) as ex:
        futs = []
        for s, y in todo:
            ix = have.get(s, pd.DatetimeIndex([]))
            ses = []
            for mo in QMONTHS:
                first_wed = pd.date_range(f"{y}-{mo:02d}-01", periods=7).to_series().loc[lambda z: z.dt.weekday == 2].iloc[0]
                c_ = ix[ix >= first_wed]
                if len(c_) and c_[0] < first_wed + pd.Timedelta(days=10):
                    ses.append(c_[0])
            futs.append(ex.submit(quote_one, c, s, y, ses))
        for i, f in enumerate(as_completed(futs)):
            rows.append(f.result())
            if i % 25 == 0:
                print(i, rows[-1], flush=True)
                pd.DataFrame(rows, columns=["symbol", "year", "spread_bps", "n", "nbbo_share"]).to_parquet(p)
    pd.DataFrame(rows, columns=["symbol", "year", "spread_bps", "n", "nbbo_share"]).to_parquet(p)
    print("QDONE", flush=True)


def main():
    if "--quotes" in sys.argv:
        return quotes()
    os.makedirs(OUT, exist_ok=True)
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 8
    need = sorted(needed(), key=lambda x: (x[1], x[0]))
    print("symbol-years", len(need), "symbols", len({s for s, _ in need}), flush=True)
    c, _ = _clients()
    fetch_daily(c, {s for s, _ in need})
    t0 = time.time(); done = 0
    with ThreadPoolExecutor(workers) as ex:
        futs = [ex.submit(fetch_one, c, s, y) for s, y in need]
        for f in as_completed(futs):
            s, y, n = f.result(); done += 1
            if n != -1:
                print(f"{done}/{len(need)} {s} {y} {n} {time.time() - t0:.0f}s", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
