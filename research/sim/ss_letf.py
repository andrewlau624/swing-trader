"""Study SS-LETF (N 877): single-stock leveraged-ETF rebalance demand -> 15:45 to close continuation.

    PYTHONPATH=. .venv/bin/python -m research.sim.ss_letf fetch [w W]   # 15:45 raw SIP minute bar, resumable
    PYTHONPATH=. .venv/bin/python -m research.sim.ss_letf               # judge -> ss_letf_out.txt

r_pre = close of the 15:45 minute bar (raw) / prior official close (Sharadar closeunadj) - 1;
r_post = official close (Sharadar closeunadj) / 15:45 bar close - 1.
"""
from __future__ import annotations

import pathlib
import re
import sys
import time

import numpy as np
import pandas as pd
import pyarrow.dataset as ds

ROOT = pathlib.Path(__file__).resolve().parents[2]
S = pathlib.Path.home() / "data/sharadar"
D = ROOT / "data/research/ss_letf"
OUT = pathlib.Path(__file__).with_name("ss_letf_out.txt")
PATS = [r"2X (?:LONG|SHORT|INVERSE) ([A-Z]{1,5})\b", r"DAILY ([A-Z]{1,5}) (?:BULL|BEAR) 2X", r"CORGI ([A-Z]{1,5}) 2X",
        r"2X ([A-Z]{1,5}) DAILY", r"(?:LONG|SHORT) ([A-Z]{1,5}) DAILY", r"1\.5X (?:LONG|SHORT) ([A-Z]{1,5})"]
START, END = "2022-07-01", "2026-09-30"


def fund_map() -> pd.DataFrame:
    t = ds.dataset(S / "tickers.parquet").to_table(columns=["table", "ticker", "name", "category"]).to_pandas()
    st = set(t.loc[(t.table == "SEP") & t.category.fillna("").str.contains("Common Stock"), "ticker"])
    f = t[t.table == "SFP"].copy()

    def und(n):
        n = str(n).upper()
        for p in PATS:
            m = re.search(p, n)
            if m and m.group(1) in st:
                return m.group(1)
    f["u"] = f.name.map(und)
    f = f.dropna(subset=["u"])
    nm = f.name.str.upper()
    f["lev"] = np.where(nm.str.contains("SHORT|INVERSE|BEAR"), -2.0, np.where(nm.str.contains("1.5X", regex=False), 1.5, 2.0))
    f["w"] = f.lev * (f.lev - 1) / 2
    return f[["ticker", "u", "lev", "w", "name"]]


def panel() -> pd.DataFrame:
    f = fund_map()
    fp = ds.dataset(S / "funds.parquet").to_table(
        columns=["ticker", "date", "close", "volume"],
        filter=ds.field("ticker").isin(list(f.ticker)) & (ds.field("date") >= pd.Timestamp("2022-01-01").date())).to_pandas()
    fp["dv"] = fp.close * fp.volume
    fp = fp.merge(f[["ticker", "u", "w"]], on="ticker").sort_values(["ticker", "date"])
    fp["dv20"] = fp.groupby("ticker").dv.transform(lambda s: s.shift(1).rolling(20, min_periods=5).median())
    fp["wdv"] = fp.w * fp.dv20
    fi = fp.groupby(["u", "date"]).wdv.sum().rename("fdv").reset_index().rename(columns={"u": "ticker"})
    t = ds.dataset(S / "tickers.parquet").to_table(columns=["table", "ticker", "category"]).to_pandas()
    common = set(t.loc[(t.table == "SEP") & t.category.fillna("").str.contains("Common Stock")
                       & ~t.category.fillna("").str.contains("ADR|Warrant|Preferred"), "ticker"])
    b = ds.dataset(S / "stocks.parquet").to_table(
        columns=["ticker", "date", "closeunadj", "close", "volume"],
        filter=ds.field("date") >= pd.Timestamp("2022-01-01").date()).to_pandas()
    b = b[b.ticker.isin(common) & b.ticker.str.fullmatch(r"[A-Z]{1,5}")].sort_values(["ticker", "date"])
    g = b.groupby("ticker", sort=False)
    b["pc"] = g.closeunadj.shift(1)
    b["udv20"] = (b.closeunadj * b.volume).groupby(b.ticker).transform(
        lambda s: s.shift(1).rolling(20, min_periods=15).median())
    b = b.merge(fi, on=["ticker", "date"], how="left")
    b["I"] = (b.fdv / b.udv20).fillna(0.0)
    b["date"] = pd.to_datetime(b.date)
    b = b[(b.date >= START) & (b.date <= END) & (b.pc >= 5) & (b.udv20 >= 1e8)]
    return b[["ticker", "date", "pc", "closeunadj", "udv20", "I"]].reset_index(drop=True)


