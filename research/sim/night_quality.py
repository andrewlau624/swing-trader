"""Study AN (Round 17): night-leg pick quality where small size helps.

    PYTHONPATH=. .venv/bin/python -m research.sim.night_quality

Pre-registration: research/drafts/round1_prose.md, "Round 17", Study AN (committed before any
number below). Builds a POINT-IN-TIME classifier from the EDGAR cache (Study T fetch) and
pre-registers filters/tilts on it. Method mirrors Study U/W: per-pick w = min(frac, 0.10),
book increment = 0.5 x (variant w) x net minus the shipped contribution; NW t day-clustered,
within-night placebo drawing the same number of picks at random.
"""
from __future__ import annotations

import json
import pathlib
import pickle
import time

import numpy as np
import pandas as pd

from . import book as B
from . import new_listings as NL
from .validate import load_sim

ROOT = pathlib.Path(__file__).resolve().parents[2]
CACHE = ROOT / "data/research/night/edgar"
OUT = ROOT / "data/research/program/night_quality_out.txt"
HALVES = (("2021-23", "2021-01-01", "2023-12-31"),
          ("2024-26", "2024-01-01", "2026-12-31"))
SIZES = (2300.0, 10000.0, 25000.0)
PERIODIC_F = {"20-F", "40-F", "6-K"}
US_F = {"10-K", "10-Q"}


def load_classes():
    mp = json.loads((CACHE / "ticker_cik.json").read_text())
    cache = {}
    for sym, c in mp.items():
        if not c:
            cache[sym] = None
            continue
        f = CACHE / f"{int(c):010d}.pkl"
        if not f.exists():
            cache[sym] = None
            continue
        s = pickle.load(open(f, "rb"))
        fl = s["filings"]
        t = pd.to_datetime(fl.acceptanceDateTime, utc=True, errors="coerce").values.astype("datetime64[ns]")
        forms = fl.form.values
        n424 = float((fl.form.str.startswith("424B") & (pd.to_datetime(fl.acceptanceDateTime, utc=True, errors="coerce") >= pd.Timestamp("2021-01-01", tz="UTC"))).sum()) / 5.75
        etp = (s.get("entityType") != "operating") or (str(s.get("sic")) == "6221") or (n424 > 100)
        cache[sym] = dict(t=t, forms=forms, etp=etp)
    return cache


def classify_at(cache, meta, sym, d):
    if NL.etf_kind(sym, meta) == "lev":
        return "LETF"
    c = cache.get(sym)
    if not c:
        return "NOMAP"
    if c["etp"]:
        return "ETP"
    hi = np.datetime64(pd.Timestamp(d), "ns")
    lo = hi - np.timedelta64(400, "D")
    w = (c["t"] >= lo) & (c["t"] <= hi)
    forms = set(c["forms"][w])
    if forms & PERIODIC_F:
        return "FOREIGN"
    if forms & US_F:
        return "US_OPER"
    return "OTHER"


def nw_t(x, lags=5):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) < 20:
        return float("nan")
    mu = x.mean(); e = x - mu; n = len(x)
    s = (e * e).sum() / n
    for k in range(1, lags + 1):
        s += 2 * (1 - k / (lags + 1)) * (e[k:] * e[:-k]).sum() / n
    return mu / np.sqrt(s / n) if s > 0 else float("nan")


