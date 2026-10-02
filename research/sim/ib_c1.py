"""Index-beat hunt, idea C1 (+ C2, C3, C5 rate sensitivity): where the bot runs, after tax, on the user's plan.

    PYTHONPATH=. .venv/bin/python -m research.sim.ib_c1

Pre-written (index_beat_ideas.md, ff9eac7, before any outcome). Track C, report-type (no N).
Plan (base) P: taxable runs the live book (V7 1.0x, cap .10, no conviction = J4's taxable) beside the proposed Roth
book (M2L + A2), wash guard G4s (Roth first). C1: taxable holds SPY (total return; ~1.3%/yr dividends taxed at the LT
rate each year; the unrealized gain is shown both held and liquidated at 20%), the Roth runs the same proposed book
with NO guard (taxable never sells, so nothing collides). C3: C1/P with the Roth's $7.5k deposited on the first
session of each year instead of $625 every 21 sessions. Edge-halves on every bot book (half of each leg's mean
removed, as program_books.joint_eh), tier costs (and tier_hi), RAW night pool. Taxable bot after tax:
taxable_frontier.after_tax (35% ST, April payment, carry-forward, $3k deduction; no trade list, so same-account wash
deferral is not modelled — a timing effect — and G4s's ~0.5% permanent cross-account disallowance is added back).
User plan: taxable $2.3k + $1k (or $2k) / 21 sessions; Roth $8.5k + $625 / 21 sessions. Windows: 2021-02..2023-12,
2024-01..2026-09 (each restarted at the plan's balances), and the full window.
Metric: combined after-tax money-weighted %/yr (IRR of deposits vs end value), C - P in pp.
"""
from __future__ import annotations

import copy
import sys

import numpy as np
import pandas as pd

from . import program_books as PB
from . import roth_opt as RO
from . import taxable_frontier as TF

PB.RAW = True
T0, R0, R_MO = 2300.0, 8500.0, 625.0
WIN = (("2021-23", "2021-02-01", "2023-12-31"), ("2024-26", "2024-01-01", "2026-09-18"),
       ("full", "2021-02-01", "2026-09-18"))
DIV, LT = 0.013, 0.20


def irr(flows):
    """flows: list of (t_years, amount), deposits negative, end value positive."""
    t = np.array([f[0] for f in flows]); a = np.array([f[1] for f in flows])
    lo, hi = -0.9, 3.0
    for _ in range(200):
        m = (lo + hi) / 2
        v = (a / (1 + m) ** t).sum()
        lo, hi = (m, hi) if v > 0 else (lo, m)
    return m


def flows_of(days, start, mo, end, lump=None):
    t0 = days[0]
    f = [(0.0, -start)]
    for i, d in enumerate(days):
        if lump is None:
            if i and i % 21 == 0:
                f.append(((d - t0).days / 365.25, -mo))
        elif i and d.year != days[i - 1].year:
            f.append(((d - t0).days / 365.25, -lump))
    f.append(((days[-1] - t0).days / 365.25, end))
    return f


def grow(r, start, mo, lump=None):
    E = start
    for i, (d, x) in enumerate(r.fillna(0).items()):
        if lump is None:
            if i and i % 21 == 0:
                E += mo
        elif i and d.year != r.index[i - 1].year:
            E += lump
        E *= 1 + x
    return E


def index_after_tax(spy, start, mo):
    """SPY total return; dividends (DIV/yr) taxed at LT each year (paid from the account);
    returns (end held, end liquidated, basis)."""
    E, basis = start, start
    for i, (d, x) in enumerate(spy.fillna(0).items()):
        if i and i % 21 == 0:
            E += mo; basis += mo
        E *= 1 + x
        E -= E * DIV / 252 * LT
        basis += E * DIV / 252 * (1 - LT)        # reinvested dividends add basis
    return E, E - LT * max(0.0, E - basis)


