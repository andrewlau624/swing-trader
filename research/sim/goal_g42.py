"""Goal hunt Studies G42 / G43 (pre-registered in round1_prose.md, commit c1e1259): officer/director buys >= $500k in names
with ADV $1-20M (G42) or >= 0.5% of market cap with ADV >= $2M (G43); buy the next session's open, hold 5, vs SPY.

    PYTHONPATH=. .venv/bin/python -m research.sim.goal_g42 build
    PYTHONPATH=. .venv/bin/python -m research.sim.goal_g42 select     # 2021-23, one look each

Output: data/research/program/goal_g42_out.txt
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

from . import book as B
from . import event_fetch as F
from .goal_g12 import buys

ROOT = pathlib.Path(__file__).resolve().parents[2]
PROG = ROOT / "data/research/program"
EVF = PROG / "goal_g42_events.parquet"
SEL = ("2021-01-01", "2023-12-31")
HOLD = 5


def out():
    f = open(PROG / "goal_g42_out.txt", "a")

    def log(*a):
        x = " ".join(str(i) for i in a)
        print(x, flush=True); f.write(x + "\n"); f.flush()
    return log


def build():
    from .jump_common import shares_hist
    log = out()
    log(f"=== G42/G43 build {pd.Timestamp.now():%Y-%m-%d %H:%M} ===")
    X = buys()
    E = X[X.insider & (X.usd > 0)].groupby(["sym", "fd"]).usd.sum().reset_index()
    E = E[E.usd >= 1e5]
    SH = shares_hist().sort_values("end")
    sh = {s: g for s, g in SH.groupby("sym")}
    bars = F.raw_bars(sorted(E.sym.unique()))
    rows = []
    for r in E.itertuples():
        b = bars.get(r.sym)
        if b is None or not len(b):
            continue
        b = b.sort_index(); idx = pd.DatetimeIndex(b.index)
        i = idx.searchsorted(r.fd + pd.Timedelta(days=1))
        if i < 20 or i + HOLD - 1 >= len(idx) or (idx[i] - r.fd).days > 7:
            continue
        h = b.iloc[i - 20:i]
        pc, adv = b.close.iloc[i - 1], (h.close * h.volume).mean()
        if pc < 5:
            continue
        seg = b.close.iloc[i - 1:i + HOLD]
        rr = (seg / seg.shift(1)).dropna()
        if ((rr > 1.8) | (rr < 0.55)).any():
            continue
        g = sh.get(r.sym)
        so = np.nan
        if g is not None:
            g = g[g.end <= r.fd]
            if len(g):
                so = float(g.shares.iloc[-1])
        rows.append(dict(sym=r.sym, fd=r.fd, d=idx[i], dx=idx[i + HOLD - 1], usd=r.usd, adv=adv, pc=pc, mcap=pc * so,
                         o=b.open.iloc[i], c1=b.close.iloc[i], c5=b.close.iloc[i + HOLD - 1]))
    T = pd.DataFrame(rows)
    T.to_parquet(EVF)
    g42, g43 = variants(T)
    log(f"  events with bars {len(T)}; G42 {len(g42)} by year {g42.groupby(g42.d.dt.year).size().to_dict()}")
    log(f"  G43 {len(g43)} by year {g43.groupby(g43.d.dt.year).size().to_dict()} (mcap known for {T.mcap.notna().mean():.0%})")


def variants(T):
    g42 = T[(T.usd >= 5e5) & (T.adv >= 1e6) & (T.adv < 2e7)]
    g43 = T[(T.usd >= 0.005 * T.mcap) & (T.adv >= 2e6)]
    return g42, g43


def select():
    from .goal_g2 import spy_adj
    log = out()
    log(f"\n=== G42/G43 SELECT 2021-23 {pd.Timestamp.now():%Y-%m-%d %H:%M} (one look each) ===")
    T = pd.read_parquet(EVF)
    S = spy_adj(); S.index = pd.DatetimeIndex(S.index)
    for lab, V in zip(("G42 >= $500k, ADV $1-20M", "G43 >= 0.5% of market cap"), variants(T)):
        V = V[(V.d >= SEL[0]) & (V.d <= SEL[1])].copy()
        prev = np.array([S.loc[:d].iloc[-2] for d in V.d])
        cb = B.cost_bps("tier", V.o.values, V.adv.values) / 1e4
        V["x5"] = (V.c5 / V.o - 1).values - (S.reindex(V.dx).values / prev - 1) - 2 * cb
        V["x1"] = (V.c1 / V.o - 1).values - (S.reindex(V.d).values / prev - 1) - 2 * cb
        dm = V.groupby("d").x5.mean()
        t = dm.mean() / (dm.std(ddof=1) / np.sqrt(len(dm)))
        log(f"  {lab}: n {len(V)} | hold5 mean {V.x5.mean():+.2%} median {V.x5.median():+.2%} hit {(V.x5 > 0).mean():.0%} "
            f"date-t {t:+.2f} worst {V.x5.min():+.1%} | by year " +
            " ".join(f"{y}:{m:+.2%}" for y, m in V.groupby(V.d.dt.year).x5.mean().items()) +
            f" | hold1 (report) mean {V.x1.mean():+.2%} median {V.x1.median():+.2%}")
        ok = len(V) >= 40 and V.x5.mean() >= 0.01 and t >= 2
        log(f"  {lab.split()[0]} select gate {'PASS -> judge' if ok else 'FAIL -> dead'}")


if __name__ == "__main__":
    {"build": build, "select": select}[sys.argv[1]]()