def main():
    t0 = time.time()
    f = open(OUT, "w")

    def log(*a):
        x = " ".join(str(i) for i in a)
        print(x, flush=True); f.write(x + "\n"); f.flush()

    log("== Study AN: night-leg pick quality (point-in-time EDGAR classifier); started",
        pd.Timestamp.now(), "==")
    s = load_sim(raw_price=True)
    N = B.night_days(raw_price=True, max_corr=0.7)
    cache = load_classes(); meta = NL.load_meta()
    log(f"loaded {time.time()-t0:.0f}s; symbols cached {len(cache)}\n")

    rows = []
    for d, nd in N.items():
        for j, sym in enumerate(nd.syms):
            rows.append(dict(d=d, sym=str(sym), ret=float(nd.ret[j]), price=float(nd.price[j]),
                             adv=float(nd.adv[j]), frac=float(nd.frac),
                             cls=classify_at(cache, meta, str(sym), d)))
    T = pd.DataFrame(rows)
    T["w"] = np.minimum(T.frac, 0.10)
    T["half"] = np.where(T.d <= pd.Timestamp(HALVES[0][2]), "2021-23", "2024-26")
    T["adv_m"] = T.adv / 1e6
    log(f"picks {len(T)}  by class:")
    for cls, g in T.groupby("cls"):
        log(f"  {cls:9s} n {len(g):5d} ({len(g)/len(T):5.1%})  median ADV ${g.adv_m.median():6.1f}M  "
            f"median px ${g.price.median():6.2f}")

    for cost in ("tier", "tier_hi"):
        c = B.cost_bps(cost, T.price.values, T.adv.values) / 1e4
        T["net"] = T.ret - 2 * c
        base = pd.Series(0.5 * T.w.values * T.net.values, index=T.d.values)
        log(f"\n[{cost}] per-class mean net, w-weighted (bp):")
        for cls, g in T.groupby("cls"):
            m = 0.5 * g.w * g.net
            log(f"  {cls:9s} all {m.mean()*1e4:7.1f}  21-23 {m[g.half=='2021-23'].mean()*1e4:7.1f}  "
                f"24-26 {m[g.half=='2024-26'].mean()*1e4:7.1f}  n {len(g)}")

        def evaluate(lab, wv):
            inc = pd.Series(0.5 * wv.values * T.net.values, index=T.d.values) - base
            half = [inc[(inc.index >= a) & (inc.index <= z)].mean() * 252 * 100 for _, a, z in HALVES]
            t = nw_t(inc.values)
            # placebo: within each night, keep the same count of picks at random, 1000 draws
            rng = np.random.default_rng(3)
            n_keep = int((wv.values > 0).sum())
            sims = []
            for _ in range(300):
                idx = rng.choice(len(T), size=max(1, n_keep), replace=False)
                m = np.zeros(len(T)); m[idx] = 1
                sims.append((0.5 * T.w.values * T.net.values * m).sum() / len(T))
            real = (0.5 * T.w.values * T.net.values * (wv.values > 0)).sum() / len(T)
            pct = float((np.array(sims) < real).mean() * 100)
            log(f"  {lab:24s} inc {half[0]:+5.2f}/{half[1]:+5.2f}pp/yr  NW t {t:+5.2f}  "
                f"placebo {pct:4.0f}%  n_kept {n_keep}")
            for E in SIZES:
                pass
            return inc, half, t, pct

        w = T.w.copy()
        keep = T.cls != "US_OPER"
        evaluate("AN1 drop US_OPER", w.where(keep, 0.0))
        keep2 = T.cls == "FOREIGN"
        evaluate("AN2 keep FOREIGN only", w.where(keep2, 0.0))
        w3 = np.where(T.cls == "FOREIGN", np.minimum(2 * w, 0.20), w)
        evaluate("AN3 FOREIGN 2x", pd.Series(w3, index=T.index))
        keep4 = T.cls != "LETF"
        evaluate("AN4 drop LETF", w.where(keep4, 0.0))
        w5 = np.where((T.cls != "US_OPER"), w, 0.0)
        w5 = np.where(T.cls == "FOREIGN", np.minimum(2 * w, 0.20), w5)
        evaluate("AN5 drop US_OPER + 2x FOREIGN", pd.Series(w5, index=T.index))

        # $/yr at small size for the best-looking tilt (AN3) and capacity
        inc3 = pd.Series(0.5 * (np.minimum(2 * w, 0.20) - w) * T.net.values, index=T.d.values)
        n_yr = len(s.days) / 252
        log(f"  AN3 $/yr: " + "  ".join(f"${E:,.0f}: {inc3.sum()/n_yr*E:+,.0f}" for E in SIZES)
            + f"   FOREIGN picks median ADV ${T[T.cls=='FOREIGN'].adv_m.median():.1f}M "
              f"(capacity: the leg is ~$115/name at $2.3k, ~$1.15k/name at $25k)")

    log(f"\ndone {time.time()-t0:.0f}s")
    f.close()


if __name__ == "__main__":
    main()
