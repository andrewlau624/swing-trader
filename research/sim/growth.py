"""Growth-optimal sizing for an EXPERIMENTAL, risk-seeking book.

    PYTHONPATH=. .venv/bin/python -m research.sim.growth

The goal here is geometric CAGR (compounded growth), not Sharpe, inside real
broker limits:
  overnight   Reg T 2x: ibs_w + night_w <= 2 (the sim charges 12%/yr on any debit)
  daytime     every position's margin requirement fits the equity:
                ibs_w * r_std + noise_cap * r_std + conviction_w * r_3x <= 1
              r_std = 1 / daytime multiplier (0.5 standard Schwab margin, 0.25 with
              4x day-trading buying power). r_3x = house requirement on TQQQ/SQQQ:
              FINRA/Cboe minimum for a 3x ETF is 75% (25% x 3), and brokers may ask 100%.
              NOTE: executor._gate computes mult - w_ibs - conv, i.e. treats TQQQ at
              the standard rate. At 75% the shipped V7 intraday cap is 0.75, not 1.0.

Sections:
  1. growth frontier at tier costs (top 10), same configs at tier_hi
  2. fragility: edge-halves (each leg's mean daily contribution cut by half, variance
     kept) x tier_hi, plus an unconstrained leverage ladder to show the Kelly cliff
  3. 5-year block-bootstrap Monte Carlo (21-day blocks): shipped V7 vs the pick
  4. COVID 2020 stress for the same two configs (legs rebuilt as in crash.py)
"""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import book as B
from . import crash as CR
from .validate import load_sim

S2 = {"QQQ": 0.5, "SMH": 0.5}
V7 = dict(tilt="live", noise=S2, weekend_scale=0.5)
R3X = 0.75


def cfg(g: float, conv: float, mult: float, noise: float | None = None, r3: float = R3X):
    """Params kwargs, or None if the daytime margin cannot hold IBS + conviction."""
    w = g / 2
    rstd = 1 / mult
    room = 1 - w * rstd - conv * r3
    if room < -1e-9:
        return None
    nmax = max(0.0, room / rstd)
    ncap = min(3.5, nmax if noise is None else min(noise, nmax))
    return dict(night_w=w, ibs_w=w, noise_cap=ncap, conviction_w=conv)


def monthly_worst(r: pd.Series) -> float:
    return float((1 + r.fillna(0)).groupby([r.index.year, r.index.month]).prod().min() - 1)


def eh(df: pd.DataFrame) -> pd.Series:
    """Edge-halves: take half of each leg's mean daily contribution away."""
    cut = 0.5 * (df["r_night"].mean() + df["r_ibs"].mean() + df["r_noise"].mean())
    return df["r"] - cut


def row(r: pd.Series) -> str:
    a, b, f = B.stats(r[:"2023-12-31"]), B.stats(r["2024-01-01":]), B.stats(r)
    return (f"{a[0]*100:5.1f}/{a[1]:4.2f}  {b[0]*100:5.1f}/{b[1]:4.2f}  "
            f"{f[0]*100:5.1f}/{f[1]:4.2f}/{f[2]*100:4.0f}  wm {monthly_worst(r)*100:5.1f}")


def lab(k) -> str:
    g, cap, conv, mult, nz = k
    return f"g{g:.1f} cap{cap:.2f} conv{conv:.1f} {int(mult)}x noise{nz if nz else 'max'}"


