"""Parity: the live-code simulator vs the research replay (grow.py, addendum 15).

    .venv/bin/python -m research.sim.validate

They should agree closely on each leg. Where they differ, the simulator is
the one running the live rules, so the difference is research drift.
"""
from __future__ import annotations

import os
import pickle
import sys

import numpy as np
import pandas as pd

from . import book as B
from .data import DATA, ROOT

CACHE = DATA / "sim_cache.pkl"


def load_sim(refresh: bool = False, noise_syms=("QQQ", "SMH")) -> B.Sim:
    if CACHE.exists() and not refresh:
        s = pickle.load(open(CACHE, "rb"))
        if set(noise_syms) <= set(s.NZ):
            return s
    s = B.Sim(noise_syms=noise_syms)
    pickle.dump(s, open(CACHE, "wb"))
    return s


def main():
    s = load_sim()
    # research replay, same data
    sys.path.insert(0, str(ROOT / "research" / "daily-strategies"))
    cwd = os.getcwd(); os.chdir(DATA)
    try:
        import grow  # noqa: E402
        nz = grow.noise_series(0.5, 1.5)
        g = grow.replay(whole=True, resplit=False, nz=nz)
    finally:
        os.chdir(cwd)
    g["r"] = (g.E.diff() - g.dep.diff()) / g.E.shift()
    print("                                              2021-23          2024-26          full")
    print(B.summary(g.dropna(), "research replay (grow.py, addendum 15)"))
    base = B.Params(ibs_cost_bps=0.5)
    print(B.summary(s.replay(base), "simulator, live rules"))
    # leg by leg, fractional $100k, no deposits
    for lab, p in [("night only", B.Params(ibs_w=0, noise_on=False, ibs_idle="cash")),
                   ("IBS only", B.Params(night_w=0, noise_on=False, ibs_idle="cash")),
                   ("noise only (QQQ 1.5x)", B.Params(night_w=0, ibs_w=0))]:
        p.whole = False
        print(B.summary(s.replay(p, start=1e5, monthly=0), "  " + lab))
    # noise parity with research/noise.py
    z = s.NZ["QQQ"]
    os.chdir(DATA)
    try:
        from noise import noise  # noqa: E402
        rr, _ = noise("QQQ", cost_bps=0.5, maxlev=1.5)
    finally:
        os.chdir(cwd)
    mine = (z.lev.clip(upper=1.5) * z.ret).reindex(rr.index).fillna(0)
    both = rr.index[(rr.index >= B.START)]
    print(f"\nnoise leg daily-return correlation, simulator vs noise.py: "
          f"{np.corrcoef(mine[both], rr[both])[0, 1]:.4f}")


if __name__ == "__main__":
    main()
