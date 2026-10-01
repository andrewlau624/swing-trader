"""AQ re-check on official auction prints (Round 19 follow-up to Study AW; report, no N).

    PYTHONPATH=. .venv/bin/python -m research.sim.aq_auction

Study AQ swept the cash-IRA Roth book's night cost per side on vendor-open returns and put the
IBS+night vs IBS-only crossover at ~6bp/side. Study AW found the vendor open overstates the night
leg by 3.8bp/trade. Same sweep (roth_cash.replay, $3k fixed, whole shares + $150 probe), with
every night return from the official crosses (auction_audit_picks.pkl), vendor shown beside it.
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from . import book as B
from . import roth_cash as RC
from .auction_audit import with_rets
from .validate import load_sim

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/aq_auction_out.txt"
COSTS = (0.0, 1.0, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.5)


def main():
    f = open(OUT, "w")

    def log(x=""):
        print(x, flush=True); f.write(x + "\n"); f.flush()

    s = load_sim(raw_price=True)
    N0 = B.night_days(raw_price=True, max_corr=0.7)
    s.I = B.ibs_days()
    T = pd.read_pickle(ROOT / "data/research/program/auction_audit_picks.pkl")
    Na = with_rets(N0, T, "ret_auc")
    ibs = RC.replay(s, N0, 3000.0, 0.0, 1.0, 150.0, 0.0)
    a = [B.stats(ibs[:"2023-12-31"])[0], B.stats(ibs["2024-01-01":])[0], B.stats(ibs)[0]]
    log(f"IBS-only 1.0 (no night): 2021-23 {a[0]*100:.1f}  2024-26 {a[1]*100:.1f}  full {a[2]*100:.1f}%/yr")
    log("night cost/side | IBS .5 + night .5 full %/yr (21-23 / 24-26): vendor | AUCTION")
    rows = []
    for c in COSTS:
        out = []
        for N in (N0, Na):
            r = RC.replay(s, N, 3000.0, 0.5, 0.5, 150.0, c)
            out.append((B.stats(r)[0], B.stats(r[:"2023-12-31"])[0], B.stats(r["2024-01-01":])[0]))
        rows.append((c, out[0][0], out[1][0], out[1][1], out[1][2]))
        log(f"  {c:4.1f}bp | {out[0][0]*100:5.1f} ({out[0][1]*100:4.1f}/{out[0][2]*100:4.1f}) | "
            f"{out[1][0]*100:5.1f} ({out[1][1]*100:4.1f}/{out[1][2]*100:4.1f})")
    for lab, j, ref in (("vendor full", 1, a[2]), ("AUCTION full", 2, a[2]),
                        ("AUCTION 2021-23", 3, a[0]), ("AUCTION 2024-26", 4, a[1])):
        x = np.array([r[0] for r in rows]); y = np.array([r[j] for r in rows]) - ref
        k = np.where((y[:-1] > 0) & (y[1:] <= 0))[0]
        cx = (x[k[0]] + y[k[0]] / (y[k[0]] - y[k[0] + 1]) * (x[k[0] + 1] - x[k[0]])) if len(k) else np.nan
        log(f"crossover vs IBS-only, {lab}: {cx:.1f}bp/side")
    f.close()


if __name__ == "__main__":
    main()
