"""Study B: taxable V6 (SPY/QQQ oversold overnight on idle money) on the RAW pool.

    PYTHONPATH=. .venv/bin/python -m research.sim.taxable_v6_raw

Pre-registration: research/drafts/round1_prose.md (stamped before any variant number).

Variants
  A1t  V6 funded ONLY by the idle IBS half (the published addendum-27 taxable test),
       on the raw-price V7 baseline (1.0x, cap .10, conv .5, corr 0.7).
  A2t  V6 funded from ALL idle overnight money: the idle IBS half + the night leg's
       unused cash. On FOMC eves the adopted F3 keeps the unused night night cash, so
       A2t uses only the idle IBS half there (the F3 priority, as pre-registered).

Costs: the V6 leg 1bp/side (tier) / 3bp/side (tier_hi); the night leg rides the cost dial
(3bp flat "measured", tier, tier_hi). Book: book.Sim.replay on the raw sim
(load_sim(raw_price=True), night pool corr 0.7), whole shares, $3k + $1k/21 sessions.

Pass bar (inherited and restated): the increment > 0 in 2021-23 AND 2024-26 at 3bp AND
tier_hi (night leg), the 2016-20 holdout not worse (Sharpe), the placebo >= 95th pct in
both halves, NW t (5 lags) >= 2.0 of the daily book increment over 2021-26, WoW EH and the
5y MC draw bars: adopt requires ALL; shadow if 1-3 hold and a rest fails; dead otherwise.
(With the t<2 known from addendum 27, the realistic outcome is shadow/dead either way:
this run's job is the RAW-pool restatement and the live-relevant A2t check.)
"""
from __future__ import annotations

import copy
import pathlib
import pickle
import time

import numpy as np
import pandas as pd

from . import book as B
from . import growth as G
from . import macro_events as ME
from . import oversold as OS
from . import rawprice as RP
from .validate import load_sim

SCR = pathlib.Path(__file__).resolve().parents[2] / "data/research/program"
OUT = SCR / "taxable_v6_raw_out.txt"
PER = (("2021-23", "2021-01-01", "2023-12-31"), ("2024-26", "2024-01-01", "2026-12-31"))


def nw_t(x, lags: int = 5) -> float:
    v = x.dropna().values
    n = len(v)
    if n < 30:
        return float("nan")
    e = v - v.mean()
    var = (e * e).sum() / n
    for k in range(1, lags + 1):
        var += 2 * (1 - k / (lags + 1)) * (e[k:] * e[:-k]).sum() / n
    return v.mean() / np.sqrt(max(var, 1e-18) / n)


def replay_a2(s, held, cost="tier"):
    """V7 + V6 funded from ALL idle overnight money (the A2t book).

    Spine = oversold.replay_ovn (the V7 base; the idle-IBS branch as shipped). Then: on a
    trigger day when the IBS leg is flat, the night leg's unused cash ALSO goes into the
    same V6 names (whole shares, equal split) — except on FOMC eves, where the adopted F3
    filler owns the unused night cash (A2t takes nothing there)."""
    base = B.Params(**{**G.V7, **G.cfg(1.0, 0.5, 2), "night_cost": cost})
    c = 1.0 if cost == "tier" else 3.0              # the V6 leg's per-side cost (add. 27)
    fe = ME.flags(s.C.index)["fomc_eve"]
    E, rows, gross, prev = 3000.0, [], 0.0, None
    for i, d in enumerate(s.days):
        if i and i % 21 == 0:
            E += 1000.0
        pl, info = s.day_pnl(E, d, base)
        bil = s.bil.get(d, 0.0)
        bil = float(bil) if np.isfinite(bil) else 0.0
        extra, tv = 0.0, 0.0
        cur = held.get(d)
        if cur and not s.I.get(prev):
            per = 0.5 * E / len(cur)               # 1) idle IBS half, as shipped
            for sym, (px, r) in cur.items():
                v = np.floor(per / px) * px
                tv += v
                extra += v * (r - 2 * c / 1e4) - v * bil
            if not bool(fe.get(d, False)):         # 2) the night leg's unused cash
                spare = max(0.0, 0.5 * E - info["night_v"])
                if spare > 0:
                    per2 = spare / len(cur)
                    for sym, (px, r) in cur.items():
                        v = np.floor(per2 / px) * px
                        tv += v
                        extra += v * (r - 2 * c / 1e4)
        pl += extra
        gross = max(gross, (info["night_v"] + tv) / E + (0.5 if s.I.get(prev) else 0.0))
        rows.append((d, pl / E, info["night"] / E, info["ibs"] / E, info["noise"] / E,
                     extra / E, tv / E))
        E += pl
        prev = d
    df = pd.DataFrame(rows, columns=["date", "r", "r_night", "r_ibs", "r_noise", "r_trig", "trig_v"])
    df = df.set_index("date")
    df.attrs["max_gross"] = gross
    return df


