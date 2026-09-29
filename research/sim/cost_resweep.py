"""Addendum 29: cost-sensitive decisions re-tested at the costs live fills measured.

    PYTHONPATH=. .venv/bin/python -m research.sim.cost_resweep

Live (2026-09-22 .. 09-28, 26 night round trips): buys -0.5bp, open sells -1.0bp/side
vs the official auction prints (95% upper bound +11.7bp). The research tiers
(book.TIERS) assumed 5-15bp (tier) and 7.5-25bp (tier_hi). 3bp flat is the
conservative stand-in for "measured"; tier_hi stays the planning floor.
  A. overnight leverage 1.0x vs 1.3x      (the lever gate)
  B. night vol20 filter 0.60 / 0.50 / 0.40
  C. night depth -8% / -7% / -6%          (addendum 20 rejected shallower)
  D. sizing profiles (addendum 22) at 3bp and tier_hi, history and edge-halves, 5y MC
"""
from __future__ import annotations

from . import book as B, depth as DP, growth as G
from .validate import load_sim

COSTS = [0.0, 3.0, "tier", "tier_hi"]
# (overnight gross, night name cap, conviction weight, intraday cap or None = max)
PROFILES = {
    "V7 shipped (1.0x, cap 0.10)": (1.0, 0.10, 0.5, None),
    "V7 at 1.3x (the lever gate)": (1.3, 0.10, 0.5, None),
    "1.3x, cap 0.15": (1.3, 0.15, 0.5, None),
    "aggressive (1.3x, cap 0.20, intraday 0.6)": (1.3, 0.20, 0.5, 0.6),
    "1.5x, cap 0.10": (1.5, 0.10, 0.5, None),
    "1.5x, cap 0.15": (1.5, 0.15, 0.5, None),
    "1.3x, no conviction": (1.3, 0.10, 0.0, None),
}


def fmt(r) -> str:
    a, b, f = B.stats(r[:"2023-12-31"]), B.stats(r["2024-01-01":]), B.stats(r)
    return (f"{a[0]*100:5.1f}/{a[1]:4.2f}  {b[0]*100:5.1f}/{b[1]:4.2f}  "
            f"{f[0]*100:5.1f}/{f[1]:4.2f}/{f[2]*100:4.0f}")


def main():
    s = load_sim()
    Ns = {c: B.night_days(max_corr=0.7, max_name_pct=c) for c in (0.10, 0.15, 0.20)}

    def run(N, g=1.0, cost="tier", conv=0.5, noise=None):
        s.N = N
        return s.replay(B.Params(**{**G.V7, **G.cfg(g, conv, 2, noise), "night_cost": cost}))

    hdr = f"{'':44s}{'cost':>8s}   2021-23      2024-26      full CAGR/Sh/DD"
    print(hdr + "\n== A. overnight leverage (the gate)")
    for c in COSTS:
        for g in (1.0, 1.3):
            print(f"  {'V7 at %.1fx overnight' % g:42s}{str(c):>8s}   {fmt(run(Ns[0.10], g, c)['r'])}")
    print("== B. night quiet-name filter (vol20 >= x)")
    for c in COSTS:
        for v in (0.60, 0.50, 0.40):
            N = B.night_days(vol_min=v, max_corr=0.7, max_name_pct=0.10)
            print(f"  {'vol_min %.2f' % v:42s}{str(c):>8s}   {fmt(run(N, 1.0, c)['r'])}")
    print("== C. night depth threshold (honest 15:50 pool)")
    x = DP.candidates()
    Nd = {t: DP.night_days(x, "plain", thresh=t) for t in (-0.08, -0.07, -0.06)}
    for c in COSTS:
        for t, N in Nd.items():
            print(f"  {'day_ret <= %.0f%%' % (t*100):42s}{str(c):>8s}   {fmt(run(N, 1.0, c)['r'])}")
    print("== D. sizing profiles: history | edge-halves (EH) | 5y MC $3k + $1k/mo under EH")
    for c in (3.0, "tier_hi"):
        for name, (g, cap, conv, nz) in PROFILES.items():
            df = run(Ns[cap], g, c, conv, nz)
            e, m = B.stats(G.eh(df)), G.mc(G.eh(df), 3000, 1000)
            print(f"  {name:42s}{str(c):>8s}   {fmt(df['r'])} | EH {e[0]*100:5.1f}/{e[1]:4.2f}/{e[2]*100:4.0f}"
                  f" | median ${m['med']:>9,.0f}  P(DD>30%) {m['dd30']:4.0%}  P(DD>50%) {m['dd50']:4.0%}")


if __name__ == "__main__":
    main()
