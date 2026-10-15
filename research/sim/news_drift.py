"""Study NEWS-DRIFT (N 885): continuation after single-symbol in-session headlines with a >= 1% first-5-minute move.

    PYTHONPATH=. .venv/bin/python -m research.sim.news_drift news          # Alpaca/Benzinga headlines 2021-26, per month
    PYTHONPATH=. .venv/bin/python -m research.sim.news_drift fetch [w W]   # raw SIP 1-min for headline stock-days + SPY
    PYTHONPATH=. .venv/bin/python -m research.sim.news_drift               # judge -> news_drift_out.txt
"""
from __future__ import annotations

import pathlib
import sys
import time

import numpy as np
import pandas as pd

from . import ssr_rd as m

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data/research/news_drift"
OUT = pathlib.Path(__file__).with_name("news_drift_out.txt")
START, END = "2021-01-01", "2026-09-30"


def fetch_news():
    import sys as _s
    _s.path.insert(0, str(ROOT))
    from alpaca.data.historical.news import NewsClient
    from alpaca.data.requests import NewsRequest
    from swingtrader.config import require_alpaca_keys
    (D / "news").mkdir(parents=True, exist_ok=True)
    k, s = require_alpaca_keys()
    c = NewsClient(k, s)
    for d in pd.bdate_range(START, END):
        f = D / "news" / f"{d.date()}.parquet"
        if f.exists():
            continue
        st = (d + pd.Timedelta(hours=9, minutes=45)).tz_localize("America/New_York")
        en = (d + pd.Timedelta(hours=15)).tz_localize("America/New_York")
        for a in range(6):
            try:
                r = c.get_news(NewsRequest(start=st, end=en, limit=5000, include_content=False))
                x = r.df.reset_index() if len(r.df) else pd.DataFrame(columns=["id", "created_at", "symbols", "headline"])
                x = x[["id", "created_at", "symbols", "headline"]]
                x["symbols"] = x.symbols.map(lambda v: ",".join(v) if isinstance(v, (list, tuple, np.ndarray)) else str(v))
                x.to_parquet(f)
                break
            except Exception as ex:  # noqa: BLE001
                print("err", d.date(), str(ex)[:100], flush=True)
                time.sleep(5 * (a + 1))
    print("news DONE", flush=True)


def events() -> pd.DataFrame:
    n = pd.concat(pd.read_parquet(f) for f in sorted((D / "news").glob("*.parquet")))
    n = n[~n.symbols.str.contains(",") & (n.symbols.str.len() > 0)]
    n["ts"] = pd.to_datetime(n.created_at, utc=True).dt.tz_convert("America/New_York")
    n["date"] = n.ts.dt.tz_localize(None).dt.normalize()
    n["mi"] = (n.ts.dt.hour - 9) * 60 + n.ts.dt.minute - 30
    n = n[(n.mi >= 15) & (n.mi <= 330)].rename(columns={"symbols": "ticker"})
    b = m.load()
    g = b.groupby("ticker", sort=False)
    b["praw"] = g.closeunadj.shift(1)
    b["adv"] = (b.close * b.volume).groupby(b.ticker).transform(lambda s: s.shift(1).rolling(20, min_periods=15).mean())
    b = b[(b.date >= START) & (b.praw >= 5) & (b.adv >= 5e6)][["ticker", "date", "praw", "adv"]]
    n["date"] = n.date.astype("datetime64[ns]")
    b["date"] = b.date.astype("datetime64[ns]")
    e = n.merge(b, on=["ticker", "date"])
    return e.sort_values("ts").drop_duplicates(["ticker", "date", "mi"])[["ticker", "date", "mi", "headline", "adv"]]


def fetch(w=0, W=1):
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from swingtrader.data import _clients
    (D / "m1").mkdir(parents=True, exist_ok=True)
    ef = D / "events.parquet"
    if not ef.exists():
        events().to_parquet(ef)
    e = pd.read_parquet(ef)
    c, _ = _clients()
    for i, (d, x) in enumerate(e.groupby("date")):
        p = D / "m1" / f"{pd.Timestamp(d).date()}.parquet"
        if p.exists() or i % W != w:
            continue
        syms = sorted(set(x.ticker) | {"SPY"})
        s = (pd.Timestamp(d) + pd.Timedelta(hours=9, minutes=30)).tz_localize("America/New_York").tz_convert("UTC")
        f = (pd.Timestamp(d) + pd.Timedelta(hours=16)).tz_localize("America/New_York").tz_convert("UTC")
        for a in range(8):
            try:
                df = c.get_stock_bars(StockBarsRequest(symbol_or_symbols=syms, timeframe=TimeFrame.Minute, start=s, end=f,
                                                       feed="sip", adjustment="raw")).df
                df.reset_index().to_parquet(p)
                break
            except Exception as ex:  # noqa: BLE001
                msg = str(ex)
                print("err", d, msg[:100], flush=True)
                if "invalid symbol:" in msg:
                    bad = msg.split("invalid symbol:")[1].split('"')[0].strip()
                    syms = [y for y in syms if y != bad]
                    continue
                time.sleep(5 * (a + 1))
        if i % 100 == 0:
            print(i, d, flush=True)
    print("DONE", flush=True)


