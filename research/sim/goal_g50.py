"""Goal hunt Studies G50 / G51 (pre-registered in round1_prose.md, commit 846f336): escalation points of CEF activist
campaigns. G50 = the activist's stake first reported >= 15%; G51 = the first proxy-contest filing. Hold 60 vs PCEF.

    PYTHONPATH=. .venv/bin/python -m research.sim.goal_g50 build|select|judge
"""
from __future__ import annotations

import pathlib
import re
import sys

import numpy as np
import pandas as pd

from . import book as B
from . import event_fetch as F
from .goal_g45 import ACT_RE, ACTIVISTS, FUND_RE, adj_bars

ROOT = pathlib.Path(__file__).resolve().parents[2]
PROG = ROOT / "data/research/program"
EVF = PROG / "goal_g50_events.parquet"
HOLD = 60
PCT = re.compile(r"percent\s+of\s+class\s+represented\s+by\s+amount\s+in\s+row\s*\(?\s*(?:11|13)\s*\)?[^0-9]{0,80}(\d{1,2}(?:\.\d+)?)\s*%", re.I)
WIN = {"select": ("2021-01-01", "2023-12-31"), "judge": ("2024-01-01", "2026-09-30"), "holdout": ("2016-01-01", "2020-12-31")}


def out():
    f = open(PROG / "goal_g50_out.txt", "a")

    def log(*a):
        x = " ".join(str(i) for i in a)
        print(x, flush=True); f.write(x + "\n"); f.flush()
    return log


def subject(h):
    subj = [n for n in h["names"] if not ACT_RE.search(n) and F.ticker_of(n) and FUND_RE.search(n)]
    act = next((m.group(0).lower() for n in h["names"] for m in [ACT_RE.search(n)] if m), None)
    return (F.ticker_of(subj[0])[0].replace("-", "."), act) if subj and act else (None, None)


def g50_events(log):
    H = []
    for q in ACTIVISTS:
        H += F.fts_years(q, "SC 13D,SC 13D/A,SCHEDULE 13D,SCHEDULE 13D/A")
    H = list({r["id"]: r for r in H}.values())
    rows = []
    for j, h in enumerate(H):
        sym, act = subject(h)
        if not sym:
            continue
        adsh, name = h["id"].split(":", 1)
        m = PCT.search(F.doc(h["ciks"][0], adsh, name)[:8000])
        rows.append(dict(sym=sym, act=act, fd=pd.Timestamp(h["date"]), pct=float(m.group(1)) if m else np.nan))
        if j % 300 == 0:
            print(f"  docs {j}/{len(H)}", flush=True)
    D = pd.DataFrame(rows).sort_values("fd")
    log(f"  13D/13D-A filings on fund subjects {len(D)}; percent parsed {D.pct.notna().mean():.0%}")
    ev = []
    for (s, a), g in D.dropna(subset=["pct"]).groupby(["sym", "act"]):
        hit = g[g.pct >= 15.0]
        if len(hit) and (g[g.fd < hit.fd.iloc[0]].pct < 15.0).all():
            ev.append(dict(sym=s, act=a, fd=hit.fd.iloc[0], kind="G50"))
    return ev


def g51_events():
    H = []
    for q in ACTIVISTS:
        H += F.fts_years(q, "PREC14A,DEFC14A,DFAN14A")
    ev = {}
    for h in {r["id"]: r for r in H}.values():
        sym, act = subject(h)
        if sym:
            k = (sym, act)
            d = pd.Timestamp(h["date"])
            if k not in ev or d < ev[k]:
                ev[k] = d
    return [dict(sym=s, act=a, fd=d, kind="G51") for (s, a), d in ev.items()]


def build():
    log = out()
    log(f"=== G50/G51 build {pd.Timestamp.now():%Y-%m-%d %H:%M} ===")
    E = pd.DataFrame(g50_events(log) + g51_events())
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
            adv, px = float((h20.close * h20.volume).mean()), float(h20.close.iloc[-1])
        rows.append(dict(kind=r.kind, sym=r.sym, act=r.act, fd=r.fd, d=d, ret=b.close.iloc[i + HOLD - 1] / b.open.iloc[i] - 1,
                         bench=pc.close.loc[dx] / pc.open.loc[d] - 1, adv=adv, px=px))
    T = pd.DataFrame(rows)
    T.to_parquet(EVF)
    for k, g in T.groupby("kind"):
        log(f"  {k}: events {len(g)} by year {g.groupby(g.d.dt.year).size().to_dict()}")


def look(name):
    log = out()
    log(f"\n=== G50/G51 {name.upper()} {pd.Timestamp.now():%Y-%m-%d %H:%M} (one look each) ===")
    T = pd.read_parquet(EVF)
    g45 = pd.read_parquet(PROG / "goal_g45_events.parquet")
    for kind, G in T.groupby("kind"):
        for h in (["select"] if name == "select" else ["judge", "holdout"]):
            a, b = WIN[h]
            V = G[(G.d >= a) & (G.d <= b)].copy()
            if not len(V):
                log(f"  {kind} {h}: n 0"); continue
            cb = B.cost_bps("tier", V.px.fillna(10).values, V.adv.fillna(1e6).values) / 1e4
            V["x"] = V.ret - V.bench - 2 * cb
            dm = V.groupby("d").x.mean()
            t = dm.mean() / (dm.std(ddof=1) / np.sqrt(len(dm))) if len(dm) > 2 else np.nan
            ex5 = V.x.sort_values().iloc[:-5].mean() if len(V) > 5 else np.nan
            ov = sum(((g45.sym == r.sym) & (g45.d <= r.d) & (g45.d >= r.d - pd.Timedelta(days=90))).any() for r in V.itertuples())
            log(f"  {kind} {h}: n {len(V)} | mean {V.x.mean():+.2%} median {V.x.median():+.2%} hit {(V.x > 0).mean():.0%} date-t {t:+.2f} "
                f"ex-best-5 {ex5:+.2%} | inside an open G45 window: {ov} | by year " +
                " ".join(f"{y}:{m:+.1%}({n})" for y, (m, n) in V.groupby(V.d.dt.year).x.agg(['mean', 'count']).iterrows()))
            if h == "select":
                ok = len(V) >= 20 and V.x.mean() >= 0.02 and t >= 2
                log(f"  {kind} select gate {'PASS -> judge' if ok else 'FAIL -> dead'}")


if __name__ == "__main__":
    {"build": build, "select": lambda: look("select"), "judge": lambda: look("judge")}[sys.argv[1]]()
