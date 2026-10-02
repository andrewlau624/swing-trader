"""Round 31 Study ID (pre-registered in round1_prose.md, commit b2cdc1c): buy the opening cross, sell the closing cross,
in the session after an officer/director open-market purchase Form 4. Variants ID1 all / ID2 ADV $1-20M / ID3 >= $20M.

    PYTHONPATH=. .venv/bin/python -m research.sim.insider_day

Output: data/research/program/insider_day_out.txt
"""
from __future__ import annotations

import glob
import pathlib

import numpy as np
import pandas as pd

from . import book as B
from . import max_edge as M
from .deep_search import base_sim, params, signflip_pct
from .outside_box import NIGHT, insider_buys
from .program_books import dsr

ROOT = pathlib.Path(__file__).resolve().parents[2]
N_PROG = 755
END = pd.Timestamp("2026-03-31")
H1, H2 = ("2021-01-01", "2023-12-31"), ("2024-01-01", "2026-03-31")
SLEEVE, CAP_EQ, CAP_ADV = 0.45, 0.10, 0.01
VARIANTS = {"ID1 all": (1e6, np.inf), "ID2 ADV $1-20M": (1e6, 2e7), "ID3 ADV >= $20M": (2e7, np.inf)}


def out():
    f = open(ROOT / "data/research/program/insider_day_out.txt", "w")

    def log(*a):
        x = " ".join(str(i) for i in a)
        print(x, flush=True); f.write(x + "\n"); f.flush()
    return log


def raw_panel():
    R = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(str(NIGHT / "insider/raw/raw*.parquet")))])
    R["d"] = R.timestamp.dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
    return R.pivot_table(index="d", columns="symbol", values="open"), R.pivot_table(index="d", columns="symbol", values="close")


def events():
    """All (session, sym) trades with raw open/close, prior raw close, ADV$ (known before the open)."""
    X = insider_buys()
    X = X[X.insider & (X.usd >= 1e4)]
    P = pd.read_pickle(NIGHT / "panel.pkl")
    C, V = P["close"], P["volume"]
    adv = (C * V).rolling(20, min_periods=15).mean()
    RO, RC = raw_panel()
    cal = C.index
    E = X.groupby(["sym", "fd"]).usd.sum().reset_index()
    rows = []
    for s, fd in zip(E.sym, E.fd):
        i = cal.searchsorted(fd + pd.Timedelta(days=1))
        if i <= 0 or i >= len(cal) or s not in RO.columns or s not in adv.columns:
            continue
        d, dp = cal[i], cal[i - 1]
        o, c, pc, a = RO.at[d, s] if d in RO.index else np.nan, RC.at[d, s] if d in RC.index else np.nan, \
            RC.at[dp, s] if dp in RC.index else np.nan, adv.at[dp, s]
        rows.append((d, s, o, c, pc, a))
    T = pd.DataFrame(rows, columns=["d", "sym", "o", "c", "pc", "adv"]).dropna()
    T = T[(T.pc >= 5) & (T.adv >= 1e6) & (T.o > 0)].drop_duplicates(["d", "sym"])
    T["ret"] = T.c / T.o - 1
    T = T[T.ret.abs() < 0.5]
    return T, X, cal


def sleeve(T, days, E, cost):
    """Daily sleeve P&L / E."""
    g = {d: x for d, x in T.groupby("d")}
    outv = []
    for d in days:
        x = g.get(d)
        if x is None:
            outv.append(0.0); continue
        per = np.minimum(np.minimum(SLEEVE * E / len(x), CAP_EQ * E), CAP_ADV * x.adv.values)
        sh = np.floor(per / x.o.values)
        c = B.cost_bps(cost, x.o.values, x.adv.values) if cost == "tier_hi" else np.full(len(x), float(cost))
        outv.append(float((sh * x.o.values * (x.ret.values - 2 * c / 1e4)).sum()) / E)
    return pd.Series(outv, index=days)


def placebo_events(T, X, cal, rng):
    """Each event moved to a random session of the same stock and year with no purchase filing within 10 sessions."""
    pos = {d: i for i, d in enumerate(cal)}
    near = {}
    for s, fd in zip(X.sym, X.fd):
        i = cal.searchsorted(fd)
        near.setdefault(s, set()).update(range(i - 10, i + 12))
    return near, pos


def main():
    T, X, cal = events()
    RO, RC = raw_panel()
    run(T, X, cal, RO, RC, VARIANTS, out(), END, N_PROG, "Study ID")
    T.to_pickle(ROOT / "data/research/program/insider_day_trades.pkl")


