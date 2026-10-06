"""PHASE 1 (exact): the live night leg at 2016-2020, reconstructed at 15:40.

Daily bars are only a proxy for the live rule, which decides at 15:40 ET on:
  day_ret = price(15:40) / prev_close - 1 <= -8%,  IBS(15:40) = (p-L)/(H-L) < 0.10
  (H/L = the day's high/low THROUGH 15:40), price in [$5,$2000], vol20>=60%, ADV>=$10M;
then buys the 16:00 close auction and sells the next 09:30 open.

This uses pre-2021 Alpaca SIP MINUTE bars (available, verified) for the candidate
(sym, date) only (signal-driven: candidates = days whose low touched -8%, a superset).
Daily bars come from the separate `bars_pre2021` cache (adjustment='all'); the raw
minute prices are mapped onto the adjusted basis with the day's adjustment factor so
splits/dividends cannot fake the day return.

Universe = the swing cache (incl. inactive names) -> survivorship-limited but not
fully-removed dead tickers. Outcome = adjusted next_open / adjusted close - 1.

Run: PYTHONPATH=. .venv/bin/python research/sim/night_exact_pre2021.py [MAX_DATES]
Writes data/research/program/night_exact_pre2021.parquet
"""
from __future__ import annotations

import glob
import os
import pathlib
import sys

import numpy as np
import pandas as pd

from swingtrader.config import require_alpaca_keys

ROOT = pathlib.Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "cache" / "bars_pre2021"
OUT = ROOT / "data/research/program/night_exact_pre2021.parquet"
START, END = pd.Timestamp("2016-01-01"), pd.Timestamp("2020-12-31")


def daily_candidates():
    """(sym, date, prev_close, adj_close, next_open, vol20, adv) for down-touch days."""
    rows = []
    for f in glob.glob(str(CACHE / "*.parquet")):
        sym = os.path.basename(f)[:-8]
        try:
            d = pd.read_parquet(f)
        except Exception:
            continue
        if d is None or len(d) < 80:
            continue
        d = d[(d.index >= START) & (d.index <= END)]
        c, h, l, v = d["close"], d["high"], d["low"], d["volume"]
        pc = c.shift(1)
        ret = c / pc - 1
        adv = (c * v).rolling(20).mean().shift(1)
        vol = (ret.rolling(20).std().shift(1) * np.sqrt(252))
        nxt = d["open"].shift(-1)
        m = ((l / pc - 1) <= -0.08) & (pc >= 5) & (pc <= 2000) & (vol >= 0.60) & (adv >= 1e7) & nxt.notna()
        if not m.any():
            continue
        s = pd.DataFrame({"sym": sym, "date": d.index[m], "prev_close": pc[m],
                          "adj_close": c[m], "next_open": nxt[m], "vol20": vol[m], "adv": adv[m]})
        rows.append(s)
    return pd.concat(rows) if rows else pd.DataFrame()


def fetch_minutes(dates_syms):
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    k, sec = require_alpaca_keys()
    cli = StockHistoricalDataClient(k, sec)
    out = {}
    for dt, syms in dates_syms:
        try:
            df = cli.get_stock_bars(StockBarsRequest(
                symbol_or_symbols=list(syms), timeframe=TimeFrame.Minute,
                start=pd.Timestamp(dt, tz="America/New_York").tz_convert("UTC").to_pydatetime(),
                end=pd.Timestamp(dt + pd.Timedelta(days=1), tz="America/New_York").tz_convert("UTC").to_pydatetime(),
                feed="sip")).df
        except Exception as exc:  # noqa: BLE001
            print(f"  min {dt} err {str(exc)[:70]}", flush=True)
            continue
        if df is None or df.empty:
            continue
        df = df.reset_index()
        df["ts"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert("America/New_York")
        out[dt] = df
    return out


def main():
    max_dates = int(sys.argv[1]) if len(sys.argv) > 1 else None
    cand = daily_candidates()
    print(f"candidate day-touches: {len(cand):,} over {cand.date.nunique()} dates", flush=True)
    cand = cand.sort_values("date")
    by_date = list(cand.groupby("date"))
    if max_dates:
        by_date = by_date[:max_dates]
    # fetch minutes in batches of dates
    results = []
    for di in range(0, len(by_date), 25):
        chunk = by_date[di:di + 25]
        ds = [(dt, g.sym.tolist()) for dt, g in chunk]
        mins = fetch_minutes(ds)
        for dt, g in chunk:
            m = mins.get(dt)
            if m is None:
                continue
            m = m[m.ts.dt.time <= pd.Timestamp("15:40").time()]
            if m.empty:
                continue
            agg = m.groupby("symbol").agg(p50=("close", "last"), H50=("high", "max"), L50=("low", "min"),
                                          raw_close=("close", "last"))
            gg = g.set_index("sym").join(agg, how="inner")
            if gg.empty:
                continue
            factor = gg["adj_close"] / gg["raw_close"]
            p50 = gg["p50"] * factor
            day_ret = p50 / gg["prev_close"] - 1
            rng = (gg["H50"] - gg["L50"]) * factor
            ibs = ((gg["p50"] - gg["L50"]) / (gg["H50"] - gg["L50"])).where(rng > 0)
            sel = (day_ret <= -0.08) & (ibs < 0.10) & (p50 >= 5) & (p50 <= 2000)
            if sel.any():
                r = pd.DataFrame({"sym": gg.index[sel], "date": dt, "day_ret": day_ret[sel],
                                  "ibs": ibs[sel], "adv": gg["adv"][sel],
                                  "ret": (gg["next_open"][sel] / gg["adj_close"][sel] - 1)})
                results.append(r)
        if di % 250 == 0:
            print(f"  dates {di}/{len(by_date)}  events so far {sum(len(x) for x in results):,}", flush=True)
    if not results:
        print("no events"); return
    R = pd.concat(results).drop_duplicates(["sym", "date"])
    R = R[R["ret"].abs() < 0.6].sort_values("date").set_index("date")
    R.to_parquet(OUT)
    print(report(R))
    print(f"wrote {len(R)} to {OUT}")


def report(r):
    b = 1e4
    lines = ["EXACT night leg (15:40 decision) on 2016-2020 pre-2021 minute data",
             "universe = swing cache (incl inactive) -> survivorship-limited", ""]
    for lab, lo, hi in [("2016-18", "2016", "2018"), ("2016-19 ex2020", "2016", "2019"),
                        ("2020", "2020", "2020"), ("ALL 2016-20", "2016", "2020")]:
        x = r.loc[lo:hi, "ret"].sort_values()
        if len(x) < 20:
            lines.append(f"{lab}: n={len(x)}"); continue
        t = x.mean() / x.std() * np.sqrt(len(x))
        lines.append(f"{lab}: n={len(x):4d} mean={x.mean()*b:6.1f}bp med={x.median()*b:6.1f} "
                     f"t={t:5.2f} hit={(x>0).mean()*100:3.0f}% ex5={x.iloc[:-5].mean()*b:6.1f}")
    lines += ["", "by year:"]
    for y, g in r.groupby(r.index.year):
        if len(g) >= 20:
            x = g["ret"]
            lines.append(f"  {y}: n={len(g):4d} mean={x.mean()*b:6.1f} med={x.median()*b:6.1f} "
                         f"hit={(x>0).mean()*100:3.0f}%")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
