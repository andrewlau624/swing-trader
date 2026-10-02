"""Jump hunt standing rule: a MEETS is registered only if it beats a SAME-DAY control on the select half.

Control = up to 400 symbols sampled from the idea's own event file (same kind of stock), each bought on every event
entry day where it has no event of its own within +-10 sessions, same hold and rule, same costs. Report: event net by
year, event minus the same-day control mean (per event, the control's mean that day), median, share above, and a
bootstrap P(mean difference <= 0). Pass = bootstrap P < 0.10. Select half only (fd 2016-01-01..2023-12-31).

    PYTHONPATH=. .venv/bin/python -m research.sim.jump_control EVENTS.parquet HOLD RULE
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from . import jump_runner as J


def run(path: str, hold: int, rule: str, lo="2016-01-01", hi="2023-12-31", seed: int = 1) -> dict:
    lo, hi = pd.Timestamp(lo), pd.Timestamp(hi)
    col = f"{rule}{hold}"
    X = J.load(path)
    T, _ = J.trades(X, lo, hi, holds=(hold,), rules=(rule,), base=False)
    T["net"] = T[col] - T.adv.map(J.cost_side) * 2
    syms = sorted(X.sym.unique())
    rng = np.random.default_rng(seed)
    cs = list(rng.choice(syms, size=min(400, len(syms)), replace=False))
    ev = {s: set(g.fd) for s, g in X.groupby("sym")}
    rows = []
    for d in sorted(T.d.unique()):
        for s in cs:
            near = ev.get(s, set())
            if not any(abs((d - f).days) <= 15 for f in near):
                rows.append(dict(sym=s, fd=pd.Timestamp(d) - pd.Timedelta(days=1)))
    C = pd.DataFrame(rows)
    TC, _ = J.trades(C, lo, hi, holds=(hold,), rules=(rule,), base=False)
    TC = TC[TC.d.isin(T.d)]
    TC["net"] = TC[col] - TC.adv.map(J.cost_side) * 2
    T["ctrl"] = T.d.map(TC.groupby("d").net.mean())
    diff = (T.net - T.ctrl).dropna().to_numpy()
    bs = diff[np.random.default_rng(0).integers(0, len(diff), (4000, len(diff)))].mean(1)
    out = dict(n=len(T), n_ctrl=len(TC), event=float(T.net.mean()), control=float(TC.net.mean()),
               diff=float(diff.mean()), diff_median=float(np.median(diff)), above=float((diff > 0).mean()),
               p=float((bs <= 0).mean()))
    print("event net by year:", T.groupby(T.d.dt.year).net.agg(["count", "mean", "median"]).round(3).T.to_string())
    print(f"{col}: events {out['n']} mean {out['event']:+.4f}; same-day control {out['n_ctrl']} trades mean "
          f"{out['control']:+.4f}; event minus control mean {out['diff']:+.4f} median {out['diff_median']:+.4f} "
          f"above {out['above']:.2f} bootstrap P {out['p']:.3f} -> {'PASSES' if out['p'] < 0.10 else 'FAILS'} the control")
    return out


if __name__ == "__main__":
    run(sys.argv[1], int(sys.argv[2]), sys.argv[3])
