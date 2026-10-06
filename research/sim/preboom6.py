"""Study PB-N — do the pre-boom conditions improve the night (crash-bounce) leg?
Pre-registered (N 829 -> 830) before any number was read. One look. No deployment."""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.sim import preboom as PB

LOG = []
PRIMARY = ["volcomp", "rngcomp", "voldry", "accumbias", "amihudrise", "ivolrise", "corrbreak", "gapfreq"]


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


def cluster_t(x):
    """Day-clustered t of the mean (x has date + ret)."""
    g = x.groupby("date").ret.mean()
    return g.mean() / (g.std(ddof=1) / np.sqrt(len(g))) if len(g) > 2 else np.nan


def main():
    from research.sim import data as DD
    x = DD.night_candidates().copy()
    x["date"] = pd.to_datetime(x.date)
    D = PB.load()
    C, E = D["C"], D["E"]
    conds, _ = PB.build_conditions(D)
    conds.update(PB.build_structural(D))
    # align each pick to the signal-day close conditions
    inb = x.sym.isin(C.columns) & x.date.isin(C.index)
    x = x[inb].copy()
    di = C.index.get_indexer(x.date)
    ci = C.columns.get_indexer(x.sym)
    for nm, M in conds.items():
        x[nm] = M.values[di, ci]
    x["score"] = x[PRIMARY].fillna(0).astype(int).sum(axis=1)
    log(f"night picks aligned: {len(x):,}  (dropped {int((~inb).sum())})  mean ret {x.ret.mean()*1e4:.1f}bp")
    for span, tag in ((PB.DISC, "DISCOVERY"), (PB.OOS, "OOS")):
        w = x[(x.date >= span[0]) & (x.date <= span[1])]
        base = w.ret.mean() * 1e4
        log("\n" + "=" * 88)
        log(f"{tag}  n={len(w):,}  base night ret={base:.1f}bp  hit={(w.ret>0).mean():.1%}")
        log(f"{'condition':12s} {'n_cond':>7s} {'meanCond':>9s} {'meanNot':>8s} {'delta':>7s} {'hitC':>6s} "
            f"{'P>=5%':>7s} {'P<=-5%':>7s} {'t(diff)':>8s}")
        for nm in list(conds.keys()):
            c = w[w[nm].fillna(False).astype(bool)]
            n = w[~w[nm].fillna(False).astype(bool)]
            if len(c) < 100:
                continue
            # day-clustered t on the per-pick difference is not defined; use cond-vs-not daily means
            d = c.groupby("date").ret.mean() - n.groupby("date").ret.mean()
            d = d.dropna()
            t = d.mean() / (d.std(ddof=1) / np.sqrt(len(d))) if len(d) > 2 else np.nan
            log(f"{nm:12s} {len(c):7,d} {c.ret.mean()*1e4:9.1f} {n.ret.mean()*1e4:8.1f} "
                f"{(c.ret.mean()-n.ret.mean())*1e4:7.1f} {(c.ret>0).mean():6.1%} {(c.ret>=.05).mean():7.2%} "
                f"{(c.ret<=-.05).mean():7.2%} {t:8.2f}")
        log("  by condition count:")
        for k in range(0, 9):
            s = w[w.score == k]
            if len(s) < 100:
                continue
            log(f"    score={k}: n={len(s):6,d} mean={s.ret.mean()*1e4:6.1f}bp hit={(s.ret>0).mean():.1%} "
                f"P>=5%={(s.ret>=.05).mean():.2%}")
    open(f"{PB.ROOT}/data/research/program/preboom6_out.txt", "w").write("\n".join(LOG) + "\n")
    log(f"\nwrote {PB.ROOT}/data/research/program/preboom6_out.txt")


if __name__ == "__main__":
    main()
