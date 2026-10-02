"""Index-beat C4: the Section 475(f) mark-to-market election as an account-structure change (report, no N).

    PYTHONPATH=. .venv/bin/python -m research.sim.ib_c4

Under 475(f) the taxable account's securities are marked to market: section 1091 (wash sales, incl. the permanent
cross-account Rev. Rul. 2008-5 disallowance) stops applying and net losses are ordinary (no $3k cap). So both accounts
can run with NO guard (G0): every night name, every IBS ETF, in both. Compared with the plan (G4s, Roth first):
taxable EH after tax at 35% (after_tax with ded = unlimited for 475; the plan keeps $3k), Roth EH. Same windows, sizes,
pool and costs as ib_c1. Trader tax status is a facts-and-circumstances CPA question; this only prices the upside.
"""
from __future__ import annotations

from . import program_books as PB
from . import taxable_frontier as TF
from .ib_c1 import R0, R_MO, T0, WIN, ctx_raw, flows_of, grow, irr, run


def main():
    ctx, Ns = ctx_raw()
    s = ctx[0]
    for cost in ("tier", "tier_hi"):
        for wl, a, b in WIN:
            days = s.days[(s.days >= a) & (s.days <= b)]
            res = {}
            for lab, guard, ded in (("P G4s", "G4s", 3000.0), ("475 G0", "G0", 1e12)):
                Tdf, Rdf, dis, gl = run(ctx, Ns, guard, cost, a, b, 1000.0)
                te = Tdf.r - 0.5 * (Tdf.r_night.mean() + Tdf.r_ibs.mean() + Tdf.r_noise.mean())
                _, info = TF.after_tax(te, rate=0.35, start=T0, monthly=1000.0, ded=ded)
                Tend = info["end_E"] - (0.35 * sum(dis.values()) if guard != "G0" else 0.0)
                Rend = grow(PB.roth_eh(Rdf), R0, R_MO)
                f = flows_of(days, T0, 1000.0, 0.0)[:-1] + flows_of(days, R0, R_MO, 0.0)[:-1]
                f.append(((days[-1] - days[0]).days / 365.25, Tend + Rend))
                res[lab] = (Tend, Rend, irr(f) * 100, sum(dis.values()) / max(sum(gl.values()), 1e-9))
            (tp, rp, ip, dp), (tc, rc, ic, dc) = res["P G4s"], res["475 G0"]
            print(f"  {cost:8s} {wl:8s} P: T ${tp:>9,.0f} R ${rp:>9,.0f} IRR {ip:5.1f}% (G4s dis {dp:4.1%}) | 475+G0: "
                  f"T ${tc:>9,.0f} R ${rc:>9,.0f} IRR {ic:5.1f}% (G0 would disallow {dc:4.0%} without 475) | {ic - ip:+5.2f}pp",
                  flush=True)


if __name__ == "__main__":
    main()
