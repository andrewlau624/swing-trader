"""Study EX — the falling-knife screen as a long-only night-leg filter.
Pre-registered (N 832 -> 833) before any filter number was read. One look. No deployment."""
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


def main():
    from research.sim import data as DD
    x = DD.night_candidates().copy()
    x["date"] = pd.to_datetime(x.date)
    D = PB.load()
    C = D["C"]
    conds, _ = PB.build_conditions(D)
    conds.update(PB.build_structural(D))
    x = x[x.sym.isin(C.columns) & x.date.isin(C.index)].copy()
    di = C.index.get_indexer(x.date); ci = C.columns.get_indexer(x.sym)
    for nm, M in conds.items():
        x[nm] = M.values[di, ci]
    x["score"] = x[PRIMARY].fillna(0).astype(int).sum(axis=1)
    arms = {
        "EX1 excl score>=2": x.score < 2,
        "EX2 excl score>=3": x.score < 3,
        "EX4 excl voldry": ~x.voldry.fillna(False).astype(bool),
    }
    for span, tag in ((PB.DISC, "DISCOVERY"), (PB.OOS, "OOS")):
        w = x[(x.date >= span[0]) & (x.date <= span[1])].copy()
        base = w.ret.mean() * 1e4
        log("\n" + "=" * 92)
        log(f"{tag}  n={len(w):,}  base={base:.1f}bp  hit={(w.ret>0).mean():.1%}")
        log(f"{'arm':20s} {'nKeep':>7s} {'keepFrac':>8s} {'keepMean':>9s} {'remMean':>8s} {'improve':>8s} {'t':>6s} {'placebo':>8s}")
        rng = np.random.default_rng(3)
        for name, keepmask in arms.items():
            k = w[keepmask]; r = w[~keepmask]
            if len(k) < 100 or len(r) < 20:
                continue
            frac = len(k) / len(w)
            improve = (k.ret.mean() - w.ret.mean()) * frac * 1e4
            kd = k.groupby("date").ret.mean(); ad = w.groupby("date").ret.mean()
            d = (kd - ad).dropna()
            t = d.mean() / (d.std(ddof=1) / np.sqrt(len(d))) if len(d) > 2 else np.nan
            # placebo: remove the same count at random
            pl = []
            n_rem = len(r)
            for _ in range(200):
                idx = rng.permutation(len(w))[:n_rem]
                kept = w.iloc[np.setdiff1d(np.arange(len(w)), idx)]
                pl.append((kept.ret.mean() - w.ret.mean()) * (len(kept) / len(w)) * 1e4)
            pct = (np.array(pl) < improve).mean()
            log(f"{name:20s} {len(k):7,d} {frac:8.1%} {k.ret.mean()*1e4:9.1f} {r.ret.mean()*1e4:8.1f} "
                f"{improve:8.1f} {t:6.2f} {pct:8.0%}")
        # EX3 tilt clean: up-weight score==0
        wt = np.where(w.score == 0, 2.0, 1.0)
        tilt = np.average(w.ret, weights=wt) * 1e4
        log(f"{'EX3 tilt score==0 2x':20s} {'':7s} {'':8s} {tilt:9.1f} {'':8s} {tilt-base:8.1f}")
    open(f"{PB.ROOT}/data/research/program/preboom8_out.txt", "w").write("\n".join(LOG) + "\n")
    log(f"\nwrote {PB.ROOT}/data/research/program/preboom8_out.txt")


if __name__ == "__main__":
    main()
