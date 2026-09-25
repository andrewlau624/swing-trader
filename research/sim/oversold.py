"""Multi-day oversold trigger for the IBS leg's idle money (candidate addendum 27).

    PYTHONPATH=. .venv/bin/python -m research.sim.oversold

Lead (pattern scan, 2026-09-25): after 3 down closes in a row, or RSI(2) < 10,
SPY/QQQ earn +30..60bp the next day in 2021-26, also on days the IBS leg is
not in. The IBS leg deploys its whole half only on days it has a pick; the
rest of the time that half sits in T-bills. Question: put that idle half into
SPY/QQQ when they are multi-day oversold?

Timing is the IBS leg's (book.ibs_days): signal on day d's close, bought at the
open of d+1, re-evaluated the next morning. Key d carries open d+1 -> open d+2.
No lookahead: RSI(2) and the down-streak use closes through d.

Sizing: ONLY the idle IBS money (ibs_w x equity minus what the IBS picks use),
split equally over triggered names the IBS leg does not already hold, whole
shares. Overnight gross cannot rise above V7's (the money was in T-bills), and
daytime margin is unchanged (the intraday cap already assumes a fully used IBS half).

Variants, fixed before running (all reported):
  V1 SPY+QQQ  3 down closes            exit next open
  V2 SPY+QQQ  RSI(2) < 10              exit next open
  V3 SPY+QQQ  either                   exit next open
  V4 SPY+QQQ  either                   hold while trigger or IBS < 0.2, max 5 sessions
  V5 IBS momentum top-3 of 18  either  exit next open
  V6 SPY+QQQ  either, 15:40 signal, bought at the close auction, sold at the
     next open (the night leg's timing), idle IBS money only. ADDED AFTER V1-V5
     ran: they missed the edge, which sits overnight (close -> open). Post-hoc,
     so its placebo and holdout carry the weight.
Costs: 1bp/side (tier; the IBS leg's), 3bp/side (tier_hi). Placebo: the best
variant's entry days reshuffled at random within each symbol (same count),
50 seeds. Holdout 2016-02 -> 2020-12 through regime_tilt's returns book.
"""
from __future__ import annotations

import pickle

import numpy as np
import pandas as pd

from . import book as B
from .crash import EPISODES
from .regime_tilt import V7, holdout_legs, tstat
from .validate import load_sim

SCRATCH = "/private/tmp/claude-501/-Users-andrewlau-Documents-Code-Projects-swing-trader/cc100773-e955-4a4c-aa47-797c4a8c7acb/scratchpad"
S2 = {"QQQ": 0.5, "SMH": 0.5}
COST = {"tier": 1.0, "tier_hi": 3.0}
VARIANTS = {
    "V1 SPY+QQQ 3-down, next": dict(uni="idx", trig="down3", hold=False),
    "V2 SPY+QQQ RSI2<10, next": dict(uni="idx", trig="rsi2", hold=False),
    "V3 SPY+QQQ either, next": dict(uni="idx", trig="either", hold=False),
    "V4 SPY+QQQ either, hold<=5": dict(uni="idx", trig="either", hold=True),
    "V5 top-3 momentum, either": dict(uni="mom", trig="either", hold=False),
}


# ------------------------------------------------------------ signals
def triggers(C: pd.DataFrame) -> dict[str, pd.DataFrame]:
    r = C.pct_change(fill_method=None)
    down3 = (r < 0) & (r.shift(1) < 0) & (r.shift(2) < 0)
    d = C.diff()
    up = d.clip(lower=0).ewm(alpha=0.5, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=0.5, adjust=False).mean()
    rsi2 = 100 - 100 / (1 + up / dn)
    return {"down3": down3, "rsi2": rsi2 < 10, "either": down3 | (rsi2 < 10)}


