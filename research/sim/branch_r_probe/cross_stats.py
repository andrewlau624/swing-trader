"""BRANCH R probe 3: cross price vs pre-close NBBO, by cross size. Execution-economics on touched data; no N."""
import numpy as np, pandas as pd
from .taq_pull import OUT

def load():
    d = pd.read_parquet(OUT / "taq_cross.parquet")
    d["X"] = d.X_sh * d.px
    d["mid59"] = (d.b59 + d.a59) / 2; d["hs59"] = (d.a59 - d.b59) / 2 / d.mid59 * 1e4
    d["mid50"] = (d.b50 + d.a50) / 2
    d["dev59"] = (d.px / d.mid59 - 1) * 1e4; d["dev50"] = (d.px / d.mid50 - 1) * 1e4
    d["z"] = (d.px - d.mid59) / ((d.a59 - d.b59) / 2)
    d["inside"] = (d.px >= d.b59 - 1e-9) & (d.px <= d.a59 + 1e-9)
    d["sh_day"] = d.X / (d.X + d.pre_usd)
    d["x_adv"] = d.X / d.dv
    d["abs_dev"] = d.dev59.abs()
    return d.replace([np.inf, -np.inf], np.nan).dropna(subset=["dev59", "hs59"])

def main():
    d = load(); L = []
    L.append(f"TAQ closing crosses (scond '6') on E-1, {len(d)} events / {d.d0.nunique()} ex-nights, {d.d0.min().date()}..{d.d0.max().date()}; "
             f"px vs events.pc median abs diff {((d.px/d.pc-1).abs().median())*1e4:.2f}bp")
    L.append(f"cross $: median ${d.X.median():,.0f} p25 ${d.X.quantile(.25):,.0f} p75 ${d.X.quantile(.75):,.0f}; shares median {d.X_sh.median():.0f}; "
             f"cross/day$ median {d.sh_day.median():.3f}")
    L.append(f"15:59:50 NBBO half-spread: median {d.hs59.median():.1f}bp mean {d.hs59.mean():.1f}; top-of-book size median {d[['bs59','as59']].min(axis=1).median():.0f} lots")
    L.append(f"cross print vs 15:59:50 mid: mean {d.dev59.mean():+.2f}bp median {d.dev59.median():+.2f}; mean |dev| {d.abs_dev.mean():.1f}bp "
             f"median |dev| {d.abs_dev.median():.1f}; in half-spread units mean z {d.z.mean():+.2f} median {d.z.median():+.2f} mean |z| {d.z.abs().mean():.2f}")
    L.append(f"print inside the 15:59:50 NBBO: {d.inside.mean():.0%}; at/above ask {(d.z>=0.999).mean():.0%}; at/below bid {(d.z<=-0.999).mean():.0%}")
    L.append(f"vs 15:50 mid: mean {d.dev50.mean():+.2f}bp, mean |dev| {d.dev50.abs().mean():.1f}bp")
    L.append(f"saving of buying at the cross vs lifting the 15:59:50 ask: mean {(d.hs59 - d.dev59).mean():.1f}bp  (cross sits {d.dev59.mean():+.1f}bp from mid)")
    for lab, col, qs in [("cross $ (X)", "X", 4), ("cross / day $vol", "sh_day", 4), ("cross / 20d $vol", "x_adv", 4)]:
        L.append(f"-- by {lab} quartile")
        b = pd.qcut(d[col], qs, duplicates="drop")
        for k, g in d.groupby(b, observed=True):
            L.append(f"   {str(k):28s} n {len(g):4d} X med ${g.X.median():>8,.0f} | dev mean {g.dev59.mean():+6.2f} |dev| {g.abs_dev.mean():5.1f} "
                     f"|z| {g.z.abs().mean():.2f} hs {g.hs59.median():5.1f}bp  frac|dev|>hs {(g.abs_dev>g.hs59).mean():.2f}")
    L.append("-- by year (signed dev bp, |dev|)")
    for y, g in d.groupby(d.d0.dt.year): L.append(f"   {y}: n {len(g)} dev {g.dev59.mean():+.2f} |dev| {g.abs_dev.mean():.1f} X med ${g.X.median():,.0f}")
    L.append("-- by class")
    for s, g in d.groupby("src"): L.append(f"   {s}: n {len(g)} dev {g.dev59.mean():+.2f} |dev| {g.abs_dev.mean():.1f} hs {g.hs59.median():.1f} X med ${g.X.median():,.0f} sh_day {g.sh_day.median():.3f}")
    # sqrt-law regression: |dev|/hs on sqrt(sh_day)
    x = np.sqrt(d.sh_day.values); y = d.abs_dev.values
    A = np.c_[np.ones_like(x), x]; coef = np.linalg.lstsq(A, y, rcond=None)[0]
    L.append(f"OLS |dev|bp = {coef[0]:.2f} + {coef[1]:.1f} * sqrt(cross/day$)   corr {np.corrcoef(x,y)[0,1]:+.2f}")
    # exceedance of signed dev beyond cross share
    (OUT.parent.parent.parent / "research/sim/branch_r_probe/cross_stats_out.txt").write_text("\n".join(L) + "\n")
    print("\n".join(L))

if __name__ == "__main__": main()
