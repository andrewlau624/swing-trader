"""Index-beat C2: taxable = SPY core + the noise leg on intraday margin only (the leg the Roth can't run); the Roth
runs the proposed book with no guard EXCEPT that its IBS leg never buys QQQ or SMH (the taxable noise leg sells QQQ/SMH
at a loss most days: a Roth purchase within 30 days would permanently disallow it, Rev. Rul. 2008-5; add. 39).
Report-type track C (no N). Same windows / sizes / pool / costs as ib_c1; EH and as-backtested.

    PYTHONPATH=. .venv/bin/python -m research.sim.ib_c2
Taxable C2 account, day by day: E *= 1 + SPY total return; E += noise P&L (fraction of E); dividends (1.3%/yr) taxed
at 20% when paid; noise P&L netted per calendar year, 35% on a net gain paid on the first session >= Apr 15 next year,
a net loss carried forward and $3k/yr of it deducted at 35% (the after_tax rules); the SPY gain taxed at 20% at the end
(liquidation-fair). Check: with the noise leg off it must reproduce ib_c1.index_after_tax.
"""
from __future__ import annotations

import copy
import sys

import numpy as np
import pandas as pd

from . import program_books as PB
from . import roth_opt as RO
from . import taxable_frontier as TF
from .ib_c1 import DIV, LT, R0, R_MO, T0, WIN, ctx_raw, flows_of, grow, index_after_tax, irr, run

ST_RATE = 0.35


def c2_account(spy, noise, days, start, mo):
    E, basis = start, start
    gain, carry, due = 0.0, 0.0, None
    for i, d in enumerate(days):
        if i and i % 21 == 0:
            E += mo; basis += mo
        x = spy.get(d, 0.0); x = 0.0 if pd.isna(x) else x
        n = noise.get(d, 0.0); n = 0.0 if pd.isna(n) else n
        pn = n * E
        E = E * (1 + x) + pn
        basis += pn                                    # realized intraday: cash, at basis
        gain += pn
        dv = E * DIV / 252
        E -= dv * LT; basis += dv * (1 - LT)            # reinvested dividend after its tax
        if due is not None and d >= due[0]:
            E -= due[1]; basis -= due[1]; due = None
        if i + 1 < len(days) and days[i + 1].year != d.year:
            net = gain + carry
            if net >= 0:
                tax, carry = ST_RATE * net, 0.0
            else:
                ded = min(3000.0, -net); tax, carry = -ST_RATE * ded, net + ded
            cand = days[days >= pd.Timestamp(f"{d.year + 1}-04-15")]
            due = (cand[0] if len(cand) else days[-1], tax); gain = 0.0
    net = gain + carry
    E -= (due[1] if due is not None else 0.0) + (ST_RATE * net if net > 0 else 0.0)
    basis -= (due[1] if due is not None else 0.0)
    return E - LT * max(0.0, E - basis)


def roth_noqqq(ctx, cost, a, b, start=R0, mo=R_MO):
    s, c_ro, nz, held = ctx
    sw = copy.copy(s); sw.days = s.days[(s.days >= a) & (s.days <= b)]
    PB.RothF3.FE = None
    R = PB.RothF3(sw, nz, held, RO.RV(mech="M2L", v6="all"), cost, start, mo)
    for d in sw.days:
        R.step(d, frozenset(), frozenset({"QQQ", "SMH"}))
    return R.frame()


def main():
    ctx, Ns = ctx_raw()
    s = ctx[0]
    spy = s.C["SPY"].pct_change()
    # check
    d0 = s.days[(s.days >= WIN[0][1]) & (s.days <= WIN[0][2])]
    chk = c2_account(spy, pd.Series(dtype=float), d0, T0, 1000.0)
    print(f"check, noise off 2021-23: C2 ${chk:,.0f} vs index_after_tax ${index_after_tax(spy.reindex(d0), T0, 1000.0)[1]:,.0f}")
    for cost in ("tier", "tier_hi"):
        for wl, a, b in WIN:
            days = s.days[(s.days >= a) & (s.days <= b)]
            Rq = roth_noqqq(ctx, cost, a, b)
            for tmo in (1000.0, 2000.0):
                Tdf, Rdf, dis, gl = run(ctx, Ns, "G4s", cost, a, b, tmo)
                yr = (days[-1] - days[0]).days / 365.25
                f = flows_of(days, T0, tmo, 0.0)[:-1] + flows_of(days, R0, R_MO, 0.0)[:-1]
                for hl in ("EH", "as-bt"):
                    h = 0.5 if hl == "EH" else 0.0
                    te = Tdf.r - h * (Tdf.r_night.mean() + Tdf.r_ibs.mean() + Tdf.r_noise.mean())
                    _, info = TF.after_tax(te, rate=ST_RATE, start=T0, monthly=tmo)
                    Tp = info["end_E"] - ST_RATE * sum(dis.values())
                    rr = (PB.roth_eh(Rdf) if h else Rdf.r); rq = (PB.roth_eh(Rq) if h else Rq.r)
                    Rp, Rc = grow(rr, R0, R_MO), grow(rq, R0, R_MO)
                    noise = Tdf.r_noise - h * Tdf.r_noise.mean()
                    Tc = c2_account(spy, noise, days, T0, tmo)
                    Ts = index_after_tax(spy.reindex(days), T0, tmo)[1]
                    ip = irr(f + [(yr, Tp + Rp)]) * 100; ic = irr(f + [(yr, Tc + Rc)]) * 100
                    i1 = irr(f + [(yr, Ts + Rc)]) * 100
                    print(f"  {cost:8s} {wl:8s} ${tmo:4.0f}/mo {hl:5s} P: T ${Tp:>9,.0f} R ${Rp:>9,.0f} IRR {ip:5.1f}% | "
                          f"C2: T ${Tc:>9,.0f} R(no QQQ/SMH IBS) ${Rc:>9,.0f} IRR {ic:5.1f}% | C2-P {ic - ip:+5.2f}pp "
                          f"| (SPY-only taxable {i1 - ip:+5.2f}pp) | noise {noise.sum() / yr * 100:+.1f}%/yr", flush=True)


if __name__ == "__main__":
    main()
