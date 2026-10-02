"""Jump hunt H17: trade-count spike with a quiet price (attention-first, RIDE).

Event (decided after the close of session d, traded at the next open): trade_count >= 5x its median over the prior
60 sessions (median >= 50 trades), |close/prev close - 1| < 3%, close in the middle half of the day's range, and no
H17 event in the same stock in the prior 30 days. Night panel (SIP daily, 2020-10..2026-09), stocks only.

    PYTHONPATH=. .venv/bin/python -m research.sim.jump_h17
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .jump_common import ROOT, first_in, save, stock_symbols


def build() -> pd.DataFrame:
    P = pd.read_pickle(ROOT / "data/research/night/panel.pkl")
    cols = sorted(set(P["close"].columns) & stock_symbols())
    tc, c, h, l = (P[k][cols] for k in ("trade_count", "close", "high", "low"))
    med = tc.rolling(60, min_periods=40).median().shift(1)
    ret = c / c.shift(1) - 1
    loc = (c - l) / (h - l).replace(0, np.nan)
    ev = (tc >= 5 * med) & (med >= 50) & (ret.abs() < 0.03) & (loc >= 0.25) & (loc <= 0.75)
    s = ev.stack()
    E = s[s].reset_index()
    E.columns = ["fd", "sym", "_"]
    return first_in(E[["sym", "fd"]], 30)


if __name__ == "__main__":
    save(build(), "h17")