def mom_universe(s) -> dict:
    """day d -> the IBS leg's momentum top-3 for the session after d (as ibs_days)."""
    from swingtrader.daily import signals as sg
    C = s.C[B.EQ18]
    days = C.index
    out, cache = {}, {}
    for j in range(260, len(days) - 1):
        today = days[j + 1]
        m = today.to_period("M")
        if m not in cache:
            cache[m] = sg.momentum_top(C[C.index < today], today, 3)
        out[days[j]] = list(cache[m])
    return out


def schedule(s, v: dict, ibs: pd.DataFrame, mom: dict, trig: dict) -> dict:
    """key d -> {sym: (open d+1, open d+1 -> open d+2)} for held names (all days, IBS-idle or not)."""
    T = trig[v["trig"]]
    O = s.O
    days = s.C.index
    held: dict = {}
    prev: dict[str, int] = {}                       # sym -> sessions held so far
    for j in range(260, len(days) - 2):
        d = days[j]
        uni = ["SPY", "QQQ"] if v["uni"] == "idx" else mom.get(d, [])
        cur = {}
        for sym in uni:
            fire = bool(T.at[d, sym]) if sym in T.columns and d in T.index else False
            keep = (v["hold"] and sym in prev and prev[sym] < 5
                    and (fire or (np.isfinite(ibs.at[d, sym]) and ibs.at[d, sym] < 0.2)))
            if fire or keep:
                o1, o2 = O.at[days[j + 1], sym], O.at[days[j + 2], sym]
                if np.isfinite(o1) and np.isfinite(o2):
                    cur[sym] = (o1, o2 / o1 - 1)
        prev = {k: prev.get(k, 0) + 1 for k in cur}
        if cur:
            held[d] = cur
    return held


def sides(held: dict, days) -> dict:
    """(key d, sym) -> sides paid: entry if not held at d-1, exit if not held at d+1."""
    ix = {d: i for i, d in enumerate(days)}
    out = {}
    for d, cur in held.items():
        i = ix[d]
        pd_, nd = days[i - 1], days[i + 1] if i + 1 < len(days) else None
        for sym in cur:
            out[(d, sym)] = int(sym not in held.get(pd_, {})) + int(nd is None or sym not in held.get(nd, {}))
    return out


def unit_leg(held: dict, sd: dict, cost: float, bil: pd.Series, idx) -> pd.Series:
    """Standalone: the leg's money equally over held names, T-bills otherwise."""
    out = {}
    for d in idx:
        cur = held.get(d)
        if cur:
            out[d] = float(np.mean([r - sd[(d, sym)] * cost / 1e4 for sym, (_, r) in cur.items()]))
        else:
            b = bil.get(d, 0.0); out[d] = float(b) if np.isfinite(b) else 0.0
    return pd.Series(out)


def trades(held: dict, sd: dict, cost: float, a, b) -> np.ndarray:
    """Per-position-day net returns in [a, b] (for bp/trade and t)."""
    return np.array([r - sd[(d, sym)] * cost / 1e4 for d, cur in held.items() if a <= d <= b
                     for sym, (_, r) in cur.items()])


# ------------------------------------------------------ 2021-26 book
def replay(s, held: dict | None, sd: dict | None, cost_model="tier", start=3000.0,
           monthly=1000.0) -> pd.DataFrame:
    base = B.Params(**{**V7, "night_cost": cost_model})
    c = COST[cost_model]
    E, rows, gross = start, [], 0.0
    for i, d in enumerate(s.days):
        if i and i % 21 == 0:
            E += monthly
        pl, info = s.day_pnl(E, d, base)
        extra, tv = 0.0, 0.0
        cur = (held or {}).get(d)
        if cur:
            ibs_syms = {x[0] for x in s.I.get(d, [])}
            names = [k for k in cur if k not in ibs_syms]
            idle = V7["ibs_w"] * E - info["ibs_v"]
            if names and idle > 0:
                b = s.bil.get(d, 0.0); b = float(b) if np.isfinite(b) else 0.0
                per = idle / len(names)
                for sym in names:
                    o1, r = cur[sym]
                    sh = np.floor(per / o1)
                    v = sh * o1
                    tv += v
                    extra += v * (r - sd[(d, sym)] * c / 1e4) - v * b    # replaces T-bills
        pl += extra
        gross = max(gross, (info["night_v"] + info["ibs_v"] + tv) / E)
        rows.append((d, pl / E, info["night"] / E, info["ibs"] / E, info["noise"] / E, extra / E, tv / E))
        E += pl
    df = pd.DataFrame(rows, columns=["date", "r", "r_night", "r_ibs", "r_noise", "r_trig", "trig_v"]).set_index("date")
    df.attrs["max_gross"] = gross
    return df


