"""Regime-conditional risk budget BETWEEN legs (candidate addendum 26a).

    PYTHONPATH=. .venv/bin/python -m research.sim.regime_tilt

The intraday leg is the book's crash hedge (+114bp on SPY -3% days) and the
night leg its crash risk (-42bp). Question: on high-risk days, does moving
budget from the overnight legs to the intraday leg raise Sharpe / cut maxDD?
Not portfolio vol targeting (dead, addendum 9): total risk is not scaled, it
is moved between legs.

Why the move has to go through margin: the V7 intraday cap is margin-bound
(2x account, TQQQ at 75%): cap = (1 - 0.5*ibs_w - 0.75*conv_w) / 0.5 = 0.75,
and on regime days the vol-target leverage (median 1.06) still exceeds it.
The night leg is bought at the close and sold at the open, so it uses no
daytime margin; cutting it frees nothing intraday. Only IBS (held through the
day) and the conviction trade free daytime room.

Signals, fixed before running (no parameter was searched):
  R  SPY 20d realised vol above its trailing 252d 80th percentile, closes
     through d-1 (~19% of days, clustered: 2018, 2020, 2022, 2024-26)
  D  SPY return on d-1 <= -2%
Timing: day d's intraday leg and night purchase use the flag known at d's
open (closes through d-1); the IBS position bought at the open of d+1 uses
closes through d. The intraday cap on d follows the IBS weight actually held
that day.

Variants, all pre-registered (every one is reported):
  T1 R: night x0.5                          (cut-only control; cf. add. 18's rejected vol>30% rule)
  T2 R: IBS -> T-bills, intraday cap 0.75 -> 1.25
  T3 R: night x0.5 + IBS -> T-bills, cap 1.25   (the transfer)
  T4 R: T3 + conviction off, cap 2.0            (all daytime room to the noise leg)
  T5 D: T3's action on prior-day SPY <= -2%
  P  placebo: T3's action on random 20-session blocks, regime-day count matched, 20 seeds

Books: 2021-02 -> 2026-09 dollar replay (whole shares, $3k + $1k/21 sessions,
tier and tier_hi night costs) and a 2016-02 -> 2020-12 holdout returns book
(IBS + intraday + conviction; night half in T-bills before 2020, the
bias-corrected daily-bar rebuild in 2020, as in crash.py / growth.py).
"""
from __future__ import annotations

import copy

import numpy as np
import pandas as pd

from . import book as B
from . import growth as G
from .crash import EPISODES
from .validate import load_sim

S2 = {"QQQ": 0.5, "SMH": 0.5}
V7 = dict(tilt="live", noise=S2, weekend_scale=0.5, night_w=0.5, ibs_w=0.5,
          conviction_w=0.5, noise_cap=0.75)
R3X, RSTD = 0.75, 0.5

# action: (night multiplier, ibs multiplier, conviction multiplier) on flagged days
ACTIONS = {
    "T1 R: night x0.5": ("R", (0.5, 1.0, 1.0)),
    "T2 R: IBS->bills, cap 1.25": ("R", (1.0, 0.0, 1.0)),
    "T3 R: night x0.5 + IBS->bills": ("R", (0.5, 0.0, 1.0)),
    "T4 R: T3 + conviction off": ("R", (0.5, 0.0, 0.0)),
    "T5 D: T3 on SPY d-1 <= -2%": ("D", (0.5, 0.0, 1.0)),
}


def cap_for(ibs_w: float, conv_w: float) -> float:
    return min(3.5, max(0.0, (1 - ibs_w * RSTD - conv_w * R3X) / RSTD))


def flags(s) -> dict:
    spy = s.C["SPY"]
    r = spy.pct_change(fill_method=None)
    rv = r.rolling(20).std() * np.sqrt(252)
    hi = rv > rv.rolling(252).quantile(0.8)
    R = hi.shift(1).astype(float).fillna(0).astype(bool)          # known at d's open
    D = (r <= -0.02).shift(1).astype(float).fillna(0).astype(bool)
    return {"R": R, "D": D}


def weights(flag_open: bool, flag_ibs: bool, act) -> tuple[float, float, float, float]:
    """night_w (key d), ibs_w (key d, bought d+1 open), conv_w (day d), cap (day d)."""
    mn, mi, mc = act
    nw = V7["night_w"] * (mn if flag_open else 1.0)
    iw = V7["ibs_w"] * (mi if flag_ibs else 1.0)
    held = V7["ibs_w"] * (mi if flag_open else 1.0)                # IBS held during day d
    cw = V7["conviction_w"] * (mc if flag_open else 1.0)
    return nw, iw, cw, cap_for(held, cw)


