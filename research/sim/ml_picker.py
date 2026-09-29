"""Study E: a gradient-boosted picker on the organic 15:50 features, purged walk-forward.

    PYTHONPATH=. .venv/bin/python -m research.sim.ml_picker

Pre-register: research/drafts/round1_prose.md, "Amendment - Study E" (stamped
Tue Sep 29 02:14:15 PDT 2026, before any Study E number).

Sample: addendum-23's honest night-candidate panel (data/research/night/features.pkl), the
same (date, sym) rows the RAW pool uses. Features at 15:50; label = the pool's close->next-open
return net of the shipped night-leg costs (book.cost_bps tier on the RAW price, per side).

Models (3): E1 HistGradientBoosting on 15 honest features (the add. 23 nine + ibs50, day50,
vol20, ret20, late-window width, log adv); E2 the same class on ONLY the add. 23 nine;
E3 Ridge on E1's set. Forward: fit 2021-02..2023-12-31, judge 2024-02-01..end (30-day purge).
Reverse: fit 2024-26 -> judge 2021-23 (no embargo possible; reported only).

Book row: V7 (raw, corr 0.7) and the as-built .15 books with the night leg's tilt driven by
the model's predictions via the shipped weight form (clip(1 + k * pred_z, 0.25, 2) / mean,
k=0.25); the placebo shuffles the weight VALUES within the day (200 draws) and the actual
book increment's mean must beat the placebo's 95th percentile in both judged halves.
"""
from __future__ import annotations

import pathlib
import pickle
import time

import numpy as np
import pandas as pd

from . import book as B
from . import growth as G
from .validate import load_sim
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/ml_picker_out.txt"
CACHE = ROOT / "data/research/program/ml_picker_preds.pkl"
PER = (("2021-23", "2021-01-01", "2023-12-31"), ("2024-26", "2024-01-01", "2026-12-31"))
FIT_A, FIT_B = "2021-02-01", "2023-12-31"
JUDGE_A = "2024-02-01"
K = 0.25

NINE = ["late", "rvol", "gap", "spy50", "idio", "dist20", "dist252", "prev", "lprice"]
EXTRA = ["ibs50", "day50", "vol20", "ret20", "width", "ladv"]
FEATS = {"E1": NINE + EXTRA, "E2": NINE}
MODELS = {
    "E1": lambda: HistGradientBoostingRegressor(max_depth=3, learning_rate=0.05, max_iter=300,
                                                min_samples_leaf=200),
    "E2": lambda: HistGradientBoostingRegressor(max_depth=3, learning_rate=0.05, max_iter=300,
                                                min_samples_leaf=200),
    "E3": lambda: Ridge(alpha=10.0),
}


def X_build(F, which):
    X = F[NINE + (["ibs50", "day50", "vol20", "ret20"] if which != "E2" else [])].copy()
    if which != "E2":
        X["width"] = (F["H50"] - F["L50"]) / F["p50"].clip(lower=1e-3)
        X["ladv"] = np.log10(np.clip(F["adv"].values, 1e3, None))
    return X.replace([np.inf, -np.inf], np.nan)


def nw_t(x, lags=5):
    v = x.dropna().values
    n = len(v)
    if n < 30:
        return float("nan")
    e = v - v.mean()
    var = (e * e).sum() / n
    for k in range(1, lags + 1):
        var += 2 * (1 - k / (lags + 1)) * (e[k:] * e[:-k]).sum() / n
    return v.mean() / np.sqrt(max(var, 1e-18) / n)


