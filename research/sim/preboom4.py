"""Study PB-M — magnitude/skew of the conditional boom. Pre-registered (N 827 -> 828)
before any magnitude number was read. Is there a long-only 'golden egg' (fat right tail)
hidden under the symmetric probability lifts? One look. No deployment."""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.sim import preboom as PB

LOG = []
PRIMARY = ["volcomp", "rngcomp", "voldry", "accumbias", "amihudrise", "ivolrise", "corrbreak", "gapfreq"]
COST = 0.0020


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


def main():
    D = PB.load()
    C, E = D["C"], D["E"]
    idx = C.index
    F20 = (C.shift(-20) / C - 1)
    F60 = (C.shift(-60) / C - 1)
    conds, _ = PB.build_conditions(D)
    conds.update(PB.build_structural(D))
    names = [n for n in conds if n not in ("ret20top", "nearhigh")]
    # additive score over the 8 panel conditions
    score = sum(conds[n].astype("int8") for n in PRIMARY)
    score = score.where(E)

    for span, tag in ((PB.DISC, "DISCOVERY"), (PB.OOS, "OOS")):
        wm = PB.win_mask(idx, span)
        v20 = (E & wm[:, None] & F20.notna()).values
        v60 = (E & wm[:, None] & F60.notna()).values
        b20 = F20.values[v20]; b60 = F60.values[v60]
        log("\n" + "=" * 110)
        log(f"{tag}  universe: mean20={np.nanmean(b20):+.2%} mean60={np.nanmean(b60):+.2%} "
            f"P60>=+100%={np.mean(b60>=1.0):.3%} skew60={pd.Series(b60).skew():.2f}")
        log(f"  base P(up | |move|>=30%) = {(b20[np.abs(b20)>=0.30]>=0.30).mean():.3f}")
        log(f"{'cond':12s} {'n20':>8s} {'mean20net':>10s} {'mean60net':>10s} {'P60>=100':>9s} "
            f"{'Rmag(>=50)':>10s} {'Lmag(<=-50)':>11s} {'skew60':>7s} {'Pup|big':>8s}")
        for nm in names:
            cm20 = conds[nm].values & v20
            cm60 = conds[nm].values & v60
            if cm20.sum() < 200:
                continue
            x20 = F20.values[cm20]; x60 = F60.values[cm60]
            big = x20[np.abs(x20) >= 0.30]
            rmag = x60[x60 >= 0.50]; lmag = x60[x60 <= -0.50]
            log(f"{nm:12s} {cm20.sum():8,d} {np.nanmean(x20)-COST:10.2%} {np.nanmean(x60)-COST:10.2%} "
                f"{np.mean(x60>=1.0):9.3%} {np.nanmean(rmag) if rmag.size else np.nan:10.1%} "
                f"{np.nanmean(lmag) if lmag.size else np.nan:11.1%} {pd.Series(x60).skew():7.2f} "
                f"{(big>=0.30).mean():8.3f}")
        # additive score: top decile vs universe
        top = score.rank(axis=1, pct=True).ge(0.90)
        cm20 = top.values & v20; cm60 = top.values & v60
        x20 = F20.values[cm20]; x60 = F60.values[cm60]
        big = x20[np.abs(x20) >= 0.30]
        rmag = x60[x60 >= 0.50]; lmag = x60[x60 <= -0.50]
        log(f"{'SCORE top10%':12s} {cm20.sum():8,d} {np.nanmean(x20)-COST:10.2%} {np.nanmean(x60)-COST:10.2%} "
            f"{np.mean(x60>=1.0):9.3%} {np.nanmean(rmag) if rmag.size else np.nan:10.1%} "
            f"{np.nanmean(lmag) if lmag.size else np.nan:11.1%} {pd.Series(x60).skew():7.2f} {(big>=0.30).mean():8.3f}")
        # score bucket monotonicity on mean20
        log("  score bucket mean20 net:", " ".join(
            f"{k}:{np.nanmean(F20.values[(score.values==k)&v20])-COST:+.2%}" for k in range(0, int(np.nanmax(score.values))+1)))
    open(f"{PB.ROOT}/data/research/program/preboom4_out.txt", "w").write("\n".join(LOG) + "\n")
    log(f"\nwrote {PB.ROOT}/data/research/program/preboom4_out.txt")


if __name__ == "__main__":
    main()