def eh(df: pd.DataFrame) -> pd.Series:
    """Edge-halves: half of every leg's mean daily contribution (trigger included) removed."""
    return df.r - 0.5 * (df.r_night.mean() + df.r_ibs.mean() + df.r_noise.mean() + df.r_trig.mean())


# ------------------------------------------------ 2016-20 holdout book
def holdout(s, legs, held: dict | None, sd: dict | None, a="2016-02-01", b="2020-12-31") -> pd.Series:
    night, ibs, bil, nz, bo = legs
    days = s.C.index[(s.C.index >= a) & (s.C.index <= b)]
    out = {}
    for d in days:
        bl = float(np.nan_to_num(bil.get(d, 0.0)))
        nv = night.get(d, np.nan)
        x = V7["night_w"] * float(nv) if np.isfinite(nv) else V7["night_w"] * bl * (d < pd.Timestamp("2020-01-02"))
        iv = ibs.get(d, np.nan)
        if np.isfinite(iv):
            x += V7["ibs_w"] * float(iv)
        else:
            cur = (held or {}).get(d)
            if cur:
                x += V7["ibs_w"] * float(np.mean([r - sd[(d, k)] * COST["tier"] / 1e4 for k, (_, r) in cur.items()]))
            else:
                x += V7["ibs_w"] * bl
        for sym, share in S2.items():
            z = nz[sym]
            if d in z.index:
                x += min(float(z.at[d, "lev"]), V7["noise_cap"]) * share * float(z.at[d, "ret"])
        x += V7["conviction_w"] * float(bo.get(d, 0.0))
        out[d] = x
    return pd.Series(out)


# ----------------------------------------------------------- helpers
def fmt(r: pd.Series) -> str:
    c, s_, d = B.stats(r)
    return f"{c*100:5.1f}/{s_:4.2f}/{d*100:4.0f}"


def ep(r: pd.Series, name: str) -> float:
    a, b = EPISODES[name]
    x = r[a:b]
    return float((1 + x).prod() - 1) * 100 if len(x) else np.nan


