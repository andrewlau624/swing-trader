"""Addendum 17: how far from optimal is the shipped book?

    .venv/bin/python -m research.sim.optimize sweep     # one-at-a-time plateaus
    .venv/bin/python -m research.sim.optimize levers    # account / leverage levers

A sweep here is NOT a search for the best value: with ~60 variants, the best
cell of any sweep is mostly luck. It answers two questions: does the shipped
value sit on a plateau (so the live number is not a lucky spike), and is
there a knob whose whole neighbourhood beats the current value in BOTH
halves (the only kind of change worth making).
"""
from __future__ import annotations

import copy
import sys

from . import book as B
from .validate import load_sim

S2 = {"QQQ": 0.5, "SMH": 0.5}
SHIPPED = dict(tilt="live", noise=S2, night_cost="tier")


def row(s, label, **kw):
    p = B.Params(**{**SHIPPED, **kw})
    print(B.summary(s.replay(p), label))


def with_night(s, **kw):
    t = copy.copy(s)
    t.N = B.night_days(**kw)
    return t


def with_ibs(s, **kw):
    t = copy.copy(s)
    t.I = B.ibs_days(**kw)
    return t


def sweep(s):
    print(f"{'':44s} {'2021-23':>16s} {'2024-26':>16s} {'full':>16s}")
    row(s, "SHIPPED (tier costs)")
    print("\n-- night: vol20 floor (shipped 0.60)")
    for v in (0.4, 0.5, 0.7, 0.8):
        row(with_night(s, vol_min=v), f"  vol_min {v}")
    print("-- night: crowding cutoff (shipped 30)")
    for c in (15, 20, 45, 60):
        row(with_night(s, crowd_n=c), f"  crowd_n {c}")
    print("-- night: per-name cap of the leg (shipped 0.10)")
    for m in (0.06, 0.08, 0.15, 0.20):
        row(with_night(s, max_name_pct=m), f"  max_name_pct {m}")
    print("-- night: duplicate-bet correlation (shipped 0.9)")
    for c in (0.7, 0.8, None):
        row(with_night(s, max_corr=c), f"  max_corr {c}")
    print("-- night: tilt strength (shipped 0.25)")
    for k in (0.0, 0.15, 0.4, 0.6):
        row(s, f"  tilt_k {k}", tilt_k=k)
    print("-- IBS: top-k by momentum (shipped 3)")
    for k in (2, 4, 5):
        row(with_ibs(s, top_k=k), f"  ibs_top_k {k}")
    print("-- IBS: threshold (shipped 0.2)")
    for x in (0.1, 0.15, 0.25, 0.3):
        row(with_ibs(s, ibs_max=x), f"  ibs_max {x}")
    print("-- weights at 1x gross (shipped 0.5 / 0.5)")
    for nw in (0.4, 0.6):
        row(s, f"  night {nw} / IBS {1 - nw:.1f}", night_w=nw, ibs_w=1 - nw)


def levers(s):
    print(f"{'':44s} {'2021-23':>16s} {'2024-26':>16s} {'full':>16s}")
    row(s, "SHIPPED: 1x overnight, 1.5x intraday")
    print("\n-- intraday budget (needs dayTradingBuyingPower: 2x acct -> 1.5, 4x -> 3.5)")
    for cap in (1.0, 2.5, 3.5):
        row(s, f"  intraday cap {cap}x", noise_cap=cap)
    print("-- overnight gross (margin interest 12%/yr)")
    for w in (0.65, 0.75, 0.9):
        row(s, f"  overnight {2*w:.1f}x (intraday 1.5x)", night_w=w, ibs_w=w)
    print("-- both")
    row(s, "  overnight 1.3x + intraday 3.5x", night_w=0.65, ibs_w=0.65, noise_cap=3.35)
    print("-- margin rate sensitivity at 1.3x overnight")
    for m in (0.08, 0.16):
        row(s, f"  1.3x overnight, margin {m:.0%}", night_w=0.65, ibs_w=0.65, margin_rate=m)


if __name__ == "__main__":
    s = load_sim()
    {"sweep": sweep, "levers": levers}[sys.argv[1] if len(sys.argv) > 1 else "sweep"](s)
