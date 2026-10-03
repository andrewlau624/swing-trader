"""Goal hunt Study G54 (pre-registered in round1_prose.md): officer/director code-P buys at closed-end-fund-like issuers;
buy the next open, hold 60, vs PCEF (dividend-adjusted).

    PYTHONPATH=. .venv/bin/python -m research.sim.goal_g54 build|select|judge
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import pandas as pd

from . import book as B
from . import event_fetch as F
from .goal_g12 import buys
from .goal_g45 import FUND_RE, adj_bars
from .goal_g53 import WIN

ROOT = pathlib.Path(__file__).resolve().parents[2]
PROG = ROOT / "data/research/program"
EVF = PROG / "goal_g54_events.parquet"
HOLD = 60


def out():
    f = open(PROG / "goal_g54_out.txt", "a")

    def log(*a):
        x = " ".join(str(i) for i in a)
        print(x, flush=True); f.write(x + "\n"); f.flush()
    return log


def build():
    log = out()
    log(f"=== G54 build {pd.Timestamp.now():%Y-%m-%d %H:%M} ===")
    names = {v["ticker"].upper().replace("-", "."): v["title"] for v in json.load(open(ROOT / "data/research/events/company_tickers.json")).values()}
    X = buys()
    E = X[X.insider & (X.usd > 0)].groupby(["sym", "fd"]).usd.sum().reset_index()
    E = E[(E.usd >= 1e4) & E.sym.map(lambda s: bool(FUND_RE.search(names.get(s, ""))) and not any(
        w in names.get(s, "").upper() for w in (" INC", " CORP", " LTD", " LLC", " PLC", " CO ", "HOLDINGS", "BANCORP")))]
    E = E.sort_values("fd")
    keep, last = [], {}
    for r in E.itertuples():
        if r.sym in last and (r.fd - last[r.sym]).days < 90:
            continue
        last[r.sym] = r.fd; keep.append(r.Index)
    E = E.loc[keep]
    log(f"  fund-insider buy events: {len(E)} on {E.sym.nunique()} funds")
    pc = adj_bars("PCEF"); pc.index = pd.DatetimeIndex(pc.index)
    raw = F.raw_bars(sorted(E.sym.unique()))
    rows = []
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
        adv = px = np.nan
        if rb is not None and len(rb) > 21:
            rb = rb.sort_index(); rb.index = pd.DatetimeIndex(rb.index)
            h20 = rb.loc[:d].iloc[-21:-1]
            if len(h20):
                adv, px = float((h20.close * h20.volume).mean()), float(h20.close.iloc[-1])
        rows.append(dict(sym=r.sym, name=names.get(r.sym, "")[:40], fd=r.fd, d=d, usd=r.usd, ret=b.close.iloc[i + HOLD - 1] / b.open.iloc[i] - 1,
                         bench=pc.close.loc[dx] / pc.open.loc[d] - 1, adv=adv, px=px))
    T = pd.DataFrame(rows)
    T.to_parquet(EVF)
    log(f"  events with bars {len(T)} by year {T.groupby(T.d.dt.year).size().to_dict()}; sample names: {T.name.drop_duplicates().head(6).tolist()}")


def look(name):
    log = out()
    log(f"\n=== G54 {name.upper()} {pd.Timestamp.now():%Y-%m-%d %H:%M} (one look) ===")
    T = pd.read_parquet(EVF)
    for h in (["select"] if name == "select" else ["judge", "holdout"]):
        a, b = WIN[h]
        V = T[(T.d >= a) & (T.d <= b)].copy()
        cb = B.cost_bps("tier", V.px.fillna(10).values, V.adv.fillna(1e6).values) / 1e4
        V["x"] = V.ret - V.bench - 2 * cb
        dm = V.groupby("d").x.mean()
        t = dm.mean() / (dm.std(ddof=1) / np.sqrt(len(dm))) if len(dm) > 2 else np.nan
        ex5 = V.x.sort_values().iloc[:-5].mean() if len(V) > 5 else np.nan
        log(f"  {h}: n {len(V)} | mean {V.x.mean():+.2%} median {V.x.median():+.2%} hit {(V.x > 0).mean():.0%} date-t {t:+.2f} "
            f"ex-best-5 {ex5:+.2%} | by year " +
            " ".join(f"{y}:{m:+.1%}({n})" for y, (m, n) in V.groupby(V.d.dt.year).x.agg(['mean', 'count']).iterrows()))
        if h == "select":
            ok = len(V) >= 30 and V.x.mean() >= 0.02 and t >= 2
            log(f"  select gate {'PASS -> judge' if ok else 'FAIL -> dead'}")


if __name__ == "__main__":
    {"build": build, "select": lambda: look("select"), "judge": lambda: look("judge")}[sys.argv[1]]()
