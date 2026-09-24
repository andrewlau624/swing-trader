"""Addendum 16 experiments, all on the live-code simulator.

    .venv/bin/python -m research.sim.experiments

Rules fixed before running: both halves (2021-23 / 2024-26) must improve, a
filter or tilt must beat its matched placebo, and the live-scale replay
($3k + $1k / 21 sessions, whole shares) is the number that decides. 21
variants are run here; with that many, a single-half win means nothing.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import book as B
from .validate import load_sim

HDR = f"{'':44s} {'2021-23':>16s} {'2024-26':>16s} {'full':>16s}"


def run(s, label, **kw):
    p = B.Params(**kw)
    print(B.summary(s.replay(p), label))
    return p


# ---------------------------------------------------------------- tilt
def trades_frame(s) -> pd.DataFrame:
    rows = []
    for d, n in s.N.items():
        for i in range(len(n.syms)):
            rows.append((d, n.ret[i], n.vol20[i], n.ret20[i], n.day_ret[i]))
    return pd.DataFrame(rows, columns=["date", "ret", "vol20", "ret20", "day"])


FEATS = ["lv", "ret20", "day"]


def _feats(vol20, ret20, day):
    f = np.column_stack([np.log(np.maximum(np.asarray(vol20, float), 1e-3)),
                         np.asarray(ret20, float), np.asarray(day, float)])
    return np.nan_to_num(f, nan=0.0, posinf=0.0, neginf=0.0)


def fit_tilt(t: pd.DataFrame, mask, k: float = 0.5):
    """OLS of winsorised next-open return on (log vol20, ret20, day return),
    fitted on `mask` only. Returns f(NightDay) -> weights with mean 1."""
    x = _feats(t.vol20.values, t.ret20.values, t.day.values)[mask]
    y = np.clip(np.nan_to_num(t.ret.values[mask]), -0.2, 0.2)
    mu, sd = x.mean(0), x.std(0)
    X = np.column_stack([np.ones(len(x)), (x - mu) / sd])
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    pred_sd = float((X[:, 1:] @ beta[1:]).std())

    def tilt(nd):
        z = (_feats(nd.vol20, nd.ret20, nd.day_ret) - mu) / sd
        w = np.clip(1 + k * (z @ beta[1:]) / pred_sd, 0.25, 2.0)
        return w / w.mean()
    return tilt, beta


def placebo(tilt, seed=0):
    """Same weights, shuffled within the day: same dispersion, no information."""
    rng = np.random.default_rng(seed)
    return lambda nd: rng.permutation(tilt(nd))


def main(only=None):
    s = load_sim()
    if only == "tilt":
        return tilt_section(s)
    print(HDR)
    print("\n--- baseline (live config, whole shares, $3k + $1k/21 sessions)")
    run(s, "live rules, flat 7.5bp night")
    run(s, "live rules, tiered night cost", night_cost="tier")
    run(s, "live rules, pessimistic tiers", night_cost="tier_hi")

    print("\n--- #3 fill unused night capital with the index overnight (close -> open, 1bp/side)")
    for f in ("SPY", "QQQ"):
        run(s, f"filler {f}", filler=f)
        run(s, f"filler {f}, tiered night cost", filler=f, night_cost="tier")

    print("\n--- #8 what the idle IBS half holds")
    for how in ("cash", "bil", "spy", "qqq", "spy_night", "qqq_night"):
        run(s, f"IBS idle -> {how}", ibs_idle=how)

    print("\n--- #6 overnight gross (margin interest 12%/yr on the debit)")
    for w in (0.5, 0.65, 0.75):
        for cost in (7.5, "tier"):
            run(s, f"night {w} + IBS {w} (gross {2*w:.1f}x), night cost {cost}",
                night_w=w, ibs_w=w, night_cost=cost)

    print("\n--- #5 intraday leg: QQQ alone vs QQQ + SMH, same 1.5x budget")
    run(s, "noise QQQ 1.0")
    run(s, "noise QQQ 0.5 + SMH 0.5", noise={"QQQ": 0.5, "SMH": 0.5})
    run(s, "noise SMH 1.0", noise={"SMH": 1.0})

    tilt_section(s)


def tilt_section(s):
    print(HDR)
    print("\n--- #4 night sizing tilt, fitted on one half, judged on the other")
    t = trades_frame(s)
    h1 = (t.date < "2024-01-01").values
    for lab, mask in (("fit 2021-23", h1), ("fit 2024-26", ~h1)):
        tilt, beta = fit_tilt(t, mask)
        print(f"  {lab}: beta (log vol20, ret20, day) = {np.round(beta[1:] * 1e4, 1)} bp/sd")
        run(s, f"  tilt ({lab})", tilt=tilt)
        run(s, f"  placebo (shuffled {lab} weights)", tilt=placebo(tilt))
        run(s, f"  tilt ({lab}), tiered cost", tilt=tilt, night_cost="tier")

    print("\n--- cost-aware skip: drop night names whose round-trip tier cost exceeds X")
    for x in (20, 30):
        run(s, f"skip if 2 x tier cost > {x}bp (tiered cost)", night_cost="tier", min_edge_bps=x)


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else None)