def preds():
    if pathlib.Path(CACHE).exists():
        return pickle.load(open(CACHE, "rb"))
    from . import data as D
    xlink = D.night_candidates(raw=True)
    F = pickle.load(open(ROOT / "data/research/night/features.pkl", "rb"))
    F["y"] = xlink.ret.values - 2 * B.cost_bps("tier", xlink.raw_p50.values, xlink.adv.values) / 1e4
    F.index = xlink.index                     # keep the (date, sym) join valid
    F = F[np.isfinite(F.y) & (F.ret.abs() <= 1)].copy()
    P = {}
    tr = F[(F.date >= FIT_A) & (F.date <= FIT_B)]
    te = F[F.date >= JUDGE_A]
    for which in ("E1", "E2", "E3"):
        Xtr, Xte = X_build(tr, which), X_build(te, which)
        m = MODELS[which]()
        key = pd.MultiIndex.from_arrays([te.date.values, te.sym.values])
        if which == "E3":
            mean, sd = Xtr.mean(), Xtr.std().replace(0, 1)
            Xtr = Xtr.fillna(mean); Xte = Xte.fillna(mean)
            m.fit((Xtr - mean) / sd, tr.y)
            P[("fwd", which)] = pd.Series(m.predict((Xte - mean) / sd), index=key)
        else:
            m.fit(Xtr, tr.y)
            P[("fwd", which)] = pd.Series(m.predict(Xte), index=key)
    te2 = F[(F.date >= FIT_A) & (F.date <= FIT_B)]
    tr2 = F[F.date >= "2024-01-01"]
    for which in ("E1", "E2", "E3"):
        Xtr, Xte = X_build(tr2, which), X_build(te2, which)
        m = MODELS[which]()
        key = pd.MultiIndex.from_arrays([te2.date.values, te2.sym.values])
        if which == "E3":
            mean, sd = Xtr.mean(), Xtr.std().replace(0, 1)
            Xtr = Xtr.fillna(mean); Xte = Xte.fillna(mean)
            m.fit((Xtr - mean) / sd, tr2.y)
            P[("rev", which)] = pd.Series(m.predict((Xte - mean) / sd), index=key)
        else:
            m.fit(Xtr, tr2.y)
            P[("rev", which)] = pd.Series(m.predict(Xte), index=key)
    pickle.dump(P, open(CACHE, "wb"))
    return P