def ctx_raw():
    ctx = RO.load_ctx()
    s0, c_ro, nz, held = ctx
    _, Ns, _ = TF.load()
    Ns, c_ro, _, _ = PB.pool_inputs(Ns, c_ro, None, None)
    s = copy.copy(s0); s.N = c_ro["N"]
    return (s, c_ro, nz, held), Ns


def run(ctx, Ns, guard, cost, a, b, tmo, lump=None):
    s, c_ro, nz, held = ctx
    sw = copy.copy(s); sw.days = s.days[(s.days >= a) & (s.days <= b)]
    cx = (sw, c_ro, nz, held)
    o = (RO.Taxable, RO.Roth, RO.TAX, RO.TAX0, RO.TAX_MO, RO.ROTH0, RO.ROTH_MO)
    PB.RothF3.FE = None
    try:
        RO.Taxable, RO.Roth, RO.TAX = PB.make_tax(1.0, 0.10, 0.0, Ns[0.10], False), PB.RothF3, 0.35
        RO.TAX0, RO.TAX_MO, RO.ROTH0, RO.ROTH_MO = T0, tmo, R0, (0.0 if lump else R_MO)
        Tdf, Rdf, dis, _, gl = RO.run_pair(cx, guard, cost, RO.RV(mech="M2L", v6="all"))
    finally:
        RO.Taxable, RO.Roth, RO.TAX, RO.TAX0, RO.TAX_MO, RO.ROTH0, RO.ROTH_MO = o
    return Tdf, Rdf, dis, gl


def main():
    ctx, Ns = ctx_raw()
    s = ctx[0]
    spy = s.C["SPY"].pct_change()
    PB.F3FLAG = None
    rates = (0.35,) if "--rates" not in sys.argv else (0.0, 0.12, 0.22, 0.32, 0.35)
    print("C1/C3 combined plan (after tax, edge-halves, RAW pool). IRR = money-weighted %/yr of both accounts.")
    for cost in ("tier", "tier_hi"):
        for tmo in (1000.0, 2000.0):
            for wl, a, b in WIN:
                days = s.days[(s.days >= a) & (s.days <= b)]
                out = {}
                for lump in (None, 7500.0):
                    # P: bot in both accounts under G4s (Roth first)
                    Tdf, Rdf, dis, gl = run(ctx, Ns, "G4s", cost, a, b, tmo, lump)
                    te = Tdf.r - 0.5 * (Tdf.r_night.mean() + Tdf.r_ibs.mean() + Tdf.r_noise.mean())
                    re_ = PB.roth_eh(Rdf)
                    Rend = grow(re_, R0, R_MO, lump)
                    pdis = sum(dis.values()) / max(sum(gl.values()), 1e-9)
                    for rate in rates:
                        net, info = TF.after_tax(te, rate=rate, start=T0, monthly=tmo)
                        Tend = info["end_E"] - rate * sum(dis.values())        # disallowed losses lose their deduction
                        out[("P", lump, rate)] = (Tend, Rend)
                    # C1: Roth unguarded (G0 with a taxable that never sells = Roth standalone), taxable = SPY
                    _, Rdf0, _, _ = run(ctx, Ns, "G0", cost, a, b, tmo, lump)
                    Rend0 = grow(PB.roth_eh(Rdf0), R0, R_MO, lump)
                    held_, liq = index_after_tax(spy.reindex(days), T0, tmo)
                    out[("C1", lump, None)] = (liq, Rend0, held_)
                dep = lambda lump: flows_of(days, T0, tmo, 0.0)[:-1] + [(x[0], x[1]) for x in flows_of(days, R0, R_MO, 0.0, lump)[:-1]]
                def comb_irr(Tend, Rend, lump):
                    f = dep(lump) + [((days[-1] - days[0]).days / 365.25, Tend + Rend)]
                    return irr(f) * 100
                for rate in rates:
                    for lump in (None, 7500.0):
                        Tp, Rp = out[("P", lump, rate)]
                        Tc, Rc, Th = out[("C1", lump, None)]
                        ip, ic = comb_irr(Tp, Rp, lump), comb_irr(Tc, Rc, lump)
                        lab = "monthly" if lump is None else "Jan lump"
                        print(f"  {cost:8s} ${tmo:4.0f}/mo {wl:8s} rate {rate:4.0%} Roth {lab:8s} | P: T ${Tp:>9,.0f} R ${Rp:>9,.0f} "
                              f"IRR {ip:5.1f}% (dis {pdis:4.1%}) | C1: SPY ${Tc:>9,.0f} (held ${Th:>9,.0f}) R ${Rc:>9,.0f} IRR {ic:5.1f}% "
                              f"| C1-P {ic - ip:+5.1f}pp", flush=True)
                    ipm = comb_irr(*out[("P", None, rate)], None); ipl = comb_irr(*out[("P", 7500.0, rate)], 7500.0)
                    print(f"      C3 (Jan lump vs monthly, plan P) {ipl - ipm:+5.2f}pp   "
                          f"(C1 book {comb_irr(*out[('C1', 7500.0, None)][:2], 7500.0) - comb_irr(*out[('C1', None, None)][:2], None):+5.2f}pp)")


