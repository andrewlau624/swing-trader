"""Verifier sensitivity for regime_robust (POST-HOC, not pre-registered; reported as such).

V1 joint walk-forward WITHOUT night IBS (its grid is one-sided: the pool was built at < 0.10, so a
   refit can only deploy less); V2 joint WF without night IBS and tilt k. 3bp and tier_hi, 2022-26.
V3 de-risk latch recovery time: events for S to walk from h back to 0 at the intact mean.

    PYTHONPATH=. .venv/bin/python -m research.sim.regime_robust_verify
"""
import pickle

from . import book as B
from . import regime_robust as RR
from .validate import load_sim


def main():
    s = load_sim()
    gp = RR.gaps(s)
    L = RR.build_legs(s)
    out = pickle.load(open(RR.SCR / "cache_regime_robust_out.pkl", "rb"))
    SEL, CAL = out["SEL"], out["CAL"]
    dates = s.days[s.days >= "2022-01-01"]
    joint = {k: {y: v for y, v in SEL[k].items() if y >= 2022} for k in RR.GRID}
    for y in joint["ibs_max"]:
        if joint["ibs_max"][y] != 0.2 and joint["ibs_topk"][y] != 3:
            joint["ibs_topk"][y] = 3
    for cost in (3.0, "tier_hi"):
        for lab, drop in (("fixed", list(RR.GRID)), ("joint all", []), ("joint ex night_ibs", ["night_ibs"]),
                          ("joint ex night_ibs,tilt_k", ["night_ibs", "tilt_k"])):
            sel = {k: v for k, v in joint.items() if k not in drop}
            r = RR.book_with(s, L, sel, cost, dates)["r"]
            print(f"  {lab:28s} {str(cost):>7s} {RR.fmt3(r)}", flush=True)
    for k, c in CAL.items():
        drift = (c["mu0"] - c["mu0"] / 2) / c["sd0"]
        print(f"  latch recovery {k:10s} h={c['h']:>3}  drift/event {drift:.3f}  events {c['h']/drift:6.0f}"
              f"  years {c['h']/drift/c['per_year']:.1f}")


if __name__ == "__main__":
    main()
