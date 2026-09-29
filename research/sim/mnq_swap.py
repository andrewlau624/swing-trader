"""Study D: MNQ (micro-futures) vs the QQQ noise leg; the 1256 vs 35% ST tax swap.

    PYTHONPATH=. .venv/bin/python -m research.sim.mnq_swap

Pre-register: research/drafts/round1_prose.md, "Amendment - Study D" (stamp
Tue Sep 29 02:04:34 PDT 2026, before any number below was computed).

Accounting:
  r_qqq(d) = min(lev_d, 0.75) * 0.5 * z.ret_d          (the sim's cached QQQ rows, 0.5bp/side)
  r_mnq(d) = min(lev_d, 0.75) * 0.5 * (g_d - sides_d * c_fut)   (the same live rule on the
     ETF-minute proxy at the futures per-side cost; lev = the same vol target series)
  r_swap(d) = r_base(d) - r_qqq(d) + r_mnq(d)          (the book pre-tax with the swap)
Tax: TF.mc_tax(r_book, r1256=r_mnq_contribution) at the sizes $3k/15k/30k/50k/100k
(+ $1k/mo scaled to the account: the deposits are $1k/mo for $3k and 5x for $15k etc to
keep the same deposit-age economics). ST 35% / LT 20%, so the 1256 blended = 0.26.
"""
from __future__ import annotations

import pathlib
import pickle
import time

import numpy as np
import pandas as pd

from . import book as B
from . import data as D
from . import growth as G
from . import taxable_frontier as TF
from .futures import noise, side_bps, SPEC
from .validate import load_sim

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/mnq_swap_out.txt"
PER = (("2021-23", "2021-01-01", "2023-12-31"), ("2024-26", "2024-01-01", "2026-12-31"),
       ("2016-20", "2016-01-01", "2020-12-31"))
CAP = 0.75


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


def half_str(x):
    out = []
    for lab, a, b in PER:
        c, sh, dd = B.stats(x[a:b])
        out.append(f"{lab} {c*100:+.1f}/{sh:4.2f}/{dd*100:3.0f}")
    return " | ".join(out)


def to_day(vals, idx, index):
    return pd.Series(np.asarray(vals, float), index=pd.Index(np.asarray(idx))).groupby(level=0).sum().reindex(index).fillna(0.0)


def main():
    fs = open(OUT, "w")

    def log(*a):
        x = " ".join(str(i) for i in a)
        print(x, flush=True)
        fs.write(x + "\n")
        fs.flush()

    t0 = time.time()
    log("== Study D: MNQ swap, started", pd.Timestamp.now(), "\n")
    qq = float(D.minutes("QQQ")["close"].values[-1, -1])
    N_mnq = SPEC["MNQ"]["ratio"] * qq * SPEC["MNQ"]["mult"]
    log(f"MNQ notional {N_mnq:,.0f} $; 7% margin {0.07*N_mnq:,.0f} $; "
        f"forced 1-contract leverage: $3k {N_mnq/3000:.1f}x | $15k {N_mnq/15000:.2f}x | "
        f"$30k {N_mnq/30000:.2f}x | $50k {N_mnq/50000:.2f}x | $100k {N_mnq/100000:.2f}x\n")

    s = load_sim(raw_price=True)
    s.N = B.night_days(raw_price=True, max_corr=0.7)
    s.BO = B.breakout_days()

    tr_mnq = noise("MNQ", target_vol=0.02)
    tr_kelly = noise("MNQ", target_vol=0.03)
    qq_now = float(D.minutes("QQQ")["close"].values[-1, -1])
    fut_c = {"tier": float(side_bps("MNQ", [qq_now], "tier")[0]),
             "tier_hi": float(side_bps("MNQ", [qq_now], "tier_hi")[0]),
             "stress": float(side_bps("MNQ", [qq_now], "stress")[0])}
    log(f"MNQ per-side cost bps at TODAY's notional: "
        f"tier {fut_c['tier']:.3f}  tier_hi {fut_c['tier_hi']:.3f}  stress {fut_c['stress']:.3f} "
        f"(the ETF's 1bp tier / 2bp tier_hi per-side; historical per-row costs use each row's own px)\n")

    base = {}
    for cost in (3.0, "tier", "tier_hi"):
        kw = {**G.V7, **G.cfg(1.0, 0.5, 2), "night_cost": cost}
        base[cost] = s.replay(B.Params(**kw))
        log(f"D1 base V7 raw {str(cost):7s}: {B.summary(base[cost])}")

    for cost in (3.0, "tier", "tier_hi"):
        ckey = "tier" if cost == 3.0 else cost
        z = s.NZ["QQQ"]
        r_q = to_day(z.ret.values * np.clip(z.lev.values, None, CAP) * 0.5,
                     z.index, base[cost]["r"].index)
        for lab, trf in (("D2 MNQ 0.02", tr_mnq), ("D3 MNQ Kelly 0.03", tr_kelly)):
            # the per-side cost computed per ROW on that row's own notional (the ratio drifts)
            sides_b = side_bps("MNQ", trf.px.values, ckey)
            netm = (trf.g.values - trf.sides.values * sides_b / 1e4)
            r_m = to_day(np.clip(trf.lev.values, None, CAP) * 0.5 * netm,
                         trf.date.values, base[cost]["r"].index)
            r_swap = base[cost]["r"] - r_q + r_m
            inc = r_swap - base[cost]["r"]
            log(f"{lab} cost {str(cost):7s}: " + half_str(inc) + f"   NW t {nw_t(inc):+.2f}")

            for E0, md in ((3000.0, 1000.0), (15000.0, 5000.0), (30000.0, 10000.0),
                           (50000.0, 16666.0), (100000.0, 33333.0)):
                m0 = TF.mc_tax(base[cost]["r"], start=E0, monthly=md)
                m1 = TF.mc_tax(r_swap, r1256=r_m, start=E0, monthly=md)
                lev1 = N_mnq / E0
                fit = "1 contract fits" if lev1 <= 2.0 else "OUT (forced 1-contract lev >2x)"
                log(f"   E0 ${E0/1e3:>5.0f}k dep ${md/1e3:.1f}k/mo lev1 {lev1:5.2f} {fit:32s} "
                    f"base: med ${m0['med']/1e3:6.1f}k P30 {m0['dd30']*100:4.1f} P50 {m0['dd50']*100:4.1f} | "
                    f"swap: med ${m1['med']/1e3:6.1f}k P30 {m1['dd30']*100:4.1f} P50 {m1['dd50']*100:4.1f}")
        log("---")
    fs.close()


if __name__ == "__main__":
    main()
