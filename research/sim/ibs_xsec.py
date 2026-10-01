"""Study AP (Round 17b): the IBS leg's selection — cross-sectional rank and always-deployed.

    PYTHONPATH=. .venv/bin/python -m research.sim.ibs_xsec

Pre-registration: research/drafts/round1_prose.md, "Round 17b", Study AP (committed before any
number below). Swaps the IBS leg's selection and judges the full V7 book (and the IBS-only
cash-IRA book) at fixed capital.
"""
from __future__ import annotations

import pathlib
import time

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import book as B
from . import data as D
from .validate import load_sim

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/ibs_xsec_out.txt"
EQ18 = B.EQ18
HALVES = (("2021-23", "2021-01-01", "2023-12-31"),
          ("2024-26", "2024-01-01", "2026-12-31"))
SIZES = (2300.0, 10000.0, 25000.0)


def ibs_days_xs(mode: str, top_k: int = 3) -> dict:
    P = D.etf(); O, H, L, C = P["open"], P["high"], P["low"], P["close"]
    closes = C[EQ18]; days = C.index
    out, mom_cache = {}, {}
    for j in range(260, len(days) - 2):
        d, today = days[j], days[j + 1]
        m = today.to_period("M")
        if m not in mom_cache:
            mom_cache[m] = sg.momentum_top(closes[closes.index < today], today, top_k)
        uni = mom_cache[m]

        def ibs_of(s):
            hi, lo, c = H.at[d, s], L.at[d, s], C.at[d, s]
            return (c - lo) / (hi - lo) if (hi > lo and np.isfinite(hi) and np.isfinite(lo)) else 1.0

        if mode == "all18_lowest1":
            cand = sorted(EQ18, key=ibs_of)
            sel = cand[:1]
        else:
            ranked = sorted(uni, key=ibs_of)
            if mode == "lowest1_thr":
                sel = [s for s in ranked if ibs_of(s) < 0.2][:1]
            elif mode == "lowest1_always":
                sel = ranked[:1]
            elif mode == "lowest2_thr":
                sel = [s for s in ranked if ibs_of(s) < 0.2][:2]
            else:
                raise ValueError(mode)
        legs = [(s, O.at[days[j + 1], s], O.at[days[j + 2], s] / O.at[days[j + 1], s] - 1)
                for s in sel if np.isfinite(O.at[days[j + 1], s]) and np.isfinite(O.at[days[j + 2], s])]
        if legs:
            out[d] = legs
    return out


def replay_fixed(s, size, p):
    return pd.Series([s.day_pnl(size, d, p)[0] / size for d in s.days], index=s.days)


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

    log("== Study AP: IBS selection (cross-sectional / always-deployed); started",
        pd.Timestamp.now(), "==")
    s = load_sim(raw_price=True)
    s.N = B.night_days(raw_price=True, max_corr=0.7)
    base_I = B.ibs_days()
    VAR = {"AP1 rank-1 thr": ibs_days_xs("lowest1_thr"),
           "AP2 rank-1 always": ibs_days_xs("lowest1_always"),
           "AP3 all18 rank-1": ibs_days_xs("all18_lowest1"),
           "AP4 rank-2 thr": ibs_days_xs("lowest2_thr"),
           "AP5 ibs_max 0.1": B.ibs_days(ibs_max=0.1)}
    log(f"ibs days: shipped {len(base_I)}; " + ", ".join(f"{k} {len(v)}" for k, v in VAR.items()) + "\n")

    for booklab, p in (
        ("V7 book", B.Params(night_w=0.5, ibs_w=0.5, night_cost="tier_hi", ibs_cost_bps=1.0,
                             noise={"QQQ": 0.5, "SMH": 0.5}, noise_cap=0.75, tilt="live",
                             weekend_scale=0.5, conviction_w=0.0)),
        ("IBS-only (cash IRA)", B.Params(night_w=0.0, ibs_w=1.0, night_cost="tier_hi", ibs_cost_bps=1.0,
                                         noise_on=False, tilt="live", weekend_scale=0.5,
                                         conviction_w=0.0))):
        log(f"== {booklab} (tier_hi, fixed capital)")
        s.I = base_I
        base = {E: replay_fixed(s, E, p) for E in SIZES}
        for E in SIZES:
            log(f"  ${E/1e3:5.1f}k shipped IBS  full {B.stats(base[E])[0]*100:5.1f}/"
                f"{B.stats(base[E])[1]:4.2f}/{B.stats(base[E])[2]*100:4.0f}")
        for lab, I in VAR.items():
            s.I = I
            for E in SIZES:
                r = replay_fixed(s, E, p)
                d = r - base[E]
                half = [d[(d.index >= a) & (d.index <= z)].mean() * 252 * 100 for _, a, z in HALVES]
                t = nw_t(d.values)
                rng = np.random.default_rng(9); X = d.values
                sims = np.array([(X * rng.choice([-1, 1], size=len(X))).mean() for _ in range(500)])
                pct = float((sims < X.mean()).mean() * 100)
                inc = (B.stats(r)[0] - B.stats(base[E])[0]) * 100
                dd = (B.stats(r)[2] - B.stats(base[E])[2]) * 100
                log(f"  ${E/1e3:5.1f}k {lab:18s} full {B.stats(r)[0]*100:5.1f}/"
                    f"{B.stats(r)[1]:4.2f}/{B.stats(r)[2]*100:4.0f}  inc {inc:+5.2f}pp "
                    f"({half[0]:+5.2f}/{half[1]:+5.2f})  t {t:+5.2f}  placebo {pct:4.0f}%  dDD {dd:+4.1f}")
        log("")
    log(f"\ndone {time.time()-t0:.0f}s")
    f.close()


if __name__ == "__main__":
    main()
