"""Index-beat R2-7: spin-offs bought ~20 sessions after first regular-way trading, held 260 sessions (long-term).

    PYTHONPATH=. .venv/bin/python -m research.sim.ib_r27 explore      # select entries 2021-01..2022-12 only
Spec: research/drafts/index_beat_ideas_r2.md (written before any spin-off bar was fetched).
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from . import event_fetch as F
from .jump_runner import cost_side, split_bars

SELECT = (pd.Timestamp("2021-01-01"), pd.Timestamp("2022-12-31"))


def spincos():
    H = []
    for q in ('"spin-off"', '"spin off"'):
        H += F.fts_years(q, "10-12B,10-12B/A", 2016, 2026)
    H = list({h["id"]: h for h in H}.values())
    first, tk = {}, {}
    for h in H:
        for nm in h["names"]:
            for t in F.ticker_of(nm):
                t = t.replace("-", ".")
                if "." in t or len(t) > 5:
                    continue
                first[t] = min(first.get(t, h["date"]), h["date"])
    return pd.Series(first).map(pd.Timestamp)


def table(entry_lag=20, hold=260):
    S = spincos()
    bars = split_bars(sorted(S.index) + ["SPY"])
    spy = bars["SPY"]["close"]; spy.index = pd.to_datetime(spy.index)
    rows = []
    for t, f0 in S.items():
        b = bars.get(t)
        if b is None or len(b) < entry_lag + hold + 5:
            continue
        b = b.copy(); b.index = pd.to_datetime(b.index)
        b = b[b.index >= f0 - pd.Timedelta(days=5)]           # trading that starts after the Form 10
        if len(b) < entry_lag + hold + 1 or b.index[0] < f0 - pd.Timedelta(days=5):
            continue
        d0 = b.index[0]
        if (d0 - f0).days > 400:                              # an old listed company filing a Form 10/A: not a new SpinCo
            continue
        e, x = b.index[entry_lag], b.index[entry_lag + hold]
        r = b.close.iloc[entry_lag + hold] / b.close.iloc[entry_lag] - 1
        rs = spy.asof(x) / spy.asof(e) - 1
        adv = float((b.close * b.volume).iloc[:entry_lag].median())
        rows.append(dict(sym=t, form10=f0, d0=d0, entry=e, exit=x, ret=r, spy=rs, adv=adv,
                         net=r - rs - 2 * cost_side(adv)))
    return pd.DataFrame(rows)


def explore():
    for lag in (20, 5):
        T = table(lag)
        s = T[(T.entry >= SELECT[0]) & (T.entry <= SELECT[1])]
        top3 = s.net.nlargest(3).index
        print(f"entry d0+{lag}: spin-offs with bars (all years) {len(T)}; SELECT entries {len(s)}: mean excess net "
              f"{s.net.mean() * 100:+.1f}%, median {s.net.median() * 100:+.1f}%, hit {(s.net > 0).mean():.0%}, "
              f"ex-top-3 {s.net.drop(top3).mean() * 100:+.1f}%; by entry year "
              + " ".join(f"{y}: {g.mean() * 100:+.1f}% (n {len(g)})" for y, g in s.net.groupby(s.entry.dt.year)))
        print("   ", ", ".join(f"{r.sym} {r.net * 100:+.0f}%" for r in s.sort_values("net").itertuples()))


if __name__ == "__main__":
    explore()
