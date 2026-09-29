"""Adversarial verification of index_mechanics P2 (post-hoc night x0.5 on QQQ prev close -> 15:30 <= -2%).

    PYTHONPATH=. .venv/bin/python -m research.sim.index_mechanics_verify

Verifier checks (all counted as variants):
  V1 threshold sensitivity -1.5 / -2.5 / -3.0%          V2 scale 0.0 / 0.75
  V3 x0.5 on QQQ >= +2% at 15:30 (same vol state, opposite sign)
  V4 x0.5 on |QQQ| >= 2%       V5 x0.5 on lagged QQQ d-1 close->close <= -2% (26a-style)
  V6 exposure-matched placebo: x0.5 on random days drawn from the high-vol pool (QQQ 20d vol
     top quintile, trailing), same count as the flag, 50 seeds
  V7 concentration: per-year contribution and top-5 day share of the daily diff
  V8 2020 holdout per-name: median, drop the 3 worst flag nights
"""
from __future__ import annotations

import pickle

import numpy as np
import pandas as pd

from . import book as B
from . import data as D
from . import index_mechanics as X
from . import index_mechanics_data as IM

H = (("2021-02-01", "2023-12-31"), ("2024-01-01", "2026-12-31"))


def sh(r):
    return np.array([B.stats(r[a:z])[1] for a, z in H])


def main():
    s = X.load_book_sim()
    f = X.flow_frame("QQQ")
    q = f.d1530
    ec = D.etf()["close"]["QQQ"]
    cc = (ec / ec.shift(1) - 1)
    lag = cc.shift(1).reindex(q.index)
    vol = cc.rolling(20).std().shift(1)
    thr = vol.rolling(252, min_periods=120).quantile(0.8)
    hv = (vol > thr).reindex(q.index).fillna(False)
    nd_days = [d for d in s.N if d in set(s.days) and d >= pd.Timestamp("2021-02-01")]
    flags = {
        "P2 (repro) <=-2% x0.5": (set(q.index[q <= -0.02]), 0.5),
        "V1 <=-1.5% x0.5": (set(q.index[q <= -0.015]), 0.5),
        "V1 <=-2.5% x0.5": (set(q.index[q <= -0.025]), 0.5),
        "V1 <=-3.0% x0.5": (set(q.index[q <= -0.03]), 0.5),
        "V2 <=-2% x0.0": (set(q.index[q <= -0.02]), 0.0),
        "V2 <=-2% x0.75": (set(q.index[q <= -0.02]), 0.75),
        "V3 >=+2% x0.5": (set(q.index[q >= 0.02]), 0.5),
        "V4 |q|>=2% x0.5": (set(q.index[q.abs() >= 0.02]), 0.5),
        "V5 lagged d-1 <=-2% x0.5": (set(lag.index[lag <= -0.02]), 0.5),
    }
    for c in ("tier", "tier_hi"):
        base = s.replay(X.v7_params(c))
        b = sh(base["r"])
        print(f"\n@{c}  base Sharpe {b[0]:.2f}/{b[1]:.2f}")
        for nm, (fl, k) in flags.items():
            r = X.p2_sim(s, fl, k).replay(X.v7_params(c))["r"]
            d = r - base["r"]
            n = sum(x in fl for x in nd_days)
            ds = sh(r) - b
            print(f"  {nm:28s} n {n:3d}  dSharpe {ds[0]:+.3f}/{ds[1]:+.3f}  {d.mean()*252*100:+.2f}pp/yr  "
                  f"NW t {X.nw_t(d):+.2f}")
            if nm.startswith("P2") and c == "tier":
                p2d = d
    # V7 concentration
    print("\nV7 P2 daily diff @tier by year (pp):",
          "  ".join(f"{y} {g.sum()*100:+.2f}" for y, g in p2d.groupby(p2d.index.year)))
    top = p2d.abs().nlargest(5)
    print(f"  total {p2d.sum()*100:+.2f}pp; top-5 |days| {p2d[top.index].sum()*100:+.2f}pp "
          f"({', '.join(str(x.date()) for x in top.index)}); without them {p2d.drop(top.index).sum()*100:+.2f}pp")
    # V6 exposure-matched placebo, high-vol pool
    base = s.replay(X.v7_params("tier"))
    b = sh(base["r"])
    flag = flags["P2 (repro) <=-2% x0.5"][0]
    real = sh(X.p2_sim(s, flag).replay(X.v7_params("tier"))["r"]) - b
    rng = np.random.default_rng(77)
    for lab, a, z in (("21-23", *H[0]), ("24-26", *H[1])):
        pass
    pool = [d for d in nd_days if hv.get(d, False)]
    nflag_h = [sum((x in flag) for x in nd_days if a <= str(x.date()) <= z) for a, z in H]
    pool_h = [[d for d in pool if a <= str(d.date()) <= z] for a, z in H]
    print(f"\nV6 high-vol pool sizes {len(pool_h[0])}/{len(pool_h[1])}, flag counts per half {nflag_h}; "
          f"flag days inside pool {sum(d in flag for d in pool)} of {sum(nflag_h)}")
    beats = np.zeros(2); pl = []
    for _ in range(50):
        fl = set()
        for ph, nf in zip(pool_h, nflag_h):
            fl |= set(rng.choice(ph, min(nf, len(ph)), replace=False))
        ds = sh(X.p2_sim(s, fl).replay(X.v7_params("tier"))["r"]) - b
        pl.append(ds); beats += real > ds
    pl = np.array(pl)
    print(f"  P2 dSharpe {real[0]:+.3f}/{real[1]:+.3f}; high-vol placebo mean {pl[:,0].mean():+.3f}/{pl[:,1].mean():+.3f} "
          f"sd {pl[:,0].std():.3f}/{pl[:,1].std():.3f}; beats {beats[0]/50:.0%}/{beats[1]/50:.0%}")
    # V8 2020 holdout per name
    d20 = pickle.load(open(IM.D20CACHE, "rb"))
    xs = {True: {}, False: {}}
    for d, (ret, vol20, day_ret, n_raw, gap) in d20.items():
        if not (pd.Timestamp("2020-01-01") <= d <= pd.Timestamp("2020-10-31")):
            continue
        keep = np.nan_to_num(vol20) >= 0.6
        if keep.any():
            xs[d in flag][d] = float(np.nanmean(ret[keep])) - 2e-3
    t = pd.Series(xs[True]); o = pd.Series(xs[False])
    print(f"\nV8 2020: flag mean {t.mean()*1e4:+.1f} median {t.median()*1e4:+.1f} (n {len(t)}), drop 3 worst "
          f"{t.drop(t.nsmallest(3).index).mean()*1e4:+.1f}; other mean {o.mean()*1e4:+.1f} median {o.median()*1e4:+.1f}")
    print("  flag nights by month:", t.groupby(t.index.to_period('M')).agg(['count', 'mean']).round(4).to_dict('index'))


if __name__ == "__main__":
    main()