# ---------------------------------------------------------------- MC
def mc(r: pd.Series, start: float, monthly: float, n: int = 4000, days: int = 1260,
       block: int = 21, seed: int = 7) -> dict:
    rng = np.random.default_rng(seed)
    x = r.fillna(0).values
    nb = days // block
    starts = rng.integers(0, len(x) - block, size=(n, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(n, -1)
    R = x[idx]
    tw = np.cumprod(1 + R, axis=1)
    dd = (tw / np.maximum.accumulate(tw, axis=1) - 1).min(axis=1)
    E = np.full(n, start); dep = start
    for t in range(R.shape[1]):
        if t and t % 21 == 0:
            E = E + monthly; dep += monthly
        E = E * (1 + R[:, t])
    return dict(p10=np.percentile(E, 10), med=np.median(E), p90=np.percentile(E, 90),
                dd30=(dd < -0.30).mean(), dd50=(dd < -0.50).mean(),
                below=(E < dep).mean(), dep=dep, ruin=(E < 0.25 * dep).mean())


# --------------------------------------------------------- COVID stress
def covid_legs(sim, caps=(0.10, 0.15, 0.20, 0.25)):
    """Unit-weight daily leg returns for 2020-01 -> 2020-12 (night bias-corrected)."""
    d20 = CR.days_2020(0.7)
    out = {}
    for cap in caps:
        o = {}
        for d in sorted(d20):
            ret, vol20, day_ret, n_raw, gap = d20[d]
            keep = np.nan_to_num(vol20) >= 0.6
            if not keep.any():
                o[d] = 0.0; continue
            r, v, dr = ret[keep], vol20[keep], day_ret[keep]
            per = min(1 / len(r), cap) * min(1.0, 30 / max(n_raw, 1))
            x = per * sg.night_tilt(v, dr) * (0.5 if gap > 1 else 1.0)
            val = float((x * (np.nan_to_num(r) - 2 * CR.COST / 1e4)).sum())
            o[d] = val - 9.1e-4 * (val != 0)
        out[cap] = pd.Series(o)
    ibs = {}
    for d, lst in sim.I.items():
        if lst:
            ibs[d] = float(np.mean([r for _, _, r in lst])) - 2e-4
    ibs = pd.Series(ibs)
    bil = sim.bil
    nz = {}
    for s, z in sim.NZ.items():
        nz[s] = z
    bo = B.breakout_days()
    return out, ibs, bil, nz, bo


def covid_book(legs, k, a="2020-02-19", b="2020-03-23"):
    night, ibs, bil, nz, bo = legs
    p = k
    days = pd.bdate_range(a, b)
    r = []
    for d in days:
        x = p["night_w"] * float(night[p["_cap"]].get(d, 0.0))
        iv = ibs.get(d, np.nan)
        x += p["ibs_w"] * (float(iv) if np.isfinite(iv) else float(np.nan_to_num(bil.get(d, 0.0))))
        for s, share in S2.items():
            z = nz[s]
            if d in z.index:
                x += min(float(z.at[d, "lev"]), p["noise_cap"]) * share * float(z.at[d, "ret"])
        x += p["conviction_w"] * float(bo.get(d, 0.0))
        debit = max(0.0, p["ibs_w"] + p["night_w"] - 1)     # upper bound: legs fully used
        x -= debit * 0.12 / 252
        r.append(x)
    r = pd.Series(r, index=days)
    tw = (1 + r).cumprod()
    return (tw.iloc[-1] - 1), (tw / tw.cummax() - 1).min(), r.min()


def main():
    s = load_sim()
    Ns = {c: B.night_days(max_corr=0.7, max_name_pct=c) for c in (0.10, 0.15, 0.20, 0.25)}

    def run(k, cost="tier"):
        g, cap, conv, mult, nz = k
        kw = cfg(g, conv, mult, nz)
        s.N = Ns[cap]
        return s.replay(B.Params(**{**V7, **kw, "night_cost": cost}))

    # shipped V7 as the executor sizes it, and as margin really allows (TQQQ at 75%)
    ship_code = dict(night_w=0.5, ibs_w=0.5, noise_cap=1.0, conviction_w=0.5)
    s.N = Ns[0.10]
    base = {c: s.replay(B.Params(**{**V7, **ship_code, "night_cost": c})) for c in ("tier", "tier_hi")}
    kb = (1.0, 0.10, 0.5, 2, None)
    base75 = {c: run(kb, c) for c in ("tier", "tier_hi")}

    grid = [k for k in itertools.product((1.0, 1.3, 1.5, 1.7, 2.0), (0.10, 0.15, 0.20, 0.25),
                                         (0.0, 0.5, 1.0, 1.5, 2.0), (2, 4), (None, 1.0))
            if cfg(k[0], k[2], k[3], k[4]) is not None]
    res = {}
    for k in grid:
        res[k] = run(k)
    top = sorted(res, key=lambda k: -B.stats(res[k]["r"])[0])
    # dedupe (noise None == 1.0 when the room is exactly 1.0)
    seen, top10 = set(), []
    for k in top:
        sig = tuple(round(v, 3) for v in cfg(k[0], k[2], k[3], k[4]).values()) + (k[1],)
        if sig in seen:
            continue
        seen.add(sig); top10.append(k)
        if len(top10) == 12:
            break

    hdr = f"{'':42s} {'2021-23':>11s}  {'2024-26':>11s}  {'full CAGR/Sh/DD':>17s}  worst month"
    print(f"== 0. shipped V7 (overnight 1.0x, cap 0.10, conviction 0.5)\n{hdr}")
    for c in ("tier", "tier_hi"):
        print(f"{'as coded (intraday cap 1.0) ' + c:42s} {row(base[c]['r'])}")
        print(f"{'TQQQ at 75% margin (cap 0.75) ' + c:42s} {row(base75[c]['r'])}")
    print(f"\n== 1. growth frontier, tier costs, {len(grid)} feasible configs "
          f"(TQQQ house margin {R3X:.0%})\n{hdr}")
    hi = {}
    for k in top10:
        kw = cfg(k[0], k[2], k[3], k[4])
        print(f"{lab(k):42s} {row(res[k]['r'])}  intraday {kw['noise_cap']:.2f}")
    print(f"\n-- the same at tier_hi\n{hdr}")
    for k in top10:
        hi[k] = run(k, "tier_hi")
        print(f"{lab(k):42s} {row(hi[k]['r'])}")

    print(f"\n== 2. fragility: edge-halves (EH) at tier and tier_hi\n{hdr}")
    print(f"{'V7 shipped EH tier':42s} {row(eh(base75['tier']))}")
    print(f"{'V7 shipped EH tier_hi':42s} {row(eh(base75['tier_hi']))}")
    # the EH x tier_hi frontier over the WHOLE grid, not just the tier winners
    ehhi = {}
    for k in grid:
        ehhi[k] = eh(run(k, "tier_hi"))
    best_eh = sorted(grid, key=lambda k: -B.stats(ehhi[k])[0])[:8]
    for k in top10[:5]:
        print(f"{'EH tier_hi  ' + lab(k):42s} {row(ehhi[k])}")
    print("-- best configs UNDER edge-halves x tier_hi (the conservative-growth choice)")
    for k in best_eh:
        print(f"{'EH tier_hi  ' + lab(k):42s} {row(ehhi[k])}   (hist tier "
              f"{B.stats(res[k]['r'])[0]*100:.1f}%)")

    print("\n-- Kelly cliff: every leg scaled by L from shipped (overnight L, conviction 0.5L, "
          "intraday cap 1.0L), UNCONSTRAINED by margin, cap 0.10")
    print(f"{'L':>5s} {'hist tier':>18s} {'tier_hi':>18s} {'EH tier_hi':>18s}")
    s.N = Ns[0.10]
    for L in (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0):
        kw = dict(night_w=0.5 * L, ibs_w=0.5 * L, noise_cap=1.0 * L, conviction_w=0.5 * L)
        out = []
        for c in ("tier", "tier_hi"):
            df = s.replay(B.Params(**{**V7, **kw, "night_cost": c}))
            out.append(B.stats(df["r"]))
            if c == "tier_hi":
                out.append(B.stats(eh(df)))
        print(f"{L:5.1f} " + " ".join(f"{c*100:7.1f}%/{d*100:5.0f}%DD" for c, _, d in out))

    aggro = top10[0]
    ehpeak = best_eh[0]
    # Growth under edge-halves is flat near its peak, while drawdown keeps
    # growing: step back to the best EH growth whose EH maxDD stays within -35%
    # (about half-Kelly on the ladder below), separately for 2x and 4x daytime.
    picks = {}
    for mult in (2, 4):
        ok = [k for k in grid if k[3] == mult and B.stats(ehhi[k])[2] >= -0.35]
        picks[mult] = max(ok, key=lambda k: B.stats(ehhi[k])[0])
    print(f"\nEH x tier_hi growth peak (~full Kelly): {lab(ehpeak)}")
    print("-- 2x daytime frontier (standard Schwab margin), tier, top 5")
    two = sorted([k for k in grid if k[3] == 2], key=lambda k: -B.stats(res[k]["r"])[0])[:5]
    for k in two:
        print(f"{lab(k):42s} {row(res[k]['r'])} | EH tier_hi {row(ehhi[k])}")
    for mult, k in picks.items():
        print(f"pick {mult}x (max EH growth with EH maxDD >= -35%): {lab(k)} -> "
              f"{cfg(k[0], k[2], k[3], k[4])}\n    hist tier {row(res[k]['r'])}\n    "
              f"tier_hi   {row(run(k, 'tier_hi')['r'])}\n    EH hi     {row(ehhi[k])}")
    pick = picks[4]

    print("\n== 3. Monte Carlo, 5 years, 21-day block bootstrap of 2021-02..2026-09 daily returns")
    cases = {"V7 shipped (75% TQQQ)": (base75["tier"], base75["tier_hi"]),
             f"pick2x {lab(picks[2])}": (run(picks[2]), run(picks[2], "tier_hi")),
             f"pick4x {lab(picks[4])}": (run(picks[4]), run(picks[4], "tier_hi")),
             f"EH-peak {lab(ehpeak)}": (res[ehpeak], run(ehpeak, "tier_hi"))}
    for name, (dft, dfh) in cases.items():
        for sc, r in (("hist tier", dft["r"]), ("EH tier_hi", eh(dfh))):
            for st, mo in ((3000, 1000), (10000, 0)):
                m = mc(r, st, mo)
                print(f"{name:42s} {sc:10s} ${st/1e3:.0f}k+${mo/1e3:.0f}k/mo: median ${m['med']:>10,.0f} "
                      f"(p10 {m['p10']:>9,.0f} p90 {m['p90']:>10,.0f}; dep {m['dep']:,.0f})  "
                      f"P(DD>30%) {m['dd30']:.0%}  P(DD>50%) {m['dd50']:.0%}  "
                      f"P(end<dep) {m['below']:.0%}  P(end<25% dep) {m['ruin']:.1%}")

    print("\n== 4. COVID crash 2020-02-19 -> 03-23 (night rebuilt from 2020 daily bars, bias-corrected)")
    legs = covid_legs(s)
    for name, k in (("V7 shipped", kb), ("pick2x", picks[2]), ("pick4x", picks[4]),
                    ("EH-peak", ehpeak), ("max-growth", aggro)):
        kw = cfg(k[0], k[2], k[3], k[4]); kw["_cap"] = k[1]
        tot, dd, worst = covid_book(legs, kw)
        print(f"  {name:12s} {lab(k):42s} episode {tot*100:+6.1f}%  maxDD {dd*100:6.1f}%  worst day {worst*100:5.1f}%")


if __name__ == "__main__":
    main()
