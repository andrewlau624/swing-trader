"""Study PB-C — the confirmation arm: once a pre-boom condition fires, follow the
direction the move starts. Pre-registered (N 826 -> 827) before any number was read.
Control: the same early move WITHOUT the condition. One look. No deployment."""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.sim import preboom as PB

LOG = []
rng = np.random.default_rng(11)
FOCUS = ["volcomp", "voldry", "amihudrise", "dtchigh", "ftdspike", "earnprox", "gapfreq"]
COST = 0.0020  # 10bp/side round trip


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


def stats(F, up, valid, nboot=300):
    """F: forward return from entry; up: entry-direction mask; valid: eligible+finite."""
    sel = valid & up
    f = F.values[sel.values]
    if len(f) < 200:
        return None
    d = F.index  # dates
    # day-clustered CI on the mean
    rows = np.flatnonzero(sel.values)
    di = (rows // F.shape[1])
    means = pd.Series(f).groupby(di).mean()
    boot = [means.sample(len(means), replace=True, random_state=int(rng.integers(1e9))).mean() for _ in range(nboot)]
    return dict(n=len(f), pboom=float((f >= 0.30).mean()), pbust=float((f <= -0.30).mean()),
                mean=float(f.mean()), med=float(np.median(f)), net=float(f.mean() - COST),
                lo=float(np.percentile(boot, 2.5)), hi=float(np.percentile(boot, 97.5)))


def main():
    D = PB.load()
    C, E = D["C"], D["E"]
    idx = C.index
    F20 = C.shift(-25) / C.shift(-5) - 1          # from entry at t+5
    F10 = C.shift(-11) / C.shift(-1) - 1          # from entry at t+1
    conds, _ = PB.build_conditions(D)
    conds.update(PB.build_structural(D))
    confs = {"e5>=+10%": (C.shift(-5) / C - 1, F20), "e3>=+8%": (C.shift(-3) / C - 1, C.shift(-23) / C.shift(-3) - 1),
             "e1>=+5%": (C.shift(-1) / C - 1, F10)}
    for span, tag in ((PB.DISC, "DISCOVERY"), (PB.OOS, "OOS")):
        wm = PB.win_mask(idx, span)
        log("\n" + "=" * 96)
        log(f"{tag}  entry after the move; fwd20 measured FROM entry; net=mean-{COST:.1%}")
        log("=" * 96)
        for cname, (e, F) in confs.items():
            base_valid = E & wm[:, None] & e.notna() & F.notna()
            log(f"\n--- confirmation {cname}")
            log(f"{'scope':11s} {'grp':4s} {'n':>8s} {'P(boom)':>8s} {'P(bust)':>8s} {'boom/bust':>9s} "
                f"{'mean':>7s} {'med':>7s} {'net':>7s} {'mean95CI':>17s}")
            scopes = [("ALL(no cond)", None)] + [(c, c) for c in FOCUS]
            for label, c in scopes:
                cm = base_valid if c is None else (conds[c] & base_valid)
                for gname, g in (("up", e >= 0.10), ("down", e <= -0.10)):
                    s = stats(F, g, cm)
                    if not s:
                        continue
                    r = s["pboom"] / s["pbust"] if s["pbust"] else np.nan
                    log(f"{label:11s} {gname:4s} {s['n']:8,d} {s['pboom']:8.2%} {s['pbust']:8.2%} {r:9.2f} "
                        f"{s['mean']:7.2%} {s['med']:7.2%} {s['net']:7.2%} [{s['lo']:6.2%},{s['hi']:6.2%}]")
    open(f"{PB.ROOT}/data/research/program/preboom3_out.txt", "w").write("\n".join(LOG) + "\n")
    log(f"\nwrote {PB.ROOT}/data/research/program/preboom3_out.txt")


if __name__ == "__main__":
    main()