def fetch(w=0, W=1):
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from swingtrader.data import _clients
    (D / "m").mkdir(parents=True, exist_ok=True)
    pf = D / "panel.parquet"
    if not pf.exists():
        panel().to_parquet(pf)
    p = pd.read_parquet(pf)
    c, _ = _clients()
    for i, (d, x) in enumerate(p.groupby("date")):
        f = D / "m" / f"{pd.Timestamp(d).date()}.parquet"
        if f.exists() or i % W != w:
            continue
        s = (pd.Timestamp(d) + pd.Timedelta(hours=15, minutes=45)).tz_localize("America/New_York").tz_convert("UTC")
        syms = sorted(x.ticker)
        out = []
        for k in range(0, len(syms), 400):
            for a in range(6):
                try:
                    df = c.get_stock_bars(StockBarsRequest(symbol_or_symbols=syms[k:k + 400], timeframe=TimeFrame.Minute,
                                                           start=s, end=s + pd.Timedelta(minutes=1), feed="sip",
                                                           adjustment="raw")).df
                    out.append(df.reset_index())
                    break
                except Exception as ex:  # noqa: BLE001
                    print("err", d, str(ex)[:100], flush=True)
                    time.sleep(5 * (a + 1))
        if out:
            pd.concat(out).to_parquet(f)
        if i % 50 == 0:
            print(i, d, flush=True)
    print("DONE", flush=True)


def ct(x, dates):
    dm = x.groupby(np.asarray(dates)).mean()
    return dm.mean(), dm.mean() / (dm.std(ddof=1) / np.sqrt(len(dm))), len(dm)


