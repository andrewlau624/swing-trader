"""Study GAP-SHORT (N 878): short >=10% opening gap-downs at the 09:31 VWAP, cover at 15:59; judge 2016-20.

    PYTHONPATH=. .venv/bin/python -m research.sim.gap_short fetch [w W]   # 2016-20 raw SIP minute bars, resumable
    PYTHONPATH=. .venv/bin/python -m research.sim.gap_short               # judge -> gap_short_out.txt

Minute bars share data/research/ssr/m1/<date>.parquet with SSR-TD (2021-26 already there for every day-low <= -7% name).
"""
from __future__ import annotations

import sys
import time

import numpy as np
import pandas as pd

from . import ssr_rd as m
from .ssr_td import D, M1

OUT = __import__("pathlib").Path(__file__).with_name("gap_short_out.txt")
EF = D / "gap_events.parquet"


def events() -> pd.DataFrame:
    b = m.load()
    g = b.groupby("ticker", sort=False)
    b["G"] = b.open / g.close.shift(1) - 1
    b["praw"] = g.closeunadj.shift(1)
    b["adv"] = (b.close * b.volume).groupby(b.ticker).transform(
        lambda s: s.shift(1).rolling(20, min_periods=15).mean())
    e = b[(b.praw >= 5) & (b.adv >= 5e6) & (b.G <= -0.09) & (b.date >= "2016-01-01") & (b.date <= "2026-09-30")
          & b.ticker.str.fullmatch(r"[A-Z]{1,5}")]
    return e[["ticker", "date", "G", "adv", "praw", "closeunadj"]].reset_index(drop=True)


def fetch(w=0, W=1):
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from swingtrader.data import _clients
    if not EF.exists():
        events().to_parquet(EF)
    e = pd.read_parquet(EF)
    e = e[e.date < "2021-01-01"]
    c, _ = _clients()
    for i, (d, x) in enumerate(e.groupby("date")):
        p = M1 / f"{pd.Timestamp(d).date()}.parquet"
        if p.exists() or i % W != w:
            continue
        syms = sorted(set(x.ticker) | {"SPY"})
        s = (pd.Timestamp(d) + pd.Timedelta(hours=9, minutes=30)).tz_localize("America/New_York").tz_convert("UTC")
        f = (pd.Timestamp(d) + pd.Timedelta(hours=16)).tz_localize("America/New_York").tz_convert("UTC")
        for a in range(6):
            try:
                df = c.get_stock_bars(StockBarsRequest(symbol_or_symbols=syms, timeframe=TimeFrame.Minute, start=s,
                                                       end=f, feed="sip", adjustment="raw")).df
                if len(df):
                    df.reset_index().to_parquet(p)
                break
            except Exception as ex:  # noqa: BLE001
                print("err", d, str(ex)[:100], flush=True)
                time.sleep(5 * (a + 1))
        if i % 50 == 0:
            print(i, d, flush=True)
    print("DONE", flush=True)


def rows() -> pd.DataFrame:
    e = pd.read_parquet(EF)
    out, bad = [], 0
    for d, x in e.groupby("date"):
        p = M1 / f"{pd.Timestamp(d).date()}.parquet"
        if not p.exists():
            continue
        b = pd.read_parquet(p)
        ts = pd.to_datetime(b.timestamp).dt.tz_convert("America/New_York")
        b["mi"] = (ts.dt.hour - 9) * 60 + ts.dt.minute - 30
        b = b[(b.mi >= 0) & (b.mi < 390)]
        if "SPY" not in set(b.symbol):
            continue
        spy = b[b.symbol == "SPY"].set_index("mi").close.reindex(range(390)).ffill()
        for r in x.itertuples():
            s = b[b.symbol == r.ticker].set_index("mi").sort_index()
            if len(s) < 30 or s.index.min() > 0 or 389 - s.index.max() > 5 or abs(s.close.iloc[-1] / r.closeunadj - 1) > 0.01:
                bad += 1
                continue
            g0 = s.open.iloc[0] / r.praw - 1
            if g0 > -0.10:
                continue
            en = s.vwap.get(1, np.nan)
            if np.isnan(en):
                en = s.close.iloc[0]
            cl = s.close.reindex(range(390)).ffill()
            path = cl.iloc[1:] / en - 1
            out.append(dict(date=pd.Timestamp(d), ticker=r.ticker, gap=g0, adv=r.adv, praw=r.praw,
                            r=cl.iloc[389] / en - 1, maxup=s.high.iloc[1:].max() / en - 1, r60=path.iloc[60],
                            spy=spy.iloc[389] / spy.iloc[1] - 1))
    print("dropped:", bad, flush=True)
    return pd.DataFrame(out)


def ct(x, dates):
    dm = x.groupby(np.asarray(dates)).mean()
    return dm.mean(), dm.mean() / (dm.std(ddof=1) / np.sqrt(len(dm))), len(dm), dm


def judge():
    rp = D / "gap_rows.parquet"
    r = rows()
    r.to_parquet(rp)
    L = []
    pr = lambda s: (print(s), L.append(s))  # noqa: E731
    pr(f"GAP-SHORT rows {len(r)} ({r.date.min().date()} .. {r.date.max().date()})")
    for uni, q in [("PRIMARY $10/$20M", (r.praw >= 10) & (r.adv >= 2e7)), ("BROAD $5/$5M", r.praw >= 5)]:
        for per, pq in [("2016-20 JUDGE", r.date < "2021-01-01"), ("2021-26 touched", r.date >= "2021-01-01")]:
            x = r[q & pq]
            net = -x.r - 0.002
            mu, t, nd, dm = ct(net, x.date)
            ex5 = dm.sort_values().iloc[:-5].mean()
            hq = (x.date < "2019-01-01") if per.startswith("2016") else (x.date < "2024-01-01")
            h1, h2 = net[hq].mean(), net[~hq].mean()
            hh = (net - (-x.spy)).mean()
            yrs = " ".join(f"{y}:{v*1e4:+.0f}" for y, v in net.groupby(x.date.dt.year).mean().items())
            win, los = net[net > 0], net[net <= 0]
            pr(f"\n{uni} {per}: n {len(x)} days {nd} ({len(x)/max(nd,1):.1f}/day)")
            pr(f"  net EWday {mu*1e4:+.1f}bp t {t:+.2f} | trade mean {net.mean()*1e4:+.1f} med {net.median()*1e4:+.1f} "
               f"hit {(net>0).mean():.2f} | ex-top5 {ex5*1e4:+.1f} | halves {h1*1e4:+.1f} / {h2*1e4:+.1f} | "
               f"20bp/side {(-x.r-0.004).mean()*1e4:+.1f} | SPY-adj {hh*1e4:+.1f}")
            pr(f"  med win {win.median()*1e4:+.0f} med loss {los.median()*1e4:+.0f} | worst trade {net.min()*1e4:+.0f} | "
               f"worst day {dm.min()*1e4:+.0f} | trades losing >10% {(net<-0.10).mean():.3f} | max adverse "
               f"excursion p90 {x.maxup.quantile(0.9)*1e4:+.0f} | short to +60m {(-x.r60-0.002).mean()*1e4:+.1f}")
            pr(f"  yrs {yrs}")
    OUT.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "fetch":
        fetch(int(sys.argv[2]) if len(sys.argv) > 2 else 0, int(sys.argv[3]) if len(sys.argv) > 3 else 1)
    else:
        judge()
