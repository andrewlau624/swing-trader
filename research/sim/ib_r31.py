"""Index-beat R3-1: hold the live noise leg's 15:59 position to the next open (explore, select 2021-23 only).

    PYTHONPATH=. .venv/bin/python -m research.sim.ib_r31
Spec: research/drafts/index_beat_log.md (R3-1).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import data as D
from .taxable_frontier import nw_t


def eod_pos(sym, lookback=14, target_vol=0.02):
    M = D.minutes(sym)
    C, V = M["close"].values, M["volume"].values
    O = M["open"].values[:, 0]
    days = M["close"].index
    move = np.abs(C / O[:, None] - 1)
    dclose = pd.Series(C[:, -1], index=days)
    prevc = np.r_[np.nan, C[:-1, -1]]
    vwap = np.cumsum(C * V, axis=1) / np.maximum(np.cumsum(V, axis=1), 1)
    rows = []
    for i in range(lookback + 1, len(days) - 1):
        sigma = sg.noise_sigma(move[i - lookback:i])
        ub, lb = sg.noise_bounds(O[i], prevc[i], sigma)
        lev = sg.noise_leverage(dclose.iloc[:i], target_vol, 1e9)
        pos = 0
        for m in range(sg.NOISE_FIRST, 390, sg.NOISE_STEP):
            pos = sg.noise_decide(pos, C[i, m], ub[m], lb[m], vwap[i, m])
        rows.append((days[i], pos, lev, O[i + 1] / C[i, 389] - 1))
    return pd.DataFrame(rows, columns=["date", "pos", "lev", "on"]).set_index("date")


def main():
    inc = None
    for sym in ("QQQ", "SMH"):
        e = eod_pos(sym)
        x = e.pos * e.lev.clip(upper=0.75) * 0.5 * e.on - (e.pos != 0) * e.lev.clip(upper=0.75) * 0.5 * 0.12 / 252
        s = e["2021-01-01":"2023-12-31"]; xs = x["2021-01-01":"2023-12-31"]
        held = s.pos != 0
        print(f"{sym}: in at 15:59 on {held.mean():.0%} of days; overnight return when long {s.on[s.pos > 0].mean() * 1e4:+.1f}bp "
              f"(n {(s.pos > 0).sum()}), when short {(-s.on[s.pos < 0]).mean() * 1e4:+.1f}bp (n {(s.pos < 0).sum()}); "
              f"all-days overnight {s.on.mean() * 1e4:+.1f}bp")
        inc = xs if inc is None else inc.add(xs, fill_value=0)
    yrs = inc.groupby(inc.index.year).sum() * 100
    print(f"increment (fraction of equity): {inc.sum() / 3 * 100:+.2f}pp/yr, NW t {nw_t(inc):+.2f}; by year "
          + " ".join(f"{y}: {v:+.2f}pp" for y, v in yrs.items()))


if __name__ == "__main__":
    main()
