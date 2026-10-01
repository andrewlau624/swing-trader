"""Round 26: Study BD — the closing-auction imbalance (Databento, first closing message 15:50-15:52 ET) as a
night-pick tilt (BD1) or a buy-imbalance filter (BD2).

    PYTHONPATH=. .venv/bin/python -m research.sim.imbalance_fetch      # data first
    PYTHONPATH=. .venv/bin/python -m research.sim.imbalance_study

Pre-registration: research/drafts/round1_prose.md, "Round 26" (commit d0d8e9a, before any data).
Night returns from the official crosses (Study AW). Judged exactly as Round 20.
"""
from __future__ import annotations

import dataclasses
import glob
import pathlib
import time

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import book as B
from . import max_edge as M
from .auction_audit import with_rets
from .auction_share import tilt_from
from .program_books import dsr
from .validate import load_sim

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/imbalance_study_out.txt"
SRC = ROOT / "data/research/night/imbalance"
N_TRIALS = 701


def load_imbalance() -> pd.DataFrame:
    parts = [pd.read_parquet(f) for f in sorted(glob.glob(str(SRC / "*.parquet")))]
    X = pd.concat([p for p in parts if len(p)], ignore_index=True)
    X["date"] = pd.to_datetime(X["date"])
    return X


def drop_tilt(N, flags: dict):
    """BD2: weight 0 on flagged picks (their slice idles), the live v1 tilt otherwise."""
    date_of = {id(nd): d for d, nd in N.items()}

    def f(nd):
        d = date_of[id(nd)]
        live = sg.night_tilt(nd.vol20, nd.day_ret, 0.25)
        return np.array([0.0 if flags.get((d, str(s)), False) else w for s, w in zip(nd.syms, live)])
    return f


def main():
    t0 = time.time()
    fh = open(OUT, "w")

    def log(*a):
        x = " ".join(str(i) for i in a)
        print(x, flush=True); fh.write(x + "\n"); fh.flush()

    log("== Round 26: Study BD (closing imbalance); started", pd.Timestamp.now(), "==")
    s = load_sim(raw_price=True)
    N0 = B.night_days(raw_price=True, max_corr=0.7)
    Na = with_rets(N0, pd.read_pickle(ROOT / "data/research/program/auction_audit_picks.pkl"), "ret_auc")
    s.N = Na; s.I = B.ibs_days()
    X = load_imbalance()
    key = {(r.date, r.sym): r for r in X.itertuples()}
    Fau = M.au_features(N0)
    rows = []
    for d, nd in Na.items():
        for j, sym in enumerate(map(str, nd.syms)):
            r = key.get((d, sym))
            adv_sh = nd.adv[j] / max(nd.price[j], 1e-9)
            if r is not None and r.side in ("A", "B") and adv_sh > 0:
                sir = (r.imb if r.side == "A" else -r.imb) / adv_sh          # + = SELL imbalance
                rel = (r.imb if r.side == "A" else -r.imb) / max(r.imb + r.paired, 1.0)
                side = r.side
            elif r is not None:
                sir, rel, side = 0.0, 0.0, "N"
            else:
                sir, rel, side = np.nan, np.nan, None
            rows.append(dict(d=d, sym=sym, sir=sir, rel=rel, side=side, tow=Fau[(d, sym)][1],
                             vol20=nd.vol20[j], depth=nd.day_ret[j], net=nd.ret[j] - 5e-4,
                             dataset=getattr(r, "dataset", None)))
    A = pd.DataFrame(rows)
    log(f"picks {len(A)}; with a closing message {A.side.notna().mean():.1%}; sides "
        f"{A.side.value_counts(dropna=False).to_dict()}; by feed {A.dataset.value_counts(dropna=False).to_dict()}")
    sel = A[(A.d <= "2023-12-31") & A.sir.notna()]
    mu, sd = float(sel.sir.mean()), float(sel.sir.std())
    log(f"SIR (sell imbalance / ADV shares) 2021-23: mean {mu:.4f} sd {sd:.4f}; median {sel.sir.median():.4f}")
    q = sel.sir.quantile([1 / 3, 2 / 3]).values
    for lab, a, z in (("2021-23", "2021-01-01", "2023-12-31"), ("2024-26", "2024-01-01", "2026-12-31")):
        x = A[(A.d >= a) & (A.d <= z) & A.sir.notna()]
        b = np.digitize(x.sir, q)
        log(f"  SIR terciles {lab}: " + " ".join(f"T{k+1} {x.net[b == k].mean()*1e4:+6.1f}bp n{(b == k).sum()}" for k in range(3))
            + f" | by side: " + " ".join(f"{sd_}: {g.net.mean()*1e4:+.1f}bp n{len(g)}" for sd_, g in x.groupby("side")))
    log("  Spearman sir: " + "  ".join(f"{k} {v:+.2f}" for k, v in
                                       A[["sir", "rel", "tow", "vol20", "depth"]].corr(method="spearman")["sir"].drop("sir").items()))
    vals = {(r.d, r.sym): r.sir for r in A.itertuples() if pd.notna(r.sir)}
    flags = {(r.d, r.sym): r.side == "B" for r in A.itertuples()}
    verdict = {"BD1": [], "BD2": []}
    for cost in M.COSTS:
        for bk, bp in M.BOOKS.items():
            p0 = B.Params(**{**bp, "night_cost": cost})
            log(f"\n  [{bk}, night {cost}/side]  full CAGR/Sh/DD")
            for E in M.SIZES:
                base = M.replay(s, E, p0); sb = B.stats(base)
                log(f"   ${E/1e3:5.1f}k shipped    {sb[0]*100:5.1f}/{sb[1]:4.2f}/{sb[2]*100:4.0f}")
                for k, tilt in (("BD1", tilt_from(Na, vals, mu, sd)), ("BD2", drop_tilt(Na, flags))):
                    r = M.replay(s, E, dataclasses.replace(p0, tilt=tilt))
                    pdd = M.p_dd50(r) if (E == 10000.0 and cost == 2.5) else None
                    ok, _ = M.judge(log, k, r, base, judged=(cost == 2.5), pdd=pdd)
                    if cost == 2.5:
                        verdict[k].append(ok)
    p0 = B.Params(**{**M.BOOKS["V7"], "night_cost": 2.5})
    base = M.replay(s, 10000.0, p0)
    rng = np.random.default_rng(26)
    for k in ("BD1", "BD2"):
        tilt = tilt_from(Na, vals, mu, sd) if k == "BD1" else drop_tilt(Na, flags)
        r = M.replay(s, 10000.0, dataclasses.replace(p0, tilt=tilt))
        act = (r - base).mean()
        sims = []
        for _ in range(200):
            if k == "BD1":
                sims.append((M.replay(s, 10000.0, dataclasses.replace(p0, tilt=tilt_from(Na, vals, mu, sd, rng=rng))) - base).mean())
            else:
                by = {}
                for (d, sym), f in flags.items():
                    by.setdefault(d, []).append((sym, f))
                sh = {}
                for d, v in by.items():
                    perm = rng.permutation([f for _, f in v])
                    sh.update({(d, sym): bool(p) for (sym, _), p in zip(v, perm)})
                sims.append((M.replay(s, 10000.0, dataclasses.replace(p0, tilt=drop_tilt(Na, sh))) - base).mean())
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
