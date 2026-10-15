"""Study SSR-TD (N 876): Rule 201 trigger-day intraday path, long from the first -k% minute to the close.

    PYTHONPATH=. .venv/bin/python -m research.sim.ssr_td fetch    # raw SIP minute bars, resumable
    PYTHONPATH=. .venv/bin/python -m research.sim.ssr_td          # judge -> ssr_td_out.txt

Events: Sharadar common stock-days with prior raw close >= $5, 20d ADV >= $5M, day low <= -7% (no T+1 condition).
Minute bars: Alpaca SIP adjustment=raw, one parquet per day in data/research/ssr/m1/. A ticker is kept only if its
last regular-hours minute close is within 1% of Sharadar's raw close that day (guards renamed/reused tickers).
"""
from __future__ import annotations

import pathlib
import sys
import time

import numpy as np
import pandas as pd

from . import ssr_rd as m

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data/research/ssr"
M1 = D / "m1"
OUT = pathlib.Path(__file__).with_name("ssr_td_out.txt")
KS = [-0.08, -0.09, -0.10, -0.11, -0.12]
COST = 0.0010


def events(start="2021-01-01", end="2026-09-30") -> pd.DataFrame:
    b = m.load()
    g = b.groupby("ticker", sort=False)
    b["L"] = b.low / g.close.shift(1) - 1
    b["praw"] = g.closeunadj.shift(1)
    b["adv"] = (b.close * b.volume).groupby(b.ticker).transform(
        lambda s: s.shift(1).rolling(20, min_periods=15).mean())
    e = b[(b.praw >= 5) & (b.adv >= 5e6) & (b.L <= -0.07) & (b.date >= start) & (b.date <= end)
          & b.ticker.str.fullmatch(r"[A-Z]{1,5}")]
    return e[["ticker", "date", "L", "adv", "praw", "closeunadj"]].reset_index(drop=True)


def fetch(start="2021-01-01", end="2026-09-30", tag="events", w=0, W=1):
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from swingtrader.data import _clients
    M1.mkdir(parents=True, exist_ok=True)
    ef = D / f"td_{tag}.parquet"
    if not ef.exists():
        events(start, end).to_parquet(ef)
    e = pd.read_parquet(ef)
    c, _ = _clients()
    t0 = time.time()
    grp = list(e.groupby("date"))
    for i, (d, x) in enumerate(grp):
        p = M1 / f"{pd.Timestamp(d).date()}.parquet"
        if p.exists() or i % W != w:
            continue
        syms = sorted(set(x.ticker) | {"SPY"})
        s = (pd.Timestamp(d) + pd.Timedelta(hours=9, minutes=30)).tz_localize("America/New_York").tz_convert("UTC")
        f = (pd.Timestamp(d) + pd.Timedelta(hours=16)).tz_localize("America/New_York").tz_convert("UTC")
        df = None
        for a in range(5):
            try:
                df = c.get_stock_bars(StockBarsRequest(symbol_or_symbols=syms, timeframe=TimeFrame.Minute, start=s,
                                                       end=f, feed="sip", adjustment="raw")).df
                break
            except Exception as ex:  # noqa: BLE001
                print("err", d, str(ex)[:120], flush=True)
                time.sleep(5 * (a + 1))
        if df is not None and len(df):
            df.reset_index().to_parquet(p)
        if i % 50 == 0:
            print(f"{i}/{len(grp)} {time.time()-t0:.0f}s", flush=True)
    print("DONE", len(grp), flush=True)


def rows(tag="events") -> pd.DataFrame:
    """One row per (event, k): trigger minute, entry VWAP, exit 15:59 close, SPY same window, +30/+60m."""
    e = pd.read_parquet(D / f"td_{tag}.parquet")
    out, bad = [], 0
    for d, x in e.groupby("date"):
        p = M1 / f"{pd.Timestamp(d).date()}.parquet"
        if not p.exists():
            continue
        b = pd.read_parquet(p)
        b["ts"] = pd.to_datetime(b.timestamp).dt.tz_convert("America/New_York")
        b["mi"] = (b.ts.dt.hour - 9) * 60 + b.ts.dt.minute - 30
        b = b[(b.mi >= 0) & (b.mi < 390)]
        if "SPY" not in set(b.symbol):
            continue
        spy = b[b.symbol == "SPY"].set_index("mi").close.reindex(range(390)).ffill()
        for r in x.itertuples():
            s = b[b.symbol == r.ticker].set_index("mi").sort_index()
            if len(s) < 30 or 389 - s.index.max() > 5 or abs(s.close.iloc[-1] / r.closeunadj - 1) > 0.01:
                bad += 1
                continue
            vw = s.vwap.reindex(range(390))
            cl = s.close.reindex(range(390)).ffill()
            ex = cl.iloc[389]
            for k in KS:
                lvl = (1 + k) * r.praw
                hit = s.index[(s.low <= lvl) & (s.index <= 330)]
                if len(hit) == 0:
                    continue
                t = int(hit[0])
                arm = "GAP" if t == 0 and s.open.iloc[0] <= lvl else "CROSS"
                en = vw.iloc[t + 1] if t + 1 < 390 and not np.isnan(vw.iloc[t + 1]) else cl.iloc[min(t + 1, 389)]
                h = {f"r{n}": cl.iloc[min(t + 1 + n, 389)] / en - 1 for n in (30, 60)}
                out.append(dict(date=pd.Timestamp(d), ticker=r.ticker, k=k, arm=arm, t=t, adv=r.adv, praw=r.praw,
                                r=ex / en - 1, spy=spy.iloc[389] / spy.iloc[min(t + 1, 389)] - 1, **h))
    print("dropped (missing/mismatched bars):", bad, flush=True)
    return pd.DataFrame(out)