if __name__ == "__main__" and "--c5" not in sys.argv:
    main()


# ---------------------------------------------------------------- C3 (dollars) and C5 (rate grid), second script part
def c5_c3():
    ctx, Ns = ctx_raw()
    s = ctx[0]
    spy = s.C["SPY"].pct_change()
    print("C5 rate grid (taxable bot after tax vs SPY, $2.3k + $1k/mo; Roth unchanged) and C3 in dollars")
    for wl, a, b in WIN:
        days = s.days[(s.days >= a) & (s.days <= b)]
        Tdf, Rdf, dis, gl = run(ctx, Ns, "G4s", "tier", a, b, 1000.0)
        te = Tdf.r - 0.5 * (Tdf.r_night.mean() + Tdf.r_ibs.mean() + Tdf.r_noise.mean())
        held_, liq = index_after_tax(spy.reindex(days), T0, 1000.0)
        for eh_lab, rr in (("EH", te), ("as-backtested", Tdf.r)):
            row = []
            for rate in (0.0, 0.12, 0.22, 0.32, 0.35):
                _, info = TF.after_tax(rr, rate=rate, start=T0, monthly=1000.0)
                row.append(f"{rate:4.0%} ${info['end_E']:>8,.0f}")
            print(f"  {wl:8s} {eh_lab:14s} bot T: " + " | ".join(row) + f" || SPY liq ${liq:,.0f} held ${held_:,.0f}")
        # C3: Roth time-weighted EH returns, lump vs monthly, waiting money in SPY (untaxed: unrealized)
        re_ = PB.roth_eh(Rdf)
        dep = pd.Series(0.0, index=days)
        for i, d in enumerate(days):
            if i and i % 21 == 0:
                dep[d] += R_MO
        yr_first = pd.Series(days, index=days).groupby(days.year).transform("first")
        lump = dep.groupby(yr_first).sum().reindex(days).fillna(0.0)
        ends = []
        for sched in (dep, lump):
            R = R0; W = 0.0
            for d in days:
                if d == yr_first[d]:
                    W += dep[days.year == d.year].sum()       # the year's Roth money is available on its first session
                R += sched[d]; W -= sched[d]
                x = re_.get(d, 0.0); R *= 1 + (0.0 if pd.isna(x) else x)
                z = spy.get(d, 0.0); W *= 1 + (0.0 if pd.isna(z) else z)
            ends.append((R, W, R + W))
        yrs = (days[-1] - days[0]).days / 365.25
        print(f"  {wl:8s} C3 Roth monthly: R ${ends[0][0]:,.0f} + waiting-in-SPY ${ends[0][1]:,.0f} = ${ends[0][2]:,.0f}; "
              f"Jan lump: R ${ends[1][0]:,.0f} = ${ends[1][2]:,.0f}; gain ${ends[1][2] - ends[0][2]:+,.0f} "
              f"(${(ends[1][2] - ends[0][2]) / yrs:+,.0f}/yr)")


if __name__ == "__main__" and "--c5" in sys.argv:
    c5_c3()
