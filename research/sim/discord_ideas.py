"""Round 18: two ideas from a quant Discord — Study AS (overnight budget split IBS/night by
trailing metrics, "softmax of metrics") and Study AT (vol-ratio / trend-slope conditioning for
the IBS mean-reversion leg).

    PYTHONPATH=. .venv/bin/python -m research.sim.discord_ideas

Pre-registration: research/drafts/round1_prose.md, "Round 18" (committed before any number).
Costs: Params.night_cost is PER SIDE (day_pnl charges 2 x c), so the registered "5bp round
trip" is night_cost=2.5.
"""
from __future__ import annotations

import dataclasses
import pathlib
import time

import numpy as np
import pandas as pd

from . import book as B
from . import data as D
from .validate import load_sim

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/discord_ideas_out.txt"
HALVES = (("2021-23", "2021-01-01", "2023-12-31"),
          ("2024-26", "2024-01-01", "2026-12-31"))
SIZES = (2300.0, 10000.0, 25000.0)
N_TRIALS = 675


def nw_t(x, lags=5):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) < 20:
        return float("nan")
    mu = x.mean(); e = x - mu; n = len(x)
    s = (e * e).sum() / n
    for k in range(1, lags + 1):
        s += 2 * (1 - k / (lags + 1)) * (e[k:] * e[:-k]).sum() / n
    return mu / np.sqrt(s / n) if s > 0 else float("nan")


# ------------------------------------------------------------ Study AS
def unit_legs(s, p) -> pd.DataFrame:
    """Per-unit daily return of each overnight leg (fractional, $100k, noise off)."""
    pf = dataclasses.replace(p, whole=False, noise_on=False, night_w=0.5, ibs_w=0.5)
    rows = []
    for d in s.days:
        _, info = s.day_pnl(1e5, d, pf)
        rows.append((d, info["night"] / 5e4, (info["ibs"] + info["idle"]) / 5e4))
    return pd.DataFrame(rows, columns=["d", "night", "ibs"]).set_index("d")


def as_weights(u: pd.DataFrame, kind: str) -> pd.Series:
    """Night weight per day (IBS = 1 - it), from leg returns lagged 2 sessions, clipped [.2, .8]."""
    win = 252 if kind == "AS3" else 63
    m = u.rolling(win, min_periods=win).mean()
    v = u.rolling(win, min_periods=win).std()
    if kind in ("AS1", "AS3"):
        sr = (m / v * np.sqrt(252)).shift(2)
        z = np.exp(sr["night"]) / (np.exp(sr["night"]) + np.exp(sr["ibs"]))
    elif kind == "AS2":
        iv = (1 / v).shift(2)
        z = iv["night"] / (iv["night"] + iv["ibs"])
    else:
        raise ValueError(kind)
    return z.clip(0.2, 0.8).fillna(0.5)


def replay_as(s, size, p, wn: pd.Series | None):
    out = []
    for d in s.days:
        q = p if wn is None else dataclasses.replace(p, night_w=float(wn[d]), ibs_w=1 - float(wn[d]))
        out.append(s.day_pnl(size, d, q)[0] / size)
    return pd.Series(out, index=s.days)


# ------------------------------------------------------------ Study AT
def at_flags(I: dict) -> dict:
    """(d, sym) -> {VR, slope} from closes up to and including d (known before the d+1 open)."""
    C = D.etf()["close"]
    lr = np.log(C).diff()
    sd10, sd60 = lr.rolling(10).std(), lr.rolling(60).std()
    vr = sd10 / sd60
    x = np.arange(50) - 24.5
    lc = np.log(C)
    out = {}
    for d, legs in I.items():
        j = C.index.get_loc(d)
        for sym, _, _ in legs:
            y = lc[sym].iloc[j - 49: j + 1].values
            sl = float(((y - y.mean()) * x).sum() / (x * x).sum()) if len(y) == 50 and np.isfinite(y).all() else np.nan
            out[(d, sym)] = {"vr": float(vr.at[d, sym]), "slope": sl}
    return out