def main():
    t0 = time.time()
    fs = open(OUT, "w")

    def log(*a):
        s_ = " ".join(str(x) for x in a)
        print(s_, flush=True)
        fs.write(s_ + "\n")
        fs.flush()

    log("== Study E: ML picker, started", pd.Timestamp.now(), "\n")
    XF = pickle.load(open(ROOT / "data/research/night/features.pkl", "rb"))
    meta = None
    from . import data as D
    xlink = D.night_candidates(raw=True)
    F0 = xlink[["date", "sym", "ret", "vol20", "adv"]].copy()
    F0["y"] = F0.ret - 2 * B.cost_bps("tier", xlink.raw_p50.values, xlink.adv.values) / 1e4
    F0 = F0[np.isfinite(F0.y) & (F0.ret.abs() <= 1)].copy()
    P = preds()
    log(f"sample: {len(F0)} candidate rows; preds cached in {time.time()-t0:4.1f} s\n")

    # fit/judge diagnostics per variant
    for tag in ("fwd", "rev"):
        for which in ("E1", "E2", "E3"):
            if (tag, which) not in P:
                continue
            p = P[(tag, which)]
            y = F0.set_index(["date", "sym"]).loc[p.index, "y"]
            a, b = (FIT_A, FIT_B) if tag == "fwd" else ("2024-01-01", "2026-12-31")
            heals = []
            for lab, a2, b2 in PER:
                sel = p[(p.index.get_level_values(0) >= a2) & (p.index.get_level_values(0) <= b2)]
                yy = y.loc[sel.index]
                heals.append(f"{lab} decile-spread")
            # per-trade percentile play: top-quintile minus bottom-quintile P&L, per judged half
            rows = []
            for lab, a2, b2 in PER:
                q = (p.index.get_level_values(0) >= a2) & (p.index.get_level_values(0) <= b2)
                sel = p.loc[q]
                if len(sel) < 200:
                    rows.append(f"{lab}: n {len(sel)} (too few)")
                    continue
                ysel = y.loc[sel.index]
                q5 = sel.rank(pct=True)
                top = ysel[q5 >= 0.95].mean() * 1e4
                bot = ysel[q5 <= 0.05].mean() * 1e4
                corr = sel.corr(ysel)
                rows.append(f"{lab}: top-btm {top - bot:+7.1f}bp  top {top:+6.1f}  bot {bot:+6.1f}  "
                            f"corr {corr:+.3f}")
            log(f"{tag} {which}: " + "   ".join(rows))
    log("")

    # ---- book rows: the same sim's books with the night leg's tilt driven by the model's
    # per-day per-pick predictions through the shipped weight form; placebo = the same
    # weights shuffled within the day, 200 draws, 95th percentile on both judged halves.
    s = load_sim(raw_price=True)
    rng = np.random.default_rng(13)
    for cap in (0.10, 0.15):
        s.N = B.night_days(raw_price=True, max_corr=0.7, max_name_pct=cap)
        for cost in ("tier", "tier_hi"):
            kw = {**G.V7, **G.cfg(1.0, 0.5, 2), "night_cost": cost}
            basev1 = s.replay(B.Params(**{**kw, "tilt": "live"}))

            def make_wm(pred_map):
                WM = {}
                for d, nd in s.N.items():
                    vals = np.array([pred_map.get((d, sy), np.nan) for sy in nd.syms], float)
                    fin = np.isfinite(vals)
                    if fin.sum() >= 2:
                        sdv = vals[fin].std()
                        if sdv > 1e-12:
                            z = np.where(fin, (vals - np.nanmean(vals)) / sdv, 0.0)
                        else:
                            z = np.zeros(len(vals))
                        z = np.where(np.isfinite(z), z, 0.0)
                        w = np.clip(1.0 + K * z, 0.25, 2.0)
                        WM[d] = w / w.mean()
                    else:
                        WM[d] = np.ones(len(nd.syms))
                return WM

            def wkey(nd):
                return (str(np.asarray(nd.syms, dtype=object)[0]), len(nd.syms))

            for tag in ("fwd", "rev"):
                for which in ("E1", "E2", "E3"):
                    if (tag, which) not in P:
                        continue
                    pm_all = P[(tag, which)]
                    WM = make_wm(dict(pm_all))
                    Wk = {}
                    for d, nd in s.N.items():
                        Wk[wkey(nd)] = WM[d]

                    def tilt_fn(nd, _g=Wk):
                        return _g.get(wkey(nd)) if _g.get(wkey(nd)) is not None else np.ones(len(nd.syms))
                    alt = s.replay(B.Params(**{**kw, "tilt": tilt_fn}))
                    inc = alt["r"] - basev1["r"]
                    draws = []
                    for _ in range(200):
                        WM2 = {}
                        for d, nd in s.N.items():
                            h = WM.get(d)
                            WM2[d] = rng.permutation(h) if (h is not None and len(h) > 1) else h
                        Wk2 = {}
                        for d, nd in s.N.items():
                            Wk2[wkey(nd)] = WM2.get(d)
                        def pf(nd, _g=Wk2):
                            h = _g.get(wkey(nd))
                            return h if h is not None else np.ones(len(nd.syms))
                        AP = s.replay(B.Params(**{**kw, "tilt": pf}))
                        draws.append(B.stats(AP["r"] - basev1["r"])[0])
                    draws = np.array(draws)
                    p1 = B.stats(inc[PER[0][1]:PER[0][2]])
                    p2 = B.stats(inc[PER[1][1]:PER[1][2]])
                    pct1 = 100 * (draws < p1[0]).mean()
                    pct2 = 100 * (draws < p2[0]).mean()
                    log(f"cap {cap:.2f} {str(cost):7s} {tag} {which}: d21-23 {p1[0]*100:+6.2f}pp "
                        f"d24-26 {p2[0]*100:+6.2f}pp full {B.stats(inc)[0]*100:+.2f}pp "
                        f"Sharpe {B.stats(inc)[1]:+.2f} NW t {nw_t(inc):+.2f} | "
                        f"placebo p95 {np.percentile(draws, 95)*100:+6.2f}pp "
                        f"| pct 21-23 {pct1:.0f}  pct 24-26 {pct2:.0f}")
    fs.close()


if __name__ == "__main__":
    main()
