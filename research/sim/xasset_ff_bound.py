"""XASSET-FF: perfect-foresight ceiling bounds for non-equity forced-flow ideas (no N, no conditional outcome read).

Bound = windows/yr x E|log return over the window| x 100% deployed x 50% capture, i.e. the %/yr a rule would earn
if it called the SIGN of every window perfectly. If the bound is < +8pp/yr at $10k the idea is ceiling-killed
without a backtest (CLAUDE.md research-priority gate). Carry-unwind bound = episodes/yr x full 20d-high -> 20d-low
drop x 50% (100% reversal of the whole crash). Free Yahoo daily closes via tme_treasury.fetch_px; cache
data/research/xasset_ff/. Output data/research/program/xasset_ff_out.txt.
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from tme_treasury import fetch_px  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data/research/xasset_ff"
OUT = ROOT / "data/research/program/xasset_ff_out.txt"
CAP = 0.5


def px(t: str) -> pd.Series:
    f = D / f"px_{t.replace('=', '_').replace('^', '')}.csv"
    if not f.exists():
        D.mkdir(parents=True, exist_ok=True)
        fetch_px(t, "2003-01-01").to_csv(f)
    return pd.read_csv(f, parse_dates=["date"]).set_index("date")["adjclose"].dropna()


def abs_window(t: str, n: int) -> float:
    lc = np.log(px(t))
    return float(lc.diff(n).abs().mean())


def carry(t: str) -> tuple[int, float, float]:
    c = px(t); lc = np.log(c); yrs = (c.index[-1] - c.index[0]).days / 365.25
    trig = (lc.diff(5) < -0.05).to_numpy(); ev, last = [], -999
    for i, f in enumerate(trig):
        if f and i - last > 20:
            ev.append(i)
        if f:
            last = i
    drops = [np.log(c.iloc[max(0, i - 20):i + 1].max() / c.iloc[i:i + 21].min()) for i in ev]
    return len(ev), len(ev) / yrs, float(np.mean(drops))


def main() -> str:
    L = ["XASSET-FF perfect-foresight ceiling bounds (sign of every window known; 100% deployed; 50% capture)", ""]
    rows = [  # name, ticker, windows/yr, window sessions
        ("C-FIX month-end WM/R FX hedge rebalance (EUR)", "FXE", 12, 1),
        ("C-FIX month-end, 3-day window", "FXE", 12, 3),
        ("C-QE quarter-end USD funding squeeze", "UUP", 4, 5),
        ("C-BCOM Jan index reweight, silver (5 roll days + 5 pre)", "SLV", 1, 10),
        ("C-BCOM Jan reweight, gold", "GLD", 1, 10),
        ("C-MUNI Jun-Aug / Dec-Jan reinvestment season", "MUB", 2, 21),
        ("ref: TME window on TLT (3 sessions, already VALIDATED +32bp/mo)", "TLT", 12, 3),
    ]
    for name, t, k, n in rows:
        a = abs_window(t, n)
        L.append(f"{name:<62} {t:<4} E|r_{n}d| {a*1e4:6.1f}bp  x {k:>2}/yr  -> bound {k*a*CAP*100:5.1f}pp/yr")
    L.append("")
    for t in ["AUDJPY=X", "FXA"]:
        n, py, dmean = carry(t)
        L.append(f"C-CARRY unwind {t:<9} episodes (5d < -5%, 20-session gap) {n} = {py:.2f}/yr, mean full drop {dmean*100:.1f}% "
                 f"-> bound (100% reversal) {py*dmean*CAP*100:.1f}pp/yr; at 2x taxable margin {2*py*dmean*CAP*100:.1f}pp")
    L.append("")
    L.append("Gate: bound < +8pp/yr at $10k -> CEILING-KILL (a perfect-sign bound already exceeds any honest capture).")
    s = "\n".join(L) + "\n"
    OUT.write_text(s)
    return s


if __name__ == "__main__":
    print(main())
