"""Study R: the Roth at $1,000 vs $3,000 sizing (whole shares + probe vs fractional).

    PYTHONPATH=. .venv/bin/python -m research.sim.roth_sizing

Pre-reg: research/drafts/round1_prose.md, "Amendment - Round 4: Study R" (stamped before
any Study R number).

The Roth book as the live code runs it on a limited-margin IRA: night 0.5 + IBS 0.5, no
intraday leg, no conviction, no borrowing; night CLS buys are floor(per * w / price)
shares with the real-money 1-share probe (night_probe_max_usd), IBS / T-bill buys are
notional orders that SchwabAdapter floors to whole shares. The night and IBS legs below
follow B.Sim.day_pnl line for line; the only additions are the probe, the book-cash
floor, and whole-share T-bills.
"""
from __future__ import annotations

import pathlib
import time

import numpy as np
import pandas as pd

from . import book as B
from .validate import load_sim
from swingtrader.daily import signals as sg

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/roth_sizing_out.txt"
PROBE_USD = 150.0          # config.yaml daily.night_probe_max_usd
SIZES = (1000.0, 2000.0, 3000.0, 5000.0)
HALVES = (("2021-23", "2021-01-01", "2023-12-31"), ("2024-26", "2024-01-01", "2026-12-31"),
          ("full", None, None))


def roth_params(cost) -> B.Params:
    return B.Params(night_w=0.5, ibs_w=0.5, night_cost=cost, ibs_cost_bps=1.0, noise_on=False,
                    tilt="live", weekend_scale=0.5, conviction_w=0.0)


def day(s: B.Sim, N: dict, E: float, d, p: B.Params, whole: bool, probe: float | None) -> tuple:
    """One day of Roth P&L in dollars + night counters (picks, skipped, probes, used, budget)."""
    pnl = 0.0
    # --- IBS leg first (bought at the open; its money is not the night leg's cash)
    ibs_leg = p.ibs_w * E; iused = 0.0
    for sym, o1, r in s.I.get(d, []):
        per = ibs_leg / len(s.I[d])
        sh = np.floor(per / o1) if whole else per / o1
        iused += sh * o1
        pnl += sh * o1 * (r - 2 * p.ibs_cost_bps / 1e4)
    idle = ibs_leg - iused
    b = s.bil.get(d, 0.0); b = float(b) if np.isfinite(b) else 0.0
    if whole and idle >= 50:            # live: T-bills only when the leg holds nothing, >= $50
        px = float(s.C.at[d, "BIL"]) if d in s.C.index and np.isfinite(s.C.at[d, "BIL"]) else np.nan
        tb = np.floor(idle / px) * px if np.isfinite(px) else 0.0
    elif whole:
        tb = 0.0
    else:
        tb = idle
    pnl += tb * b
    cash = E - iused - tb
    # --- night leg
    leg = p.night_w * E
    nd = N.get(d)
    cnt = dict(picks=0, skipped=0, probes=0, used=0.0, budget=0.0)
    if nd is not None:
        w = sg.night_tilt(nd.vol20, nd.day_ret, p.tilt_k)
        c = B.cost_bps(p.night_cost, nd.price, nd.adv)
        per = leg * nd.frac * w
        if p.weekend_scale != 1.0 and s._gap(d) > 1:
            per = per * p.weekend_scale
        cnt["picks"] = len(per); cnt["budget"] = float(per.sum())
        for i in range(len(per)):
            if whole:
                q = np.floor(per[i] / nd.price[i])
                if q < 1 and probe and nd.price[i] <= probe:
                    q = 1.0; cnt["probes"] += 1
                if q < 1:
                    cnt["skipped"] += 1; continue
                if cash - q * nd.price[i] < 0:          # executor: "book cash exhausted"
                    cnt["skipped"] += 1; continue
            else:
                q = per[i] / nd.price[i]
            cash -= q * nd.price[i]
            v = q * nd.close[i]
            cnt["used"] += v
            pnl += v * (nd.ret[i] - 2 * c[i] / 1e4)
    return pnl, cnt


def replay(s, N, size, p, whole, probe, fixed=True) -> tuple[pd.Series, dict]:
    """fixed=True: the book is reset to `size` every day (P&L withdrawn) -> the daily
    return on that capital. fixed=False: compounding from `size`, no deposits."""
    E, rs, tot = size, [], dict(picks=0, skipped=0, probes=0, used=0.0, budget=0.0)
    for d in s.days:
        pl, cnt = day(s, N, E, d, p, whole, probe)
        rs.append(pl / E)
        for k in tot:
            tot[k] += cnt[k]
        if not fixed:
            E += pl
    return pd.Series(rs, index=s.days), tot


