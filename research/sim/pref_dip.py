"""Study PREF-DIP (N 880): resting dip bids at prior close x (1-k) in thin $25-par paper, exit in the closing cross.

    PYTHONPATH=. .venv/bin/python -m research.sim.pref_dip fetch [w W]   # raw SIP 1-min for candidate name-days
    PYTHONPATH=. .venv/bin/python -m research.sim.pref_dip               # judge -> pref_dip_out.txt

Candidate name-days: daily raw low < prior close x (1 - 0.005) - $0.01 (necessary for any k >= 0.5% fill).
"""
from __future__ import annotations

import pathlib
import sys
import time

import numpy as np
import pandas as pd
import pyarrow.dataset as ds

ROOT = pathlib.Path(__file__).resolve().parents[2]
S = pathlib.Path.home() / "data/sharadar"
D = ROOT / "data/research/pref_dip"
OUT = pathlib.Path(__file__).with_name("pref_dip_out.txt")
KS = [0.005, 0.010, 0.015]


def universe(start="2021-01-01", end="2026-09-30") -> pd.DataFrame:
    t = ds.dataset(S / "tickers.parquet").to_table(columns=["table", "ticker", "category"]).to_pandas()
    pref = set(t.loc[(t.table == "SEP") & (t.category == "Domestic Preferred Stock"), "ticker"])
    etd = set(t.loc[(t.table == "SFP") & (t.category == "ETD"), "ticker"])
    cols = ["ticker", "date", "low", "close", "volume", "closeunadj"]
    b = pd.concat([ds.dataset(S / "stocks.parquet").to_table(columns=cols, filter=ds.field("ticker").isin(list(pref))).to_pandas(),
                   ds.dataset(S / "funds.parquet").to_table(columns=cols, filter=ds.field("ticker").isin(list(etd))).to_pandas()])
    b["date"] = pd.to_datetime(b.date)
    b = b.sort_values(["ticker", "date"])
    g = b.groupby("ticker", sort=False)
    b["pc"] = g.closeunadj.shift(1)
    b["lowraw"] = b.low / b.close * b.closeunadj
    b["dv"] = (b.closeunadj * b.volume).groupby(b.ticker).transform(lambda s: s.shift(1).rolling(20, min_periods=10).median())
    a = ds.dataset(S / "actions.parquet").to_table(columns=["date", "action", "ticker"]).to_pandas()
    a = a[(a.action == "dividend")]
    a["date"] = pd.to_datetime(a.date)
    ex = set(zip(a.ticker, a.date))
    b["nd"] = g.date.shift(-1)
    b["exd"] = [(tk, d) in ex or (tk, n) in ex for tk, d, n in zip(b.ticker, b.date, b.nd)]
    b = b[(b.date >= start) & (b.date <= end) & b.pc.between(10, 60) & (b.dv >= 1e5) & ~b.exd]
    b = b[b.ticker.str.fullmatch(r"[A-Z]{1,5}-P[A-Z]{1,2}") | b.ticker.isin(etd)]
    b["sym"] = b.ticker.str.replace("-P", ".PR", regex=False)
    b["ret"] = b.closeunadj / b.pc - 1
    b["mkt"] = b.groupby("date").ret.transform("mean")
    return b[["ticker", "sym", "date", "pc", "lowraw", "closeunadj", "dv", "ret", "mkt"]].reset_index(drop=True)


