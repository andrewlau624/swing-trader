"""DEEP-PULL (N 1057) + BRK-RETEST (N 1058): the two remaining bounce-tree siblings (round1_prose.md, 2026-10-19).
Run: .venv/bin/python -m research.sim.pull_retest -> data/research/program/pull_retest_out.txt
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

from . import winsig as W
from .hl_bounce import PERIODS, load, pivots

OUT = pathlib.Path(__file__).resolve().parents[2] / "data" / "research" / "program" / "pull_retest_out.txt"
LVL, RLO, RHI, TOL = 50, 3, 30, 1.01


def deep_pull(t: pd.DataFrame) -> dict[str, pd.Series]:
    g = t.groupby("ticker", sort=False)
    hi252 = g["close"].transform(lambda s: s.rolling(252, min_periods=200).max())
    hi60 = g["close"].transform(lambda s: s.rolling(60, min_periods=40).max())
    # state as of the pivot-low bar, carried forward to the signal bar via the pivot segment
    seg = t["pl_bar"]
    at_piv = t["bar"].eq(seg + 3)  # confirmation bar of the current pivot low; hi60/hi252 shifted 3 bars back = as of the pivot bar
    h60p = hi60.groupby(t["ticker"], sort=False).shift(3).where(at_piv)
    h252p = hi252.groupby(t["ticker"], sort=False).shift(3).where(at_piv)
    key = [t["ticker"], seg]
    h60p = h60p.groupby(key, sort=False).ffill()
    h252p = h252p.groupby(key, sort=False).ffill()
    near = h60p >= 0.97 * h252p
    far = h60p < 0.90 * h252p
    depth = t["pl_cur"] / h60p - 1
    deep = depth.between(-0.20, -0.05)
    return {"E1 DEEP-PULL near 52w high, 5-20% pullback bounce (PRIMARY H10)": t["sig"] & near & deep,
            "E2 control: same bounce, far from 52w high (<0.90)": t["sig"] & far & deep,
            "E3 near 52w high, shallow <5%": t["sig"] & near & (depth > -0.05),
            "E4 near 52w high, deep >20%": t["sig"] & near & (depth < -0.20)}


def retest(t: pd.DataFrame) -> dict[str, pd.Series]:
    g = t.groupby("ticker", sort=False)
    prior_max = g["close"].transform(lambda s: s.shift(1).rolling(LVL, min_periods=LVL).max())
    brk = t["close"] > prior_max
    lvl = prior_max.where(brk)
    bbar = t["bar"].where(brk)
    key_t = t["ticker"]
    L = lvl.groupby(key_t, sort=False).ffill()
    B = bbar.groupby(key_t, sort=False).ffill()
    age = t["bar"] - B
    win = (age >= RLO) & (age <= RHI)
    touch = win & (t["low"] <= TOL * L)
    hold = touch & (t["close"] > L)
    fail = touch & (t["close"] < L)
    # first touch per breakout only
    key = [key_t, B]
    first_touch = touch & (touch.groupby(key, sort=False).cumsum() == 1)
    return {"D1 BRK-RETEST first touch of 50d breakout level, holds (PRIMARY H5)": first_touch & hold,
            "D2 control: first touch, fails (close < L)": first_touch & fail,
            "D3 breakout day itself (buy open b+1)": brk & prior_max.notna()}


def run(kind: str, lines: list[str]) -> dict:
    t = pivots(load(kind))
    arms = {**deep_pull(t), **retest(t)}
    lines.append(f"\n=== {kind.upper()} ===")
    res = {}
    for pname, (lo, hi) in PERIODS.items():
        lines.append(f"-- {pname} --")
        for lab, m in arms.items():
            H = 10 if lab.startswith("E") else 5
            r = W.judge(t, m, lo, hi, lab, primary=H)
            res[(pname, lab)] = r
            lines.append(W.fmt(r, H))
    for lab in list(arms)[:1] + [k for k in arms if k.startswith("D1")]:
        sel = t[arms[lab] & t.liq]
        H = 10 if lab.startswith("E") else 5
        yr = sel.groupby(sel.date.dt.year)[f"x{H}"].agg(["mean", "size"])
        lines.append(f"   {lab[:14]} by year (H{H} bp/n): " + " ".join(f"{y}:{v['mean']*1e4:+.0f}/{int(v['size'])}" for y, v in yr.iterrows()))
    del t
    return res


def main():
    lines = [f"DEEP-PULL (N 1057) + BRK-RETEST (N 1058) one look {pd.Timestamp.today():%Y-%m-%d}. Excess vs EW liq universe, buy open s+1, "
             f"cost {W.COST*1e4:.0f}bp RT, shock {W.SHOCK*1e4:.0f}bp. E arms judged at H10, D arms at H5."]
    verdict = []
    for kind in ("etf", "stock"):
        res = run(kind, lines)
        for tag, H in (("E1", 10), ("D1", 5)):
            ok = all(W.passes(r, H) for (p, lab), r in res.items() if lab.startswith(tag))
            verdict.append(f"{kind} {tag}: {'PASS' if ok else 'KILL'}")
    lines.append("\nVERDICT (registered bar, both periods): " + "; ".join(verdict))
    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    sys.exit(main())
