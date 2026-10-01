"""Round 19 (max edge from outside sources): Study AU (night picks tilted by trailing overnight-return
persistence) and Study AV (IBS leg state exits). Study AW (auction-print audit) is `auction_audit.py`.

    PYTHONPATH=. .venv/bin/python -m research.sim.max_edge

Pre-registration: research/drafts/round1_prose.md, "Round 19" (commit dc53fcb, before any number).
Candidate list: research/drafts/max_edge_candidates.md. Params.night_cost is PER SIDE.
"""
from __future__ import annotations

import dataclasses
import pathlib
import time

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import book as B
from . import data as D
from .validate import load_sim

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/max_edge_out.txt"
HALVES = (("2021-23", "2021-01-01", "2023-12-31"), ("2024-26", "2024-01-01", "2026-12-31"))
SIZES = (2300.0, 10000.0, 25000.0)
N_TRIALS = 680
BOOKS = {
    "V7": dict(night_w=0.5, ibs_w=0.5, ibs_cost_bps=1.0, noise={"QQQ": 0.5, "SMH": 0.5},
               noise_cap=0.75, tilt="live", weekend_scale=0.5, conviction_w=0.0),
    "Roth": dict(night_w=0.5, ibs_w=0.5, ibs_cost_bps=1.0, noise_on=False,
                 tilt="live", weekend_scale=0.5, conviction_w=0.0),
}
COSTS = (2.5, "tier_hi")          # judged, reported


def nw_t(x, lags=5):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    mu = x.mean(); e = x - mu; n = len(x)
    s = (e * e).sum() / n
    for k in range(1, lags + 1):
        s += 2 * (1 - k / (lags + 1)) * (e[k:] * e[:-k]).sum() / n
    return mu / np.sqrt(s / n) if s > 0 else float("nan")


def p_dd50(r, years=5, paths=1000, block=21, seed=3):
    """Stationary block bootstrap of daily returns: P(maxDD over `years` > 50%)."""
    x = np.asarray(r.fillna(0), float); n = len(x); L = 252 * years
    rng = np.random.default_rng(seed); hit = 0
    for _ in range(paths):
        idx = np.empty(L, int); i = rng.integers(n)
        for k in range(L):
            if k and rng.random() < 1 / block:
                i = rng.integers(n)
            idx[k] = i; i = (i + 1) % n
        eq = np.cumprod(1 + x[idx]); dd = (eq / np.maximum.accumulate(eq) - 1).min()
        hit += dd < -0.5
    return hit / paths


def replay(s, size, p):
    return pd.Series([s.day_pnl(size, d, p)[0] / size for d in s.days], index=s.days)


def judge(log, lab, r, base, judged=True, pdd=None):
    d = r - base
    half = [d[(d.index >= a) & (d.index <= z)].mean() * 252 * 100 for _, a, z in HALVES]
    t = nw_t(d.values)
    rng = np.random.default_rng(9); X = d.values
    sims = np.array([(X * rng.choice([-1, 1], size=len(X))).mean() for _ in range(1000)])
    pct = float((sims < X.mean()).mean() * 100)
    sr, sb = B.stats(r), B.stats(base)
    inc, ddd = (sr[0] - sb[0]) * 100, (sr[2] - sb[2]) * 100
    ok = half[0] > 0 and half[1] > 0 and t >= 2.0 and pct >= 95 and ddd >= -2.0
    if pdd is not None:
        ok = ok and pdd <= 0.05
    log(f"    {lab:10s} {sr[0]*100:5.1f}/{sr[1]:4.2f}/{sr[2]*100:4.0f}  inc {inc:+5.2f}pp "
        f"({half[0]:+5.2f}/{half[1]:+5.2f})  t {t:+5.2f}  plac {pct:3.0f}%  dDD {ddd:+4.1f}"
        + (f"  P(DD>50) {pdd:.1%}" if pdd is not None else "")
        + ("" if not judged else f"  {'PASS' if ok else 'fail'}"))
    return ok, inc


# ---------------------------------------------------------------- Study AU features
def au_features(N):
    """(date, sym) -> (ON20, TOW), from the SIP daily panel up to d's open."""
    P = D.panel(); O, C = P["open"], P["close"]
    gap = (O / C.shift(1) - 1).where(lambda x: x.abs() <= 1)
    intr = (C / O - 1).where(lambda x: x.abs() <= 1)
    on20 = gap.rolling(20, min_periods=15).mean()                      # t = d-19..d
    tow = ((gap > 0) & (intr < 0)).astype(float).where(gap.notna() & intr.notna())
    tow20 = tow.shift(1).rolling(20, min_periods=15).sum()             # t = d-20..d-1
    out = {}
    for d, nd in N.items():
        for sym in nd.syms:
            sym = str(sym)
            a = on20.at[d, sym] if (d in on20.index and sym in on20.columns) else np.nan
            b = tow20.at[d, sym] if (d in tow20.index and sym in tow20.columns) else np.nan
            out[(d, sym)] = (float(a), float(b))
    return out


