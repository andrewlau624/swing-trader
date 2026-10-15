"""Study BTC-FIX (N 879): spot-bitcoin ETF NAV window (15:00-16:00 ET) flow, pre vs post 2024-01-11.

    PYTHONPATH=. .venv/bin/python -m research.sim.btc_fix fetch   # Alpaca crypto BTC/USD 1-min, monthly parquet
    PYTHONPATH=. .venv/bin/python -m research.sim.btc_fix         # judge -> btc_fix_out.txt
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data/research/btc_fix"
OUT = pathlib.Path(__file__).with_name("btc_fix_out.txt")
LAUNCH = pd.Timestamp("2024-01-11")
COST = 0.0005


def fetch():
    from alpaca.data.historical import CryptoHistoricalDataClient
    from alpaca.data.requests import CryptoBarsRequest
    from alpaca.data.timeframe import TimeFrame
    D.mkdir(parents=True, exist_ok=True)
    c = CryptoHistoricalDataClient()
    for m in pd.date_range("2021-01-01", "2026-09-01", freq="MS"):
        f = D / f"{m.date()}.parquet"
        if f.exists():
            continue
        df = c.get_crypto_bars(CryptoBarsRequest(symbol_or_symbols="BTC/USD", timeframe=TimeFrame.Minute,
                                                 start=m.tz_localize("UTC"),
                                                 end=(m + pd.offsets.MonthBegin(1)).tz_localize("UTC"))).df
        df.reset_index().to_parquet(f)
        print(m.date(), len(df), flush=True)


def ct(x, d):
    x = pd.Series(np.asarray(x)); return x.mean(), x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))


def judge():
    b = pd.concat(pd.read_parquet(f) for f in sorted(D.glob("*.parquet")))
    b["ts"] = pd.to_datetime(b.timestamp).dt.tz_convert("America/New_York")
    px = b.set_index("ts").close.sort_index()
    px = px[~px.index.duplicated()].resample("1min").last().ffill()
    days = pd.bdate_range("2021-01-04", "2026-09-30")
    from pandas.tseries.holiday import USFederalHolidayCalendar
    days = days.difference(USFederalHolidayCalendar().holidays("2021-01-01", "2026-12-31"))
    tz = "America/New_York"

    def at(d, h, mi=0):
        return px.asof(pd.Timestamp(d).tz_localize(tz) + pd.Timedelta(hours=h, minutes=mi))
    rows = []
    for d in days:
        p = {k: at(d, *k) for k in [(9, 30), (11, 0), (12, 0), (13, 0), (14, 0), (15, 0), (16, 0), (18, 0)]}
        if any(pd.isna(v) for v in p.values()):
            continue
        lr = lambda a, b_: np.log(p[b_] / p[a])  # noqa: E731
        rows.append(dict(date=d, W=lr((15, 0), (16, 0)), H13=lr((13, 0), (14, 0)), H11=lr((11, 0), (12, 0)),
                         R=lr((16, 0), (18, 0)), pre=lr((9, 30), (15, 0))))
    x = pd.DataFrame(rows)
    x["post"] = x.date >= LAUNCH
    L = []
    pr = lambda s: (print(s), L.append(s))  # noqa: E731
    pr(f"BTC-FIX days {len(x)} pre {(~x.post).sum()} post {x.post.sum()}")
    pr("(1) mean |return| by hour (bp), pre -> post, ratio")
    rat = {}
    for c in ["W", "H13", "H11", "R"]:
        a, b2 = x.loc[~x.post, c].abs().mean(), x.loc[x.post, c].abs().mean()
        rat[c] = b2 / a
        pr(f"   {c:4s} pre {a*1e4:6.1f} post {b2*1e4:6.1f} ratio {b2/a:.2f}")
    pr(f"   W ratio / mean(H13,H11) ratio = {rat['W']/((rat['H13']+rat['H11'])/2):.2f}")
    pr("(2) corr(W, R) reversal; corr(pre, W) continuation")
    for nm, s in [("pre", x[~x.post]), ("post", x[x.post])]:
        pr(f"   {nm}: corr(W,R) {s.W.corr(s.R):+.3f}  corr(pre,W) {s.pre.corr(s.W):+.3f}  mean W {s.W.mean()*1e4:+.1f}bp "
           f"(t {ct(s.W, s.date)[1]:+.2f})  mean H13 {s.H13.mean()*1e4:+.1f}")
    pr("(3) trades, net 5bp/side")
    for nm, sig, ret in [("FLOWPROXY sign(pre) x W", np.sign(x.pre), x.W), ("FADE -sign(W) x R", -np.sign(x.W), x.R)]:
        g = sig * ret - 2 * COST
        for per, q in [("pre-2024", ~x.post), ("post", x.post), ("post 2024", x.post & (x.date < "2025-01-01")),
                       ("post 2025-26", x.date >= "2025-01-01")]:
            s = g[q]
            mu, t = ct(s, None)
            pr(f"   {nm:26s} {per:12s} n {len(s):4d} mean {mu*1e4:+6.1f}bp t {t:+5.2f} med {s.median()*1e4:+6.1f} "
               f"hit {(s>0).mean():.2f} ex-top5 {s.sort_values().iloc[:-5].mean()*1e4:+6.1f}")
    OUT.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    fetch() if len(sys.argv) > 1 and sys.argv[1] == "fetch" else judge()
