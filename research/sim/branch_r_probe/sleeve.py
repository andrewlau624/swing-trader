"""BRANCH R probe 4: recompute the PREF-EX+ETDX sleeve $/yr vs participation p with a measured-impact cost curve.
Reuses pref_exec.account (equal split across a night's events, cap p x ex-ante auction $, whole shares) and etdx_exec.rows.
cost per leg (decimal) = base + impact(p); impact models (per leg, bp), A/B/C below; reported gross of tax, fixed account (no compounding).
    PYTHONPATH=. .venv/bin/python -m research.sim.branch_r_probe.sleeve
"""
import numpy as np, pandas as pd
from ..etdx_exec import rows
from ..pref_exec import account
from .cross_stats import load
from .taq_pull import OUT

P = [0.05, 0.10, 0.20, 0.30, 0.50]
ACC = [1e4, 2.5e4]

def main():
    L = []
    c = load(); dev = c.abs_dev.mean(); b = 32.6; sh = c.sh_day.median()
    try:
        o = pd.read_parquet(OUT / "taq_open.parquet"); o["X"] = o.open_sh * o.open_px
        o["mid"] = (o.bo + o.ao) / 2; o["ad"] = ((o.open_px / o.mid - 1) * 1e4).abs(); o = o.replace([np.inf, -np.inf], np.nan).dropna(subset=["ad"])
        dev_o = o.ad.mean()
    except Exception:
        dev_o = np.nan
    both = pd.concat([rows("pref"), rows("etdx")], ignore_index=True)
    lo = max(rows("pref").d.min(), rows("etdx").d.min()); hi = min(rows("pref").d.max(), rows("etdx").d.max())
    both = both[(both.d >= lo) & (both.d <= hi)].dropna(subset=["pc", "cap_close_ea", "cap_open_ea"])
    # floor-subtracted dispersion: |dev| in the lowest cross/day-vol quartile is quote noise, not imbalance impact
    q = pd.qcut(c.sh_day, 4, labels=False); floor = c.abs_dev[q == 0].mean(); exc = c.abs_dev[q == 3].mean() - floor
    OS = 3.3   # open half-spread (median 60bp) / close half-spread (18bp)
    L.append(f"floor |dev| {floor:.1f}bp; top-quartile excess dispersion {exc:.1f}bp at median cross/day share {c.sh_day[q==3].median():.2f}")
    models = {  # (close-leg impact bp, open-leg impact bp) at participation p
        "C  sqrt-law on day $vol (b=32.6)":      lambda p: (b * np.sqrt(sh) * (np.sqrt(1 + p) - 1),) * 2,
        "D  PREF-PART 0.8*sqrt(100p)":           lambda p: (0.8 * np.sqrt(100 * p),) * 2,
        "S1 stress: excess/cross, g=1":          lambda p: (min(exc * p, 18), min(exc * p * OS, 60)),
        "S2 severe: excess/cross, g=.25, cap hs": lambda p: (min(exc * p * 4, 18), min(exc * p * 4 * OS, 60)),
    }
    L.insert(0, f"BRANCH R sleeve: PREF+ETDX official crosses {lo.date()}..{hi.date()}, {len(both)} events")
    L.append("gross $/yr (account fixed, no leverage, whole shares); base = flat bp/side on top of impact")
    L.append("")
    for base in (0.0, 5.0):
        for name, f in models.items():
            for col in ("co", "cc"):
                for a in ACC:
                    cells = []
                    for p in P:
                        ic, io = f(p)
                        ci = (ic + base) / 1e4
                        co_ = ((io if col == "co" else ic) + base) / 1e4
                        d, pct, use = account(both, col, a, p, ci, co_, True, False)
                        cells.append(f"{d:6,.0f}")
                    L.append(f"base {base:3.0f}bp | {name:38s} {col.upper()} ${a:>6,.0f} | " + " ".join(f"p{int(p*100):>3d}%:{x}" for p, x in zip(P, cells)))
        L.append("")
    s = "\n".join(L); (OUT.parent.parent.parent / "research/sim/branch_r_probe/sleeve_out.txt").write_text(s + "\n"); print(s)

if __name__ == "__main__": main()
