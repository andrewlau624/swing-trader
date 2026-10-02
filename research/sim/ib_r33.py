"""Index-beat R3-3: the Roth as 0.5 SPY + 3x noise leg on the other half (report). PYTHONPATH=. python -m research.sim.ib_r33"""
from __future__ import annotations

import pandas as pd

from . import program_books as PB
from . import roth_opt as RO
from .ib_c1 import R0, R_MO, T0, WIN, ctx_raw, flows_of, grow, irr, run


def main():
    ctx, Ns = ctx_raw()
    s = ctx[0]
    spy = s.C["SPY"].pct_change()
    for cost in ("tier", "tier_hi"):
        for wl, a, b in WIN:
            days = s.days[(s.days >= a) & (s.days <= b)]
            _, Rdf, _, _ = run(ctx, Ns, "G0", cost, a, b, 1000.0)
            for hl, h in (("EH", 0.5), ("as-bt", 0.0)):
                book = PB.roth_eh(Rdf) if h else Rdf.r
                noise = Rdf.r_noise - h * Rdf.r_noise.mean()
                bil = pd.Series({d: RO.bil(s, d) for d in days})
                v = 0.5 * spy.reindex(days).fillna(0) + noise.reindex(days).fillna(0) + 0.5 * bil
                Eb, Ev, Es = grow(book, R0, R_MO), grow(v, R0, R_MO), grow(spy.reindex(days), R0, R_MO)
                f = flows_of(days, R0, R_MO, 0.0)[:-1]; yr = (days[-1] - days[0]).days / 365.25
                ib, iv, i_s = (irr(f + [(yr, E)]) * 100 for E in (Eb, Ev, Es))
                print(f"  {cost:8s} {wl:8s} {hl:5s} Roth book ${Eb:>9,.0f} ({ib:5.1f}%) | 0.5 SPY + noise ${Ev:>9,.0f} ({iv:5.1f}%) "
                      f"| all-SPY ${Es:>9,.0f} ({i_s:5.1f}%) | V-book {iv - ib:+5.1f}pp", flush=True)


if __name__ == "__main__":
    main()