def keep_rule(kind):
    return {"AT1": lambda f: not (f["vr"] < 0.8),
            "AT2": lambda f: not (f["vr"] > 1.25),
            "AT3": lambda f: f["slope"] > 0}[kind]


def replay_at(s, size, p, I_full, keep):
    """Skipped picks keep their slice of the IBS half in BIL (registered idle rule)."""
    out = []
    saved = s.I
    try:
        for d in s.days:
            legs = I_full.get(d, [])
            kept = [lg for lg in legs if keep(d, lg[0])]
            n, k = len(legs), len(kept)
            if n == 0 or k == n:
                s.I = I_full; q = p; extra = 0.0
            else:
                s.I = {d: kept} if k else {}
                q = dataclasses.replace(p, ibs_w=p.ibs_w * k / n)
                b = s.bil.get(d, 0.0); b = float(b) if np.isfinite(b) else 0.0
                extra = p.ibs_w * size * (n - k) / n * b
            out.append((s.day_pnl(size, d, q)[0] + extra) / size)
    finally:
        s.I = saved
    return pd.Series(out, index=s.days)


# ------------------------------------------------------------ judging
def judge(log, lab, r, base, rng_seed=9):
    d = r - base
    half = [d[(d.index >= a) & (d.index <= z)].mean() * 252 * 100 for _, a, z in HALVES]
    t = nw_t(d.values)
    rng = np.random.default_rng(rng_seed); X = d.values
    sims = np.array([(X * rng.choice([-1, 1], size=len(X))).mean() for _ in range(1000)])
    pct = float((sims < X.mean()).mean() * 100)
    sr, sb = B.stats(r), B.stats(base)
    inc, ddd = (sr[0] - sb[0]) * 100, (sr[2] - sb[2]) * 100
    ok = half[0] > 0 and half[1] > 0 and t >= 2.0 and pct >= 95 and ddd >= -2.0
    log(f"    {lab:22s} {sr[0]*100:5.1f}/{sr[1]:4.2f}/{sr[2]*100:4.0f}  inc {inc:+5.2f}pp "
        f"({half[0]:+5.2f}/{half[1]:+5.2f})  t {t:+5.2f}  plac {pct:3.0f}%  dDD {ddd:+4.1f}  "
        f"{'PASS' if ok else 'fail'}")
    return ok


