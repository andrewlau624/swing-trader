"""Slow-bear hedges for the V7 book (hostile review, charge 5 follow-up).

    .venv/bin/python -m research.sim.hedge

The book's only short side is the QQQ/SMH intraday leg, ~0 in 2025-26. If it
fails, a 2022-style slow bear is unhedged. Six candidates, priors written
BEFORE running (rule: pick on 2021-23 book / 2016-23 standalone, judge
2024-26, both-halves CAGR may fall at most ~1pp, must beat a placebo):

  C1 IBS only while SPY > 200d SMA, else T-bills. Prior WEAK/NEGATIVE:
     short-term reversal in ETFs is strongest in falling, volatile markets;
     addendum 7 found the per-ETF 200d filter hurt (12.3 -> 4.9). Checked
     because the review asked; expected dead.
  C2 night leg x0.5 while SPY < 200d SMA. Prior: in a bear a -8% day is more
     often repricing than forced selling, and the leg's crash risk clusters
     there. Expect a smaller 2022 hit and some lost return.
  C3 -1x SPY sleeve (SH-like), 0.25 of equity, held close->close while SPY <
     200d SMA. Prior: time-series momentum (Moskowitz-Ooi-Pedersen 2012);
     a 200d rule historically cuts equity drawdowns and whipsaws in V-shaped
     recoveries. Expect + in 2022, - in 2020 rebound / 2025.
  C4 same with actual SQQQ at 1/3 of 0.25 while QQQ < 200d. Prior: as C3, but
     matched to the book's tech tilt (IBS top-3 and intraday are tech-heavy).
  C5 C3 with a second confirmation (SPY < 200d AND 50d < 200d). Prior: fewer
     whipsaws, later entry.
  C6 placebo: C3's sleeve on random days at C3's frequency (20 seeds).

VIX term structure was on the list; yfinance is not installed and Alpaca has
no index data, so it is skipped. Roth: C1, C2 feasible; C3-C5 feasible only
as long inverse ETFs sized from idle cash (no borrowing) -- see the table.
Signals use closes through d-1; sleeves hold close d -> close d+1.
"""
from __future__ import annotations

import copy

import numpy as np
import pandas as pd

from . import book as B
from .crash import EPISODES
from .validate import load_sim

S2 = {"QQQ": 0.5, "SMH": 0.5}
V7 = dict(tilt="live", noise=S2, weekend_scale=0.5, conviction_w=0.5, noise_cap=1.0)
W = 0.25              # sleeve size, fraction of equity
SH_FEE = 0.0089 / 252  # SH expense ratio, daily


def replay_regime(s: B.Sim, p: B.Params, ibs_off=None, night_scale=None,
                  start=3000.0, monthly=1000.0) -> pd.DataFrame:
    """Sim.replay with a per-day hook: ibs_off[d] -> the IBS half sits in
    T-bills; night_scale[d] -> night weight multiplier."""
    rows, E = [], start
    for i, d in enumerate(s.days):
        if i and i % 21 == 0:
            E += monthly
        q = p
        saved = None
        if ibs_off is not None and bool(ibs_off.get(d, False)) and d in s.I:
            saved = s.I.pop(d)
        if night_scale is not None and night_scale.get(d, 1.0) != 1.0:
            q = copy.copy(p); q.night_w = p.night_w * float(night_scale[d])
        pl, info = s.day_pnl(E, d, q)
        if saved is not None:
            s.I[d] = saved
        rows.append((d, pl / E if E else 0.0,
                     info["night_v"] / (p.night_w * E) if E else 0.0))
        E += pl
    return pd.DataFrame(rows, columns=["date", "r", "night_used"]).set_index("date")


def stats(r):
    return B.stats(r)


def halves(r):
    return [stats(r[:"2023-12-31"]), stats(r["2024-01-01":]), stats(r)]


def fmt(parts):
    return "  ".join(f"{c*100:5.1f}/{s:4.2f}/{d*100:4.0f}" for c, s, d in parts)


def ep(r, a, b):
    x = r[a:b]
    return float((1 + x).prod() - 1) if len(x) else np.nan


