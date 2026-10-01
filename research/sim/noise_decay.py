"""Noise leg decay check after publication (Round 21 report; no N). Outside prompt: a public replication
(codecat-ops/zarattini-2024-momentum-spy) finds the same rule on SPY at Sharpe ~0 since 2025.

    PYTHONPATH=. .venv/bin/python -m research.sim.noise_decay

Per instrument (QQQ, SMH, and SPY for reference): the unlevered noise-area rule net of 0.5bp/side
(B.noise_days), by year and before/after the paper (SSRN, May 2024), with NW t and a trend test.
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from . import book as B
from .max_edge import nw_t

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/noise_decay_out.txt"


def main():
    f = open(OUT, "w")

    def log(x=""):
        print(x, flush=True); f.write(x + "\n"); f.flush()

    for sym in ("QQQ", "SMH", "SPY"):
        z = B.noise_days(sym, cost=0.5)
        r = z.ret
        log(f"\n{sym}: unlevered net bp/day, Sharpe (by year)")
        line = []
        for y, g in r.groupby(r.index.year):
            line.append(f"{y}: {g.mean()*1e4:+5.1f}/{g.mean()/g.std()*np.sqrt(252):+.2f}")
        log("  " + "  ".join(line))
        for lab, a, b in (("2016-2024-05", "2016", "2024-05-31"), ("2024-06+", "2024-06-01", "2027")):
            g = r[a:b]
            log(f"  {lab}: n {len(g)}  {g.mean()*1e4:+.2f}bp/day  Sharpe {g.mean()/g.std()*np.sqrt(252):+.2f}  NW t {nw_t(g.values):+.2f}")
        g = r["2025-01-01":]
        log(f"  2025+: {g.mean()*1e4:+.2f}bp/day  Sharpe {g.mean()/g.std()*np.sqrt(252):+.2f}  NW t {nw_t(g.values):+.2f}")
        x = np.arange(len(r)) / 252.0
        b = np.polyfit(x, r.values, 1)[0]
        e = r.values - np.polyval(np.polyfit(x, r.values, 1), x)
        se = np.sqrt((e ** 2).sum() / (len(x) - 2) / ((x - x.mean()) ** 2).sum())
        log(f"  linear trend in daily net: {b*1e4:+.3f}bp/day per year (t {b/se:+.2f}, iid)")
    f.close()


if __name__ == "__main__":
    main()