def mc(rs: dict, start: dict, n=4000, days=1260, block=21, seed=7) -> dict:
    """Paired block bootstrap: the same block draws for every variant."""
    lens = {len(r) for r in rs.values()}
    assert len(lens) == 1
    L = lens.pop()
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, L - block, size=(n, days // block))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(n, -1)
    out = {}
    for k, r in rs.items():
        R = r.fillna(0).values[idx]
        tw = np.cumprod(1 + R, axis=1)
        dd = (tw / np.maximum.accumulate(tw, axis=1) - 1).min(axis=1)
        out[k] = dict(term=tw[:, -1] * start[k], dd30=(dd < -0.30).mean(), mult=tw[:, -1])
    return out


def main():
    t0 = time.time()
    fs = open(OUT, "w")

    def log(*a):
        x = " ".join(str(i) for i in a)
        print(x, flush=True)
        fs.write(x + "\n")
        fs.flush()

    log("== Study R: the Roth at $1k vs $3k (whole shares + probe vs fractional); started",
        pd.Timestamp.now(), "==\n")
    s = load_sim(raw_price=True)
    N10 = B.night_days(raw_price=True, max_corr=0.7)
    N15 = B.night_days(raw_price=True, max_corr=0.7, max_name_pct=0.15)
    s.N = N10
    log(f"data loaded {time.time() - t0:.0f}s; {len(s.days)} sessions "
        f"{s.days[0]:%Y-%m-%d}..{s.days[-1]:%Y-%m-%d}\n")

    for cost in ("tier", "tier_hi"):
        p = roth_params(cost)
        # sanity: fractional, compounding, through the unmodified simulator
        ref = s.replay(B.Params(**{**p.__dict__, "whole": False}), start=3000.0, monthly=0.0)
        mine, _ = replay(s, N10, 3000.0, p, whole=False, probe=None, fixed=False)
        a, b = B.stats(ref["r"])[0], B.stats(mine)[0]
        log(f"[{cost}] SANITY $3k fractional compounding: B.Sim {a*100:.2f}%/yr vs this study "
            f"{b*100:.2f}%/yr (diff {abs(a-b)*100:.2f}pp; bar 0.5pp) -> "
            f"{'OK' if abs(a - b) <= 0.005 else 'VOID'}")

        V = {}
        for sz in SIZES:
            V[f"R whole+probe ${sz/1e3:.0f}k"] = (sz, N10, True, PROBE_USD)
        for sz in SIZES:
            V[f"R fractional ${sz/1e3:.0f}k"] = (sz, N10, False, None)
        V["R9 whole+probe $1k cap .15"] = (1000.0, N15, True, PROBE_USD)
        V["R10 whole no-probe $1k"] = (1000.0, N10, True, None)
        R, T = {}, {}
        for k, (sz, N, wh, pr) in V.items():
            R[k], T[k] = replay(s, N, sz, p, wh, pr, fixed=True)

        log(f"\n[{cost}] fixed capital (reset daily), CAGR / Sharpe / maxDD")
        log(f"{'variant':30s} " + "  ".join(f"{h:>18s}" for h, _, _ in HALVES)
            + "   skipped  probes  deployed")
        for k in V:
            parts = []
            for h, a_, b_ in HALVES:
                c_, sh, dd = B.stats(R[k][a_:b_] if a_ else R[k])
                parts.append(f"{c_*100:6.1f}%/{sh:4.2f}/{dd*100:4.0f}")
            t = T[k]
            skip = t["skipped"] / t["picks"] if t["picks"] else 0.0
            prb = t["probes"] / max(1, t["picks"] - t["skipped"])
            dep = t["used"] / t["budget"] if t["budget"] else 0.0
            log(f"{k:30s} " + "  ".join(parts) + f"   {skip*100:6.1f}%  {prb*100:5.1f}%  {dep*100:6.1f}%")

        log(f"\n[{cost}] gap G = whole+probe - fractional (pp/yr), tracking error (pp/yr)")
        for sz in SIZES:
            w_, f_ = R[f"R whole+probe ${sz/1e3:.0f}k"], R[f"R fractional ${sz/1e3:.0f}k"]
            g = [(B.stats(w_[a_:b_] if a_ else w_)[0] - B.stats(f_[a_:b_] if a_ else f_)[0]) * 100
                 for _, a_, b_ in HALVES]
            te = (w_ - f_).std() * np.sqrt(252) * 100
            log(f"  ${sz/1e3:.0f}k  2021-23 {g[0]:+6.2f}  2024-26 {g[1]:+6.2f}  full {g[2]:+6.2f}   TE {te:5.2f}")
        base1 = R["R whole+probe $1k"]
        for k in ("R9 whole+probe $1k cap .15", "R10 whole no-probe $1k"):
            g = [(B.stats(R[k][a_:b_] if a_ else R[k])[0] - B.stats(base1[a_:b_] if a_ else base1)[0]) * 100
                 for _, a_, b_ in HALVES]
            dd = (B.stats(R[k])[2] - B.stats(base1)[2]) * 100
            log(f"  {k:28s} vs $1k whole+probe: 2021-23 {g[0]:+6.2f}  2024-26 {g[1]:+6.2f}  "
                f"full {g[2]:+6.2f}  maxDD {dd:+.1f}pp")

        # compounding (secondary)
        log(f"\n[{cost}] compounding from the start size, no deposits: full CAGR / end $")
        for k, (sz, N, wh, pr) in V.items():
            r, _ = replay(s, N, sz, p, wh, pr, fixed=False)
            log(f"  {k:30s} {B.stats(r)[0]*100:6.1f}%/yr  end ${sz*(1+r).prod():>9,.0f}")

        # MC
        m = mc(R, {k: v[0] for k, v in V.items()})
        log(f"\n[{cost}] MC 5y, 4000 paired paths, 21-day blocks: p10 / median / p90 terminal $, "
            "P(DD>30%), paired median whole/fractional")
        for k, (sz, *_rest) in V.items():
            t = m[k]["term"]
            pair = ""
            fk = f"R fractional ${sz/1e3:.0f}k"
            if k.startswith("R whole") and fk in m:
                pair = f"  paired {np.median(m[k]['mult'] / m[fk]['mult']):.3f}"
            log(f"  {k:30s} ${np.percentile(t,10):>8,.0f} ${np.median(t):>8,.0f} "
                f"${np.percentile(t,90):>8,.0f}  DD30 {m[k]['dd30']*100:5.1f}%{pair}")
        log("")
    log(f"done {time.time() - t0:.0f}s")
    fs.close()


if __name__ == "__main__":
    main()
