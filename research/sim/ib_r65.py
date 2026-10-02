"""Index-beat R6-5: SPY core + every leg stacked on margin (portable alpha) in taxable. PYTHONPATH=. python -m research.sim.ib_r65"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import program_books as PB
from . import taxable_frontier as TF
from .ib_c1 import R0, R_MO, T0, WIN, ctx_raw, flows_of, grow, irr, run
from .ib_c2 import ST_RATE, c2_account, roth_noqqq

MARGIN = 0.12


def main():
    ctx, Ns = ctx_raw()
    s = ctx[0]
    spy = s.C["SPY"].pct_change()
    N = Ns[0.10]
    used = pd.Series({d: min(1.0, nd.frac * len(nd.syms)) for d, nd in N.items()})
    ibs_on = pd.Series({d: 1.0 for d in s.I})
    for cost in ("tier", "tier_hi"):
        for wl, a, b in WIN:
            days = s.days[(s.days >= a) & (s.days <= b)]
            Rq = roth_noqqq(ctx, cost, a, b)
            for tmo in (1000.0, 2000.0):
                Tdf, Rdf, dis, gl = run(ctx, Ns, "G4s", cost, a, b, tmo)
                yr = (days[-1] - days[0]).days / 365.25
                f = flows_of(days, T0, tmo, 0.0)[:-1] + flows_of(days, R0, R_MO, 0.0)[:-1]
                te = Tdf.r - 0.5 * (Tdf.r_night.mean() + Tdf.r_ibs.mean() + Tdf.r_noise.mean())
                _, info = TF.after_tax(te, rate=ST_RATE, start=T0, monthly=tmo)
                Tp = info["end_E"] - ST_RATE * sum(dis.values())
                Rp, Rc = grow(PB.roth_eh(Rdf), R0, R_MO), grow(PB.roth_eh(Rq), R0, R_MO)
                legs = sum(Tdf[k] - 0.5 * Tdf[k].mean() for k in ("r_noise", "r_night", "r_ibs"))
                debit = 0.5 * ibs_on.reindex(days).fillna(0) + 0.5 * used.reindex(days).fillna(0)
                stack = legs.reindex(days).fillna(0) - debit * MARGIN / 252
                Tc = c2_account(spy, stack, days, T0, tmo)
                Tn = c2_account(spy, (Tdf.r_noise - 0.5 * Tdf.r_noise.mean()), days, T0, tmo)
                ip, ic, i2 = (irr(f + [(yr, E)]) * 100 for E in (Tp + Rp, Tc + Rc, Tn + Rc))
                print(f"  {cost:8s} {wl:8s} ${tmo:4.0f}/mo EH | P {ip:5.1f}% | stacked {ic:5.1f}% ({ic - ip:+5.2f}pp) | C2 noise-only "
                      f"{i2:5.1f}% ({i2 - ip:+5.2f}pp) | mean debit {debit.mean():.2f}E, interest {debit.mean() * MARGIN * 100:.1f}%/yr", flush=True)


if __name__ == "__main__":
    main()


def risk():
    ctx, Ns = ctx_raw()
    s = ctx[0]
    spy = s.C["SPY"].pct_change()
    used = pd.Series({d: min(1.0, nd.frac * len(nd.syms)) for d, nd in Ns[0.10].items()})
    ibs_on = pd.Series({d: 1.0 for d in s.I})
    a, b = WIN[2][1], WIN[2][2]
    days = s.days[(s.days >= a) & (s.days <= b)]
    Tdf, _, _, _ = run(ctx, Ns, "G4s", "tier", a, b, 1000.0)
    for hl, h in (("EH", 0.5), ("as-bt", 0.0)):
        legs = sum(Tdf[k] - h * Tdf[k].mean() for k in ("r_noise", "r_night", "r_ibs"))
        debit = 0.5 * ibs_on.reindex(days).fillna(0) + 0.5 * used.reindex(days).fillna(0)
        st = spy.reindex(days).fillna(0) + legs.reindex(days).fillna(0) - debit * MARGIN / 252
        bot = (Tdf.r - h * (Tdf.r_night.mean() + Tdf.r_ibs.mean() + Tdf.r_noise.mean())).reindex(days).fillna(0)
        for lab, r in (("SPY", spy.reindex(days).fillna(0)), ("bot (plan)", bot), ("stacked", st)):
            c = (1 + r).cumprod(); dd = (c / c.cummax() - 1).min()
            w = r.groupby(r.index.to_period("M")).apply(lambda x: (1 + x).prod() - 1).min()
            print(f"  {hl:5s} {lab:11s} CAGR {(c.iloc[-1] ** (252 / len(c)) - 1) * 100:5.1f}%  maxDD {dd * 100:6.1f}%  worst month {w * 100:6.1f}%  "
                  f"2022 {((1 + r['2022']).prod() - 1) * 100:+6.1f}%")


if __name__ == "__main__" and False:
    pass