def run(T, X, cal, RO, RC, variants, log, end, n_prog, title, h2=H2):
    """The registered evaluation (sleeve in V7, halves, NW t, sign-flip, feature placebo, judge half); X = all events
    (sym, fd) for the placebo exclusion window. Shared by Round 32 A1/A2 (filing_day.py)."""
    s = base_sim()
    days = s.days[s.days <= end]
    H2 = h2
    log(f"{title}: {len(T)} trades on {T.d.nunique()} sessions, {T.d.min().date()}..{T.d.max().date()}; book window {days[0].date()}..{days[-1].date()}")
    # placebo pools: per (sym, year) eligible sessions
    near = {}
    for sym, fd in zip(X.sym, X.fd):
        i = cal.searchsorted(fd)
        near.setdefault(sym, set()).update(range(i - 10, i + 12))
    P = pd.read_pickle(NIGHT / "panel.pkl")
    adv = ((P["close"] * P["volume"]).rolling(20, min_periods=15).mean()).shift(1)
    noise = sum(share * np.minimum(s.NZ[k]["lev"], 0.75) * s.NZ[k]["ret"] for k, share in {"QQQ": 0.5, "SMH": 0.5}.items()).reindex(days).fillna(0)
    for lab, (lo, hi) in variants.items():
        V = T[(T.adv >= lo) & (T.adv < hi)]
        log(f"\n== {lab}: {len(V)} trades; per trade gross {V.ret.mean()*1e4:+.1f}bp (median {V.ret.median()*1e4:+.1f}); "
            f"net 2.5bp/side {V.ret.mean()*1e4-5:+.1f}; by year " + " ".join(f"{y}:{v*1e4:+.1f}" for y, v in V.groupby(V.d.dt.year).ret.mean().items()))
        res = {}
        for cost in (2.5, "tier_hi"):
            for E in M.SIZES:
                base = M.replay(s, E, params(cost)).reindex(days)
                inc = sleeve(V, days, E, cost)
                r = base + inc
                sb, sr = B.stats(base), B.stats(r)
                h = [inc[a:z].mean() * 252 * 100 for a, z in (H1, H2)]
                res[(cost, E)] = (base, r, inc)
                log(f"  [{lab}] {cost}/side ${E/1e3:.1f}k base {sb[0]*100:5.1f}%/{sb[1]:4.2f}/{sb[2]*100:4.0f}  var {sr[0]*100:5.1f}%/{sr[1]:4.2f}/{sr[2]*100:4.0f}  "
                    f"inc {(sr[0]-sb[0])*100:+5.2f}pp (${(sr[0]-sb[0])*E:+,.0f}/yr)  halves {h[0]:+5.2f}/{h[1]:+5.2f}pp  dDD {(sr[2]-sb[2])*100:+4.1f}")
        base, r, d = res[(2.5, 10000.0)]
        t, pct = M.nw_t(d.values), signflip_pct(d.values)
        # feature placebo
        rng = np.random.default_rng(31); sims = []
        Vy = V.assign(y=V.d.dt.year)
        elig = {}
        for sym, y in set(zip(Vy.sym, Vy.y)):
            if sym not in RO.columns:
                continue
            idx = [i for i in np.where(cal.year == y)[0] if i not in near.get(sym, ()) and 0 < i]
            elig[(sym, y)] = np.array(idx)
        for k in range(200):
            rows = []
            for sym, y in zip(Vy.sym, Vy.y):
                e = elig.get((sym, y))
                if e is None or not len(e):
                    continue
                i = int(rng.choice(e)); dd, dp = cal[i], cal[i - 1]
                o = RO.at[dd, sym] if dd in RO.index else np.nan
                c = RC.at[dd, sym] if dd in RC.index else np.nan
                a = adv.at[dd, sym] if sym in adv.columns else np.nan
                if np.isfinite(o) and np.isfinite(c) and o > 0 and np.isfinite(a) and abs(c / o - 1) < 0.5:
                    rows.append((dd, sym, o, c, a))
            Q = pd.DataFrame(rows, columns=["d", "sym", "o", "c", "adv"]).drop_duplicates(["d", "sym"])
            Q["ret"] = Q.c / Q.o - 1
            sims.append(sleeve(Q, days, 10000.0, 2.5).mean())
        extra = float((np.array(sims) < d.mean()).mean() * 100)
        halves_ok = all(min(res[(2.5, E)][2][a:z].mean() for a, z in (H1, H2)) > 0 for E in M.SIZES)
        ddd = (B.stats(r)[2] - B.stats(base)[2]) * 100
        pdd = M.p_dd50(r); q = dsr(d, n_trials=n_prog)
        d2 = d[H2[0]:H2[1]]; t2 = M.nw_t(d2.values)
        ev2 = V[(V.d >= H2[0]) & (V.d <= H2[1])].ret.mean() * 1e4 - 5
        log(f"  [{lab}] $10k 2.5bp: NW t {t:+.2f}  sign-flip {pct:.0f}%  feature placebo {extra:.0f}% (placebo mean {np.mean(sims)*25200:+.2f}pp/yr)  "
            f"dDD {ddd:+.1f}pp  P(DD>50) {pdd:.1%}  DSR {q['dsr']:.3f} (N {n_prog})  corr(inc, noise) {np.corrcoef(d.values, noise.values)[0,1]:+.2f}")
        log(f"  [{lab}] judge half alone: event net {ev2:+.1f}bp, daily-sleeve NW t {t2:+.2f}")
        ok = halves_ok and t >= 2 and pct >= 95 and extra >= 95 and ddd >= -2 and pdd <= 0.05 and ev2 > 0 and t2 >= 2
        log(f"  [{lab}] -> {'PASS' if ok else 'DEAD'}")


if __name__ == "__main__":
    main()
