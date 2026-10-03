"""Goal hunt Study G12 (pre-registered in round1_prose.md, commit 41b08ed): officer/director buys >= $500k whose Form 4 is
accepted 09:30-15:20 ET on a session day; buy the first 1-minute bar starting >= acceptance + 5 min, sell the closing cross.
Costs tier_hi per side + 5bp extra on entry.

    PYTHONPATH=. .venv/bin/python -m research.sim.goal_g12 build
    PYTHONPATH=. .venv/bin/python -m research.sim.goal_g12 select     # 2021-23, one look

Output: data/research/program/goal_g12_out.txt
"""
from __future__ import annotations

import glob
import pathlib
import sys
import zipfile

import numpy as np
import pandas as pd

from . import book as B
from . import event_fetch as F

ROOT = pathlib.Path(__file__).resolve().parents[2]
PROG = ROOT / "data/research/program"
EVF = PROG / "goal_g12_events.parquet"
SEL = ("2021-01-01", "2023-12-31")
EXTRA = 5e-4


def out():
    f = open(PROG / "goal_g12_out.txt", "a")

    def log(*a):
        x = " ".join(str(i) for i in a)
        print(x, flush=True); f.write(x + "\n"); f.flush()
    return log


def buys() -> pd.DataFrame:
    f = PROG / "goal_g12_buys.parquet"
    if f.exists():
        return pd.read_parquet(f)
    zs = sorted(glob.glob(str(ROOT / "data/research/jump/insider/201[6-9]q?_form345.zip"))) + \
        sorted(glob.glob(str(ROOT / "data/research/night/insider/20[2-9]?q?_form345.zip")))
    rows = []
    for z in zs:
        Z = zipfile.ZipFile(z)
        rd = lambda n: pd.read_csv(Z.open(n), sep="\t", dtype=str, low_memory=False, on_bad_lines="skip")
        S = rd("SUBMISSION.tsv")[["ACCESSION_NUMBER", "FILING_DATE", "ISSUERTRADINGSYMBOL", "DOCUMENT_TYPE", "ISSUERCIK"]]
        N = rd("NONDERIV_TRANS.tsv")[["ACCESSION_NUMBER", "TRANS_CODE", "TRANS_ACQUIRED_DISP_CD", "TRANS_SHARES", "TRANS_PRICEPERSHARE"]]
        R = rd("REPORTINGOWNER.tsv")[["ACCESSION_NUMBER", "RPTOWNER_RELATIONSHIP"]]
        N = N[(N.TRANS_CODE == "P") & (N.TRANS_ACQUIRED_DISP_CD == "A")].copy()
        N["usd"] = pd.to_numeric(N.TRANS_SHARES, errors="coerce") * pd.to_numeric(N.TRANS_PRICEPERSHARE, errors="coerce")
        g = N.groupby("ACCESSION_NUMBER").usd.sum().reset_index()
        rel = R.groupby("ACCESSION_NUMBER").RPTOWNER_RELATIONSHIP.agg(lambda x: " ".join(map(str, x))).rename("rel").reset_index()
        g = g.merge(S, on="ACCESSION_NUMBER").merge(rel, on="ACCESSION_NUMBER", how="left")
        rows.append(g[g.DOCUMENT_TYPE.isin(["4", "4/A"])])
        print(z.split("/")[-1], len(rows[-1]), flush=True)
    X = pd.concat(rows)
    X["fd"] = pd.to_datetime(X.FILING_DATE, format="%d-%b-%Y", errors="coerce")
    X["sym"] = X.ISSUERTRADINGSYMBOL.str.upper().str.strip().str.replace("-", ".", regex=False)
    X["insider"] = X.rel.fillna("").str.contains("Director|Officer", case=False)
    X = X.dropna(subset=["fd", "usd", "sym"]).drop_duplicates("ACCESSION_NUMBER")
    X = X[["fd", "sym", "usd", "insider", "ACCESSION_NUMBER", "ISSUERCIK"]]
    X.to_parquet(f)
    return X