def fetch(w=0, W=1):
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from swingtrader.data import _clients
    (D / "m1").mkdir(parents=True, exist_ok=True)
    uf = D / "universe.parquet"
    if not uf.exists():
        universe().to_parquet(uf)
    u = pd.read_parquet(uf)
    c_ = u[u.lowraw < u.pc * (1 - KS[0]) - 0.01]
    c, _ = _clients()
    for i, (d, x) in enumerate(c_.groupby("date")):
        p = D / "m1" / f"{pd.Timestamp(d).date()}.parquet"
        if p.exists() or i % W != w:
            continue
        s = (pd.Timestamp(d) + pd.Timedelta(hours=9, minutes=30)).tz_localize("America/New_York").tz_convert("UTC")
        f = (pd.Timestamp(d) + pd.Timedelta(hours=16)).tz_localize("America/New_York").tz_convert("UTC")
        syms = sorted(set(x.sym[~x.sym.str.contains(r"\d")]))
        for a in range(8):
            try:
                df = c.get_stock_bars(StockBarsRequest(symbol_or_symbols=syms, timeframe=TimeFrame.Minute,
                                                       start=s, end=f, feed="sip", adjustment="raw")).df
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
    u = pd.read_parquet(D / "universe.parquet")
    nd = u.date.nunique()
    c_ = u[u.lowraw < u.pc * (1 - KS[0]) - 0.01]
    out = []
    for d, x in c_.groupby("date"):
        p = D / "m1" / f"{pd.Timestamp(d).date()}.parquet"
        if not p.exists():
            continue
        b = pd.read_parquet(p)
        ts = pd.to_datetime(b.timestamp).dt.tz_convert("America/New_York")
        b["mi"] = (ts.dt.hour - 9) * 60 + ts.dt.minute - 30
        b = b[(b.mi >= 15) & (b.mi <= 360)]
        for r in x.itertuples():
            s = b[b.symbol == r.sym]
            for k in KS:
                lim = round(r.pc * (1 - k), 2)
                h = s[s.low < lim - 0.01]
                if len(h) == 0:
                    continue
                h0 = h.iloc[0]
                out.append(dict(date=pd.Timestamp(d), ticker=r.ticker, k=k, mi=int(h0.mi), lim=lim,
                                fdv=float(h0.volume * h0.vwap), r=r.closeunadj / lim - 1, mkt=r.mkt, dv=r.dv))
    f = pd.DataFrame(out)
    f.to_parquet(D / "fills.parquet")
    L = []
    pr = lambda s_: (print(s_), L.append(s_))  # noqa: E731
    pr(f"PREF-DIP universe name-days {len(u)} over {nd} days, {u.ticker.nunique()} names; candidate name-days {len(c_)}")
    for k in KS:
        x = f[f.k == k]
        net = x.r - 0.0005
        mu, t, ndd, dm = ct(net, x.date)
        h1, h2 = net[x.date < "2024-01-01"].mean(), net[x.date >= "2024-01-01"].mean()
        adj = (x.r - x.mkt - 0.0005)
        yrs = " ".join(f"{y}:{v*1e4:+.0f}" for y, v in net.groupby(x.date.dt.year).mean().items())
        win, los = net[net > 0], net[net <= 0]
        pr(f"\nk {k:.3f}{'  PRIMARY' if k == 0.01 else ''}: fills {len(x)} on {ndd} days ({len(x)/nd:.2f}/universe-day)")
        pr(f"  net/fill mean {net.mean()*1e4:+.1f}bp med {net.median()*1e4:+.1f} hit {(net>0).mean():.2f} | EWday "
           f"{mu*1e4:+.1f} t {t:+.2f} | ex-top5 {dm.sort_values().iloc[:-5].mean()*1e4:+.1f} | halves {h1*1e4:+.1f} / "
           f"{h2*1e4:+.1f} | 20bp exit {(x.r-0.002).mean()*1e4:+.1f} | mkt-adj {adj.mean()*1e4:+.1f}")
        pr(f"  med win {win.median()*1e4:+.0f} med loss {los.median()*1e4:+.0f} | worst fill {net.min()*1e4:+.0f} | worst day "
           f"{dm.min()*1e4:+.0f} | fill-minute $vol median ${x.fdv.median():,.0f} | 20d $vol median ${x.dv.median():,.0f}")
        pr(f"  yrs {yrs}")
    OUT.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "fetch":
        fetch(int(sys.argv[2]) if len(sys.argv) > 2 else 0, int(sys.argv[3]) if len(sys.argv) > 3 else 1)
    else:
        judge()