def ct(x: pd.Series, dates: pd.Series):
    """Day-clustered t: mean of daily means / se."""
    dm = x.groupby(dates.values).mean()
    return dm.mean(), dm.mean() / (dm.std(ddof=1) / np.sqrt(len(dm))) if len(dm) > 2 else np.nan, len(dm)


def judge(tag="events", out=OUT):
    rp = D / f"td_rows_{tag}.parquet"
    r = pd.read_parquet(rp) if rp.exists() else rows(tag)
    r.to_parquet(rp)
    L = []
    pr = lambda s: (print(s), L.append(s))  # noqa: E731
    pr(f"SSR-TD rows {len(r)}, events {r.groupby(['date','ticker']).ngroups}, days {r.date.nunique()} "
       f"({r.date.min().date()} .. {r.date.max().date()})")
    for arm in ["CROSS", "GAP"]:
        pr(f"\n== {arm} arm: long from trigger+1 VWAP to 15:59 close; net = r - 2x10bp ==")
        for k in KS:
            x = r[(r.arm == arm) & (r.k == k)]
            if len(x) < 30:
                continue
            net = x.r - 2 * COST
            mu, t, nd = ct(net, x.date)
            hx = (x.r - x.spy) - 2 * COST
            mh, th, _ = ct(hx, x.date)
            dm = net.groupby(x.date.values).mean().sort_values()
            ex5 = dm.iloc[:-5].mean()
            h1 = net[x.date < "2024-01-01"]; h2 = net[x.date >= "2024-01-01"]
            yrs = " ".join(f"{y}:{v*1e4:+.0f}" for y, v in net.groupby(x.date.dt.year).mean().items())
            pr(f"k {k:+.2f} n {len(x):6d} days {nd:5d} | EWday {mu*1e4:+7.1f}bp t {t:+5.2f} | trade mean "
               f"{net.mean()*1e4:+7.1f} med {net.median()*1e4:+7.1f} hit {(net>0).mean():.2f} | spyhedged "
               f"{mh*1e4:+6.1f} t {th:+5.2f} | ex-top5days {ex5*1e4:+6.1f} | H1 {h1.mean()*1e4:+6.1f} "
               f"H2 {h2.mean()*1e4:+6.1f} | 20bp/side {(x.r-0.004).mean()*1e4:+6.1f} | r30 {x.r30.mean()*1e4:+6.1f} "
               f"r60 {x.r60.mean()*1e4:+6.1f}")
            pr(f"          yrs {yrs}")
    # discontinuity: same event, paired across thresholds (CROSS at -9, -10, -11 all present)
    x = r[r.arm == "CROSS"].pivot_table(index=["date", "ticker"], columns="k", values="r")
    x = x.dropna(subset=[-0.09, -0.10, -0.11])
    dd = x[-0.10] - (x[-0.09] + x[-0.11]) / 2
    mu, t, nd = ct(dd, x.index.get_level_values(0).to_series())
    pr(f"\nDISCONTINUITY D = r(-10) - mean(r(-9), r(-11)), paired CROSS events n {len(dd)} days {nd}: "
       f"{mu*1e4:+.1f}bp t {t:+.2f} (trade mean {dd.mean()*1e4:+.1f}, med {dd.median()*1e4:+.1f})")
    for a, b2 in [(-0.08, -0.09), (-0.09, -0.10), (-0.10, -0.11), (-0.11, -0.12)]:
        y = r[r.arm == "CROSS"].pivot_table(index=["date", "ticker"], columns="k", values="r").dropna(subset=[a, b2])
        st = y[b2] - y[a]
        mu2, t2, _ = ct(st, y.index.get_level_values(0).to_series())
        pr(f"  step {a:+.2f} -> {b2:+.2f}: {mu2*1e4:+6.1f}bp t {t2:+5.2f} n {len(st)}")
    out.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "fetch":
        fetch(w=int(sys.argv[2]) if len(sys.argv) > 2 else 0, W=int(sys.argv[3]) if len(sys.argv) > 3 else 1)
    else:
        judge()
