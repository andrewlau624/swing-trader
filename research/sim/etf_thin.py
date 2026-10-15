"""Study ETF-THIN (N 884): resting bids at hedged fair value x (1-k) in thin benchmark-tracking ETFs; exit official close.

    PYTHONPATH=. .venv/bin/python -m research.sim.etf_thin fetch [w W]   # raw SIP 1-min, candidate name-days + benchmarks
    PYTHONPATH=. .venv/bin/python -m research.sim.etf_thin               # judge -> etf_thin_out.txt
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
D = ROOT / "data/research/etf_thin"
OUT = pathlib.Path(__file__).with_name("etf_thin_out.txt")
BENCH = "SPY QQQ IWM DIA MDY IJR EFA EEM EWJ VNQ GLD AGG TLT IEF SHY LQD HYG XLB XLE XLF XLI XLK XLP XLU XLV XLY XLC XLRE".split()
KS = [0.005, 0.010]
START, END = "2021-01-01", "2026-09-30"


def universe() -> pd.DataFrame:
    t = ds.dataset(S / "tickers.parquet").to_table(columns=["table", "ticker", "category", "name"]).to_pandas()
    t = t[(t.table == "SFP") & (t.category == "ETF")]
    lev = t.name.str.upper().str.contains(r"2X|3X|ULTRA|INVERSE|SHORT|BEAR|BULL|LEVERAG|-1X|DAILY|1\.5X|1\.25X|BUFFER|OPTION|INCOME|COVERED|VOLATIL|VIX")
    thin = set(t.ticker[~lev]) - set(BENCH)
    cols = ["ticker", "date", "high", "low", "close", "volume", "closeadj", "closeunadj"]
    b = ds.dataset(S / "funds.parquet").to_table(columns=cols, filter=ds.field("date") >= pd.Timestamp("2020-05-01").date()).to_pandas()
    b["date"] = pd.to_datetime(b.date)
    b = b[b.ticker.isin(thin | set(BENCH))].sort_values(["ticker", "date"])
    g = b.groupby("ticker", sort=False)
    b["ret"] = g.closeadj.pct_change()
    b["pc"] = g.closeunadj.shift(1)
    b["hiraw"] = b.high / b.close * b.closeunadj
    b["loraw"] = b.low / b.close * b.closeunadj
    b["dv"] = (b.closeunadj * b.volume).groupby(b.ticker).transform(lambda s: s.shift(1).rolling(20, min_periods=10).median())
    R = b.pivot(index="date", columns="ticker", values="ret")
    bench = b[b.ticker.isin(BENCH)].set_index(["date", "ticker"])
    # benchmark assignment per month, from the prior 120 sessions
    rows = []
    months = pd.date_range(START, END, freq="MS")
    RB = R[[c for c in BENCH if c in R]]
    for mo in months:
        w = R[R.index < mo].tail(120)
        if len(w) < 100:
            continue
        wb = RB.loc[w.index]
        cand = [c for c in w.columns if c not in BENCH and w[c].notna().sum() >= 100]
        X = w[cand]
        best = None
        for bn in wb.columns:
            x = wb[bn]
            ok = X.notna() & x.notna().values[:, None]
            xm = x.values[:, None]
            Xv = X.where(ok)
            xx = pd.DataFrame(np.where(ok, xm, np.nan), index=X.index, columns=cand)
            cov = ((Xv - Xv.mean()) * (xx - xx.mean())).mean()
            beta = cov / xx.var(ddof=0)
            r2 = (cov ** 2) / (xx.var(ddof=0) * Xv.var(ddof=0))
            f = pd.DataFrame({"bench": bn, "beta": beta, "r2": r2})
            best = f if best is None else best.where(best.r2 >= f.r2, f)
        best = best[(best.r2 >= 0.97) & (best.beta > 0)]
        best["month"] = mo
        rows.append(best.rename_axis("ticker").reset_index())
    a = pd.concat(rows)
    b["month"] = b.date.values.astype("datetime64[M]")
    u = b.merge(a, on=["ticker", "month"])
    u = u[(u.date >= START) & (u.date <= END) & (u.pc >= 10) & u.dv.between(5e4, 2e6)]
    bb = bench.reset_index()[["date", "ticker", "pc", "hiraw", "closeunadj"]].rename(
        columns={"ticker": "bench", "pc": "bpc", "hiraw": "bhi", "closeunadj": "bcl"})
    u = u.merge(bb, on=["date", "bench"])
    act = ds.dataset(S / "actions.parquet").to_table(columns=["date", "action", "ticker"]).to_pandas()
    act = act[act.action == "dividend"]
    ex = set(zip(act.ticker, pd.to_datetime(act.date)))
    u = u[[(tk, d) not in ex for tk, d in zip(u.ticker, u.date)]]
    u["cand"] = u.loraw < u.pc * (1 + u.beta * (u.bhi / u.bpc - 1)) * (1 - KS[0]) - 0.01
    return u[["ticker", "date", "pc", "loraw", "closeunadj", "dv", "bench", "beta", "r2", "bpc", "bcl", "cand"]].reset_index(drop=True)


def fetch(w=0, W=1):
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from swingtrader.data import _clients
    (D / "m1").mkdir(parents=True, exist_ok=True)
    uf = D / "universe.parquet"
    if not uf.exists():
        universe().to_parquet(uf)
    u = pd.read_parquet(uf)
    c_ = u[u.cand]
    c, _ = _clients()
    for i, (d, x) in enumerate(c_.groupby("date")):
        p = D / "m1" / f"{pd.Timestamp(d).date()}.parquet"
        if p.exists() or i % W != w:
            continue
        syms = sorted(set(x.ticker) | set(x.bench))
        syms = [y for y in syms if y.isalpha()]
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
    u = pd.read_parquet(D / "universe.parquet")
    c_ = u[u.cand]
    out = []
    for d, x in c_.groupby("date"):
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
        lo = b.pivot_table(index="mi", columns="symbol", values="low").reindex(range(390))
        for r in x.itertuples():
            if r.ticker not in lo or r.bench not in cl:
                continue
            fv = r.pc * (1 + r.beta * (cl[r.bench] / r.bpc - 1))
            for k in KS:
                lim = (fv.shift(1) * (1 - k)).round(2)
                hit = lo[r.ticker].loc[15:360] < (lim.loc[15:360] - 0.01)
                if not hit.any():
                    continue
                m = int(hit.idxmax())
                L_ = lim.loc[m]
                rt = r.closeunadj / L_ - 1
                hb = cl[r.bench].iloc[389] / cl[r.bench].loc[m] - 1
                out.append(dict(date=pd.Timestamp(d), ticker=r.ticker, bench=r.bench, k=k, mi=m, beta=r.beta, dv=r.dv,
                                r=rt, h=hb, disc=L_ / fv.loc[m] - 1))
    f = pd.DataFrame(out)
    f.to_parquet(D / "fills.parquet")
    L = []
    pr = lambda s_: (print(s_), L.append(s_))  # noqa: E731
    pr(f"ETF-THIN universe name-days {len(u)} ({u.ticker.nunique()} ETFs, {u.date.nunique()} days); candidates {len(c_)}")
    pr(f"benchmarks used: {u.bench.value_counts().head(8).to_dict()}")
    for k in KS:
        x = f[f.k == k]
        hn = x.r - x.beta * x.h - 0.0005 - 0.0002
        un = x.r - 0.0005
        mu, t, nd, dm = ct(hn, x.date)
        h1, h2 = hn[x.date < "2024-01-01"].mean(), hn[x.date >= "2024-01-01"].mean()
        win, los = hn[hn > 0], hn[hn <= 0]
        yrs = " ".join(f"{y}:{v*1e4:+.0f}" for y, v in hn.groupby(x.date.dt.year).mean().items())
        pr(f"\nk {k:.3f}{'  PRIMARY' if k == 0.005 else ''}: fills {len(x)} on {nd} days ({len(x)/max(nd,1):.1f}/fill-day), "
           f"{x.ticker.nunique()} ETFs")
        pr(f"  HEDGED net/fill mean {hn.mean()*1e4:+.1f}bp med {hn.median()*1e4:+.1f} hit {(hn>0).mean():.2f} | EWday "
           f"{mu*1e4:+.1f} t {t:+.2f} | ex-top5 {dm.sort_values().iloc[:-5].mean()*1e4:+.1f} | halves {h1*1e4:+.1f} / "
           f"{h2*1e4:+.1f} | 20bp exit {(x.r - x.beta*x.h - 0.0022).mean()*1e4:+.1f} | UNHEDGED {un.mean()*1e4:+.1f} med "
           f"{un.median()*1e4:+.1f}")
        pr(f"  med win {win.median()*1e4:+.0f} med loss {los.median()*1e4:+.0f} worst {hn.min()*1e4:+.0f} worst day "
           f"{dm.min()*1e4:+.0f} | 20d $vol med ${x.dv.median():,.0f} | {yrs}")
    OUT.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "fetch":
        fetch(int(sys.argv[2]) if len(sys.argv) > 2 else 0, int(sys.argv[3]) if len(sys.argv) > 3 else 1)
    else:
        judge()
