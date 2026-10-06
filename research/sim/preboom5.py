"""Study PB-O — does a pre-boom condition predict the OVERNIGHT (close t -> open t+1)?
Pre-registered (N 828 -> 829) before any number was read. One look. No deployment."""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.sim import preboom as PB

LOG = []


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


def main():
    D = PB.load()
    C, O, E = D["C"], D["O"], D["E"]
    idx = C.index
    ON = O.shift(-1) / C - 1          # close t -> open t+1
    ID = C.shift(-1) / O.shift(-1) - 1  # open t+1 -> close t+1
    conds, _ = PB.build_conditions(D)
    conds.update(PB.build_structural(D))
    names = list(conds.keys())
    for span, tag in ((PB.DISC, "DISCOVERY"), (PB.OOS, "OOS")):
        wm = PB.win_mask(idx, span)
        v = E & wm[:, None] & ON.notna() & ID.notna()
        onb = ON.values[v.values]; idb = ID.values[v.values]
        log("\n" + "=" * 96)
        log(f"{tag}  universe overnight mean={np.nanmean(onb):+.3%}  intraday mean={np.nanmean(idb):+.3%}")
        log(f"{'condition':12s} {'n':>8s} {'ONmean':>8s} {'ON>=+5%':>8s} {'ON<=-5%':>8s} {'ON up-dn':>9s} "
            f"{'IDmean':>8s} {'ID up-dn':>9s}")
        for nm in names:
            c = conds[nm].values & v.values
            if c.sum() < 200:
                continue
            on = ON.values[c]; idr = ID.values[c]
            onu = np.mean(on >= 0.05); ond = np.mean(on <= -0.05)
            idu = np.mean(idr >= 0.05); idd = np.mean(idr <= -0.05)
            log(f"{nm:12s} {c.sum():8,d} {np.nanmean(on)-0.0005:8.3%} {onu:8.2%} {ond:8.2%} "
                f"{onu-ond:9.3f} {np.nanmean(idr)-0.0005:8.3%} {idu-idd:9.3f}")
    open(f"{PB.ROOT}/data/research/program/preboom5_out.txt", "w").write("\n".join(LOG) + "\n")
    log(f"\nwrote {PB.ROOT}/data/research/program/preboom5_out.txt")


if __name__ == "__main__":
    main()