def make_tilt(N, F, kind, mu, sd, shuffle_rng=None):
    date_of = {id(nd): d for d, nd in N.items()}

    def f(nd):
        d = date_of[id(nd)]
        live = sg.night_tilt(nd.vol20, nd.day_ret, 0.25)
        j = 0 if kind in ("AU1", "AU2") else 1
        v = np.array([F[(d, str(s))][j] for s in nd.syms], float)
        if shuffle_rng is not None:
            v = shuffle_rng.permutation(v)
        if kind == "AU2":
            return np.where(np.isfinite(v) & (v < 0), 0.0, live)
        z = np.where(np.isfinite(v), (v - mu[j]) / sd[j], 0.0)
        w = live * np.clip(1 + 0.25 * z, 0.25, 2.0)
        return w * live.mean() / w.mean()
    return f


# ---------------------------------------------------------------- Study AV
def av_days(kind, top_k=3, ibs_max=0.2, cap=5):
    """As B.ibs_days, but an entered name is re-held until the state exit (AV1 IBS > 0.5,
    AV2 close > prior high), `cap` sessions after its last IBS < 0.2 signal, or leaving the top-3."""
    P = D.etf(); O, H, L, C = P["open"], P["high"], P["low"], P["close"]
    closes = C[B.EQ18]; days = C.index
    out, mom_cache, extra = {}, {}, {}
    for j in range(260, len(days) - 2):
        d, today = days[j], days[j + 1]
        m = today.to_period("M")
        if m not in mom_cache:
            mom_cache[m] = sg.momentum_top(closes[closes.index < today], today, top_k)
        uni = mom_cache[m]
        last = {s: {"high": H.at[d, s], "low": L.at[d, s], "close": C.at[d, s]} for s in uni}
        tg = set(sg.ibs_targets(last, ibs_max))
        hold = []
        for s in uni:
            if s in tg:
                extra[s] = 0; hold.append(s); continue
            if s not in extra:
                continue
            rng_ = H.at[d, s] - L.at[d, s]
            ibs = (C.at[d, s] - L.at[d, s]) / rng_ if rng_ > 0 else 0.5
            done = ibs > 0.5 if kind == "AV1" else C.at[d, s] > H.at[days[j - 1], s]
            if done or extra[s] + 1 >= cap:
                extra.pop(s); continue
            extra[s] += 1; hold.append(s)
        for s in list(extra):
            if s not in uni:
                extra.pop(s)
        legs = [(s, O.at[days[j + 1], s], O.at[days[j + 2], s] / O.at[days[j + 1], s] - 1)
                for s in hold if np.isfinite(O.at[days[j + 1], s]) and np.isfinite(O.at[days[j + 2], s])]
        if legs:
            out[d] = legs
    return out


def unit_ibs(I, a, z):
    """Equal-weight daily IBS leg return (open->open, -2bp), 0 when flat."""
    days = D.etf()["close"].index
    days = days[(days >= a) & (days <= z)]
    return pd.Series([np.mean([r - 2e-4 for _, _, r in I[d]]) if d in I else 0.0 for d in days], index=days)


