"""Study AL (Round 17): the idle Roth — what the limited-margin delay costs and whether a
cash-IRA book clears the bar.

    PYTHONPATH=. .venv/bin/python -m research.sim.roth_cash

Pre-registration: research/drafts/round1_prose.md, "Round 17", Study AL (committed before any
number below). Nothing in this module is live code.

A plain cash IRA cannot borrow, short, or use unsettled proceeds for an intraday round trip.
The shipped Roth IBS leg (buy open d+1, sell open d+2) and night leg (buy close d, sell open
d+1) each sell on the funding sale's T+1 settlement date, so they are good-faith-violation
safe (add. 38 Q4); the 3x-ETF intraday leg is the only one that needs limited margin. The
cash-IRA book is therefore IBS + night, no intraday leg. Two readings of same-day reuse:
  lenient  = 0.5 IBS + 0.5 night (allowed, add. 38 Q4)
  strict   = 0.25 + 0.25 (each overnight dollar works every other night)
The limited-margin reference is roth_opt's M3 (live 15:40 SGOV + greedy night skip) and M2L.

Whole shares + the real-money 1-share night probe ($150) are modelled; deposits are the
guaranteed $7,500/yr ($625 every 21 sessions). Returns are time-weighted daily returns on the
capital actually in the account that day.
"""
from __future__ import annotations

import pathlib
import time

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import book as B
from . import roth_opt as RO
from .validate import load_sim

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/roth_cash_out.txt"
PROBE_USD = 150.0
HALVES = (("2021-23", "2021-01-01", "2023-12-31"),
          ("2024-26", "2024-01-01", "2026-12-31"),
          ("full", None, None))
SIZES = (1000.0, 3000.0, 7800.0)


# ------------------------------------------------------------------ the cash-IRA day
def cash_day(s, N, E, d, prev_ibs_v, w_n, w_i, probe, cost, ibs_on=True, night_on=True):
    """One day of the cash Roth: IBS bought at the open (key d), night bought at the close.
    Whole shares; the night leg carries the live 1-share probe and a book-cash floor. The
    IBS half not invested parks in BIL (whole shares, only when >= $50)."""
    pnl = 0.0
    # --- IBS leg (key d's signal is bought at the open of the next session)
    iused = 0.0
    legs = s.I.get(d, []) if ibs_on else []
    if legs:
        ibs_leg = w_i * E
        for sym, o1, r in legs:
            per = ibs_leg / len(legs)
            sh = np.floor(per / o1)
            iused += sh * o1
            pnl += sh * o1 * (r - 2 * 1.0 / 1e4)
    idle = max(0.0, w_i * E - iused)
    b = s.bil.get(d, 0.0); b = float(b) if np.isfinite(b) else 0.0
    px = float(s.C.at[d, "BIL"]) if d in s.C.index and np.isfinite(s.C.at[d, "BIL"]) else np.nan
    tb = np.floor(idle / px) * px if (np.isfinite(px) and idle >= 50) else 0.0
    pnl += tb * b
    cash = E - iused - tb
    # --- night leg (close of d), on the cash free at 15:40
    nused = 0.0
    nd = N.get(d) if night_on else None
    if nd is not None:
        leg = min(w_n * E, max(0.0, cash))
        w = sg.night_tilt(nd.vol20, nd.day_ret, 0.25)
        c = B.cost_bps(cost, nd.price, nd.adv)
        per = leg * nd.frac * w
        if s._gap(d) > 1:
            per = per * 0.5
        for i in range(len(per)):
            q = np.floor(per[i] / nd.price[i])
            if q < 1 and probe and nd.price[i] <= probe:
                q = 1.0
            if q < 1:
                continue
            if cash - q * nd.price[i] < 0:
                continue
            cash -= q * nd.price[i]
            v = q * nd.close[i]
            nused += v
            pnl += v * (nd.ret[i] - 2 * c[i] / 1e4)
    return pnl, iused, nused


def replay(s, N, size, w_n, w_i, probe, cost, alt=False, fixed=True, monthly=0.0):
    rs, E, prev_ibs = [], size, 0.0
    for i, d in enumerate(s.days):
        if i and i % 21 == 0:
            E += monthly
        ibs_on = (i % 2 == 0) if alt else True
        night_on = (i % 2 == 1) if alt else True
        pl, iused, nused = cash_day(s, N, E, d, prev_ibs, w_n, w_i, probe, cost,
                                    ibs_on=ibs_on, night_on=night_on)
        rs.append(pl / E)
        prev_ibs = iused
        if not fixed:
            E += pl
    return pd.Series(rs, index=s.days)


