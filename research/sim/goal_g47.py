"""Goal hunt Study G47 (pre-registered in round1_prose.md): first 13D by a specialist small-bank activist (Stilwell, PL
Capital, Driver, Basswood); buy the next open, hold 120 sessions, vs KRE (dividend-adjusted).

    PYTHONPATH=. .venv/bin/python -m research.sim.goal_g47 build|select|judge
"""
from __future__ import annotations

import pathlib
import re
import sys

import numpy as np
import pandas as pd

from . import book as B
from . import event_fetch as F
from .goal_g45 import adj_bars

ROOT = pathlib.Path(__file__).resolve().parents[2]
PROG = ROOT / "data/research/program"
EVF = PROG / "goal_g47_events.parquet"
ACTIVISTS = ['"Stilwell"', '"PL Capital"', '"Driver Management"', '"Basswood"']
ACT_RE = re.compile(r"stilwell|pl capital|driver management|driver opportunity|basswood", re.I)
HOLD = 120
WIN = {"select": ("2021-01-01", "2023-12-31"), "judge": ("2024-01-01", "2026-09-30"), "holdout": ("2016-01-01", "2020-12-31")}


def out():
    f = open(PROG / "goal_g47_out.txt", "a")

    def log(*a):
        x = " ".join(str(i) for i in a)
        print(x, flush=True); f.write(x + "\n"); f.flush()
    return log


def build():
    log = out()
    log(f"=== G47 build {pd.Timestamp.now():%Y-%m-%d %H:%M} ===")
    H = []
    for q in ACTIVISTS:
        H += F.fts_years(q, "SC 13D,SCHEDULE 13D")
    H = [h for h in {r["id"]: r for r in H}.values() if h["form"] in ("SC 13D", "SCHEDULE 13D")]
    rows = []
    for h in H:
        subj = [n for n in h["names"] if not ACT_RE.search(n) and F.ticker_of(n)]
        act = next((m.group(0).lower() for n in h["names"] for m in [ACT_RE.search(n)] if m), None)
        if subj and act:
            rows.append(dict(sym=F.ticker_of(subj[0])[0].replace("-", "."), name=subj[0][:40], act=act, fd=pd.Timestamp(h["date"])))
    E = pd.DataFrame(rows).sort_values("fd").drop_duplicates(["sym", "act"])
    log(f"  13D originals with a listed subject: {len(E)}")
    k = adj_bars("KRE"); k.index = pd.DatetimeIndex(k.index)
    raw = F.raw_bars(sorted(E.sym.unique()))
    out_rows = []
    for r in E.itertuples():
        b = adj_bars(r.sym)
        if not len(b):
            continue
        b.index = pd.DatetimeIndex(b.index); b = b.sort_index()
        i = b.index.searchsorted(r.fd + pd.Timedelta(days=1))
        if i < 20 or i + HOLD - 1 >= len(b) or (b.index[i] - r.fd).days > 7:
            continue
        d, dx = b.index[i], b.index[i + HOLD - 1]
        if d not in k.index or dx not in k.index:
            continue
        rb = raw.get(r.sym)
        if rb is None or len(rb) < 25:
            continue
        rb = rb.sort_index(); rb.index = pd.DatetimeIndex(rb.index)
        h20 = rb.loc[:d].iloc[-21:-1]
        adv, px = float((h20.close * h20.volume).mean()), float(h20.close.iloc[-1])
        if adv < 2e5:
            continue
        out_rows.append(dict(sym=r.sym, name=r.name, act=r.act, fd=r.fd, d=d, ret=b.close.iloc[i + HOLD - 1] / b.open.iloc[i] - 1,
                             bench=k.close.loc[dx] / k.open.loc[d] - 1, adv=adv, px=px))
    T = pd.DataFrame(out_rows)
    T.to_parquet(EVF)
    log(f"  events {len(T)} by year {T.groupby(T.d.dt.year).size().to_dict()}; by activist {T.act.value_counts().to_dict()}")


def look(name):
    log = out()
    log(f"\n=== G47 {name.upper()} {pd.Timestamp.now():%Y-%m-%d %H:%M} (one look) ===")
    T = pd.read_parquet(EVF)
    halves = ["select"] if name == "select" else ["judge", "holdout"]
    for h in halves:
        a, b = WIN[h]
        V = T[(T.d >= a) & (T.d <= b)].copy()
        cb = B.cost_bps("tier", V.px.values, V.adv.values) / 1e4
        V["x"] = V.ret - V.bench - 2 * cb
        dm = V.groupby("d").x.mean()
        t = dm.mean() / (dm.std(ddof=1) / np.sqrt(len(dm))) if len(dm) > 2 else np.nan
        ex5 = V.x.sort_values().iloc[:-5].mean() if len(V) > 5 else np.nan
        log(f"  {h}: n {len(V)} | mean {V.x.mean():+.2%} median {V.x.median():+.2%} hit {(V.x > 0).mean():.0%} date-t {t:+.2f} "
            f"ex-best-5 {ex5:+.2%} worst {V.x.min():+.1%} | by year " +
            " ".join(f"{y}:{m:+.1%}({n})" for y, (m, n) in V.groupby(V.d.dt.year).x.agg(['mean', 'count']).iterrows()))
        if h == "select":
            ok = len(V) >= 20 and V.x.mean() >= 0.03 and t >= 2
            log(f"  select gate {'PASS -> judge' if ok else 'FAIL -> dead'}")


if __name__ == "__main__":
    {"build": build, "select": lambda: look("select"), "judge": lambda: look("judge")}[sys.argv[1]]()