def placebo(s, held: dict, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    days = [d for d in s.C.index[260:-2]]
    O = s.O
    ix = {d: i for i, d in enumerate(s.C.index)}
    by: dict[str, int] = {}
    for d, cur in held.items():
        for sym in cur:
            by[sym] = by.get(sym, 0) + 1
    out: dict = {}
    for sym, n in by.items():
        for d in rng.choice(days, size=n, replace=False):
            i = ix[d]
            o1, o2 = O.iloc[i + 1][sym], O.iloc[i + 2][sym]
            if np.isfinite(o1) and np.isfinite(o2):
                out.setdefault(d, {})[sym] = (o1, o2 / o1 - 1)
    return out


# ----------------------------------------------- V6: overnight, 15:40 signal
def honest_1540(s) -> dict[str, pd.Series]:
    """'either' trigger evaluated at 15:40 with the 15:40 price as today's close."""
    out = {}
    for sym in ("SPY", "QQQ"):
        m = B.D.minutes(sym)["close"]
        p = m.iloc[:, 369].reindex(s.C.index)               # bar ending 15:40
        c = s.C[sym]
        chg_prev = c.diff()
        up = chg_prev.clip(lower=0).ewm(alpha=0.5, adjust=False).mean().shift(1)
        dn = (-chg_prev.clip(upper=0)).ewm(alpha=0.5, adjust=False).mean().shift(1)
        chg = p - c.shift(1)
        up_t = 0.5 * up + 0.5 * chg.clip(lower=0)
        dn_t = 0.5 * dn + 0.5 * (-chg).clip(lower=0)
        rsi = 100 - 100 / (1 + up_t / dn_t)
        down3 = (p < c.shift(1)) & (c.shift(1) < c.shift(2)) & (c.shift(2) < c.shift(3))
        out[sym] = (down3 | (rsi < 10)).fillna(False)
    return out


def schedule_ovn(s, sig: dict) -> dict:
    """key d -> {sym: (close d, close d -> open d+1)}."""
    on = s.O.shift(-1) / s.C - 1
    held = {}
    for d in s.C.index[260:-1]:
        cur = {k: (s.C.at[d, k], on.at[d, k]) for k in sig if bool(sig[k].get(d, False))
               and np.isfinite(on.at[d, k])}
        if cur:
            held[d] = cur
    return held


def placebo_ovn(s, held: dict, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    on = s.O.shift(-1) / s.C - 1
    days = list(s.C.index[260:-1])
    by: dict[str, int] = {}
    for cur in held.values():
        for k in cur:
            by[k] = by.get(k, 0) + 1
    out: dict = {}
    for k, n in by.items():
        for d in rng.choice(days, size=n, replace=False):
            if np.isfinite(on.at[d, k]):
                out.setdefault(d, {})[k] = (s.C.at[d, k], on.at[d, k])
    return out


def replay_ovn(s, held: dict, cost_model="tier", start=3000.0, monthly=1000.0) -> pd.DataFrame:
    """V7 plus the overnight trigger, bought only when the IBS leg holds nothing
    overnight (no key d-1 position), so the money is idle T-bill money."""
    base = B.Params(**{**V7, "night_cost": cost_model})
    c = COST[cost_model]
    E, rows, gross, prev = start, [], 0.0, None
    for i, d in enumerate(s.days):
        if i and i % 21 == 0:
            E += monthly
        pl, info = s.day_pnl(E, d, base)
        extra, tv = 0.0, 0.0
        cur = held.get(d)
        if cur and not s.I.get(prev):
            b = s.bil.get(d, 0.0); b = float(b) if np.isfinite(b) else 0.0
            per = V7["ibs_w"] * E / len(cur)
            for k, (px, r) in cur.items():
                v = np.floor(per / px) * px
                tv += v
                extra += v * (r - 2 * c / 1e4) - v * b
        pl += extra
        gross = max(gross, (info["night_v"] + tv) / E + (V7["ibs_w"] if s.I.get(prev) else 0.0))
        rows.append((d, pl / E, info["night"] / E, info["ibs"] / E, info["noise"] / E, extra / E, tv / E))
        E += pl
        prev = d
    df = pd.DataFrame(rows, columns=["date", "r", "r_night", "r_ibs", "r_noise", "r_trig", "trig_v"]).set_index("date")
    df.attrs["max_gross"] = gross
    return df


def holdout_ovn(s, legs, held: dict, a="2016-02-01", b="2020-12-31") -> pd.Series:
    base = holdout(s, legs, None, None, a, b)
    ibs = legs[1]
    ix = list(s.C.index)
    pos = {d: i for i, d in enumerate(ix)}
    x = base.copy()
    for d in base.index:
        cur = held.get(d)
        prev = ix[pos[d] - 1]
        if cur and not np.isfinite(ibs.get(prev, np.nan)):
            bl = float(np.nan_to_num(legs[2].get(d, 0.0)))
            x[d] += V7["ibs_w"] * (float(np.mean([r for _, r in cur.values()])) - 2 * COST["tier"] / 1e4 - bl)
    return x


def main_v6(s, legs, base, base_ho, P3):
    sig = honest_1540(s)
    held = schedule_ovn(s, sig)
    close_sig = {k: triggers(s.C)["either"][k] for k in ("SPY", "QQQ")}
    agree = np.mean([bool(sig[k].get(d, False)) == bool(close_sig[k].get(d, False))
                     for k in sig for d in s.C.index[300:]])
    print(f"\n== V6 (post-hoc): either-trigger at 15:40, close auction -> next open. "
          f"15:40 signal agrees with the close signal on {agree:.1%} of symbol-days")
    on = s.O.shift(-1) / s.C - 1
    for lab, a, b in P3:
        for k in ("SPY", "QQQ"):
            x = np.array([cur[k][1] for d, cur in held.items() if a <= d <= b and k in cur]) - 2e-4
            print(f"   {lab} {k}: {x.mean()*1e4:+6.1f}bp/night net of 1bp/side, t {x.mean()/(x.std(ddof=1)/np.sqrt(len(x))):+.2f}, n {len(x)}"
                  f"   (every night, same symbol: {on[k][a:b].mean()*1e4 - 2:+.1f}bp)")
    bk = {c: replay_ovn(s, held, c) for c in COST}
    ho = holdout_ovn(s, legs, held)
    t, b0 = bk["tier"].r, base["tier"].r
    dsh = [B.stats(t[:"2023-12-31"])[1] - B.stats(b0[:"2023-12-31"])[1],
           B.stats(t["2024-01-01":])[1] - B.stats(b0["2024-01-01":])[1],
           B.stats(ho)[1] - B.stats(base_ho)[1]]
    print(f"{'V6 book':30s} {fmt(t[:'2023-12-31']):>13s} {fmt(t['2024-01-01':]):>13s} {fmt(t):>13s} "
          f"{fmt(bk['tier_hi'].r):>13s} {fmt(eh(bk['tier_hi'])):>13s} {fmt(ho):>13s}  "
          f"{dsh[0]:+.2f}/{dsh[1]:+.2f}/{dsh[2]:+.2f}   {tstat(t - b0, 1):+.2f}/{tstat(ho - base_ho, 1):+.2f}   "
          f"{bk['tier']['trig_v'].max() + 0:.2f} trig, gross {bk['tier'].attrs['max_gross']:.2f}x")
    ps = []
    for seed in range(50):
        ph = placebo_ovn(s, held, seed)
        pb, phh = replay_ovn(s, ph, "tier"), holdout_ovn(s, legs, ph)
        ps.append([B.stats(pb.r[:"2023-12-31"])[1] - B.stats(b0[:"2023-12-31"])[1],
                   B.stats(pb.r["2024-01-01":])[1] - B.stats(b0["2024-01-01":])[1],
                   B.stats(phh)[1] - B.stats(base_ho)[1]])
    ps = np.array(ps)
    print("   placebo (same nights per symbol, random dates, 50 seeds): " + "   ".join(
        f"{lab} real {dsh[j]:+.2f} placebo {ps[:, j].mean():+.2f} beats {int((dsh[j] > ps[:, j]).sum())}/50"
        for j, lab in enumerate(("21-23", "24-26", "ho"))))
    names = ["2018 Q4 selloff", "COVID crash", "COVID rebound", "2022 bear", "Aug 2024 unwind", "Apr 2025 tariffs"]
    full = pd.concat([ho, t]).sort_index(); full = full[~full.index.duplicated()]
    print("   episodes: " + "  ".join(f"{n} {ep(full, n):+.1f}%" for n in names))
    df = bk["tier"]; onf = df.trig_v > 0
    print(f"   deployed on {onf.mean():.0%} of sessions, avg {df.trig_v[onf].mean():.2f} of equity, "
          f"adds {df.r_trig.mean()*252*100:+.1f}pp/yr (simple, vs T-bills); tier_hi adds "
          f"{bk['tier_hi'].r_trig.mean()*252*100:+.1f}pp/yr")
    yr = lambda r: (1 + r).groupby(r.index.year).prod() - 1
    print("   calendar years V7 -> V6: " + "  ".join(f"{y}: {a*100:+.0f}->{b*100:+.0f}%"
                                                    for y, a, b in zip(yr(b0).index, yr(b0), yr(t))))
    return held, bk, ho, dsh


def main():
    s = load_sim()
    s.N = B.night_days(max_corr=0.7, max_name_pct=0.10)
    P = s.C
    H, L = (B.D.etf()[k] for k in ("high", "low"))
    ibs = (P - L) / (H - L)
    trig = triggers(P)
    mom = mom_universe(s)
    legs = holdout_legs(s)
    days = s.C.index

    base = {c: replay(s, None, None, c) for c in COST}
    base_ho = holdout(s, legs, None, None)
    print(f"V7 baseline: tier {fmt(base['tier'].r)}  tier_hi {fmt(base['tier_hi'].r)}  "
          f"holdout {fmt(base_ho)}  (IBS leg idle on {100 - 100 * len([d for d in s.days if s.I.get(d)]) / len(s.days):.0f}% of 2021-26 sessions)")

    P3 = [("2016-20", pd.Timestamp("2016-02-01"), pd.Timestamp("2020-12-31")),
          ("2021-23", pd.Timestamp("2021-02-01"), pd.Timestamp("2023-12-31")),
          ("2024-26", pd.Timestamp("2024-01-01"), pd.Timestamp("2026-09-18"))]

    print("\n== standalone leg (all trigger days, IBS-held or not), tier 1bp/side: bp per position-day, NW t, n")
    res, H_, SD = {}, {}, {}
    for name, v in VARIANTS.items():
        held = schedule(s, v, ibs, mom, trig)
        sd = sides(held, days)
        H_[name], SD[name] = held, sd
        cells = []
        for lab, a, b in P3:
            x = trades(held, sd, COST["tier"], a, b)
            u = unit_leg(held, sd, COST["tier"], s.bil, days[(days >= a) & (days <= b)])
            cells.append(f"{x.mean()*1e4:+6.1f}bp t{tstat(u - s.bil.reindex(u.index).fillna(0), 1):+4.1f} "
                         f"n{len(x):4d} | {fmt(u)}")
        print(f"{name:30s} " + "   ".join(cells))

    print("\n== V7 + trigger in the idle IBS half (dollar replay 2021-26; holdout returns book)")
    hdr = (f"{'':30s} {'2021-23':>13s} {'2024-26':>13s} {'2021-26':>13s} {'tier_hi':>13s} "
           f"{'EH tier_hi':>13s} {'2016-20 ho':>13s}  dSh 21-23/24-26/ho  t(diff) 21-26/ho  max gross")
    print(hdr)
    rows = {"V7 shipped": (base, base_ho)}
    for name in VARIANTS:
        rows[name] = ({c: replay(s, H_[name], SD[name], c) for c in COST},
                      holdout(s, legs, H_[name], SD[name]))
    for name, (bk, ho) in rows.items():
        t = bk["tier"].r
        b0 = base["tier"].r
        dsh = [B.stats(t[:"2023-12-31"])[1] - B.stats(b0[:"2023-12-31"])[1],
               B.stats(t["2024-01-01":])[1] - B.stats(b0["2024-01-01":])[1],
               B.stats(ho)[1] - B.stats(base_ho)[1]]
        tt = (tstat(t - b0, 1), tstat(ho - base_ho, 1))
        res[name] = dict(dsh=dsh, t=tt, bk=bk, ho=ho)
        print(f"{name:30s} {fmt(t[:'2023-12-31']):>13s} {fmt(t['2024-01-01':]):>13s} {fmt(t):>13s} "
              f"{fmt(bk['tier_hi'].r):>13s} {fmt(eh(bk['tier_hi'])):>13s} {fmt(ho):>13s}  "
              f"{dsh[0]:+.2f}/{dsh[1]:+.2f}/{dsh[2]:+.2f}   {tt[0]:+.2f}/{tt[1]:+.2f}   "
              f"{bk['tier'].attrs['max_gross']:.2f}x")

    # fit on one half, judge on the other (selection by Sharpe change in the fit half)
    cand = list(VARIANTS)
    fit_a = max(cand, key=lambda k: res[k]["dsh"][0])
    fit_b = max(cand, key=lambda k: res[k]["dsh"][1])
    print(f"\nfit 2021-23 -> pick {fit_a}: judge 2024-26 dSh {res[fit_a]['dsh'][1]:+.2f}, holdout {res[fit_a]['dsh'][2]:+.2f}")
    print(f"fit 2024-26 -> pick {fit_b}: judge 2021-23 dSh {res[fit_b]['dsh'][0]:+.2f}, holdout {res[fit_b]['dsh'][2]:+.2f}")

    # placebo for every variant: same count per symbol, random days, 50 seeds
    print("\n== placebo (entry days shuffled per symbol, 50 seeds): Sharpe change vs V7")
    for name in VARIANTS:
        ps = []
        for seed in range(50):
            ph = placebo(s, H_[name], seed)
            psd = sides(ph, days)
            bk = replay(s, ph, psd, "tier")
            ho = holdout(s, legs, ph, psd)
            ps.append([B.stats(bk.r[:"2023-12-31"])[1] - B.stats(base["tier"].r[:"2023-12-31"])[1],
                       B.stats(bk.r["2024-01-01":])[1] - B.stats(base["tier"].r["2024-01-01":])[1],
                       B.stats(ho)[1] - B.stats(base_ho)[1]])
        ps = np.array(ps)
        real = res[name]["dsh"]
        print(f"{name:30s} " + "   ".join(
            f"{lab} real {real[j]:+.2f} placebo {ps[:, j].mean():+.2f} beats {int((real[j] > ps[:, j]).sum())}/50"
            for j, lab in enumerate(("21-23", "24-26", "ho"))))

    print("\n== episodes (%): 2018/COVID from the holdout book, the rest from the 2021-26 replay")
    names = ["2018 Q4 selloff", "COVID crash", "COVID rebound", "2022 bear", "Aug 2024 unwind", "Apr 2025 tariffs"]
    print(f"{'':30s}" + "".join(f"{n[:15]:>17s}" for n in names))
    for name, (bk, ho) in rows.items():
        full = pd.concat([ho, bk["tier"].r]).sort_index()
        full = full[~full.index.duplicated()]
        print(f"{name:30s}" + "".join(f"{ep(full, n):+16.1f}%" for n in names))

    # usage: how often the trigger actually deploys the idle half
    print("\n== usage in the book (2021-26, tier)")
    for name in VARIANTS:
        df = rows[name][0]["tier"]
        on = df.trig_v > 0
        print(f"{name:30s} deployed on {on.mean():.0%} of sessions, avg {df.trig_v[on].mean():.2f} of equity when on, "
              f"adds {df.r_trig.mean()*252*100:+.1f}pp/yr (simple, vs T-bills)")

    held6, bk6, ho6, dsh6 = main_v6(s, legs, base, base_ho, P3)
    # V6 is the only variant whose placebo passes in both judged halves; save it as the candidate
    if sum(dsh6) >= max(sum(res[k]["dsh"]) for k in cand):
        best, bk = "V6 overnight either (15:40)", bk6["tier"]
        on = s.O.shift(-1) / s.C - 1
        idx = days[days >= "2016-02-01"]
        unit = pd.Series({d: (float(np.mean([r for _, r in held6[d].values()])) - 2e-4) if d in held6
                          else float(np.nan_to_num(s.bil.get(d, 0.0))) for d in idx})
    else:
        best = max(cand, key=lambda k: min(res[k]["dsh"]))
        bk = rows[best][0]["tier"]
        unit = unit_leg(H_[best], SD[best], COST["tier"], s.bil, days[days >= "2016-02-01"])
    with open(f"{SCRATCH}/r1_series.pkl", "wb") as fh:
        pickle.dump({"v7": base["tier"].r, "v7_plus": bk.r, "leg_unit": unit, "variant": best}, fh)
    print(f"\nsaved {best} series to {SCRATCH}/r1_series.pkl")


if __name__ == "__main__":
    main()
