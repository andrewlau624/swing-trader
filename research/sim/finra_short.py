"""Round 21: Study AY — FINRA daily short-sale volume ratio (SVR5) as a night-pick tilt, both signs.

    PYTHONPATH=. .venv/bin/python -m research.sim.finra_short_fetch      # data first
    PYTHONPATH=. .venv/bin/python -m research.sim.finra_short

Pre-registration: research/drafts/round1_prose.md, "Round 21" (commit 6a0f535, before any number).
Every night return is from the official crosses (Study AW).
"""
from __future__ import annotations

import dataclasses
import glob
import pathlib
import time

import numpy as np
import pandas as pd

from . import book as B
from . import data as D
from . import max_edge as M
from .auction_audit import with_rets
from .auction_share import tilt_from
from .program_books import dsr
from .validate import load_sim

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/finra_short_out.txt"
SRC = ROOT / "data/research/night/finra_short"
N_TRIALS = 686


def svr5(N):
    parts = []
    for f in sorted(glob.glob(str(SRC / "*.parquet"))):
        x = pd.read_parquet(f); x["d"] = pd.Timestamp(pathlib.Path(f).stem); parts.append(x)
    X = pd.concat(parts)
    SV = X.pivot_table(index="d", columns="Symbol", values="ShortVolume", aggfunc="sum")
    TV = X.pivot_table(index="d", columns="Symbol", values="TotalVolume", aggfunc="sum")
    cal = D.etf()["close"].index
    SV, TV = SV.reindex(cal), TV.reindex(cal)
    pos = {d: i for i, d in enumerate(cal)}
    out = {}
    for d, nd in N.items():
        i = pos[d]
        for sym in map(str, nd.syms):
            if sym not in TV.columns:
                out[(d, sym)] = np.nan; continue
            tv = TV[sym].iloc[i - 5:i]; sv = SV[sym].iloc[i - 5:i]
            ok = tv > 0
            out[(d, sym)] = float(sv[ok].sum() / tv[ok].sum()) if ok.sum() >= 3 else np.nan
    return out


def main():
    t0 = time.time()
    fh = open(OUT, "w")

    def log(*a):
        x = " ".join(str(i) for i in a)
        print(x, flush=True); fh.write(x + "\n"); fh.flush()

    log("== Round 21: Study AY (FINRA short-volume ratio); started", pd.Timestamp.now(), "==")
    s = load_sim(raw_price=True)
    N0 = B.night_days(raw_price=True, max_corr=0.7)
    Na = with_rets(N0, pd.read_pickle(ROOT / "data/research/program/auction_audit_picks.pkl"), "ret_auc")
    s.N = Na; s.I = B.ibs_days()
    V = svr5(N0)
    Fau = M.au_features(N0)
    rows = []
    for d, nd in Na.items():
        for j, sym in enumerate(map(str, nd.syms)):
            rows.append(dict(d=d, svr=V[(d, sym)], tow=Fau[(d, sym)][1], vol20=nd.vol20[j], depth=nd.day_ret[j],
                             lprice=np.log(nd.price[j]), ladv=np.log(nd.adv[j]), net=nd.ret[j] - 5e-4))
    A = pd.DataFrame(rows)
    sel = A[A.d <= "2023-12-31"]
    mu, sd = float(sel.svr.mean()), float(sel.svr.std())
    log(f"picks {len(A)}; SVR5 coverage {A.svr.notna().mean():.1%}; 2021-23 mean {mu:.3f} sd {sd:.3f}")
    q = sel.svr.quantile([1 / 3, 2 / 3]).values
    for lab, a, z in (("2021-23", "2021-01-01", "2023-12-31"), ("2024-26", "2024-01-01", "2026-12-31")):
        x = A[(A.d >= a) & (A.d <= z) & A.svr.notna()]
        b = np.digitize(x.svr, q)
        log(f"  {lab}: " + " ".join(f"T{k+1} {x.net[b == k].mean()*1e4:+6.1f}bp n{(b == k).sum()}" for k in range(3)))
    log("  Spearman svr: " + "  ".join(f"{k} {v:+.2f}" for k, v in
                                       A.drop(columns=["d", "net"]).corr(method="spearman")["svr"].drop("svr").items()))
    hi = dict(V)
    lo = {k: (2 * mu - v) if np.isfinite(v) else np.nan for k, v in V.items()}     # mirror: low SVR up-weighted
    vals = {"AY1": hi, "AY2": lo}
    verdict = {"AY1": [], "AY2": []}
    for cost in M.COSTS:
        for bk, bp in M.BOOKS.items():
            p0 = B.Params(**{**bp, "night_cost": cost})
            log(f"\n  [{bk}, night {cost}/side]  full CAGR/Sh/DD")
            for E in M.SIZES:
                base = M.replay(s, E, p0); sb = B.stats(base)
                log(f"   ${E/1e3:5.1f}k shipped    {sb[0]*100:5.1f}/{sb[1]:4.2f}/{sb[2]*100:4.0f}")
                for k in ("AY1", "AY2"):
                    r = M.replay(s, E, dataclasses.replace(p0, tilt=tilt_from(Na, vals[k], mu, sd)))
                    pdd = M.p_dd50(r) if (E == 10000.0 and cost == 2.5) else None
                    ok, _ = M.judge(log, k, r, base, judged=(cost == 2.5), pdd=pdd)
                    if cost == 2.5:
                        verdict[k].append(ok)
    p0 = B.Params(**{**M.BOOKS["V7"], "night_cost": 2.5})
    base = M.replay(s, 10000.0, p0)
    for k in ("AY1", "AY2"):
        r = M.replay(s, 10000.0, dataclasses.replace(p0, tilt=tilt_from(Na, vals[k], mu, sd)))
        act = (r - base).mean(); rng = np.random.default_rng(17)
        sims = [(M.replay(s, 10000.0, dataclasses.replace(p0, tilt=tilt_from(Na, vals[k], mu, sd, rng=rng))) - base).mean()
                for _ in range(200)]
        pct = float((np.array(sims) < act).mean() * 100)
        log(f"  {k} feature shuffle (200): actual {act*25200:+.2f}pp/yr, pct {pct:.0f}%; "
            f"increment DSR at N {N_TRIALS} {dsr(r - base, n_trials=N_TRIALS)['dsr']:.3f}")
        verdict[k].append(pct >= 95)
    log("\n######## verdicts")
    for k, v in verdict.items():
        log(f"   {k}: {sum(v)}/{len(v)} checks pass -> {'SHADOW' if all(v) else 'DEAD'}")
    log(f"\ndone {time.time()-t0:.0f}s")
    fh.close()


if __name__ == "__main__":
    main()