def main():
    s = load_sim()
    p = B.Params(**V7); p.night_cost = "tier"
    C = s.C
    spy, qqq = C["SPY"], C["QQQ"]
    below = lambda px, n: (px < px.rolling(n).mean()).shift(1).fillna(False)
    spy200 = below(spy, 200)
    qqq200 = below(qqq, 200)
    dbl = (spy200 & (spy.rolling(50).mean() < spy.rolling(200).mean()).shift(1).fillna(False))
    cc = lambda px: px.shift(-1) / px - 1
    sh = -cc(spy) - SH_FEE
    sq = cc(C["SQQQ"]) / 3.0            # 1/3 weight of SQQQ ~ -1x QQQ, real decay/fees
    sleeves = {"C3 SH/SPY200": (spy200, sh), "C4 SQQQ/QQQ200": (qqq200, sq),
               "C5 SH/double": (dbl, sh)}

    base = replay_regime(s, p)
    r0 = base["r"]
    unused = (1 - base["night_used"].clip(0, 1)) * p.night_w
    out = {"V7 base": r0}
    out["C1 IBS off SPY<200"] = replay_regime(s, p, ibs_off=spy200)["r"]
    out["C2 night x0.5 SPY<200"] = replay_regime(s, p, night_scale=spy200.map({True: 0.5, False: 1.0}))["r"]

    def sleeve_r(flag, ret, roth=False):
        f = flag.reindex(r0.index).fillna(False).astype(float)
        x = ret.reindex(r0.index).fillna(0.0)
        w = np.minimum(W, unused) if roth else W
        debit = 0.0 if roth else np.maximum(0.0, W - unused)
        return f * (w * x - debit * p.margin_rate / 252)

    for k, (flag, ret) in sleeves.items():
        out[k] = r0 + sleeve_r(flag, ret)
        out[k + " (Roth: idle cash only)"] = r0 + sleeve_r(flag, ret, roth=True)

    # placebo for C3: same number of sleeve days, random
    f3 = sleeves["C3 SH/SPY200"][0].reindex(r0.index).fillna(False)
    n_on = int(f3.sum())
    pl = []
    for seed in range(20):
        rng = np.random.default_rng(seed)
        fr = pd.Series(False, index=r0.index)
        fr.iloc[rng.choice(len(fr), n_on, replace=False)] = True
        pl.append(r0 + sleeve_r(fr, sh))
    out["C6 placebo (random days, mean of 20)"] = pd.concat(pl, axis=1).mean(axis=1)

    # the scenario the hedge is for: the intraday leg (and conviction) dead
    print("\nIF THE INTRADAY LEG DIES (no noise, no conviction), tier costs, Roth-style idle-cash sizing")
    q = B.Params(**{**V7, "noise_on": False, "conviction_w": 0.0}); q.night_cost = "tier"
    bq = replay_regime(s, q)
    rq = bq["r"]; unq = (1 - bq["night_used"].clip(0, 1)) * q.night_w
    def sl(flag, ret):
        f = flag.reindex(rq.index).fillna(False).astype(float)
        return f * np.minimum(W, unq) * ret.reindex(rq.index).fillna(0.0)
    dead = {"no intraday: base": rq}
    for k, (flag, ret) in sleeves.items():
        dead["no intraday: " + k] = rq + sl(flag, ret)
    for k, (flag, ret) in (("C4", sleeves["C4 SQQQ/QQQ200"]),):
        n4 = int(flag.reindex(rq.index).fillna(False).sum()); acc = []
        for seed in range(20):
            rng = np.random.default_rng(seed)
            fr = pd.Series(False, index=rq.index); fr.iloc[rng.choice(len(fr), n4, replace=False)] = True
            acc.append(rq + sl(fr, ret))
        dead["no intraday: C4 placebo (20 seeds)"] = pd.concat(acc, axis=1).mean(axis=1)
    for k, r in dead.items():
        e = [ep(r, *EPISODES[x]) for x in ("2022 bear", "Aug 2024 unwind", "Apr 2025 tariffs")]
        print(f"{k:38} {fmt(halves(r))}   " + "  ".join(f"{v*100:+5.1f}" for v in e))
    # C4 placebo at Roth sizing on the full book
    n4 = int(sleeves["C4 SQQQ/QQQ200"][0].reindex(r0.index).fillna(False).sum()); acc = []
    for seed in range(20):
        rng = np.random.default_rng(seed)
        fr = pd.Series(False, index=r0.index); fr.iloc[rng.choice(len(fr), n4, replace=False)] = True
        acc.append(r0 + sleeve_r(fr, sq, roth=True))
    out["C4 placebo, Roth sizing (20 seeds)"] = pd.concat(acc, axis=1).mean(axis=1)

    print(f"sleeve on-days 2021-26: C3 {f3.mean():.0%}, C4 "
          f"{sleeves['C4 SQQQ/QQQ200'][0].reindex(r0.index).fillna(False).mean():.0%}, "
          f"C5 {sleeves['C5 SH/double'][0].reindex(r0.index).fillna(False).mean():.0%}")
    print("\nBOOK, tier costs (CAGR/Sharpe/maxDD)   2021-23            2024-26            full"
          "              2022    Aug24   Apr25")
    for k, r in out.items():
        e = [ep(r, *EPISODES[x]) for x in ("2022 bear", "Aug 2024 unwind", "Apr 2025 tariffs")]
        print(f"{k:38} {fmt(halves(r))}   " + "  ".join(f"{v*100:+5.1f}" for v in e))

    # standalone sleeves 2016-2026 (unit weight = 0.25 of equity), incl. pre-2021 crashes
    print("\nSLEEVE ALONE at 0.25 of equity, % over the episode (and per-year 2016-23 / 2024-26)")
    idx = C.index[C.index >= "2016-02-01"]
    hdr = ["2018 Q4 selloff", "COVID crash", "COVID rebound", "2022 bear", "Aug 2024 unwind", "Apr 2025 tariffs"]
    print(f"{'':20}" + "".join(f"{h[:14]:>16}" for h in hdr) + "   16-23/yr  24-26/yr")
    for k, (flag, ret) in sleeves.items():
        x = (flag.reindex(idx).fillna(False).astype(float) * W * ret.reindex(idx).fillna(0.0))
        yr = lambda y: float(((1 + y).prod()) ** (252 / max(len(y), 1)) - 1)
        print(f"{k:20}" + "".join(f"{ep(x, *EPISODES[h])*100:+15.1f}%" for h in hdr)
              + f"   {yr(x[:'2023-12-31'])*100:+6.2f}%  {yr(x['2024-01-01':])*100:+6.2f}%")

    # what the flags do to IBS / night per trade in the pick period (2016-23 IBS; 2021-23 night)
    ibs = pd.Series({d: np.mean([r for _, _, r in v]) for d, v in s.I.items() if v})
    ibs = ibs[ibs.index >= "2016-02-01"]
    f = spy200.reindex(ibs.index).fillna(False).values.astype(bool)
    for lab, m in (("2016-23", ibs.index <= "2023-12-31"), ("2024-26", ibs.index >= "2024-01-01")):
        a, b = ibs[m & f], ibs[m & ~f]
        print(f"\nIBS per trade {lab}: SPY<200d {a.mean()*1e4:+.1f}bp (n {len(a)})  "
              f"SPY>200d {b.mean()*1e4:+.1f}bp (n {len(b)})")


if __name__ == "__main__":
    main()
