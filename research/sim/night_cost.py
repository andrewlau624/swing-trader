"""Study AQ (Round 17c): the night leg's cost crossover, and the cash-IRA Roth at the brief's
stressed cost (measured x2 ~ 5bp round trip).

    PYTHONPATH=. .venv/bin/python -m research.sim.night_cost

Pre-registration: research/drafts/round1_prose.md, "Round 17c", Study AQ (committed before any
number below). Report only; no new variant.
"""
from __future__ import annotations

import pathlib
import time

import numpy as np
import pandas as pd

from . import book as B
from . import roth_cash as RC
from .validate import load_sim

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/night_cost_out.txt"
SIZES = (2300.0, 10000.0, 25000.0)


def main():
    t0 = time.time()
    f = open(OUT, "w")

    def log(*a):
        x = " ".join(str(i) for i in a)
        print(x, flush=True); f.write(x + "\n"); f.flush()

    log("== Study AQ: night-leg cost crossover; started", pd.Timestamp.now(), "==")
    s = load_sim(raw_price=True)
    N = B.night_days(raw_price=True, max_corr=0.7)
    s.N = N
    bil = s.bil.reindex(s.days).fillna(0.0)

    log("\n-- cash-IRA Roth, fixed $3k, full CAGR by flat night round-trip cost (bp)")
    log(f"{'cost bp':>7s} {'IBS.5+night.5':>15s} {'IBS only 1.0':>13s} {'night only 1.0':>15s}")
    for c in (0.0, 2.5, 5.0, 7.5, 10.0, 15.0, 20.0, "tier", "tier_hi"):
        vals = [B.stats(RC.replay(s, N, 3000.0, wn, wi, 150.0, c))[0] * 100
                for wn, wi in ((0.5, 0.5), (0.0, 1.0), (1.0, 0.0))]
        log(f"{str(c):>7s} {vals[0]:15.1f} {vals[1]:13.1f} {vals[2]:15.1f}")

    log("\n-- taxable V7 book (B.Sim.replay, $3k + $1k/21), full CAGR by flat night cost")
    p_base = dict(night_w=0.5, ibs_w=0.5, noise={"QQQ": 0.5, "SMH": 0.5}, noise_cap=0.75,
                  tilt="live", weekend_scale=0.5, conviction_w=0.0, ibs_cost_bps=1.0)
    for c in (0.0, 2.5, 5.0, 7.5, 10.0, 15.0, "tier", "tier_hi"):
        df = s.replay(B.Params(**{**p_base, "night_cost": c}))
        log(f"  {str(c):>7s} {B.stats(df['r'])[0]*100:6.1f}%/yr  (21-23 "
            f"{B.stats(df['r'][:'2023-12-31'])[0]*100:.1f}, 24-26 {B.stats(df['r']['2024':])[0]*100:.1f})")

    log("\n-- AL1 (IBS .5 + night .5, cash IRA) at the brief's stress (5bp) and measured (2.5bp)")
    for c in (2.5, 5.0):
        r = RC.replay(s, N, 3000.0, 0.5, 0.5, 150.0, c)
        a, sh, dd = B.stats(r)
        h1, h2 = B.stats(r[: "2023-12-31"]), B.stats(r["2024":])
        d = (r - bil).loc["2021-01-01":]
        t = RC.nw_t(d)
        x = d.values
        rng = np.random.default_rng(17)
        sims = np.array([(x * rng.choice([-1, 1], size=len(x))).mean() for _ in range(1000)])
        pct = float((sims < x.mean()).mean() * 100)
        mc = RC.RO.G.mc(r, 3000, 1000)
        log(f"  {c:4.1f}bp  full {a*100:5.1f}%/Sh {sh:4.2f}/DD {dd*100:4.0f}  halves "
            f"{h1[0]*100:.1f}/{h2[0]*100:.1f}  NW t vs BIL {t:+5.2f}  placebo {pct:4.0f}%  "
            f"P(DD30) {mc['dd30']:.0%} P(DD50) {mc['dd50']:.0%}")
        for E in SIZES:
            log(f"        ${E/1e3:5.1f}k -> +${(a - B.stats(bil)[0]) * E:,.0f}/yr vs BIL")

    log("\n-- net exposure: night leg's $/yr at measured costs, per $1k of leg")
    log("   (0bp 31.3% - 18.6% IBS = +12.7pp of the 1.0 leg; at 5bp the crossover is reached)")
    log(f"\ndone {time.time()-t0:.0f}s")
    f.close()


if __name__ == "__main__":
    main()