def ct(x, dates):
    dm = x.groupby(np.asarray(dates)).mean()
    return dm.mean(), dm.mean() / (dm.std(ddof=1) / np.sqrt(len(dm))), len(dm), dm


def judge():
    e = pd.read_parquet(D / "events.parquet")
    out = []
    for d, x in e.groupby("date"):
        p = D / "m1" / f"{pd.Timestamp(d).date()}.parquet"
        if not p.exists():
            continue
        b = pd.read_parquet(p)
        if "timestamp" not in b:
            continue
        ts = pd.to_datetime(b.timestamp).dt.tz_convert("America/New_York")
        b["mi"] = (ts.dt.hour - 9) * 60 + ts.dt.minute - 30
        b = b[(b.mi >= 0) & (b.mi < 390)]
        cl = b.pivot_table(index="mi", columns="symbol", values="close").reindex(range(390)).ffill()
        vw = b.pivot_table(index="mi", columns="symbol", values="vwap").reindex(range(390))
        if "SPY" not in cl:
            continue
        done = set()
        for r in x.sort_values("mi").itertuples():
            if r.ticker in done or r.ticker not in cl:
                continue
            t = int(r.mi)
            if t + 66 > 389 or np.isnan(cl[r.ticker].iloc[t - 1]):
                continue
            m5 = cl[r.ticker].iloc[t + 5] / cl[r.ticker].iloc[t - 1] - 1
            if abs(m5) < 0.01:
                continue
            done.add(r.ticker)
            en = vw[r.ticker].iloc[t + 6]
            if np.isnan(en):
                en = cl[r.ticker].iloc[t + 6]
            sg = np.sign(m5)
            spy = cl["SPY"]
            out.append(dict(date=pd.Timestamp(d), ticker=r.ticker, mi=t, m5=m5, adv=r.adv,
                            r60=sg * (cl[r.ticker].iloc[t + 66] / en - 1), rc=sg * (cl[r.ticker].iloc[389] / en - 1),
                            s60=sg * (spy.iloc[t + 66] / spy.iloc[t + 6] - 1), headline=r.headline))
    f = pd.DataFrame(out)
    f.to_parquet(D / "rows.parquet")
    L = []
    pr = lambda s_: (print(s_), L.append(s_))  # noqa: E731
    pr(f"NEWS-DRIFT single-symbol in-session headlines: {len(e)}; events |m5| >= 1%: {len(f)} on {f.date.nunique()} days")
    for nm, q in [("|m5|>=1% PRIMARY", f.m5.abs() >= 0.01), ("|m5|>=2%", f.m5.abs() >= 0.02),
                  ("up moves", (f.m5 > 0)), ("down moves", (f.m5 < 0)), ("ADV>=$50M", f.adv >= 5e7)]:
        x = f[q]
        for h in ["r60", "rc"]:
            net = x[h] - 0.002
            mu, t, nd, dm = ct(net, x.date)
            h1, h2 = net[x.date < "2024-01-01"].mean(), net[x.date >= "2024-01-01"].mean()
            extra = f" | SPY-hedged {(x.r60 - x.s60 - 0.002).mean()*1e4:+.1f}" if h == "r60" else ""
            pr(f"{nm:17s} {h:3s} n {len(x):5d} net mean {net.mean()*1e4:+6.1f}bp med {net.median()*1e4:+6.1f} hit "
               f"{(net>0).mean():.2f} | EWday {mu*1e4:+6.1f} t {t:+5.2f} | ex-top5 {dm.sort_values().iloc[:-5].mean()*1e4:+6.1f} "
               f"| halves {h1*1e4:+6.1f} / {h2*1e4:+6.1f} | 20bp/side {(x[h]-0.004).mean()*1e4:+6.1f}{extra}")
    OUT.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    a = sys.argv[1] if len(sys.argv) > 1 else ""
    if a == "news":
        fetch_news()
    elif a == "fetch":
        fetch(int(sys.argv[2]) if len(sys.argv) > 2 else 0, int(sys.argv[3]) if len(sys.argv) > 3 else 1)
    else:
        judge()