# ---------------------------------------------------- 2021-26 dollar replay
def replay(s, F: pd.Series | None, act, cost="tier", start=3000.0, monthly=1000.0) -> pd.Series:
    base = B.Params(**{**V7, "night_cost": cost})
    Fi = None if F is None else F.shift(-1).astype(float).fillna(0).astype(bool)
    E, out = start, {}
    for i, d in enumerate(s.days):
        if i and i % 21 == 0:
            E += monthly
        q = base
        extra = 0.0
        if F is not None:
            fo, fi = bool(F.get(d, False)), bool(Fi.get(d, False))
            if fo or fi:
                nw, iw, cw, cap = weights(fo, fi, act)
                q = copy.copy(base)
                q.night_w, q.ibs_w, q.conviction_w, q.noise_cap = nw, iw, cw, cap
                b = s.bil.get(d, 0.0)                              # the IBS money taken out sits in bills
                extra = (V7["ibs_w"] - iw) * E * (float(b) if np.isfinite(b) else 0.0)
        pl, _ = s.day_pnl(E, d, q)
        pl += extra
        out[d] = pl / E if E else 0.0
        E += pl
    return pd.Series(out)


# ------------------------------------------------ 2016-20 holdout returns book
def holdout_legs(s):
    night20, ibs, bil, nz, bo = G.covid_legs(s, caps=(0.10,))
    n = night20[0.10]
    n = n[n.index < "2020-11-05"]
    return n, ibs, bil, nz, bo


def holdout(s, legs, F: pd.Series | None, act, a="2016-02-01", b="2020-12-31") -> pd.Series:
    night, ibs, bil, nz, bo = legs
    days = s.C.index[(s.C.index >= a) & (s.C.index <= b)]
    Fi = None if F is None else F.shift(-1).astype(float).fillna(0).astype(bool)
    out = {}
    for d in days:
        fo = bool(F.get(d, False)) if F is not None else False
        fi = bool(Fi.get(d, False)) if F is not None else False
        nw, iw, cw, cap = weights(fo, fi, act) if (fo or fi) else (
            V7["night_w"], V7["ibs_w"], V7["conviction_w"], V7["noise_cap"])
        bl = float(np.nan_to_num(bil.get(d, 0.0)))
        nv = night.get(d, np.nan)
        x = nw * float(nv) if np.isfinite(nv) else V7["night_w"] * bl * (d < pd.Timestamp("2020-01-02"))
        iv = ibs.get(d, np.nan)
        x += iw * (float(iv) if np.isfinite(iv) else bl) + (V7["ibs_w"] - iw) * bl
        for sym, share in S2.items():
            z = nz[sym]
            if d in z.index:
                x += min(float(z.at[d, "lev"]), cap) * share * float(z.at[d, "ret"])
        x += cw * float(bo.get(d, 0.0))
        out[d] = x
    return pd.Series(out)


# ----------------------------------------------------------------- helpers
def block_flags(F: pd.Series, idx, seed: int, block: int = 20) -> pd.Series:
    n = int(F.reindex(idx).fillna(False).sum())
    rng = np.random.default_rng(seed)
    f = pd.Series(False, index=idx)
    while f.sum() < n:
        i = rng.integers(0, len(idx) - block)
        f.iloc[i:i + block] = True
    return f


def tstat(d: pd.Series, lag: int = 5) -> float:
    """Newey-West t of the mean daily difference (a day is the cluster; lag for regime runs)."""
    x = d.fillna(0).values
    n = len(x); m = x.mean(); e = x - m
    g = [np.dot(e[k:], e[:n - k]) / n for k in range(lag + 1)]
    v = g[0] + 2 * sum((1 - k / (lag + 1)) * g[k] for k in range(1, lag + 1))
    return float(m / np.sqrt(v / n)) if v > 0 else float("nan")


def fmt(r: pd.Series) -> str:
    c, s_, d = B.stats(r)
    return f"{c*100:5.1f}/{s_:4.2f}/{d*100:4.0f}"


def ep(r: pd.Series, name: str) -> float:
    a, b = EPISODES[name]
    x = r[a:b]
    return float((1 + x).prod() - 1) * 100 if len(x) else np.nan