def dollars(r, start, monthly):
    E = start
    for i, x in enumerate(r.fillna(0).values):
        if i and i % 21 == 0:
            E += monthly
        E *= 1 + x
    return E


def stat(r):
    a, b, f = B.stats(r[:"2023-12-31"]), B.stats(r["2024-01-01":]), B.stats(r)
    return f"{a[0]*100:5.1f}/{a[1]:4.2f}  {b[0]*100:5.1f}/{b[1]:4.2f}  {f[0]*100:5.1f}/{f[1]:4.2f}/{f[2]*100:4.0f}"


def nw_t(x: pd.Series, lags: int = 5) -> float:
    x = x.dropna().values
    if len(x) < 20:
        return float("nan")
    n, mu = len(x), x.mean()
    e = x - mu
    s = (e * e).sum() / n
    for k in range(1, lags + 1):
        g = (e[k:] * e[:-k]).sum() / n
        s += 2 * (1 - k / (lags + 1)) * g
    return (mu / np.sqrt(s / n)) if s > 0 else float("nan")


def main():
    t0 = time.time()
    f = open(OUT, "w")

    def log(*a):
        x = " ".join(str(i) for i in a)
        print(x, flush=True)
        f.write(x + "\n"); f.flush()

    log("== Study AL: the idle Roth (cash-IRA book vs limited margin); started",
        pd.Timestamp.now(), "==")
    s = load_sim(raw_price=True)
    N = B.night_days(raw_price=True, max_corr=0.7)
    s.N = N
    ctx = RO.load_ctx()
    log(f"data {time.time()-t0:.0f}s; {len(s.days)} sessions {s.days[0]:%Y-%m-%d}..{s.days[-1]:%Y-%m-%d}\n")

    bil = s.bil.reindex(s.days).fillna(0.0)
    spy = s.spy.reindex(s.days).fillna(0.0)

    # ---------------- part B: book variants (fixed capital series to compare like for like)
    # limited-margin references from roth_opt (whole shares, live mechanics)
    VARS = {
        "AL1 cash lenient (IBS .5+night .5)": dict(w_n=0.5, w_i=0.5, probe=PROBE_USD),
        "AL2 cash strict (.25+.25)":          dict(w_n=0.25, w_i=0.25, probe=PROBE_USD),
        "AL3 IBS only 1.0":                   dict(w_n=0.0, w_i=1.0, probe=PROBE_USD),
        "AL4 night only 1.0":                 dict(w_n=1.0, w_i=0.0, probe=PROBE_USD),
        "AL6 AL1 whole no probe":             dict(w_n=0.5, w_i=0.5, probe=None),
    }
    for cost in ("tier", "tier_hi", 3.0):
        log(f"\n[{cost}] 2021-23                      2024-26                      full CAGR/Sh/DD")
        res = {}
        m3 = RO.run_roth(ctx, RO.RV(mech="M3", L=1.5), cost)["r"]
        m2l = RO.run_roth(ctx, RO.RV(mech="M2L", L=1.5), cost)["r"]
        res["M3 limited margin (ref)"] = m3
        res["M2L limited margin (ref)"] = m2l
        log(f"  {'M3 limited margin (ref)':34s} {stat(m3)}")
        log(f"  {'M2L limited margin (ref)':34s} {stat(m2l)}")
        for lab, kw in VARS.items():
            r = replay(s, N, 3000.0, cost=cost, **kw)
            res[lab] = r
            log(f"  {lab:34s} {stat(r)}")
        res["BIL (idle)"] = bil
        res["SPY"] = spy
        log(f"  {'BIL (idle)':34s} {stat(bil)}")
        log(f"  {'SPY':34s} {stat(spy)}")
        # AL5 alternating
        al5 = replay(s, N, 3000.0, w_n=0.5, w_i=0.5, probe=PROBE_USD, cost=cost, alt=True)
        res["AL5 alternate sessions"] = al5
        log(f"  {'AL5 alternate sessions':34s} {stat(al5)}")

        if str(cost) == "tier_hi":
            log("\n  verdict vs BIL (tier_hi): NW t (2021-26) on daily diff, sign-flip placebo pct, "
                "maxDD vs M3, mc $3k+$1k P(DD30/50)")
            for lab in ("AL1 cash lenient (IBS .5+night .5)", "AL2 cash strict (.25+.25)",
                        "AL3 IBS only 1.0", "AL4 night only 1.0", "AL5 alternate sessions",
                        "M3 limited margin (ref)"):
                r = res[lab]
                d = (r - bil).loc["2021-01-01":]
                t = nw_t(d)
                x = (r - bil).loc["2021-01-01":].values
                rng = np.random.default_rng(11)
                sims = np.array([(x * rng.choice([-1, 1], size=len(x))).mean() for _ in range(1000)])
                pct = float((sims < x.mean()).mean() * 100)
                e = r.copy()
                mc = RO.G.mc(e, 3000, 1000)
                dd = (B.stats(r)[2] - B.stats(m3)[2]) * 100
                log(f"    {lab:34s} t {t:+5.2f}  placebo {pct:5.1f}%  dMaxDD {dd:+4.1f}pp  "
                    f"P30 {mc['dd30']:.0%} P50 {mc['dd50']:.0%}")

    # ---------------- part A: cost of the delay ($1k/$3k + $7.5k/yr)
    log("\n== A. cost of the delay: $start + $7,500/yr ($625/21 sessions), tier_hi")
    log(f"{'start':>6s} {'book':30s} {'full CAGR':>9s} {'end $':>10s} {'$/mo vs BIL':>12s} {'$/mo vs M3':>11s}")
    for cost in ("tier_hi",):
        for S in (1000.0, 3000.0):
            r_m3 = RO.run_roth(ctx, RO.RV(mech="M3", L=1.5), cost, start=S, monthly=625.0)["r"]
            r_m2l = RO.run_roth(ctx, RO.RV(mech="M2L", L=1.5), cost, start=S, monthly=625.0)["r"]
            E_m3 = dollars(r_m3, S, 625.0)
            E_m2l = dollars(r_m2l, S, 625.0)
            E_bil = dollars(bil, S, 625.0)
            E_spy = dollars(spy, S, 625.0)
            rows = {}
            rows["M3 limited margin"] = (r_m3, E_m3)
            rows["M2L limited margin"] = (r_m2l, E_m2l)
            rows["AL1 cash lenient (.5+.5)"] = (replay(s, N, S, 0.5, 0.5, PROBE_USD, cost), None)
            rows["AL3 cash IBS only 1.0"] = (replay(s, N, S, 0.0, 1.0, PROBE_USD, cost), None)
            rows["AL4 cash night only 1.0"] = (replay(s, N, S, 1.0, 0.0, PROBE_USD, cost), None)
            rows["AL6 cash no probe"] = (replay(s, N, S, 0.5, 0.5, None, cost), None)
            rows["BIL (idle)"] = (bil, E_bil)
            rows["SPY"] = (spy, E_spy)
            n_mo = len(s.days) / 21
            for lab, (r, E) in rows.items():
                if E is None:
                    E = dollars(r, S, 625.0)
                cagr = B.stats(r)[0]
                d_bil = (E - E_bil) / n_mo
                d_m3 = (E - E_m3) / n_mo
                log(f"{S:6.0f} {lab:30s} {cagr*100:8.1f}% {E:10,.0f} {d_bil:12,.0f} {d_m3:11,.0f}")
        # value of starting 6/12 months earlier (compounding + avoiding a bad start)
        for wait in (6, 12):
            n = wait * 21
            al = replay(s, N, 3000.0, 0.5, 0.5, PROBE_USD, "tier_hi").iloc[:n]
            b_ = bil.iloc[:n]
            v_al = 3000 * (1 + al).prod()
            v_bil = 3000 * (1 + b_).prod()
            log(f"  start-now vs wait {wait:2d} mo (first {wait} months, $3k): AL1 ${v_al:,.0f} "
                f"vs BIL ${v_bil:,.0f} = ${v_al - v_bil:+,.0f}")
    log(f"\ndone {time.time()-t0:.0f}s")
    f.close()


if __name__ == "__main__":
    main()
