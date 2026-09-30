"""Study X: an impact-optimal per-name cap for the night leg.

    PYTHONPATH=. .venv/bin/python -m research.sim.night_cap

Pre-registration: research/drafts/round1_prose.md, "Round 10" (commit 8f3e04a).
q_i <= ADV_i (g / (3 Y_rule sigma_i))^2; judged under Study V's truth models A (sqrt(q/ADV)) and
B (sqrt(q / auction share of ADV)), Y 0.5 / 1, with 1bp/side live cost. Freed money stays cash.
"""
from __future__ import annotations

import time

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import book as B
from .night_filings import FULL, ROOT

OUT = ROOT / "data/research/program/night_cap_out.txt"
SIZES = (2_300, 25_000, 100_000, 250_000, 500_000, 1_000_000, 5_000_000)
G_BPS = 22.0
AUC = (0.037, 0.016)          # Study V: median closing / opening bar share of ADV
TRUTHS = {"A/Y.5": (0.5, (1.0, 1.0)), "A/Y1": (1.0, (1.0, 1.0)),
          "B/Y.5": (0.5, AUC), "B/Y1": (1.0, AUC)}
RULES = {"uncapped": None, "Y_rule 1": 1.0, "Y_rule 2": 2.0, "Y_rule 4": 4.0}


def main():
    t0 = time.time()
    fs = open(OUT, "w")

    def log(*a):
        s_ = " ".join(str(x) for x in a)
        print(s_, flush=True)
        fs.write(s_ + "\n")
        fs.flush()

    log("== Study X: impact-optimal per-name night cap, started", pd.Timestamp.now(), "\n")
    N = B.night_days(raw_price=True, max_corr=0.7)
    T = pd.DataFrame([dict(d=pd.Timestamp(d), ret=nd.ret[j], vol=nd.vol20[j], adv=nd.adv[j],
                           w=min(nd.frac, 0.10))
                      for d, nd in N.items() if pd.Timestamp(d) >= pd.Timestamp(FULL[0])
                      for j in range(len(nd.syms))])
    sess = B.D.returns20().index
    days = sess[(sess >= FULL[0]) & (sess <= FULL[1])]
    yrs = len(days) / 252
    sig = (T.vol / np.sqrt(252)).values                  # daily sd, fraction

    res = {}
    for rname, yr_ in RULES.items():
        for E in SIZES:
            q = 0.5 * E * T.w.values
            if yr_ is not None:
                q = np.minimum(q, sg.night_impact_cap(T.adv.values, T.vol.values, G_BPS, yr_))
            bind = float(np.mean(q < 0.5 * E * T.w.values - 1e-9))
            for tname, (Y, (fc, fo)) in TRUTHS.items():
                imp = Y * sig * (np.sqrt(q / (T.adv.values * fc)) + np.sqrt(q / (T.adv.values * fo)))
                pnl = q * (T.ret.values - 2e-4 - imp)             # $ per trade
                usd = pd.Series(pnl).groupby(T.d.values).sum().reindex(days).fillna(0).sum() / yrs
                res[(rname, E, tname)] = (usd, bind)

    for tname in TRUTHS:
        log(f"## truth {tname}: night-leg $/yr (share of orders the cap binds)")
        log(f"{'equity':>11s} " + " ".join(f"{r:>20s}" for r in RULES))
        for E in SIZES:
            log(f"${E:>10,} " + " ".join(
                f"{res[(r, E, tname)][0]:>12,.0f} ({res[(r, E, tname)][1]:4.0%})" for r in RULES))
        log("")

    log("## pre-registered criteria")
    passers = []
    for r in list(RULES)[1:]:
        c1 = res[(r, 2_300, "A/Y1")][1] == 0
        c2 = all(res[(r, E, t)][0] >= res[("uncapped", E, t)][0] - 1
                 for E in SIZES if E >= 25_000 for t in TRUTHS)
        c3 = all(res[(r, E, t)][0] >= 0 for E in SIZES for t in ("A/Y1", "B/Y.5"))
        mn = min(res[(r, 1_000_000, t)][0] for t in TRUTHS)
        log(f"  {r}: inert at $2.3k {c1}; never below uncapped {c2}; >= 0 under A/Y1 & B/Y.5 {c3}; "
            f"min $/yr at $1M {mn:,.0f}")
        if c1 and c2 and c3:
            passers.append((mn, r))
    log(f"\n  ADOPT: {max(passers)[1] if passers else 'none'}")
    log(f"\ndone in {time.time() - t0:4.0f} s")


if __name__ == "__main__":
    main()
