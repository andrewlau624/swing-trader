"""Round 20: Study AX (closing / opening auction-share tilts on the night leg) and AU3 robustness
reports R1 (TOW from the official crosses) and R2 (AU3 under the 15% name cap; AU3 on tilt v2).

    PYTHONPATH=. .venv/bin/python -m research.sim.auction_hist_fetch      # data first
    PYTHONPATH=. .venv/bin/python -m research.sim.auction_share

Pre-registration: research/drafts/round1_prose.md, "Round 20" (commit df4f8c6, before any number).
Every night return is from the official crosses (Study AW). Params.night_cost is PER SIDE.
"""
from __future__ import annotations

import dataclasses
import glob
import json
import pathlib
import time

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import book as B
from . import data as D
from . import max_edge as M
from .auction_audit import with_rets
from .program_books import dsr
from .validate import load_sim

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/auction_share_out.txt"
HIST = ROOT / "data/research/night/auction_hist"
N_TRIALS = 684


def load_hist():
    """sym -> DataFrame(date -> o_p, o_s, c_p, c_s) of the largest-size cross prints."""
    out = {}
    for f in sorted(glob.glob(str(HIST / "b*.json"))):
        for sym, v in json.load(open(f)).items():
            rows = []
            for x in v:
                o = max(x["o"], key=lambda q: q.get("s", 0)) if x.get("o") else None
                c = max(x["c"], key=lambda q: q.get("s", 0)) if x.get("c") else None
                rows.append((pd.Timestamp(x["d"]), o["p"] if o else np.nan, o["s"] if o else np.nan,
                             c["p"] if c else np.nan, c["s"] if c else np.nan))
            out[sym] = pd.DataFrame(rows, columns=["d", "o_p", "o_s", "c_p", "c_s"]).set_index("d").sort_index()
    return out


def features(N, Hh):
    """(d, sym) -> dict(csh, osh, tow_x) from the 20 completed sessions before d."""
    P = D.panel(); V = P["volume"]
    x = D.night_candidates(raw=True)
    rawf = {(a, b): f for a, b, f in zip(x.date, x.sym, x.raw_f)}
    cal = D.etf()["close"].index
    pos = {d: i for i, d in enumerate(cal)}
    out = {}
    for d, nd in N.items():
        i = pos[d]; win = cal[max(0, i - 21):i]           # 21 sessions: 20 gaps need the one before
        for sym in map(str, nd.syms):
            h = Hh.get(sym)
            res = dict(csh=np.nan, osh=np.nan, tow_x=np.nan)
            if h is not None:
                w = h.reindex(win)
                f = rawf.get((d, sym), 1.0)
                f = f if np.isfinite(f) and f > 0 else 1.0
                vol = (V[sym].reindex(win) / f) if sym in V.columns else pd.Series(np.nan, index=win)
                cs = (w.c_s / vol).where(vol > 0).iloc[1:]
                os_ = (w.o_s / vol).where(vol > 0).iloc[1:]
                cs = cs.where(cs <= 1); os_ = os_.where(os_ <= 1)
                if cs.notna().sum() >= 15:
                    res["csh"] = float(cs.mean())
                if os_.notna().sum() >= 15:
                    res["osh"] = float(os_.mean())
                res["tow_x"] = sg.tug_of_war(w.o_p.values, w.c_p.values)
            out[(d, sym)] = res
    return out


def tilt_from(N, vals: dict, mu, sd, base="v1", prev=None, rng=None):
    date_of = {id(nd): d for d, nd in N.items()}

    def f(nd):
        d = date_of[id(nd)]
        if base == "v2":
            pv = np.array([prev.get((d, str(s)), np.nan) for s in nd.syms])
            lv = sg.night_tilt_v2(nd.vol20, nd.day_ret, pv, 0.25)
        else:
            lv = sg.night_tilt(nd.vol20, nd.day_ret, 0.25)
        if vals is None:
            return lv
        v = np.array([vals.get((d, str(s)), np.nan) for s in nd.syms], float)
        if rng is not None:
            v = rng.permutation(v)
        z = np.where(np.isfinite(v), (v - mu) / sd, 0.0)
        w = lv * np.clip(1 + 0.25 * z, 0.25, 2.0)
        return w * lv.mean() / w.mean()
    return f


