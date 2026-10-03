"""Goal hunt Study G53 (pre-registered in round1_prose.md): first 13D on a closed-end fund by any filer other than G45's six
activists; buy the next open, hold 60, vs PCEF (dividend-adjusted).

    PYTHONPATH=. .venv/bin/python -m research.sim.goal_g53 build|select|judge
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

from . import book as B
from . import event_fetch as F
from .goal_g45 import ACT_RE, FUND_RE, adj_bars

ROOT = pathlib.Path(__file__).resolve().parents[2]
PROG = ROOT / "data/research/program"
EVF = PROG / "goal_g53_events.parquet"
HOLD = 60
WIN = {"select": ("2021-01-01", "2023-12-31"), "judge": ("2024-01-01", "2026-09-30"), "holdout": ("2016-01-01", "2020-12-31")}


def out():
    f = open(PROG / "goal_g53_out.txt", "a")

    def log(*a):
        x = " ".join(str(i) for i in a)
        print(x, flush=True); f.write(x + "\n"); f.flush()
    return log


def build():
    log = out()
    log(f"=== G53 build {pd.Timestamp.now():%Y-%m-%d %H:%M} ===")
    tk = F.company_tickers()
    rows = []
    for y in range(2016, 2027):
        for q in range(1, 5):
            if (y, q) > (2026, 3):
                continue
            D = F.full_index(y, q)
            if not len(D):
                continue
            D = D[D.form.isin(["SC 13D", "SCHEDULE 13D"])]
            D = D.assign(acc=D.path.str.split("/").str[-1])
            for p, g in D.groupby("acc"):
                subj = [r for r in g.itertuples() if str(int(r.cik)) in tk and FUND_RE.search(r.company)]
                filers = [r for r in g.itertuples() if not (str(int(r.cik)) in tk and FUND_RE.search(r.company))]
                if len(subj) != 1 or not filers or any(ACT_RE.search(f.company) for f in filers):
                    continue
                s = subj[0]
                rows.append(dict(sym=tk[str(int(s.cik))][0], subj=s.company[:40], filer=filers[0].company[:40],
                                 fd=pd.Timestamp(s.date)))
    E = pd.DataFrame(rows).sort_values("fd").drop_duplicates(["sym", "filer"])
    log(f"  first 13Ds on fund-like subjects by non-G45 filers: {len(E)}")
    pc = adj_bars("PCEF"); pc.index = pd.DatetimeIndex(pc.index)
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
        if d not in pc.index or dx not in pc.index:
            continue
        rb = raw.get(r.sym)
        adv = px = np.nan
        if rb is not None and len(rb) > 21:
            rb = rb.sort_index(); rb.index = pd.DatetimeIndex(rb.index)
            h20 = rb.loc[:d].iloc[-21:-1]
            if len(h20):
                adv, px = float((h20.close * h20.volume).mean()), float(h20.close.iloc[-1])
        out_rows.append(dict(sym=r.sym, subj=r.subj, filer=r.filer, fd=r.fd, d=d, ret=b.close.iloc[i + HOLD - 1] / b.open.iloc[i] - 1,
                             bench=pc.close.loc[dx] / pc.open.loc[d] - 1, adv=adv, px=px))
    T = pd.DataFrame(out_rows)
    T.to_parquet(EVF)
    log(f"  events with bars {len(T)} by year {T.groupby(T.d.dt.year).size().to_dict()}")
    log("  top filers: " + ", ".join(f"{k} {v}" for k, v in T.filer.value_counts().head(8).items()))


def look(name):
    log = out()
    log(f"\n=== G53 {name.upper()} {pd.Timestamp.now():%Y-%m-%d %H:%M} (one look) ===")
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
