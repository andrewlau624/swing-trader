"""Round 16, Study AI: how much daytime capital the conviction trade can take (round1_prose.md Round 16 AI).

    PYTHONPATH=. .venv/bin/python -m research.sim.conviction_ai        # ~10 s

Increment of (weight w, intraday mult) vs the shipped (0.5, same mult), additive in daily return. The day's QQQ/SMH
noise cap follows growth.cfg(1.0, w, mult). AI4 (w 2.0) is the MNQ reference: futures margin, noise cap unchanged.
"""
from __future__ import annotations

import pickle

import numpy as np
import pandas as pd

from . import book as B
from . import data as D
from . import growth as G
from . import program_books as PB
from . import taxable_frontier as TF
from .conviction_af import BP_RES, CONV_SIDE, HALVES, SCR, SIZES, conv_trades, noise_legs

N_PROGRAM = 634
ROWS = {  # label: (w, mult, w0, mult0, noise follows w)
    "REF off vs on, m2": (0.0, 2.0, 0.5, 2.0, True),
    "REF off vs on, m4": (0.0, 4.0, 0.5, 4.0, True),
    "AI1 w .75 m2": (0.75, 2.0, 0.5, 2.0, True),
    "AI2 w 1.0 m2": (1.0, 2.0, 0.5, 2.0, True),
    "AI3 w 1.0 m4": (1.0, 4.0, 0.5, 4.0, True),
    "AI4 w 2.0 MNQ": (2.0, 2.0, 0.5, 2.0, False),
}


def cap(w, mult):
    c = G.cfg(1.0, w, mult)
    return c["noise_cap"] if c else np.nan


def increment(days, conv_net, NZ, w, mult, w0, mult0, noise_follows=True) -> pd.Series:
    cn = conv_net.reindex(days).fillna(0.0)
    d = (w - w0) * cn
    c1 = cap(w, mult) if noise_follows else cap(w0, mult0)
    c0 = cap(w0, mult0)
    for s, share in G.S2.items():
        z = NZ[s].reindex(days)
        lev, ret = z["lev"].fillna(0.0), z["ret"].fillna(0.0)
        d = d + share * (np.minimum(lev, c1) - np.minimum(lev, c0)) * ret
    return d


def main():
    T = conv_trades()
    days = pd.DatetimeIndex(D.minutes("QQQ")["close"].index[15:])
    bp = pickle.load(open(BP_RES, "rb"))["res"]
    b3 = bp[("B3 moderate10c", "M2 base", "tier_hi")]
    r0, e0 = b3["r"], b3["eh"]
    print(f"noise caps: " + ", ".join(f"w {w} m{m:g} {cap(w, m):.2f}" for w in (0, .5, .75, 1.0) for m in (2.0, 4.0)))
    res = {}
    for cost in ("ship", "th"):
        NZ = noise_legs(cost)
        conv_net = T["gross"] - 2 * CONV_SIDE[cost] / 1e4
        print(f"\n== {cost}: increment vs w 0.5 at the same mult (REF rows: 'off' minus 'on'; turning it on = the negative)")
        for lab, (w, m, w0, m0, nf) in ROWS.items():
            inc = increment(days, conv_net, NZ, w, m, w0, m0, nf)
            # mult-4 rows: move the cached m2 book to m4 first
            shift = increment(days, conv_net, NZ, 0.5, m, 0.5, 2.0) if m != 2.0 else 0.0 * inc
            rng = np.random.default_rng(19)
            X = inc.values
            sims = np.array([(X * rng.choice([-1, 1], size=len(X))).mean() for _ in range(1000)])
            pct = float((sims < X.mean()).mean() * 100)
            i2 = inc.reindex(r0.index).fillna(0.0); s2 = shift.reindex(r0.index).fillna(0.0)
            rb, rv = r0 + s2, r0 + s2 + i2
            eb = e0 + s2 - 0.5 * s2.mean(); ev = eb + i2 - 0.5 * i2.mean()
            x = dict(inc=inc, pct=pct, rb=rb, rv=rv)
            line = (f"  {lab:20s} " + "  ".join(f"{h} {inc[a:z].mean()*252*100:+6.2f}pp" for h, a, z in HALVES) +
                    f" | NW t {TF.nw_t(inc):+5.2f} | placebo {pct:5.1f}")
            if cost == "th":
                mcb = TF.mc_tax(eb, 0.35, start=3000, monthly=1000); mcv = TF.mc_tax(ev, 0.35, start=3000, monthly=1000)
                x.update(mcb=mcb, mcv=mcv, dsr=PB.dsr(inc, n_trials=N_PROGRAM))
                line += (f" | B3 {PB.halves(rv)} maxDD {B.stats(rv)[2]*100:5.1f} (base {B.stats(rb)[2]*100:5.1f}) | "
                         f"P50 {mcv['dd50']:.1%} (base {mcb['dd50']:.1%}) P30 {mcv['dd30']:.0%} ({mcb['dd30']:.0%}) | "
                         f"worst trade {w * conv_net.min()*100:+5.1f}% of equity | DSR {x['dsr']['dsr']:.2f}")
            res[(cost, lab)] = x
            print(line, flush=True)
    print("\n== money, tier_hi: increment x E per yr, 2016-26 (2024-26); after 35% tax. REF rows shown as TURN-ON value")
    for lab in ROWS:
        inc = res[("th", lab)]["inc"] * (-1 if lab.startswith("REF") else 1)
        a, b = inc.mean() * 252, inc["2024":].mean() * 252
        print(f"  {lab:20s} " + " | ".join(f"${E/1e3:g}k {a*E:+8,.0f} ({b*E:+8,.0f}) AT {0.65*a*E:+8,.0f}" for E in SIZES))
    print("\n== capacity, 2024-26: TQQQ notional / TQQQ $ volume in the entry minute")
    sh = T["dvol_m0"]["2024":].replace(0, np.nan)
    for E in SIZES:
        print(f"  E ${E:>9,.0f}: " + "  ".join(f"w {w}: med {(E*w/sh).median():6.2%} p95 {(E*w/sh).quantile(.95):6.2%}" for w in (0.5, 1.0, 1.33)))
    pickle.dump(res, open(SCR / "conviction_ai_res.pkl", "wb"))


if __name__ == "__main__":
    main()