def main():
    t0 = time.time()
    fh = open(OUT, "w")

    def log(*a):
        x = " ".join(str(i) for i in a)
        print(x, flush=True); fh.write(x + "\n"); fh.flush()

    log("== Round 20: Study AX + AU3 reports R1/R2; started", pd.Timestamp.now(), "==")
    s = load_sim(raw_price=True)
    N0 = B.night_days(raw_price=True, max_corr=0.7)
    T = pd.read_pickle(ROOT / "data/research/program/auction_audit_picks.pkl")
    Na = with_rets(N0, T, "ret_auc")
    s.N = Na; s.I = B.ibs_days()
    Hh = load_hist()
    F = features(N0, Hh)
    Fau = M.au_features(N0)
    A = pd.DataFrame([dict(d=d, sym=sy, **v, tow=Fau[(d, sy)][1]) for (d, sy), v in F.items()])
    A["vol20"] = [nd.vol20[j] for d, nd in N0.items() for j in range(len(nd.syms))]
    A["depth"] = [nd.day_ret[j] for d, nd in N0.items() for j in range(len(nd.syms))]
    A["lprice"] = [np.log(nd.price[j]) for d, nd in N0.items() for j in range(len(nd.syms))]
    A["ladv"] = [np.log(nd.adv[j]) for d, nd in N0.items() for j in range(len(nd.syms))]
    A["net"] = [Na[d].ret[j] - 5e-4 for d, nd in N0.items() for j in range(len(nd.syms))]
    sel = A[A.d <= "2023-12-31"]
    log(f"picks {len(A)}; coverage csh {A.csh.notna().mean():.1%} osh {A.osh.notna().mean():.1%} "
        f"tow_x {A.tow_x.notna().mean():.1%}")
    consts = {}
    for c in ("csh", "osh", "tow_x"):
        consts[c] = (float(sel[c].mean()), float(sel[c].std()))
        q = sel[c].quantile([1 / 3, 2 / 3]).values
        line = []
        for lab, a, z in (("2021-23", "2021-01-01", "2023-12-31"), ("2024-26", "2024-01-01", "2026-12-31")):
            x = A[(A.d >= a) & (A.d <= z) & A[c].notna()]
            b = np.digitize(x[c], q)
            line.append(f"{lab}: " + " ".join(f"T{k+1} {x.net[b == k].mean()*1e4:+6.1f}bp n{(b == k).sum()}" for k in range(3)))
        log(f"  {c}: 2021-23 mean {consts[c][0]:.4f} sd {consts[c][1]:.4f} | " + " | ".join(line))
    cs = A[["csh", "osh", "tow", "tow_x", "vol20", "depth", "lprice", "ladv"]].corr(method="spearman")
    for c in ("csh", "osh", "tow_x"):
        log(f"  Spearman {c}: " + "  ".join(f"{k} {v:+.2f}" for k, v in cs[c].drop(c).items()))

    vals = {c: {(r.d, r.sym): getattr(r, c) for r in A.itertuples()} for c in ("csh", "osh", "tow_x")}
    verdict = {"AX1": [], "AX2": []}
    log("\n######## Study AX (auction returns)")
    for cost in M.COSTS:
        for bk, bp in M.BOOKS.items():
            p0 = B.Params(**{**bp, "night_cost": cost})
            log(f"\n  [{bk}, night {cost}/side]  full CAGR/Sh/DD")
            for E in M.SIZES:
                base = M.replay(s, E, p0); sb = B.stats(base)
                log(f"   ${E/1e3:5.1f}k shipped    {sb[0]*100:5.1f}/{sb[1]:4.2f}/{sb[2]*100:4.0f}")
                for k, c in (("AX1", "csh"), ("AX2", "osh")):
                    r = M.replay(s, E, dataclasses.replace(p0, tilt=tilt_from(Na, vals[c], *consts[c])))
                    pdd = M.p_dd50(r) if (E == 10000.0 and cost == 2.5) else None
                    ok, _ = M.judge(log, k, r, base, judged=(cost == 2.5), pdd=pdd)
                    if cost == 2.5:
                        verdict[k].append(ok)
    p0 = B.Params(**{**M.BOOKS["V7"], "night_cost": 2.5})
    base = M.replay(s, 10000.0, p0)
    for k, c in (("AX1", "csh"), ("AX2", "osh")):
        r = M.replay(s, 10000.0, dataclasses.replace(p0, tilt=tilt_from(Na, vals[c], *consts[c])))
        act = (r - base).mean()
        rng = np.random.default_rng(13)
        sims = [(M.replay(s, 10000.0, dataclasses.replace(p0, tilt=tilt_from(Na, vals[c], *consts[c], rng=rng))) - base).mean()
                for _ in range(200)]
        pct = float((np.array(sims) < act).mean() * 100)
        q = dsr(r - base, n_trials=N_TRIALS)
        log(f"  {k} feature shuffle (200): actual {act*25200:+.2f}pp/yr, pct {pct:.0f}%; increment DSR at N {N_TRIALS} {q['dsr']:.3f}")
        verdict[k].append(pct >= 95)

    # ---------------- reports
    log("\n######## R1 — AU3 with TOW from the official crosses (V7 / Roth, 2.5bp, auction returns)")
    for bk in ("V7", "Roth"):
        p = B.Params(**{**M.BOOKS[bk], "night_cost": 2.5})
        for E in M.SIZES:
            b0 = M.replay(s, E, p)
            r = M.replay(s, E, dataclasses.replace(p, tilt=tilt_from(Na, vals["tow_x"], *consts["tow_x"])))
            M.judge(log, f"{bk} ${E/1e3:.1f}k", r, b0, judged=False)

    log("\n######## R2 — AU3 under the 15% name cap (moderate) and on top of tilt v2 (V7 $10k, 2.5bp, auction returns)")
    tow_v = {k: v[1] for k, v in Fau.items()}
    mu_t, sd_t = M.TOW_CONST if hasattr(M, "TOW_CONST") else (5.14, 2.10)
    s15 = load_sim(raw_price=True)
    N15 = with_rets(B.night_days(raw_price=True, max_corr=0.7, max_name_pct=0.15), T, "ret_auc")
    s15.N = N15; s15.I = s.I
    b15 = M.replay(s15, 10000.0, p0)
    r15 = M.replay(s15, 10000.0, dataclasses.replace(p0, tilt=tilt_from(N15, tow_v, mu_t, sd_t)))
    M.judge(log, "cap .15", r15, b15, judged=False)
    C = D.panel()["close"]; prev = {}
    for d, nd in Na.items():
        i = C.index.get_loc(d)
        for sym in map(str, nd.syms):
            prev[(d, sym)] = float(C[sym].iloc[i - 1] / C[sym].iloc[i - 2] - 1) if sym in C.columns and i >= 2 else np.nan
    bv2 = M.replay(s, 10000.0, dataclasses.replace(p0, tilt=tilt_from(Na, None, 0, 1, base="v2", prev=prev)))
    rv2 = M.replay(s, 10000.0, dataclasses.replace(p0, tilt=tilt_from(Na, tow_v, mu_t, sd_t, base="v2", prev=prev)))
    M.judge(log, "on v2", rv2, bv2, judged=False)

    log("\n######## verdicts (6 judged cells + feature-shuffle placebo)")
    for k, v in verdict.items():
        log(f"   {k}: {sum(v)}/{len(v)} checks pass -> {'SHADOW' if all(v) else 'DEAD'}")
    log(f"\ndone {time.time()-t0:.0f}s")
    fh.close()


if __name__ == "__main__":
    main()
