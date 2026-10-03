"""Goal hunt Study G45 (pre-registered in round1_prose.md, commit cd548ad): first activist 13D (Saba, Karpus, Bulldog, City
of London, 1607, Almitas) on a closed-end fund; buy the next session's open, hold 60, vs PCEF, dividend-adjusted.

    PYTHONPATH=. .venv/bin/python -m research.sim.goal_g45 build
    PYTHONPATH=. .venv/bin/python -m research.sim.goal_g45 select     # 2021-23, one look

Output: data/research/program/goal_g45_out.txt
"""
from __future__ import annotations

import pathlib
import re
import sys

import numpy as np
import pandas as pd

from . import book as B
from . import event_fetch as F

ROOT = pathlib.Path(__file__).resolve().parents[2]
PROG = ROOT / "data/research/program"
EVF = PROG / "goal_g45_events.parquet"
ACTIVISTS = ['"Saba Capital"', '"Karpus"', '"Bulldog Investors"', '"City of London Investment"', '"1607 Capital"', '"Almitas"']
ACT_RE = re.compile(r"saba|karpus|bulldog|city of london|1607|almitas", re.I)
FUND_RE = re.compile(r"fund|trust|income|municipal|opportunit|strategic|dividend|global|capital", re.I)
SEL = ("2021-01-01", "2023-12-31")
HOLD = 60


def out():
    f = open(PROG / "goal_g45_out.txt", "a")

    def log(*a):
        x = " ".join(str(i) for i in a)
        print(x, flush=True); f.write(x + "\n"); f.flush()
    return log


def adj_bars(sym: str) -> pd.DataFrame:
    f = F._cache("bars", "adj", f"{sym.replace('/', '_')}.parquet")
    if f.exists():
        return pd.read_parquet(f)
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from swingtrader.daily.marketdata import _clients, trade_date
    data, _ = _clients()
    try:
        df = data.get_stock_bars(StockBarsRequest(symbol_or_symbols=sym, timeframe=TimeFrame.Day, start=pd.Timestamp("2015-10-01", tz="UTC"),
                                                  end=pd.Timestamp("2026-09-30", tz="UTC"), feed="sip", adjustment="all")).df
        df = df.reset_index()
        df["date"] = trade_date(df["timestamp"])
        df = df.set_index("date")[["open", "close", "volume"]]
    except Exception:
        df = pd.DataFrame(columns=["open", "close", "volume"])
    df.to_parquet(f)
    return df


def build():
    log = out()
    log(f"=== G45 build {pd.Timestamp.now():%Y-%m-%d %H:%M} ===")
    H = []
    for q in ACTIVISTS:
        H += F.fts_years(q, "SC 13D,SCHEDULE 13D")
    H = list({r["id"]: r for r in H}.values())
    H = [h for h in H if h["form"] in ("SC 13D", "SCHEDULE 13D")]
    rows = []
    for h in H:
        subj = [n for n in h["names"] if not ACT_RE.search(n) and F.ticker_of(n) and FUND_RE.search(n)]
        act = next((m.group(0).lower() for n in h["names"] for m in [ACT_RE.search(n)] if m), None)
        if not subj or not act:
            continue
        rows.append(dict(sym=F.ticker_of(subj[0])[0].replace("-", "."), name=subj[0][:40], act=act, fd=pd.Timestamp(h["date"])))
    E = pd.DataFrame(rows).sort_values("fd").drop_duplicates(["sym", "act"])
    log(f"  13D originals by the activists on fund-like subjects: {len(E)}")
    out_rows = []
    pc = adj_bars("PCEF"); pc.index = pd.DatetimeIndex(pc.index)
    raw = F.raw_bars(sorted(E.sym.unique()))
    for r in E.itertuples():
        b = adj_bars(r.sym)
        if not len(b):
            continue
        b.index = pd.DatetimeIndex(b.index); b = b.sort_index()
        i = b.index.searchsorted(r.fd + pd.Timedelta(days=1))
        if i < 20 or i + HOLD - 1 >= len(b) or (b.index[i] - r.fd).days > 7:
            continue
        d, dx = b.index[i], b.index[i + HOLD - 1]
        if d not in pc.index or dx not in pc.index:
            continue
        rb = raw.get(r.sym)
        adv = float((rb.close * rb.volume).loc[:d].iloc[-21:-1].mean()) if rb is not None and len(rb) else np.nan
        rpx = float(rb.close.loc[:d].iloc[-2]) if rb is not None and len(rb) > 1 else np.nan
        out_rows.append(dict(sym=r.sym, name=r.name, act=r.act, fd=r.fd, d=d, dx=dx, ret=b.close.iloc[i + HOLD - 1] / b.open.iloc[i] - 1,
                             bench=pc.close.loc[dx] / pc.open.loc[d] - 1, adv=adv, px=rpx))
    T = pd.DataFrame(out_rows)
    T.to_parquet(EVF)
    log(f"  events with bars {len(T)} by year {T.groupby(T.d.dt.year).size().to_dict()}; by activist {T.act.value_counts().to_dict()}")


