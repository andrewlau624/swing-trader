"""Study SH — is the falling-knife short edge accessible (liquid, easy-to-borrow)?
Pre-registered (N 831 -> 832) before any short number was read. One look. No deployment."""
from __future__ import annotations

import json
import numpy as np
import pandas as pd

from research.sim import preboom as PB

LOG = []
PRIMARY = ["volcomp", "rngcomp", "voldry", "accumbias", "amihudrise", "ivolrise", "corrbreak", "gapfreq"]
COST = 0.0040       # 20bp/side round trip per leg
BORROW_ETB = 0.0025  # 0.5%/yr over 20 sessions
BORROW_HTB = 0.025   # 5%/yr


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


def main():
    D = PB.load()
    C, E, adv = D["C"], D["E"], D["adv"]
    idx = C.index
    F20 = (C.shift(-20) / C - 1)
    conds, _ = PB.build_conditions(D)
    score = sum(conds[n].astype("int8") for n in PRIMARY).where(E)
    meta = json.load(open(f"{PB.ROOT}/data/research/night/asset_meta.json"))
    etb = np.array([bool(meta.get(s, {}).get("easy_to_borrow")) for s in C.columns])
    etbM = pd.DataFrame(np.tile(etb, (len(idx), 1)), index=idx, columns=C.columns)
    liquid = adv >= 50e6
    groups = {"ALL": E, "ETB": E & etbM, "ETB+liquid": E & etbM & liquid, "liquid": E & liquid}
    # long-short: short the high-stress names (score>=3), long the clean names (score==0)
    top = score.ge(3); bot = score.eq(0)
    for span, tag in ((PB.DISC, "DISCOVERY"), (PB.OOS, "OOS")):
        wm = PB.win_mask(idx, span)
        valid = wm[:, None] & F20.notna()
        log("\n" + "=" * 92)
        log(f"{tag}  (short score>=3, long score==0; net=LS - 2*20bp - 0.5% borrow)")
        log(f"{'group':12s} {'nTop':>8s} {'shortNet':>9s} {'topF20':>8s} {'botF20':>8s} {'LSgross':>8s} {'LSnet':>8s} {'t(LS)':>7s}")
        for gname, g in groups.items():
            v = g & valid
            topv = top & v; botv = bot & v
            if int(topv.values.sum()) < 100 or int(botv.values.sum()) < 100:
                continue
            short_net = -F20.where(topv).mean().mean() - COST - (BORROW_ETB if "ETB" in gname else BORROW_HTB)
            ls_d = (F20.where(botv).mean(axis=1) - F20.where(topv).mean(axis=1)).dropna()
            t = ls_d.mean() / (ls_d.std(ddof=1) / np.sqrt(len(ls_d))) if len(ls_d) > 2 else np.nan
            borrow = BORROW_ETB if "ETB" in gname else BORROW_HTB
            log(f"{gname:12s} {int(topv.values.sum()):8,d} {short_net:9.2%} {F20.where(topv).mean().mean():8.2%} "
                f"{F20.where(botv).mean().mean():8.2%} {ls_d.mean():8.2%} {ls_d.mean()-2*COST-borrow:8.2%} {t:7.2f}")
        # individual conditions, short edge on ETB+liquid
        log("  individual short edge (ETB+liquid, 20d, net of cost+0.5% borrow):")
        for nm in list(conds.keys()):
            v = groups["ETB+liquid"] & valid
            sh = -(F20.where(conds[nm] & v)).values
            sh = sh[np.isfinite(sh)]
            if sh.size < 100:
                continue
            log(f"    {nm:12s} n={sh.size:7,d} shortNet={np.nanmean(sh)-COST-BORROW_ETB:+.2%} hit={(sh>0).mean():.1%}")
    open(f"{PB.ROOT}/data/research/program/short_pb_out.txt", "w").write("\n".join(LOG) + "\n")
    log(f"\nwrote {PB.ROOT}/data/research/program/short_pb_out.txt")


if __name__ == "__main__":
    main()