def minute_bars(sym: str, day: pd.Timestamp) -> pd.DataFrame:
    f = F._cache("min", "g12", f"{sym}_{day:%Y%m%d}.parquet")
    if f.exists():
        return pd.read_parquet(f)
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from swingtrader.daily.marketdata import _clients
    data, _ = _clients()
    a = pd.Timestamp(day.strftime("%Y-%m-%d") + " 09:30", tz="America/New_York")
    try:
        df = data.get_stock_bars(StockBarsRequest(symbol_or_symbols=sym, timeframe=TimeFrame.Minute, start=a,
                                                  end=a + pd.Timedelta(hours=6, minutes=30), feed="sip", adjustment="raw")).df
        df = df.reset_index()[["timestamp", "open", "close"]] if df is not None and len(df) else pd.DataFrame(columns=["timestamp", "open", "close"])
    except Exception:
        df = pd.DataFrame(columns=["timestamp", "open", "close"])
    if len(df):
        df["timestamp"] = pd.to_datetime(df.timestamp).dt.tz_convert("America/New_York").dt.tz_localize(None)
    df.to_parquet(f)
    return df


def build():
    log = out()
    log(f"=== G12 build {pd.Timestamp.now():%Y-%m-%d %H:%M} ===")
    X = buys()
    I = X[X.insider & (X.usd >= 5e5)].copy()
    log(f"  accessions >= $500k officer/director: {len(I)} ({I.fd.min():%Y-%m-%d}..{I.fd.max():%Y-%m-%d})")
    acc = []
    for j, r in enumerate(I.itertuples()):
        h = F.hdr(r.ISSUERCIK, r.ACCESSION_NUMBER)
        acc.append(F.accepted_et(h))
        if j % 500 == 0:
            print(f"  hdr {j}/{len(I)}", flush=True)
    I["acc"] = acc
    I = I.dropna(subset=["acc"])
    hm = I.acc.dt.hour * 60 + I.acc.dt.minute
    I = I[(hm >= 570) & (hm < 920) & (I.acc.dt.weekday < 5)]
    I["day"] = I.acc.dt.normalize()
    I = I.sort_values("acc").drop_duplicates(["sym", "day"])
    log(f"  accepted 09:30-15:20 on weekdays: {len(I)}")
    bars = F.raw_bars(sorted(I.sym.unique()))
    rows = []
    for r in I.itertuples():
        b = bars.get(r.sym)
        if b is None or not len(b):
            continue
        b = b.sort_index(); idx = pd.DatetimeIndex(b.index)
        if r.day not in idx:
            continue
        i = idx.get_loc(r.day)
        if i < 20:
            continue
        h20 = b.iloc[i - 20:i]
        pc, adv = b.close.iloc[i - 1], (h20.close * h20.volume).mean()
        if pc < 5 or adv < 2e7:
            continue
        m = minute_bars(r.sym, r.day)
        if not len(m):
            continue
        e = m[m.timestamp >= r.acc + pd.Timedelta(minutes=5)]
        if not len(e):
            continue
        rows.append(dict(sym=r.sym, d=r.day, acc=r.acc, usd=r.usd, entry_t=e.timestamp.iloc[0], entry=e.open.iloc[0],
                         c=b.close.iloc[i], adv=adv, pc=pc))
    T = pd.DataFrame(rows)
    T.to_parquet(EVF)
    log(f"  events with bars and filters: {len(T)} by year {T.groupby(T.d.dt.year).size().to_dict()}")


def net(T):
    cb = B.cost_bps("tier_hi", T.entry.values, T.adv.values) / 1e4
    return (T.c / T.entry - 1).values - 2 * cb - EXTRA


def select():
    log = out()
    log(f"\n=== G12 SELECT 2021-23 {pd.Timestamp.now():%Y-%m-%d %H:%M} (one look) ===")
    T = pd.read_parquet(EVF)
    V = T[(T.d >= SEL[0]) & (T.d <= SEL[1])]
    V = V[(V.c / V.entry - 1).abs() < 0.5]
    x = net(V)
    t = x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))
    yrs = pd.Series(x, index=V.d.dt.year.values).groupby(level=0).agg(["mean", "count"])
    log(f"  n {len(x)} mean {x.mean() * 1e4:+.1f}bp median {np.median(x) * 1e4:+.1f} hit {(x > 0).mean():.0%} t {t:+.2f} | "
        + " ".join(f"{y}:{m * 1e4:+.0f}({n})" for y, (m, n) in yrs.iterrows()))
    ok = len(x) >= 40 and x.mean() >= 30e-4 and t >= 2
    log(f"  select gate {'PASS -> judge' if ok else 'FAIL -> dead'}")


if __name__ == "__main__":
    {"build": build, "select": select}[sys.argv[1]]()