def select():
    log = out()
    log(f"\n=== G45 SELECT 2021-23 {pd.Timestamp.now():%Y-%m-%d %H:%M} (one look) ===")
    T = pd.read_parquet(EVF)
    V = T[(T.d >= SEL[0]) & (T.d <= SEL[1])].copy()
    cb = B.cost_bps("tier", V.px.fillna(10).values, V.adv.fillna(1e6).values) / 1e4
    V["x"] = V.ret - V.bench - 2 * cb
    dm = V.groupby("d").x.mean()
    t = dm.mean() / (dm.std(ddof=1) / np.sqrt(len(dm))) if len(dm) > 2 else np.nan
    log(f"  n {len(V)} on {len(dm)} dates | mean {V.x.mean():+.2%} median {V.x.median():+.2%} hit {(V.x > 0).mean():.0%} date-t {t:+.2f} "
        f"worst {V.x.min():+.1%} | by year " + " ".join(f"{y}:{m:+.2%}({n})" for y, (m, n) in V.groupby(V.d.dt.year).x.agg(['mean', 'count']).iterrows()))
    ok = len(V) >= 30 and V.x.mean() >= 0.02 and t >= 2
    log(f"  select gate {'PASS -> judge' if ok else 'FAIL -> dead'}")


def judge():
    """The one judge look (2024-26) + holdout (2016-20), as registered."""
    log = out()
    log(f"\n=== G45 JUDGE {pd.Timestamp.now():%Y-%m-%d %H:%M} (one look) ===")
    T = pd.read_parquet(EVF)
    for lab, (a, b) in (("judge 2024-26", ("2024-01-01", "2026-09-30")), ("holdout 2016-20", ("2016-01-01", "2020-12-31"))):
        V = T[(T.d >= a) & (T.d <= b)].copy()
        cb = B.cost_bps("tier", V.px.fillna(10).values, V.adv.fillna(1e6).values) / 1e4
        V["x"] = V.ret - V.bench - 2 * cb
        dm = V.groupby("d").x.mean()
        t = dm.mean() / (dm.std(ddof=1) / np.sqrt(len(dm))) if len(dm) > 2 else np.nan
        ex5 = V.x.sort_values().iloc[:-5].mean() if len(V) > 5 else np.nan
        log(f"  {lab}: n {len(V)} on {len(dm)} dates | mean {V.x.mean():+.2%} median {V.x.median():+.2%} hit {(V.x > 0).mean():.0%} "
            f"date-t {t:+.2f} | ex best 5 trades {ex5:+.2%} | worst {V.x.min():+.1%} ({V.loc[V.x.idxmin(), 'sym']}) | by year "
            + " ".join(f"{y}:{m:+.2%}({n})" for y, (m, n) in V.groupby(V.d.dt.year).x.agg(['mean', 'count']).iterrows()))
        V[["sym", "act", "d", "x"]].to_csv(PROG / f"goal_g45_{lab.split()[0]}.csv", index=False)


if __name__ == "__main__":
    {"build": build, "select": select, "judge": judge}[sys.argv[1]]()