def judge():
    p = pd.read_parquet(D / "panel.parquet")
    bars = []
    for f in sorted((D / "m").glob("*.parquet")):
        b = pd.read_parquet(f)
        ts = pd.to_datetime(b.timestamp).dt.tz_convert("America/New_York")
        b = b[(ts.dt.hour == 15) & (ts.dt.minute == 45)]
        bars.append(pd.DataFrame({"ticker": b.symbol, "date": pd.Timestamp(f.stem), "p45": b.close}))
    m = p.merge(pd.concat(bars), on=["ticker", "date"])
    m["r_pre"] = m.p45 / m.pc - 1
    m["r_post"] = m.closeunadj / m.p45 - 1
    m = m[(m.r_pre.abs() < 0.5) & (m.r_post.abs() < 0.2)]
    L = []
    pr = lambda s: (print(s), L.append(s))  # noqa: E731
    pr(f"SS-LETF stock-days {len(m)}, days {m.date.nunique()}, names with I>0: {m[m.I>0].ticker.nunique()}, "
       f"stock-days I>=0.05: {(m.I>=0.05).sum()}")
    # FE regression via within-day demeaning
    for c_ in ["r_post", "r_pre"]:
        m[c_ + "_d"] = m[c_] - m.groupby("date")[c_].transform("mean")
    m["Ix"] = m.I * m.r_pre_d
    X = m[["r_pre_d", "Ix"]].values
    y = m.r_post_d.values
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    e = y - X @ beta
    XtX = np.linalg.inv(X.T @ X)
    meat = np.zeros((2, 2))
    for _, idx in m.groupby("date").indices.items():
        s = X[idx].T @ e[idx]
        meat += np.outer(s, s)
    se = np.sqrt(np.diag(XtX @ meat @ XtX))
    pr(f"FE regression r_post ~ r_pre + I x r_pre: b {beta[0]:+.4f} (t {beta[0]/se[0]:+.2f}), "
       f"c {beta[1]:+.4f} (t {beta[1]/se[1]:+.2f})")
    for lo, hi in [(0, 1e-9), (1e-9, 0.02), (0.02, 0.05), (0.05, 0.1), (0.1, 9)]:
        x = m[(m.I >= lo) & (m.I < hi) & (m.r_pre.abs() >= 0.03)]
        if len(x) < 20:
            continue
        sg = np.sign(x.r_pre) * x.r_post
        mu, t, nd = ct(sg, x.date)
        pr(f"  I [{lo:.2f},{hi:.2f}) |r_pre|>=3%: n {len(x):6d} gross dir-ret mean {sg.mean()*1e4:+6.1f} "
           f"med {sg.median()*1e4:+6.1f} EWday {mu*1e4:+6.1f} t {t:+5.2f}")
    x = m[(m.I >= 0.05) & (m.r_pre.abs() >= 0.03)].copy()
    x["g"] = np.sign(x.r_pre) * x.r_post
    for nm, sub in [("ALL", x), ("LONG (up days)", x[x.r_pre > 0]), ("SHORT (down days)", x[x.r_pre < 0])]:
        net = sub.g - 0.001
        mu, t, nd = ct(net, sub.date)
        dm = net.groupby(sub.date.values).mean().sort_values()
        h1 = net[sub.date < "2025-01-01"].mean(); h2 = net[sub.date >= "2025-01-01"].mean()
        yrs = " ".join(f"{y}:{v*1e4:+.0f}" for y, v in net.groupby(sub.date.dt.year).mean().items())
        pr(f"TRADE {nm}: n {len(sub)} days {nd} | net mean {net.mean()*1e4:+.1f} med {net.median()*1e4:+.1f} "
           f"hit {(net>0).mean():.2f} | EWday {mu*1e4:+.1f} t {t:+.2f} | ex-top5 {dm.iloc[:-5].mean()*1e4:+.1f} | "
           f"H1 {h1*1e4:+.1f} H2 {h2*1e4:+.1f} | 10bp/side {(sub.g-0.002).mean()*1e4:+.1f} | {yrs}")
    ctl = m[(m.I == 0) & (m.r_pre.abs() >= 0.03)]
    cg = np.sign(ctl.r_pre) * ctl.r_post
    dd = pd.concat([x.groupby("date").g.mean().rename("t"), cg.groupby(ctl.date.values).mean().rename("c")], axis=1).dropna()
    diff = dd.t - dd.c
    pr(f"PLACEBO controls I=0 |r_pre|>=3%: n {len(ctl)} gross {cg.mean()*1e4:+.1f}; paired day diff treated-control "
       f"{diff.mean()*1e4:+.1f}bp t {diff.mean()/(diff.std()/np.sqrt(len(diff))):+.2f} days {len(diff)}")
    for u in x.ticker.value_counts().index[:12]:
        s = x[x.ticker == u]
        pr(f"   {u:5s} n {len(s):4d} gross {s.g.mean()*1e4:+6.1f} med {s.g.median()*1e4:+6.1f} I~{s.I.median():.2f}")
    OUT.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "fetch":
        fetch(int(sys.argv[2]) if len(sys.argv) > 2 else 0, int(sys.argv[3]) if len(sys.argv) > 3 else 1)
    else:
        judge()