def main():
    fs = open(OUT, "w")

    def log(*a):
        x = " ".join(str(i) for i in a)
        print(x, flush=True)
        fs.write(x + "\n")
        fs.flush()

    t0 = time.time()
    log("== Study B: taxable V6 on the raw pool, started", pd.Timestamp.now(), "\n")
    rp = pickle.load(open(RP.CACHE, "rb"))
    N_raw = rp["raw"][0.10]
    s = load_sim(raw_price=True)
    s.N = N_raw
    s.BO = B.breakout_days()
    log(f"loaded in {time.time()-t0:4.1f} s; pool days {len(N_raw)}")

    sig = OS.honest_1540(s)
    held = OS.schedule_ovn(s, sig)
    close_sig = OS.triggers(s.C)["either"]
    agree = np.mean([bool(sig[k].get(d, False)) == bool(close_sig[k].get(d, False))
                     for k in ("SPY", "QQQ") for d in s.C.index[300:]])
    log(f"trigger nights {len(held)}; the 15:40 rule agrees with the close rule on {agree:.1%}\n")

    base = {}
    for c in ("tier", "tier_hi"):
        kw = {**G.V7, **G.cfg(1.0, 0.5, 2), "night_cost": c}
        base[c] = s.replay(B.Params(**kw))
        log(f"base V7 raw {c:7s}: {B.summary(base[c])}")

    r1 = {c: OS.replay_ovn(s, held, c) for c in ("tier", "tier_hi")}
    r2 = {c: replay_a2(s, held, c) for c in ("tier", "tier_hi")}
    res = {}

    def sm(r):
        c2, sh2, dd2 = B.stats(r[:"2023-12-31"])
        c3, sh3, dd3 = B.stats(r["2024-01-01":])
        c4, sh4, dd4 = B.stats(r)
        return (f"{c2*100:5.1f}/{sh2:4.2f}/{dd2*100:4.0f} | "
                f"{c3*100:5.1f}/{sh3:4.2f}/{dd3*100:4.0f} | "
                f"{c4*100:5.1f}/{sh4:4.2f}/{dd4*100:4.0f}")

    for lab, rr in (("A1t idle-IBS only", r1), ("A2t all idle overnight", r2)):
        log("")
        log(f"== {lab}")
        for c, r in rr.items():
            rb = r["r"] - base[c]["r"]
            res[(lab, c)] = rb
            p1 = B.stats(rb[PER[0][1]:PER[0][2]])[0] * 100
            p2 = B.stats(rb[PER[1][1]:PER[1][2]])[0] * 100
            log(f"{c:7s}: {sm(r['r'])}  max gross {float(r.attrs['max_gross']):.2f}x")
            log(f"   increment pp CAGR vs base: {p1:+6.2f} {p2:+6.2f} | full "
                f"{B.stats(rb)[0]*100:+6.2f}  NW t {nw_t(rb):+5.2f}")

    # 2016-20 holdout: the ETF legs from the returns book; the night leg = the raw 2020
    # rebuild through program_books.night2020 (the same series addenda use)
    from .crash import COST as CR_COST
    from .program_books import night2020
    n10 = night2020(rp["y2020"]["raw"][0], 0.10)
    n10 = n10[n10.index < "2020-11-05"]
    _legs = OS.holdout_legs(load_sim(raw_price=True))
    legs_hold = (n10,) + tuple(_legs[1:])
    ho_base = OS.holdout(s, legs_hold, None, None)
    ho_a1 = OS.holdout_ovn(s, legs_hold, held)
    log("")
    log(f"holdout 2016-20 base : {sm(ho_base)}")
    log(f"holdout 2016-20 A1t  : {sm(ho_a1)}   dSharpe {B.stats(ho_a1)[1]-B.stats(ho_base)[1]:+.2f}")
    log("  (A2t has no holdout leg: the night-money branch needs the 2016-20 night leg at the")
    log("  tier costs; A1t's holdout stands for the leg the two variants share.)")

    # placebo: the same trigger count per symbol on random dates, 200 seeds, both modes
    pl = []
    for seed in range(200):
        ph = OS.placebo_ovn(s, held, seed)
        pb1 = OS.replay_ovn(s, ph, "tier")
        pb2 = replay_a2(s, ph, "tier")
        pl.append([B.stats(pb1.r - base["tier"].r.reindex(pb1.r.index).fillna(0))[0],
                   B.stats(pb2.r - base["tier"].r.reindex(pb2.r.index).fillna(0))[0]])
    pl = np.array(pl)
    log("")
    for j, lab in enumerate(("A1t", "A2t")):
        rseries = r1 if j == 0 else r2
        rr = rseries["tier"]["r"] - base["tier"].r.reindex(rseries["tier"].index).fillna(0)
        for _, a, b2 in PER:
            hi = rr[a:b2].mean()
            pct = 100 * (pl[:, j] < hi).mean()
            log(f"placebo {lab} {a}: increment mean {hi*252*100:+6.1f}pp/yr  placebo mean "
                f"{pl[:, j].mean()*252*100:+6.1f}  p95 {np.percentile(pl[:, j], 95)*252*100:+6.1f}  "
                f"pct {pct:.0f}")

    def yr(r):
        return (1 + r).groupby(r.index.year).prod() - 1

    log("")
    a1 = r1["tier"]["r"] - base["tier"].r.reindex(r1["tier"].index).fillna(0)
    a2 = r2["tier"]["r"] - base["tier"].r.reindex(r2["tier"].index).fillna(0)
    log("calendar years A1t increment pp: " + "  ".join(
        f"{y}:{v*100:+.1f}" for y, v in zip(yr(a1).index, yr(a1) * 100)))
    log("calendar years A2t increment pp: " + "  ".join(
        f"{y}:{v*100:+.1f}" for y, v in zip(yr(a2).index, yr(a2) * 100)))
    log("")
    fs.close()


if __name__ == "__main__":
    main()
