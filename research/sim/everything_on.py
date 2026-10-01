"""Round 26 report (no variants, no N): the 'everything on' book as ONE simulation, not a sum of lever estimates.

    PYTHONPATH=. .venv/bin/python -m research.sim.everything_on

The weekly digest's "Backtest, everything on" line (31% + 15pp brokerage) adds each lever's separately measured
gain. Levers interact (leverage stacks on the same night trades, margin interest, drawdowns compound), so this
replays them cumulatively, one step at a time, on the official-cross night returns (Study AW), at fixed capital
$2.3k / $10k / $25k, 2.5bp/side (tier_hi reported), with the program's own sizing map (growth.cfg: overnight
gross g, conviction weight, intraday multiplier -> night/IBS weights, noise cap, margin):
  S0 live today        g 1.0, conviction 0, mult 2.48
  S1 + tug-of-war tilt (Study AU3)
  S2 + 15% night name cap (moderate profile)
  S3 + conviction trade 0.5
  S4 + 4x intraday margin (mult 4)
  S5 + 1.3x overnight (g 1.3; 12%/yr margin interest on the debit)
"""
from __future__ import annotations

import dataclasses
import pathlib

import numpy as np
import pandas as pd

from . import book as B
from . import growth as G
from . import max_edge as M
from .auction_audit import with_rets
from .validate import load_sim

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/everything_on_out.txt"


def main():
    f = open(OUT, "w")

    def log(x=""):
        print(x, flush=True); f.write(x + "\n"); f.flush()

    s = load_sim(raw_price=True)
    T = pd.read_pickle(ROOT / "data/research/program/auction_audit_picks.pkl")
    N10 = with_rets(B.night_days(raw_price=True, max_corr=0.7), T, "ret_auc")
    raw10 = B.night_days(raw_price=True, max_corr=0.7)
    raw15 = B.night_days(raw_price=True, max_corr=0.7, max_name_pct=0.15)
    assert all(list(raw15[d].syms) == list(raw10[d].syms) for d in raw10), "the cap changes sizes, not picks"
    N15 = with_rets(raw15, T, "ret_auc")
    s.I = B.ibs_days()
    F10, F15 = M.au_features(N10), M.au_features(N15)
    A = np.array([v for (d, _), v in F10.items() if d <= pd.Timestamp("2023-12-31")], float)
    mu, sd = np.nanmean(A, axis=0), np.nanstd(A, axis=0)

    steps = [
        ("S0 live today", 1.0, 0.0, 2.48, False, N10, F10),
        ("S1 + tug-of-war tilt", 1.0, 0.0, 2.48, True, N10, F10),
        ("S2 + 15% name cap", 1.0, 0.0, 2.48, True, N15, F15),
        ("S3 + conviction 0.5", 1.0, 0.5, 2.48, True, N15, F15),
        ("S4 + 4x intraday", 1.0, 0.5, 4.0, True, N15, F15),
        ("S5 + 1.3x overnight", 1.3, 0.5, 4.0, True, N15, F15),
    ]
    for cost in (2.5, "tier_hi"):
        log(f"\n== night cost {cost}/side; CAGR / Sharpe / maxDD  (2021-23 | 2024-26 | full)  + after 32% ST tax")
        for E in M.SIZES:
            log(f"  -- fixed ${E/1e3:.1f}k")
            prev = None
            for lab, g, conv, mult, tow, N, F in steps:
                kw = G.cfg(g, conv, mult)
                if kw is None:
                    log(f"   {lab:24s} infeasible at this margin"); continue
                s.N = N
                p = B.Params(**{**G.V7, **kw, "night_cost": cost})
                if tow:
                    p = dataclasses.replace(p, tilt=M.make_tilt(N, F, "AU3", mu, sd))
                r = M.replay(s, E, p)
                h1, h2, fu = B.stats(r[:"2023-12-31"]), B.stats(r["2024-01-01":]), B.stats(r)
                inc = "" if prev is None else f"  step {(fu[0]-prev)*100:+5.1f}pp"
                pdd = f"  P(DD>50) {M.p_dd50(r):.0%}" if (E == 10000.0 and cost == 2.5) else ""
                log(f"   {lab:24s} {h1[0]*100:5.1f}/{h1[1]:4.2f} | {h2[0]*100:5.1f}/{h2[1]:4.2f} | "
                    f"{fu[0]*100:5.1f}/{fu[1]:4.2f}/{fu[2]*100:4.0f}  AT {fu[0]*0.68*100:5.1f}{inc}{pdd}")
                prev = fu[0]
    # ---- edge-halves (the program's standard haircut, growth.eh): half of each leg's mean daily
    # contribution taken away, costs and margin interest kept. The digest's PLAN lines use these.
    log("\n== edge-halves (EH) at 2.5bp/side, fixed $10k: half of every leg's mean contribution removed")
    for lab, g, conv, mult, tow, N, F in steps:
        kw = G.cfg(g, conv, mult)
        s.N = N
        p = B.Params(**{**G.V7, **kw, "night_cost": 2.5})
        if tow:
            p = dataclasses.replace(p, tilt=M.make_tilt(N, F, "AU3", mu, sd))
        legs = []
        for d in s.days:
            pl, info = s.day_pnl(10000.0, d, p)
            legs.append((d, pl / 1e4, info["night"] / 1e4, info["ibs"] / 1e4, info["noise"] / 1e4))
        L = pd.DataFrame(legs, columns=["d", "r", "n", "i", "z"]).set_index("d")
        eh = L.r - 0.5 * (L.n.mean() + L.i.mean() + L.z.mean())
        a, b = B.stats(L.r), B.stats(eh)
        log(f"   {lab:24s} full {a[0]*100:5.1f}%  EH {b[0]*100:5.1f}% / Sharpe {b[1]:4.2f} / maxDD {b[2]*100:4.0f}%  "
            f"AT {b[0]*0.68*100:5.1f}%")
    f.close()


if __name__ == "__main__":
    main()
