"""Study H: the 24-ETF IBS pool's tie-break resolved (F2's follow-up; alphabetical).

    PYTHONPATH=. .venv/bin/python -m research.sim.ibs_24_univ

Pre-reg: research/drafts/round1_prose.md, "Amendment - Round 3: Study H" (stamped
Tue Sep 29 09:52:46 PDT 2026, before any Study H number).

Variants (3):
  H1 the F2-family 24-ETF pool (equity 18 + non-equity 10), SORTED alphabetically before
     the momentum call, so the tie-break is order-independent; 3bp / tier / tier_hi.
  H2 the same pool with the non-equity sleeve at a 0.25 leg share (a smaller budget).
  H3 the same 24-ETF pool with a within-pool corr-dedupe (drop ties whose 20-day
     Pearson r > 0.9 with a higher-ranked pick, before the top-3).
Everything else identical to the raw-pool V7 baselines used in every recent study.
"""
from __future__ import annotations

import pathlib
import time

import numpy as np
import pandas as pd

from . import book as B
from . import growth as G
from . import data as D
from .validate import load_sim
from swingtrader.daily import signals as sg

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/ibs_24_univ_out.txt"
NE10 = ["TLT", "IEF", "GLD", "SLV", "USO", "HYG", "XLP", "XLU", "EEM", "EFA"]
# Correction (2026-09-29): the first run hand-typed a 15-name "EQ18" (no XLP/XLU/XLB)
# and took the first 3 of sg.momentum_top(..., 8), which returns its top-k SORTED
# ALPHABETICALLY: it traded the alphabetically-first 3 of the top 8, not the top 3.
# Its "tie-break" verdict came from that bug. This version mirrors book.ibs_days
# exactly (momentum ranked for the NEXT session's month, cached per month) with only
# the pool changed; H0 (the shipped 18) must reproduce the baseline to the bp.
EQ18 = list(B.EQ18)


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


def momentum_ranked(closes, today, lookback=252, skip=21):
    """sg.momentum_top's ranking WITHOUT its final alphabetical sort (best first)."""
    c = closes[closes.index < today]
    mom = c.shift(skip) / c.shift(lookback) - 1
    me = mom.groupby([mom.index.year, mom.index.month]).tail(1)
    me = me[me.index.to_period("M") < today.to_period("M")]
    if me.empty:
        return []
    return list(me.iloc[-1].dropna().sort_values(ascending=False, kind="mergesort").index)


def ibs_pool(pool, k=3, ibs_max=0.2, dedupe=False):
    pool = list(dict.fromkeys(pool))
    P = D.etf()
    O, H, L, C = P["open"], P["high"], P["low"], P["close"]
    closes = C[pool]
    days = C.index
    out, cache = {}, {}
    for j in range(260, len(days) - 2):
        d, today = days[j], days[j + 1]
        m = today.to_period("M")
        if m not in cache:
            if not dedupe:
                cache[m] = sg.momentum_top(closes[closes.index < today], today, k)
            else:       # H3: walk best-first, drop a name whose 20d RETURNS corr > 0.9 with a kept one
                rets = closes[closes.index < today].pct_change().iloc[-20:]
                keep = []
                for s_ in momentum_ranked(closes, today):
                    if not any(abs(rets[s_].corr(rets[x])) > 0.9 for x in keep):
                        keep.append(s_)
                    if len(keep) == k:
                        break
                cache[m] = sorted(keep)
        uni = cache[m]
        last = {s: {"high": H.at[d, s], "low": L.at[d, s], "close": C.at[d, s]} for s in uni}
        tg = sg.ibs_targets(last, ibs_max)
        legs = [(s, O.at[days[j + 1], s], O.at[days[j + 2], s] / O.at[days[j + 1], s] - 1)
                for s in tg if np.isfinite(O.at[days[j + 1], s]) and np.isfinite(O.at[days[j + 2], s])]
        if legs:
            out[d] = legs
    return out


def main():
    t0 = time.time()
    fs = open(OUT, "w")

    def log(*a):
        x = " ".join(str(i) for i in a)
        print(x, flush=True)
        fs.write(x + "\n")
        fs.flush()

    log("== Study H (corrected rerun): 24-ETF IBS top-3, mirrors book.ibs_days; started", pd.Timestamp.now(),
        f"==\n")
    s = load_sim(raw_price=True)
    s.N = B.night_days(raw_price=True, max_corr=0.7)
    I86 = s.I
    H_CONFIGS = {
        "H0 shipped 18 (control)": (EQ18, False),
        "H1 24-univ top-3": (list(dict.fromkeys(EQ18 + NE10)), False),
        "H2 22-univ top-3": (list(dict.fromkeys(EQ18 + NE10[:4])), False),
        "H3 24-univ corr-dedupe": (list(dict.fromkeys(EQ18 + NE10)), True),
    }
    for cost in (3.0, "tier", "tier_hi"):
        kw = {**G.V7, **G.cfg(1.0, 0.5, 2), "night_cost": cost}
        s.I = I86
        base = s.replay(B.Params(**kw))
        for lab, (pool, ded) in H_CONFIGS.items():
            newI = ibs_pool(pool, dedupe=ded)
            s.I = newI
            r = s.replay(B.Params(**kw))
            inc = r["r"] - base["r"]
            for lab2, a, b2 in (("2021-23", "2021-01-01", "2023-12-31"),
                                ("2024-26", "2024-01-01", "2026-12-31"),
                                ("2016-20", "2016-02-01", "2020-12-31")):
                p = B.stats(inc[a:b2])
                log(f"{str(cost):7s} {lab:24s} {lab2}: d {p[0]*100:+6.2f}pp / Sharpe {p[1]:4.2f} / DD {p[2]*100:3.0f}")
            tt = nw_t(inc)
            log(f"{'':7s} {'':24s} full: {B.stats(inc)[0]*100:+6.2f}pp  NW t {tt:+4.2f}\n")
    fs.close()


if __name__ == "__main__":
    main()
