"""Study PB addendum — the pre-registered A/B discriminators: direction asymmetry
(with day-clustered bootstrap), momentum orthogonality, per-year stability, concentration.
Reads nothing not already in the pre-registration. No deployment."""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.sim import preboom as PB

rng = np.random.default_rng(7)
LOG = []


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


def dstats(cond, target, valid):
    c = (cond & valid).values
    t = (target & valid).values
    v = valid.values
    return np.stack([c.sum(1), (t & c).sum(1), v.sum(1), (t & v).sum(1)], 1).astype("float64")


def boot_lift_diff(su, sd, nboot=400):
    n = len(su)
    du, dd = [], []
    for _ in range(nboot):
        i = rng.integers(0, n, n)
        a, b = su[i], sd[i]
        # up: col0 nc, col1 nbc, col2 nv, col3 nb
        pu = a[:, 1].sum() / max(a[:, 0].sum(), 1)
        bu = a[:, 3].sum() / max(a[:, 2].sum(), 1)
        pd = b[:, 1].sum() / max(b[:, 0].sum(), 1)
        bd = b[:, 3].sum() / max(b[:, 2].sum(), 1)
        du.append(pu / bu); dd.append(pd / bd)
    du, dd = np.array(du), np.array(dd)
    return float(np.mean(du - dd)), float(np.percentile(du - dd, 2.5)), float(np.percentile(du - dd, 97.5))


def main():
    D = PB.load()
    C, E, L = D["C"], D["E"], D["L"]
    idx = C.index
    F20 = (C.shift(-20) / C - 1)
    F60 = (C.shift(-60) / C - 1)
    boom20 = F20.ge(PB.BOOM20)
    boom60 = F60.ge(PB.BOOM60)
    down20 = F20.le(PB.DOWN20)
    conds, vol20 = PB.build_conditions(D)
    conds.update(PB.build_structural(D))
    names = list(conds.keys())
    mom = conds["ret20top"]

    for span, tag in ((PB.DISC, "DISCOVERY"), (PB.OOS, "OOS")):
        wm = PB.win_mask(idx, span)
        valid20 = E & wm[:, None] & F20.notna()
        valid60 = E & wm[:, None] & F60.notna()
        log("\n" + "=" * 108)
        log(f"{tag} {span[0]}..{span[1]}   base20={float(boom20.values[valid20.values].mean()):.3%} "
            f"base60={float(boom60.values[valid60.values].mean()):.3%}")
        log("=" * 108)
        log(f"{'condition':12s} {'upL20':>6s} {'dnL20':>6s} {'up-dn':>7s} {'95% CI':>16s} "
            f"{'upL60':>6s} {'orthoUp':>8s} {'orthoBase':>9s} {'orthoLift':>9s}")
        for nm in names:
            su20 = dstats(conds[nm], boom20, valid20)
            sd20 = dstats(conds[nm], down20, valid20)
            su60 = dstats(conds[nm], boom60, valid60)
            up20 = su20[:, 1].sum() / max(su20[:, 0].sum(), 1) / (su20[:, 3].sum() / max(su20[:, 2].sum(), 1))
            dn20 = sd20[:, 1].sum() / max(sd20[:, 0].sum(), 1) / (sd20[:, 3].sum() / max(sd20[:, 2].sum(), 1))
            up60 = su60[:, 1].sum() / max(su60[:, 0].sum(), 1) / (su60[:, 3].sum() / max(su60[:, 2].sum(), 1))
            m, lo, hi = boot_lift_diff(su20, sd20)
            # orthogonality: within the NON-momentum universe
            sub = valid20 & ~mom
            o = dstats(conds[nm], boom20, sub)
            oc = o[:, 1].sum() / max(o[:, 0].sum(), 1)
            ob = o[:, 3].sum() / max(o[:, 2].sum(), 1)
            log(f"{nm:12s} {up20:6.2f} {dn20:6.2f} {m:7.2f} [{lo:6.2f},{hi:6.2f}] "
                f"{up60:6.2f} {oc:8.2%} {ob:9.2%} {oc / ob:9.2f}")

    # per-year right-tail lift (OOS+discovery pooled, by calendar year)
    wm = PB.win_mask(idx, ("2021-01-01", "2026-06-30"))
    valid = E & wm[:, None] & F20.notna()
    log("\nper-year up-lift boom20:")
    log(f"{'condition':12s} " + " ".join(f"{y:>6d}" for y in range(2021, 2027)))
    for nm in names:
        row = []
        for y in range(2021, 2027):
            ym = (idx >= f"{y}-01-01") & (idx <= f"{y}-12-31")
            v = valid & ym[:, None]
            c = conds[nm] & v
            b = boom20 & v
            if c.values.sum() < 100:
                row.append(float("nan")); continue
            pc = b.values[c.values].mean(); bs = b.values[v.values].mean()
            row.append(pc / bs if bs else np.nan)
        log(f"{nm:12s} " + " ".join(f"{x:6.2f}" for x in row))

    # concentration of cond & boom20 (OOS): unique names, months, top-5 share
    wm = PB.win_mask(idx, PB.OOS)
    v = E & wm[:, None] & F20.notna()
    log("\nconcentration (OOS, cond & boom20):")
    log(f"{'condition':12s} {'nboom':>7s} {'#sym':>6s} {'#mon':>6s} {'top5%':>7s}")
    for nm in names:
        c = conds[nm] & v & boom20
        st = np.argwhere(c.values)
        if len(st) == 0:
            continue
        syms = C.columns[st[:, 1]]
        months = C.index[st[:, 0]].to_period("M")
        vc = pd.Series(syms).value_counts()
        log(f"{nm:12s} {len(st):7d} {vc.size:6d} {pd.Series(months).nunique():6d} {vc.head(5).sum()/len(st):7.2%}")

    open(f"{PB.ROOT}/data/research/program/preboom2_out.txt", "w").write("\n".join(LOG) + "\n")
    log(f"\nwrote {PB.ROOT}/data/research/program/preboom2_out.txt")


if __name__ == "__main__":
    main()