def main():
    t0 = time.time()
    f = open(OUT, "w")

    def log(*a):
        x = " ".join(str(i) for i in a)
        print(x, flush=True); f.write(x + "\n"); f.flush()

    log("== Round 18 (Discord ideas): Studies AS, AT; started", pd.Timestamp.now(), "==")
    s = load_sim(raw_price=True)
    s.N = B.night_days(raw_price=True, max_corr=0.7)
    I_full = B.ibs_days()
    s.I = I_full

    books = {
        "V7": dict(night_w=0.5, ibs_w=0.5, ibs_cost_bps=1.0, noise={"QQQ": 0.5, "SMH": 0.5},
                   noise_cap=0.75, tilt="live", weekend_scale=0.5, conviction_w=0.0),
        "IBS+night": dict(night_w=0.5, ibs_w=0.5, ibs_cost_bps=1.0, noise_on=False,
                          tilt="live", weekend_scale=0.5, conviction_w=0.0),
    }
    costs = (2.5, "tier_hi")
    passes = {}

    # ---------------- Study AS
    log("\n######## Study AS — overnight budget split by trailing metrics")
    for c in costs:
        p0 = B.Params(**{**books["V7"], "night_cost": c})
        u = unit_legs(s, p0)
        log(f"\n-- night cost {c} per side: leg unit returns (ann. mean / Sharpe) "
            f"night {u.night.mean()*25200:.1f}%/{u.night.mean()/u.night.std()*15.87:.2f}  "
            f"ibs {u.ibs.mean()*25200:.1f}%/{u.ibs.mean()/u.ibs.std()*15.87:.2f}  corr {u.corr().iloc[0,1]:+.2f}")
        W = {k: as_weights(u, k) for k in ("AS1", "AS2", "AS3")}
        for k, w in W.items():
            log(f"   {k} night weight: mean {w.mean():.2f}  sd {w.std():.2f}  "
                f"at clip {((w <= 0.2) | (w >= 0.8)).mean():.0%}")
        for bk, bp in books.items():
            p = B.Params(**{**bp, "night_cost": c})
            log(f"  [{bk}]  full CAGR/Sh/DD")
            for E in SIZES:
                base = replay_as(s, E, p, None)
                sb = B.stats(base)
                log(f"   ${E/1e3:5.1f}k fixed .5/.5            {sb[0]*100:5.1f}/{sb[1]:4.2f}/{sb[2]*100:4.0f}")
                for k, w in W.items():
                    ok = judge(log, f"{k}", replay_as(s, E, p, w), base)
                    passes.setdefault(k, []).append(ok)

    # ---------------- Study AT
    log("\n######## Study AT — vol-ratio / trend-slope conditioning of IBS picks")
    F = at_flags(I_full)
    log("\n-- per-trade gross (open->open, -2bp), kept vs skipped, by period")
    periods = (("2016-20", "2016-01-01", "2020-12-31"), ("2021-23", "2021-01-01", "2023-12-31"),
               ("2024-26", "2024-01-01", "2026-12-31"))
    rows = [(d, sym, r - 2e-4, F[(d, sym)]) for d, legs in I_full.items() for sym, _, r in legs]
    log(f"   picks {len(rows)}, first {min(I_full)} ; VR median {np.nanmedian([x[3]['vr'] for x in rows]):.2f}")
    gap_sign = {}
    for k in ("AT1", "AT2", "AT3"):
        kr = keep_rule(k)
        line = []
        for pl, a, z in periods:
            sel = [(x[2], kr(x[3])) for x in rows if pd.Timestamp(a) <= x[0] <= pd.Timestamp(z)]
            kp = np.array([g for g, kk in sel if kk]); sk = np.array([g for g, kk in sel if not kk])
            if len(sk) > 1 and len(kp) > 1:
                gap = kp.mean() - sk.mean()
                tt = gap / np.sqrt(kp.var(ddof=1) / len(kp) + sk.var(ddof=1) / len(sk))
            else:
                gap, tt = np.nan, np.nan
            if pl == "2016-20":
                gap_sign[k] = gap > 0
            line.append(f"{pl}: keep {kp.mean()*1e4 if len(kp) else np.nan:+6.1f}bp n{len(kp):4d} | "
                        f"skip {sk.mean()*1e4 if len(sk) else np.nan:+6.1f}bp n{len(sk):4d} | gap t {tt:+5.2f}")
        log(f"   {k}: " + "\n        ".join(line))
    for c in costs:
        for bk, bp in books.items():
            p = B.Params(**{**bp, "night_cost": c})
            log(f"\n  [{bk}, night cost {c}]  full CAGR/Sh/DD")
            for E in SIZES:
                s.I = I_full
                base = replay_as(s, E, p, None)
                sb = B.stats(base)
                log(f"   ${E/1e3:5.1f}k shipped IBS            {sb[0]*100:5.1f}/{sb[1]:4.2f}/{sb[2]*100:4.0f}")
                for k in ("AT1", "AT2", "AT3"):
                    kr = keep_rule(k)
                    keep = lambda d, sym, kr=kr: kr(F[(d, sym)])
                    ok = judge(log, k, replay_at(s, E, p, I_full, keep), base)
                    passes.setdefault(k, []).append(ok)

    log("\n######## verdicts (every size x book x cost must pass; AT also needs the 2016-20 gap > 0)")
    for k, v in passes.items():
        extra = "" if not k.startswith("AT") else f"  2016-20 gap>0: {gap_sign.get(k)}"
        allok = all(v) and (gap_sign.get(k, True) if k.startswith("AT") else True)
        log(f"   {k}: {sum(v)}/{len(v)} cells pass{extra} -> {'SHADOW' if allok else 'DEAD'}")
    log(f"\ndone {time.time()-t0:.0f}s")
    f.close()


if __name__ == "__main__":
    main()
