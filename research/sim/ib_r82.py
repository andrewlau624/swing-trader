"""Index-beat R8-2: the Roth as 1/3 UPRO + 2/3 the Roth book (stacking without margin), on the combined plan.

    PYTHONPATH=. .venv/bin/python -m research.sim.ib_r82
Spec: index_beat_log.md (R8-2). Combined plan IRR (taxable + Roth, after tax, EH) for: P; P with the R8-2 Roth; R6-5 taxable
with the R8-2 Roth. COVID: UPRO and SPY 2020-02-19..03-23 and all of 2020.
"""
from __future__ import annotations

import pandas as pd

from . import program_books as PB
from . import taxable_frontier as TF
from .ib_c1 import R0, R_MO, T0, WIN, ctx_raw, flows_of, grow, irr, run
from .ib_c2 import ST_RATE, c2_account, roth_noqqq
from .ib_r65 import MARGIN


def mix(base, up):
    u = up.reindex(base.index).fillna(0)
    return base * 2 / 3 + u / 3 - (u - base).abs() * (2 / 9) * 1e-4


def main():
    ctx, Ns = ctx_raw()
    s = ctx[0]
    spy, up = s.C["SPY"].pct_change(), s.C["UPRO"].pct_change()
    used = pd.Series({d: min(1.0, nd.frac * len(nd.syms)) for d, nd in Ns[0.10].items()})
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
                Rp = grow(PB.roth_eh(Rdf), R0, R_MO)
                Ru = grow(mix(PB.roth_eh(Rdf), up), R0, R_MO)
                Ruq = grow(mix(PB.roth_eh(Rq), up), R0, R_MO)
                legs = sum(Tdf[k] - 0.5 * Tdf[k].mean() for k in ("r_noise", "r_night", "r_ibs"))
                debit = 0.5 * ibs_on.reindex(days).fillna(0) + 0.5 * used.reindex(days).fillna(0)
                Ts = c2_account(spy, legs.reindex(days).fillna(0) - debit * MARGIN / 252, days, T0, tmo)
                ip, iu, isu = (irr(f + [(yr, E)]) * 100 for E in (Tp + Rp, Tp + Ru, Ts + Ruq))
                print(f"  {cost:8s} {wl:8s} ${tmo:4.0f}/mo EH | P {ip:5.1f}% | P + UPRO-Roth {iu:5.1f}% ({iu - ip:+5.2f}pp) | "
                      f"R6-5 + UPRO-Roth {isu:5.1f}% ({isu - ip:+5.2f}pp)", flush=True)
    for a, b in (("2020-02-19", "2020-03-23"), ("2020-01-02", "2020-12-31")):
        for nm, x in (("SPY", spy), ("UPRO", up)):
            c = (1 + x[a:b].fillna(0)).cumprod()
            print(f"  {a}..{b} {nm}: return {(c.iloc[-1] - 1) * 100:+.1f}%, max DD {(c / c.cummax() - 1).min() * 100:.1f}%")


if __name__ == "__main__":
    main()


def vs_index_and_risk():
    """POST-HOC checks for the R6-5 + R8-2 combination: (1) vs SPY in both accounts; (2) MC drawdown risk per account."""
    ctx, Ns = ctx_raw()
    s = ctx[0]
    spy, up = s.C["SPY"].pct_change(), s.C["UPRO"].pct_change()
    used = pd.Series({d: min(1.0, nd.frac * len(nd.syms)) for d, nd in Ns[0.10].items()})
    ibs_on = pd.Series({d: 1.0 for d in s.I})
    from .ib_c1 import index_after_tax
    for wl, a, b in WIN:
        days = s.days[(s.days >= a) & (s.days <= b)]
        Rq = roth_noqqq(ctx, "tier", a, b)
        for tmo in (1000.0, 2000.0):
            Tdf, Rdf, dis, gl = run(ctx, Ns, "G4s", "tier", a, b, tmo)
            yr = (days[-1] - days[0]).days / 365.25
            f = flows_of(days, T0, tmo, 0.0)[:-1] + flows_of(days, R0, R_MO, 0.0)[:-1]
            legs = sum(Tdf[k] - 0.5 * Tdf[k].mean() for k in ("r_noise", "r_night", "r_ibs"))
            debit = 0.5 * ibs_on.reindex(days).fillna(0) + 0.5 * used.reindex(days).fillna(0)
            Ts = c2_account(spy, legs.reindex(days).fillna(0) - debit * MARGIN / 252, days, T0, tmo)
            Ruq = grow(mix(PB.roth_eh(Rq), up), R0, R_MO)
            Ti = index_after_tax(spy.reindex(days), T0, tmo)[1]
            Ri = grow(spy.reindex(days), R0, R_MO)
            ii, isu = (irr(f + [(yr, E)]) * 100 for E in (Ti + Ri, Ts + Ruq))
            print(f"  {wl:8s} ${tmo:4.0f}/mo tier EH | SPY in both accounts {ii:5.1f}% | R6-5 + UPRO-Roth {isu:5.1f}% ({isu - ii:+5.2f}pp vs index)")
    a, b = WIN[2][1], WIN[2][2]
    days = s.days[(s.days >= a) & (s.days <= b)]
    _, Rdf, _, _ = run(ctx, Ns, "G0", "tier", a, b, 1000.0)
    Rq = roth_noqqq(ctx, "tier", a, b)
    for nm, r in (("Roth book EH", PB.roth_eh(Rdf)), ("Roth SPY", spy.reindex(days).fillna(0)), ("Roth 1/3 UPRO + 2/3 book", mix(PB.roth_eh(Rq), up))):
        m = TF.mc_tax(r, rate=0.0, lt=0.0, start=R0, monthly=R_MO)
        print(f"  MC 5y {nm:26s} median ${m['med']:,.0f} p10 ${m['p10']:,.0f} P(DD>30%) {m['dd30']:.0%} P(DD>50%) {m['dd50']:.1%}")


if __name__ == "__main__" and False:
    pass
