"""Goal hunt Study G31 (pre-registered in round1_prose.md, commit b9ccd52): follow-on offering pricings; buy the entry
session's open if it is within 1% of the offer price, exit at the first close < 0.97 x offer or the 3rd session's close.

    PYTHONPATH=. .venv/bin/python -m research.sim.goal_g31 build
    PYTHONPATH=. .venv/bin/python -m research.sim.goal_g31 select     # 2021-23, one look

Output: data/research/program/goal_g31_out.txt
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
EVF = PROG / "goal_g31_events.parquet"
Q = '"announces pricing" "public offering" "common stock" "per share"'
PX = re.compile(r"pric\w*[^$]{0,250}?\$\s?(\d{1,4}(?:\.\d{1,4})?)\s+per\s+share", re.I)
SEL = ("2021-01-01", "2023-12-31")


def out():
    f = open(PROG / "goal_g31_out.txt", "a")

    def log(*a):
        x = " ".join(str(i) for i in a)
        print(x, flush=True); f.write(x + "\n"); f.flush()
    return log


def build():
    log = out()
    log(f"=== G31 build {pd.Timestamp.now():%Y-%m-%d %H:%M} ===")
    H = F.fts_years(Q, "8-K")
    log(f"  fts hits {len(H)}")
    rows = []
    for j, h in enumerate(H):
        tk = F.ticker_of(h["names"][0]) if h["names"] else []
        if not tk:
            continue
        adsh, name = h["id"].split(":", 1)
        t = F.doc(h["ciks"][0], adsh, name)
        if re.search(r"preferred stock|depositary shares|warrants? to purchase|pre-funded", t[:3000], re.I):
            continue                                              # common stock offerings only (units / preferred out)
        m = PX.search(t)
        if not m:
            continue
        acc = F.accepted_et(F.hdr(h["ciks"][0], adsh))
        rows.append(dict(sym=tk[0].replace("-", "."), fd=pd.Timestamp(h["date"]), px=float(m.group(1)), acc=acc))
        if j % 300 == 0:
            print(f"  docs {j}/{len(H)}", flush=True)
    E = pd.DataFrame(rows).sort_values(["sym", "fd"])
    keep, last = [], {}
    for r in E.itertuples():
        if r.sym in last and (r.fd - last[r.sym]).days <= 30:
            continue
        last[r.sym] = r.fd
        keep.append(r.Index)
    E = E.loc[keep]
    bars = F.raw_bars(sorted(E.sym.unique()))
    out_rows = []
    for r in E.itertuples():
        b = bars.get(r.sym)
        if b is None or not len(b):
            continue
        b = b.sort_index(); idx = pd.DatetimeIndex(b.index)
        pre = r.acc is not None and not pd.isna(r.acc) and (r.acc.hour * 60 + r.acc.minute) < 570
        i = idx.searchsorted(r.fd) if pre else idx.searchsorted(r.fd + pd.Timedelta(days=1))
        if i < 20 or i + 2 >= len(idx) or (idx[i] - r.fd).days > 7:
            continue                                              # IPOs (< 20 prior sessions) and stale events dropped
        h20 = b.iloc[i - 20:i]
        o = b.open.iloc[i]
        cl = b.close.iloc[i:i + 3].values
        stop = next((k for k in range(3) if cl[k] < 0.97 * r.px), None)
        ex = cl[stop] if stop is not None else cl[2]
        out_rows.append(dict(sym=r.sym, fd=r.fd, d=idx[i], px=r.px, o=o, ex=ex, pc=b.close.iloc[i - 1],
                             adv=(h20.close * h20.volume).mean(), near=abs(o / r.px - 1) <= 0.01))
    T = pd.DataFrame(out_rows)
    T = T[(T.px / T.pc).between(0.5, 1.2)]                       # parse guard: offer within 50-120% of the prior close
    T.to_parquet(EVF)
    log(f"  events {len(T)} (open within 1% of offer: {int(T.near.sum())}) by year {T.groupby(T.d.dt.year).size().to_dict()}")


def select():
    log = out()
    log(f"\n=== G31 SELECT 2021-23 {pd.Timestamp.now():%Y-%m-%d %H:%M} (one look) ===")
    T = pd.read_parquet(EVF)
    V = T[(T.d >= SEL[0]) & (T.d <= SEL[1])]
    for lab, X in (("G31 open within 1% of offer", V[V.near]), ("all events (report)", V)):
        cb = B.cost_bps("tier", X.o.values, X.adv.values) / 1e4
        x = (X.ex / X.o - 1).values - 2 * cb
        t = x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else np.nan
        yrs = pd.Series(x, index=X.d.dt.year.values).groupby(level=0).agg(["mean", "count"])
        log(f"  {lab}: n {len(x)} mean {x.mean():+.2%} median {np.median(x):+.2%} hit {(x > 0).mean():.0%} t {t:+.2f} worst {x.min():+.1%} | "
            + " ".join(f"{y}:{m:+.1%}({n})" for y, (m, n) in yrs.iterrows()))
        if lab.startswith("G31"):
            ok = len(x) >= 40 and x.mean() >= 0.0075 and t >= 2
            log(f"  select gate {'PASS -> judge' if ok else 'FAIL -> dead'}")


if __name__ == "__main__":
    {"build": build, "select": select}[sys.argv[1]]()
