"""Round 16, Study AJ: the conviction trade in MNQ instead of TQQQ (round1_prose.md Round 16 AJ).

    PYTHONPATH=. .venv/bin/python -m research.sim.conviction_aj        # ~15 s

Same signal and minutes as the shipped trade; MNQ return = 3 x QQQ's move over them (QQQ as the NQ proxy, as
research/sim/futures.py). Futures margin 10% of notional -> r3 0.30 per unit weight in growth.cfg.
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

N_PROGRAM = 637
MNQ_SIDE = {"ship": 0.5, "th": 1.0}
R3_MNQ = 0.30
MNQ_PER_QQQ = 82.0            # MNQ notional ≈ $2 x NQ ≈ $2 x 41 x QQQ
BLEND = 0.6 * TF.TAX_LT + 0.4 * TF.TAX_ST
VARS = {"AJ1 w .5 MNQ": 0.5, "AJ2 w .75 MNQ": 0.75, "AJ3 w 1.0 MNQ": 1.0}


def cap(w, mult, r3):
    c = G.cfg(1.0, w, mult, r3=r3)
    return c["noise_cap"] if c else np.nan


def main():
    T = conv_trades()
    Q = D.minutes("QQQ")["close"]
    pos = {d: i for i, d in enumerate(Q.index)}
    Qv = Q.values
    q = []
    for d, r in T.iterrows():
        i = pos[d]
        q.append(r.dir * (Qv[i, int(r.xm)] / Qv[i, int(r.m0)] - 1))
    T["g_mnq"] = 3 * np.array(q)
    T["qqq_px"] = [Qv[pos[d], int(r.m0)] for d, r in T.iterrows()]
    print("tracking on the same trades: mean gross TQQQ {:+.1f}bp vs 3xQQQ {:+.1f}bp; corr {:.4f}; mean diff {:+.2f}bp".format(
        T.gross.mean() * 1e4, T.g_mnq.mean() * 1e4, np.corrcoef(T.gross, T.g_mnq)[0, 1], (T.gross - T.g_mnq).mean() * 1e4))
    for h, a, z in HALVES:
        print(f"  {h}: TQQQ {T.gross[a:z].mean()*1e4:+6.1f}bp  3xQQQ {T.g_mnq[a:z].mean()*1e4:+6.1f}bp")
    days = pd.DatetimeIndex(D.minutes("QQQ")["close"].index[15:])
    bp = pickle.load(open(BP_RES, "rb"))["res"]
    b3 = bp[("B3 moderate10c", "M2 base", "tier_hi")]
    r0, e0 = b3["r"], b3["eh"]
    print("noise caps (mult 2 / 4): TQQQ w .5 {:.2f}/{:.2f}; ".format(cap(.5, 2, .75), cap(.5, 4, .75)) +
          "; ".join(f"MNQ w {w} {cap(w, 2, R3_MNQ):.2f}/{cap(w, 4, R3_MNQ):.2f}" for w in VARS.values()))
    res = {}
    for cost in ("ship", "th"):
        NZ = noise_legs(cost)
        tq = (T.gross - 2 * CONV_SIDE[cost] / 1e4).reindex(days).fillna(0.0)
        mq = (T.g_mnq - 2 * MNQ_SIDE[cost] / 1e4).reindex(days).fillna(0.0)
        for mult in (2.0, 4.0):
            print(f"\n== {cost}, mult {mult:g}: increment vs shipped w .5 TQQQ")
            shift = pd.Series(0.0, index=days)
            if mult != 2.0:
                for s, share in G.S2.items():
                    z = NZ[s].reindex(days); lev, ret = z.lev.fillna(0), z.ret.fillna(0)
                    shift += share * (np.minimum(lev, cap(.5, mult, .75)) - np.minimum(lev, cap(.5, 2, .75))) * ret
            for lab, w in VARS.items():
                inc = w * mq - 0.5 * tq
                noise_d = pd.Series(0.0, index=days)
                for s, share in G.S2.items():
                    z = NZ[s].reindex(days); lev, ret = z.lev.fillna(0), z.ret.fillna(0)
                    noise_d += share * (np.minimum(lev, cap(w, mult, R3_MNQ)) - np.minimum(lev, cap(.5, mult, .75))) * ret
                inc = inc + noise_d
                rng = np.random.default_rng(20)
                X = inc.values
                sims = np.array([(X * rng.choice([-1, 1], size=len(X))).mean() for _ in range(1000)])
                pct = float((sims < X.mean()).mean() * 100)
                line = (f"  {lab:14s} " + "  ".join(f"{h} {inc[a:z].mean()*252*100:+6.2f}pp" for h, a, z in HALVES) +
                        f" | NW t {TF.nw_t(inc):+5.2f} | placebo {pct:5.1f} | noise part {noise_d.mean()*252*100:+5.2f}pp/yr")
                x = dict(inc=inc, pct=pct, w=w, mq=mq, tq=tq, noise_d=noise_d)
                if cost == "th":
                    i2, s2 = inc.reindex(r0.index).fillna(0), shift.reindex(r0.index).fillna(0)
                    rb, rv = r0 + s2, r0 + s2 + i2
                    eb = e0 + s2 - 0.5 * s2.mean(); ev = eb + i2 - 0.5 * i2.mean()
                    r56 = (w * mq).reindex(r0.index).fillna(0)
                    mcb = TF.mc_tax(eb, 0.35, start=3000, monthly=1000)
                    mcv = TF.mc_tax(ev, 0.35, r1256=r56, start=3000, monthly=1000)
                    ds = PB.dsr(inc, n_trials=N_PROGRAM)
                    x.update(mcv=mcv, mcb=mcb, dsr=ds)
                    line += (f" | B3 {PB.halves(rv)} maxDD {B.stats(rv)[2]*100:5.1f} (base {B.stats(rb)[2]*100:5.1f}) "
                             f"| P50 {mcv['dd50']:.1%} (base {mcb['dd50']:.1%}) P30 {mcv['dd30']:.0%} ({mcb['dd30']:.0%}) "
                             f"| MC med ${mcv['med']:,.0f} (base ${mcb['med']:,.0f}) | DSR {ds['dsr']:.2f}")
                res[(cost, mult, lab)] = x
                print(line, flush=True)

    print("\n== whole contracts: one MNQ ≈ 82 x QQQ price; min equity for 1 contract (2024-26 median QQQ price)")
    px = T.qqq_px["2024":].median()
    for lab, w in VARS.items():
        print(f"  {lab}: 1 contract = ${MNQ_PER_QQQ*px:,.0f} notional -> needs E >= ${MNQ_PER_QQQ*px/(3*w):,.0f}")
    print("\n== money (tier_hi, mult 2), whole contracts, 2016-26 (2024-26); after tax: MNQ 60/40 (blend "
          f"{BLEND:.0%}), TQQQ and noise 35%")
    for lab, w in VARS.items():
        x = res[("th", 2.0, lab)]
        out = []
        for E in SIZES:
            n = np.floor(3 * w * E / (MNQ_PER_QQQ * T.qqq_px.reindex(days).ffill().bfill()))
            weff = n * MNQ_PER_QQQ * T.qqq_px.reindex(days).ffill().bfill() / (3 * E)
            leg = weff * x["mq"]
            inc = leg - 0.5 * x["tq"] + x["noise_d"]
            at = leg * (1 - BLEND) - 0.5 * x["tq"] * 0.65 + x["noise_d"] * 0.65
            out.append(f"${E/1e3:g}k (w_eff {weff['2024':].mean():.2f}) {inc.mean()*252*E:+8,.0f} ({inc['2024':].mean()*252*E:+8,.0f}) AT {at.mean()*252*E:+8,.0f}")
        print(f"  {lab:14s} " + " | ".join(out))
    print("\n== capacity (stated): contracts at w 1.0 = 3E / (82 x QQQ); MNQ trades ~1-2M contracts/day (CME, 2025), "
          "i.e. thousands per minute")
    for E in SIZES:
        print(f"  E ${E:>9,.0f}: {3*E/(MNQ_PER_QQQ*px):6.1f} contracts at w 1.0")
    pickle.dump(res, open(SCR / "conviction_aj_res.pkl", "wb"))


if __name__ == "__main__":
    main()