def main():
    t0 = time.time()
    f = open(OUT, "w")

    def log(*a):
        x = " ".join(str(i) for i in a)
        print(x, flush=True); f.write(x + "\n"); f.flush()

    log("== Round 19: Studies AU, AV; started", pd.Timestamp.now(), "==")
    s = load_sim(raw_price=True)
    s.N = B.night_days(raw_price=True, max_corr=0.7)
    I_ship = B.ibs_days(); s.I = I_ship
    verdict = {}

    # ======================= Study AU
    log("\n######## Study AU — night picks tilted by trailing overnight-return persistence")
    F = au_features(s.N)
    sel = [v for (d, _), v in F.items() if d <= pd.Timestamp("2023-12-31")]
    A = np.array(sel, float)
    mu = np.nanmean(A, axis=0); sd = np.nanstd(A, axis=0)
    log(f"picks {len(F)}; feature coverage ON20 {np.isfinite([v[0] for v in F.values()]).mean():.1%} "
        f"TOW {np.isfinite([v[1] for v in F.values()]).mean():.1%}; 2021-23 mean/sd ON20 "
        f"{mu[0]*1e4:+.1f}/{sd[0]*1e4:.1f}bp  TOW {mu[1]:.2f}/{sd[1]:.2f}")
    # per-pick net by tercile (2021-23 cut points), 2.5bp/side
    rows = []
    for d, nd in s.N.items():
        for j, sym in enumerate(nd.syms):
            rows.append((d, *F[(d, str(sym))], nd.ret[j] - 5e-4))
    T = pd.DataFrame(rows, columns=["d", "on20", "tow", "net"])
    for col in ("on20", "tow"):
        q = T[T.d <= "2023-12-31"][col].quantile([1 / 3, 2 / 3]).values
        line = []
        for lab, a, z in (("2021-23", "2021-01-01", "2023-12-31"), ("2024-26", "2024-01-01", "2026-12-31")):
            x = T[(T.d >= a) & (T.d <= z) & T[col].notna()]
            b = np.digitize(x[col], q)
            line.append(f"{lab}: " + " ".join(f"T{k+1} {x.net[b == k].mean()*1e4:+6.1f}bp n{(b == k).sum()}"
                                                for k in range(3)))
        log(f"  {col} terciles (net 2.5bp/side): " + " | ".join(line))

    for kind in ("AU1", "AU2", "AU3"):
        verdict[kind] = []
    for c in COSTS:
        for bk, bp in BOOKS.items():
            p0 = B.Params(**{**bp, "night_cost": c})
            log(f"\n  [{bk}, night {c}/side]  full CAGR/Sh/DD")
            for E in SIZES:
                base = replay(s, E, p0); sb = B.stats(base)
                log(f"   ${E/1e3:5.1f}k shipped    {sb[0]*100:5.1f}/{sb[1]:4.2f}/{sb[2]*100:4.0f}")
                for kind in ("AU1", "AU2", "AU3"):
                    r = replay(s, E, dataclasses.replace(p0, tilt=make_tilt(s.N, F, kind, mu, sd)))
                    pdd = p_dd50(r) if (E == 10000.0 and c == 2.5) else None
                    ok, _ = judge(log, kind, r, base, judged=(c == 2.5), pdd=pdd)
                    if c == 2.5:
                        verdict[kind].append(ok)
    # feature-shuffle placebo, V7 $10k 2.5bp
    p0 = B.Params(**{**BOOKS["V7"], "night_cost": 2.5})
    base = replay(s, 10000.0, p0)
    for kind in ("AU1", "AU3"):
        act = (replay(s, 10000.0, dataclasses.replace(p0, tilt=make_tilt(s.N, F, kind, mu, sd))) - base).mean()
        rng = np.random.default_rng(11)
        sims = [(replay(s, 10000.0, dataclasses.replace(p0, tilt=make_tilt(s.N, F, kind, mu, sd, rng))) - base).mean()
                for _ in range(200)]
        pct = float((np.array(sims) < act).mean() * 100)
        log(f"  {kind} within-night feature shuffle (200): actual {act*25200:+.2f}pp/yr, pct {pct:.0f}%")
        verdict[kind].append(pct >= 95)

    # ======================= Study AV
    log("\n######## Study AV — IBS leg state exits")
    IV = {k: av_days(k) for k in ("AV1", "AV2")}
    for lab, I in (("shipped", I_ship), *IV.items()):
        nlegs = sum(len(v) for v in I.values())
        u = [unit_ibs(I, pd.Timestamp(a), pd.Timestamp(z)) for a, z in
             (("2016-01-01", "2020-12-31"), ("2021-01-01", "2023-12-31"), ("2024-01-01", "2026-12-31"))]
        log(f"  {lab:8s} leg-days {nlegs:5d}  unit IBS leg %/yr 2016-20 / 21-23 / 24-26: "
            + " / ".join(f"{x.mean()*25200:+5.1f}" for x in u))
    hold16 = {}
    for k, I in IV.items():
        a = unit_ibs(I, pd.Timestamp("2016-01-01"), pd.Timestamp("2020-12-31"))
        b = unit_ibs(I_ship, pd.Timestamp("2016-01-01"), pd.Timestamp("2020-12-31"))
        hold16[k] = (a - b).mean() >= 0
        log(f"  {k} 2016-20 holdout unit increment {(a-b).mean()*25200:+.2f}pp/yr, NW t {nw_t((a-b).values):+.2f}")
        verdict[k] = [hold16[k]]
    for c in COSTS:
        for bk, bp in BOOKS.items():
            p0 = B.Params(**{**bp, "night_cost": c})
            log(f"\n  [{bk}, night {c}/side]  full CAGR/Sh/DD")
            for E in SIZES:
                s.I = I_ship
                base = replay(s, E, p0); sb = B.stats(base)
                log(f"   ${E/1e3:5.1f}k shipped    {sb[0]*100:5.1f}/{sb[1]:4.2f}/{sb[2]*100:4.0f}")
                for k, I in IV.items():
                    s.I = I
                    r = replay(s, E, p0)
                    pdd = p_dd50(r) if (E == 10000.0 and c == 2.5) else None
                    ok, _ = judge(log, k, r, base, judged=(c == 2.5), pdd=pdd)
                    if c == 2.5:
                        verdict[k].append(ok)
                s.I = I_ship

    log("\n######## verdicts (all judged cells at 2.5bp/side, both books, 3 sizes; + extra placebo / holdout)")
    for k, v in verdict.items():
        log(f"   {k}: {sum(v)}/{len(v)} checks pass -> {'SHADOW' if all(v) else 'DEAD'}")
    log(f"\ndone {time.time()-t0:.0f}s")
    f.close()


if __name__ == "__main__":
    main()