def main():
    s = load_sim()
    s.N = B.night_days(max_corr=0.7, max_name_pct=0.10)
    Fs = flags(s)
    legs = holdout_legs(s)
    for k, F in Fs.items():
        print(f"flag {k}: 2016-20 {F['2016-02-01':'2020-12-31'].mean():.0%} of days, "
              f"2021-23 {F['2021-02-01':'2023-12-31'].mean():.0%}, 2024-26 {F['2024-01-01':].mean():.0%}")

    books = {"V7 (shipped, cap 0.75)": (None, None)}
    books.update({k: (Fs[f], a) for k, (f, a) in ACTIONS.items()})
    res = {}
    for lab, (F, act) in books.items():
        res[lab] = dict(tier=replay(s, F, act, "tier"), hi=replay(s, F, act, "tier_hi"),
                        ho=holdout(s, legs, F, act))

    # placebo: T3's action on random 20-session blocks
    act3 = ACTIONS["T3 R: night x0.5 + IBS->bills"][1]
    R = Fs["R"]
    pl = []
    for seed in range(20):
        fr = block_flags(R, s.days, seed)
        fh = block_flags(R, s.C.index[(s.C.index >= "2016-02-01") & (s.C.index <= "2020-12-31")], seed)
        pl.append(dict(tier=replay(s, fr, act3, "tier"), ho=holdout(s, legs, fh, act3)))

    v7 = res["V7 (shipped, cap 0.75)"]
    hdr = (f"{'':34s} {'2021-23':>13s} {'2024-26':>13s} {'2021-26 tier':>13s} {'tier_hi':>13s} "
           f"{'2016-20 ho':>13s}   dSh 21-23/24-26/ho   t(diff) 21-26/ho")
    print("\nCAGR / Sharpe / maxDD (time-weighted)\n" + hdr)
    for lab, r in res.items():
        t = r["tier"]
        dsh = [B.stats(t[:"2023-12-31"])[1] - B.stats(v7["tier"][:"2023-12-31"])[1],
               B.stats(t["2024-01-01":])[1] - B.stats(v7["tier"]["2024-01-01":])[1],
               B.stats(r["ho"])[1] - B.stats(v7["ho"])[1]]
        tt = (tstat(t - v7["tier"]), tstat(r["ho"] - v7["ho"]))
        print(f"{lab:34s} {fmt(t[:'2023-12-31']):>13s} {fmt(t['2024-01-01':]):>13s} {fmt(t):>13s} "
              f"{fmt(r['hi']):>13s} {fmt(r['ho']):>13s}   {dsh[0]:+.2f}/{dsh[1]:+.2f}/{dsh[2]:+.2f}"
              f"   {tt[0]:+.2f} / {tt[1]:+.2f}")

    # placebo distribution of Sharpe change
    psh = np.array([[B.stats(p["tier"][:"2023-12-31"])[1] - B.stats(v7["tier"][:"2023-12-31"])[1],
                     B.stats(p["tier"]["2024-01-01":])[1] - B.stats(v7["tier"]["2024-01-01":])[1],
                     B.stats(p["ho"])[1] - B.stats(v7["ho"])[1],
                     B.stats(p["tier"])[2] - B.stats(v7["tier"])[2]] for p in pl])
    t3 = res["T3 R: night x0.5 + IBS->bills"]
    real = [B.stats(t3["tier"][:"2023-12-31"])[1] - B.stats(v7["tier"][:"2023-12-31"])[1],
            B.stats(t3["tier"]["2024-01-01":])[1] - B.stats(v7["tier"]["2024-01-01":])[1],
            B.stats(t3["ho"])[1] - B.stats(v7["ho"])[1],
            B.stats(t3["tier"])[2] - B.stats(v7["tier"])[2]]
    print("\nplacebo (T3 action on random 20-session blocks, 20 seeds): Sharpe change vs V7")
    for j, name in enumerate(("2021-23", "2024-26", "2016-20 holdout", "maxDD 2021-26 (pp)")):
        sc = 100 if j == 3 else 1
        print(f"  {name:20s} T3 {real[j]*sc:+.2f}   placebo mean {psh[:, j].mean()*sc:+.2f}  "
              f"p90 {np.percentile(psh[:, j], 90)*sc:+.2f}  T3 beats {int((real[j] > psh[:, j]).sum())}/20")

    print("\nepisodes (% over the window; 2018 and COVID from the holdout book)")
    names = ["2018 Q4 selloff", "COVID crash", "COVID rebound", "2022 bear", "Aug 2024 unwind", "Apr 2025 tariffs"]
    print(f"{'':34s}" + "".join(f"{n[:15]:>17s}" for n in names))
    for lab, r in res.items():
        full = pd.concat([r["ho"], r["tier"]]).sort_index()
        full = full[~full.index.duplicated()]
        print(f"{lab:34s}" + "".join(f"{ep(full, n):+16.1f}%" for n in names))

    # where the difference comes from: the legs on regime days
    print("\nV7 legs on R days vs other days, 2021-26 (mean bp of equity per day)")
    s.N = B.night_days(max_corr=0.7, max_name_pct=0.10)
    df = s.replay(B.Params(**{**V7, "night_cost": "tier"}))
    f = R.reindex(df.index).fillna(False).astype(bool)
    for c in ("r_night", "r_ibs", "r_noise", "r"):
        a, b = df[c][f], df[c][~f]
        print(f"  {c:8s} R {a.mean()*1e4:+6.1f}bp (sd {a.std()*1e4:5.0f})   other {b.mean()*1e4:+6.1f}bp "
              f"(sd {b.std()*1e4:5.0f})")


if __name__ == "__main__":
    main()
