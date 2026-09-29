"""Study P: the 1-share night probe on vs off at the live books' sizes.

    PYTHONPATH=. .venv/bin/python -m research.sim.probe_off

Pre-reg: research/drafts/round1_prose.md, "Amendment - Round 4b: Study P". Same
model as Study R (roth_sizing.day); only the probe and the size change.
"""
from __future__ import annotations

import pathlib

import pandas as pd

from . import book as B
from .validate import load_sim
from .roth_sizing import PROBE_USD, replay, roth_params

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/probe_off_out.txt"
SIZES = (1000.0, 2000.0, 2259.0, 3000.0, 5000.0)
HALVES = (("2021-23", "2021-01-01", "2023-12-31"), ("2024-26", "2024-01-01", "2026-12-31"))


def main():
    fs = open(OUT, "w")

    def log(*a):
        x = " ".join(str(i) for i in a)
        print(x, flush=True)
        fs.write(x + "\n")

    log("== Study P: probe on vs off; started", pd.Timestamp.now(), "==\n")
    s = load_sim(raw_price=True)
    N10 = B.night_days(raw_price=True, max_corr=0.7)
    s.N = N10
    verdict = True
    for cost in ("tier", "tier_hi"):
        p = roth_params(cost)
        for sz in SIZES:
            on, _ = replay(s, N10, sz, p, True, PROBE_USD, fixed=True)
            off, _ = replay(s, N10, sz, p, True, None, fixed=True)
            cells = []
            for lab, a, b in HALVES + (("full", None, None),):
                x, y = B.stats(on[a:b]), B.stats(off[a:b])
                cells.append((lab, x, y))
            line = "  ".join(f"{lab} on {x[0]*100:5.1f}/{x[1]:.2f}/{x[2]*100:3.0f} off {y[0]*100:5.1f}/{y[1]:.2f}/{y[2]*100:3.0f}"
                             for lab, x, y in cells)
            log(f"{cost:7s} ${sz:>6,.0f}  {line}")
            if sz in (2000.0, 2259.0, 3000.0):
                for lab, x, y in cells:
                    if lab != "full" and y[0] < x[0]:
                        verdict = False
                        log(f"         FAIL: {lab} no-probe CAGR below probe")
                    if y[2] < x[2] - 0.03:
                        verdict = False
                        log(f"         FAIL: {lab} no-probe maxDD worse by > 3pp")
        log("")
    log(f"VERDICT (pre-registered rule): {'PROBE OFF' if verdict else 'KEEP PROBE'}")
    fs.close()


if __name__ == "__main__":
    main()
