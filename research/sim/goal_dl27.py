"""Goal hunt deal rule DL-G27 (round1_prose.md): mutual savings bank conversions bought at the $10 subscription price,
sold at the first day's close / the 20th session's close.

    PYTHONPATH=. .venv/bin/python -m research.sim.goal_dl27
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from . import book as B
from . import event_fetch as F

ROOT = pathlib.Path(__file__).resolve().parents[2]
Q = '"plan of conversion" "subscription offering" "eligible account holders"'


def main():
    H = F.fts_years(Q, "S-1")
    rows = {}
    for h in H:
        tk = F.ticker_of(h["names"][0]) if h["names"] else []
        cik = h["ciks"][0]
        d = pd.Timestamp(h["date"])
        if cik not in rows or d < rows[cik]["s1"]:
            rows[cik] = dict(cik=cik, name=h["names"][0][:40], s1=d, tk=tk[0] if tk else None)
    E = pd.DataFrame(rows.values())
    tk = F.company_tickers()                                 # cik -> current tickers, for issuers listed later
    E["tk"] = [t if t else (tk.get(str(int(c)), [None]) or [None])[0] for t, c in zip(E.tk, E.cik)]
    E = E.dropna(subset=["tk"])
    bars = F.raw_bars(sorted(E.tk.unique()))
    out = []
    for r in E.itertuples():
        b = bars.get(r.tk)
        if b is None or not len(b):
            continue
        b = b.sort_index(); b.index = pd.DatetimeIndex(b.index)
        if b.index[0] <= r.s1:                                  # traded before the S-1: a second step (old minority
            continue                                            # shares), not a $10 first listing; excluded
        b = b[b.index > r.s1]
        if len(b) < 21 or (b.index[0] - r.s1).days > 365:   # first session must follow the S-1 within a year
            continue
        c1, c20 = b.close.iloc[0], b.close.iloc[19]
        cs = B.cost_bps("tier", np.array([c1]), np.array([1e6]))[0] / 1e4
        out.append(dict(tk=r.tk, name=r.name, ipo=b.index[0], d1=c1 / 10 - 1 - cs, d20=c20 / 10 - 1 - cs, open1=b.open.iloc[0]))
    D = pd.DataFrame(out).sort_values("ipo")
    D.to_csv(ROOT / "data/research/program/goal_dl27_deals.csv", index=False)
    for k in ("d1", "d20"):
        x = D[k]
        print(f"{k}: n {len(x)} mean {x.mean():+.1%} median {x.median():+.1%} hit {(x > 0).mean():.0%} worst {x.min():+.1%} "
              f"({D.loc[x.idxmin(), 'tk']}) best {x.max():+.1%}")
        print("   by year: " + " ".join(f"{y}:{g.median():+.1%}({len(g)})" for y, g in x.groupby(D.ipo.dt.year)))


if __name__ == "__main__":
    main()
