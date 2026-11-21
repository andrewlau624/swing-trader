"""DEEP round 2d N 1251 SNAP-HGB and N 1252 SIG-RESID (round1_prose.md "## Amendment - DEEP round 2d"; N 1250 -> 1252).

    SIG_CACHE=<dir> PYTHONPATH=. python3 -m research.sim.exp_sig2

Reuses the N 1243 pipeline (research/sim/exp_sig.py, imported, not copied) and its cached full-store features
(build("full", ...) -> SIG_CACHE/full_2026-12-31.npz, written by the exp_sig report pass).
N 1251 = HGB (max_iter 200, random_state 0) on the 4 snapshot features; this is the exp_sig report-pass HGB/snap series exactly
(same code, same cache, deterministic), recomputed here so the per-week series is available; the mean is checked against the
exp_sig log line. N 1252 = the same HGB on snapshot + signature features (4 + 118 = 122).
Expanding yearly refit from 1998, OOS years 2011..2026. JUDGE 2011-01..2026-10 (halves 2011-18 / 2019-26).
Gates (each model): G1 long excess vs universe EW net >= +15bp/wk; G1b NW t >= 2.5; G2 halves > 0; G3 ex-top-5 weeks > 0;
G4 2x cost (10bp/side) > 0; G7 beta-matched excess > 0 = long net - [EW + (beta_port - 1) x SPY], beta_port = OLS slope of the
weekly long-book gross return on SPY's 5d return over the judge window (EW beta reported). N 1252 also: G8 beats N 1251 by
>= +5bp/wk. DSR at N 1252.
"""
from __future__ import annotations

import gc
import hashlib
import pathlib
import time

import numpy as np
import pandas as pd

from research.sim import exp_sig as E
from research.sim.exp_rl import dsr

OUT = E.ROOT / "research/sim/exp_sig2_out.txt"
N_TRIALS = 1252
J_END = pd.Timestamp("2026-10-31")
H1_END = pd.Timestamp("2018-12-31")
lines: list[str] = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    lines.append(s)


def slope(y, x):
    x = x - x.mean()
    return float((x * (y - y.mean())).sum() / (x * x).sum())


def evaluate(tag, D, pred, decs, spy):
    P = E.portfolio(D, pred, decs)
    dates = D.dates[decs]
    x = E.excess(P); x2 = E.excess(P, E.SHOCK)
    h1 = dates <= H1_END
    bp = slope(P["L"], spy); be = slope(P["EW"], spy)
    xb = P["L"] - E.COST * P["TL"] - (P["EW"] + (bp - 1) * spy)
    l = E.ls(P)
    t = E.tstat(x, E.NW)
    ds = dsr(x, N_TRIALS)
    say(f"  {tag}: long excess net {x.mean()*1e4:+.1f}bp/wk t {t:+.2f} | halves 2011-18 {x[h1].mean()*1e4:+.1f} / 2019-26 "
        f"{x[~h1].mean()*1e4:+.1f} | ex-top5 {E.ex_top5(x)*1e4:+.1f} | 2x cost {x2.mean()*1e4:+.1f} | beta-matched "
        f"{xb.mean()*1e4:+.1f} (beta_port {bp:.2f}, EW beta {be:.2f}, t {E.tstat(xb, E.NW):+.2f}) | median {np.median(x)*1e4:+.1f} "
        f"hit {(x>0).mean()*100:.0f}% | gross long-EW {(P['L']-P['EW']).mean()*1e4:+.1f} | turnover {P['TL'].mean():.2f}/wk | "
        f"LS net {l.mean()*1e4:+.1f}bp/wk t {E.tstat(l, E.NW):+.2f} | DSR(N {N_TRIALS}) {ds:.3f} | weeks {len(x)} "
        f"({dates[0].date()}..{dates[-1].date()})")
    yr = pd.Series(x, index=dates.year).groupby(level=0).mean() * 1e4
    say("    by year (bp/wk): " + " ".join(f"{y}:{v:+.0f}" for y, v in yr.items()))
    say(f"    deciles (5d return minus EW, bp): {E.decile_table(D, pred, decs)}")
    gates = [("G1 excess>=+15bp/wk", x.mean() >= E.GATE_EXC), ("G1b t>=2.5", t >= E.GATE_T),
             ("G2 halves>0", x[h1].mean() > 0 and x[~h1].mean() > 0), ("G3 ex-top-5>0", E.ex_top5(x) > 0),
             ("G4 2x cost>0", x2.mean() > 0), ("G7 beta-matched>0", xb.mean() > 0)]
    return x, gates, dict(x=x, x2=x2, xb=xb, h1=h1, t=t, ds=ds)


def main():
    t0 = time.time()
    sha = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]
    say(f"DEEP round 2d N 1251 SNAP-HGB / N 1252 SIG-RESID (program N {N_TRIALS}; code sha256 {sha}; exp_sig sha256 "
        f"{hashlib.sha256(pathlib.Path(E.__file__).read_bytes()).hexdigest()[:16]}; threads 3)")
    d = E.build("full", "2026-12-31", "2026-12-31")
    spy_all = d["spy"]
    res = {}
    for name, X in (("N1251 SNAP-HGB (4 snapshot)", d["XS"]), ("N1252 SIG-RESID (4 snapshot + 118 signature)", None)):
        dd = dict(d)
        dd["X"] = X if X is not None else np.hstack([d["XS"], d["X"]])
        D = E.Data(dd, "sig")
        yrs = list(range(E.JUDGE_LAST_Y + 1, int(D.years.max()) + 1))
        pr, it, _ = E.run_hgb(D, yrs)
        say(f"\n## {name}: features {D.X.shape[1]}, rows {len(D.y):,}; n_iter by year: " + " ".join(f"{y}:{v}" for y, v in it.items())
            + f" ({time.time()-t0:.0f}s)")
        decs = np.where((D.dates >= pd.Timestamp("2011-01-01")) & (D.dates <= J_END))[0]
        res[name] = evaluate(name.split()[0], D, pr, decs, spy_all[decs])
        del D, dd, pr; gc.collect()
    (k1, k2) = list(res)
    x1, g1, _ = res[k1]; x2, g2, _ = res[k2]
    diff = x2 - x1
    g2 = g2 + [("G8 beats SNAP-HGB by>=5bp", diff.mean() >= 5e-4)]
    say(f"\n  N1252 - N1251: {diff.mean()*1e4:+.1f}bp/wk (t {E.tstat(diff, E.NW):+.2f})")
    say("\nGATES")
    for k, g in ((k1, g1), (k2, g2)):
        say(f"  {k.split()[0]}: " + "; ".join(f"{n} {'PASS' if v else 'FAIL'}" for n, v in g))
    for k, g in ((k1, g1), (k2, g2)):
        ok = all(v for _, v in g)
        say(f"{'PASS' if ok else 'KILL'}: {k}" + ("" if ok else " - failed: " + ", ".join(n for n, v in g if not v)))
    say(f"total {time.time()-t0:.0f}s")
    OUT.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
