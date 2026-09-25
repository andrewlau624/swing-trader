"""End-of-day intraday momentum (Gao, Han, Li & Zhou 2018), addendum 27 candidate.

    PYTHONPATH=. .venv/bin/python -m research.sim.late_momentum

Claim: the first half-hour (prev close -> 10:00) and the 15:00-15:30 return
predict the last half-hour on SPY; leveraged-ETF rebalancing and hedging flows
push into the close in the direction of the day's move.

Timing matches the bot: signal from the 15:30 bar (minute 360), entry at the
15:31 decision (minute 361 close; +1 min delay test = minute 362), exit either
at the 15:57 flatten (minute 387 open) or at the official close auction (MOC,
submitted with the entry, well before the 15:50 cutoff).

Pre-registered variants (all reported):
  V1 sign(prev close -> 10:00)                          Gao's first half-hour
  V2 sign(open -> 15:30)                                the day's intraday trend
  V3 sign(15:00 -> 15:30)                               Gao's second predictor
  V4 sign(prev close -> 15:30) if |.| > 1 sigma(20d)    big-move days
  V5 sign(prev close -> 15:30) if |.| > 2 sigma(20d)    LETF rebalancing, very big days

Overlap: the live noise leg's position after its 15:30 decision is held to the
close. Late-leg trades are split by that position (same / flat / opposite).
Book: the late leg trades QQQ in the daytime margin the noise leg is NOT using
at 15:30: free = cap (0.75, V7) - noise gross at 15:30.
"""
from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import book as B
from . import data as D
from . import growth as G

SCR = Path("/private/tmp/claude-501/-Users-andrewlau-Documents-Code-Projects-swing-trader/"
           "cc100773-e955-4a4c-aa47-797c4a8c7acb/scratchpad")
PERIODS = [("2016-20", "2016", "2020"), ("2021-23", "2021", "2023"), ("2024-26", "2024", "2026")]
TIER, STRESS = 0.5, 2.0          # bp per side (the repo's intraday cost; stressed)
V7_CAP = 0.75                    # V7 intraday cap, fraction of equity (addendum 22)


def noise_pos_1530(sym: str, lookback: int = 14) -> pd.Series:
    """The live noise rule's position held from the 15:30 decision to the close."""
    M = D.minutes(sym)
    C, V = M["close"].values, M["volume"].values
    O = M["open"].values[:, 0]
    days = M["close"].index
    move = np.abs(C / O[:, None] - 1)
    prevc = np.r_[np.nan, C[:-1, -1]]
    vwap = np.cumsum(C * V, axis=1) / np.maximum(np.cumsum(V, axis=1), 1)
    out = {}
    for i in range(lookback + 1, len(days)):
        sigma = sg.noise_sigma(move[i - lookback:i])
        ub, lb = sg.noise_bounds(O[i], prevc[i], sigma)
        pos = 0
        for m in range(sg.NOISE_FIRST, 390, sg.NOISE_STEP):
            pos = sg.noise_decide(pos, C[i, m], ub[m], lb[m], vwap[i, m])
        out[days[i]] = pos
    return pd.Series(out)


def late_frame(sym: str) -> pd.DataFrame:
    M = D.minutes(sym)
    C, O = M["close"], M["open"]
    days = C.index
    auction = D.etf()["close"][sym].reindex(days)
    pc = C.iloc[:, 389].shift(1)
    f = pd.DataFrame(index=days)
    f["first"] = C.iloc[:, 30] / pc - 1
    f["o1530"] = C.iloc[:, 360] / O.iloc[:, 0] - 1
    f["l30"] = C.iloc[:, 360] / C.iloc[:, 330] - 1
    f["d1530"] = C.iloc[:, 360] / pc - 1
    f["sig20"] = (C.iloc[:, 389].pct_change()).rolling(20).std().shift(1)   # known at d-1
    ent, ent2 = C.iloc[:, 361], C.iloc[:, 362]
    f["r_57"] = O.iloc[:, 387] / ent - 1           # exit at the 15:57 flatten
    f["r_moc"] = auction / ent - 1                 # exit at the close auction
    f["r_moc_d1"] = auction / ent2 - 1             # one minute late in
    f["r_57_d1"] = O.iloc[:, 387] / ent2 - 1
    return f


def signals(f: pd.DataFrame) -> dict[str, pd.Series]:
    s = np.sign
    big1 = f.d1530.abs() > f.sig20
    big2 = f.d1530.abs() > 2 * f.sig20
    return {"V1 first half-hour": s(f["first"]),
            "V2 open->15:30": s(f.o1530),
            "V3 15:00->15:30": s(f.l30),
            "V4 day move > 1 sigma": s(f.d1530).where(big1, 0.0),
            "V5 day move > 2 sigma": s(f.d1530).where(big2, 0.0)}


def trade_rets(f, sig, col, cost):
    """Per-day unit return; 0 on no-trade days. Cost: 2 sides on trade days."""
    r = sig * f[col] - (sig != 0) * 2 * cost / 1e4
    return r.fillna(0.0)


def tstat(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 5 and x.std() > 0 else np.nan


def per_trade(r, sig, a, z):
    m = (sig[a:z] != 0)
    x = r[a:z][m]
    return x.mean() * 1e4, tstat(x), int(m.sum())


def placebo(f, sig, col, cost, a, z, seeds=100):
    """Random side on the same trade days: share of seeds the real rule beats."""
    m = (sig[a:z] != 0).values
    real = trade_rets(f[a:z], sig[a:z], col, cost)[m].mean()
    rng = np.random.default_rng(11)
    base = f[a:z][col].values[m]
    beats = 0
    for _ in range(seeds):
        side = rng.choice([-1.0, 1.0], size=m.sum())
        beats += real > np.nanmean(side * base - 2 * cost / 1e4)
    return beats / seeds


def main():
    L = []
    say = lambda s="": (print(s), L.append(s))
    frames = {s: late_frame(s) for s in ("SPY", "QQQ", "SMH")}
    npos = {s: noise_pos_1530(s) for s in ("QQQ", "SMH")}

    say("== 1. Standalone, 1x, per trade (bp, t, n) | CAGR/Sharpe of the unit series | placebo beats")
    for sym, f in frames.items():
        say(f"\n--- {sym}")
        for name, sig in signals(f).items():
            for col, cost, lab in (("r_moc", TIER, "MOC tier"), ("r_57", TIER, "15:57 tier"),
                                   ("r_moc", STRESS, "MOC 2bp"), ("r_moc_d1", TIER, "MOC +1min")):
                r = trade_rets(f, sig, col, cost)
                cells = []
                for p, a, z in PERIODS:
                    bp, t, n = per_trade(r, sig, a, z)
                    c, sh, dd = B.stats(r[a:z])
                    pb = placebo(f, sig, col, cost, a, z) if lab == "MOC tier" else np.nan
                    cells.append(f"{bp:+5.1f}bp t{t:+4.1f} n{n:4d} {c*100:+5.1f}%/{sh:+4.2f}"
                                 + (f" pb{pb:4.0%}" if np.isfinite(pb) else ""))
                say(f"{name:22s} {lab:10s} | " + " | ".join(cells))

    # fit / judge on QQQ MOC tier: best on 2016-20, best on 2021-23
    f = frames["QQQ"]; S = signals(f)
    score = lambda nm, a, z: B.stats(trade_rets(f, S[nm], "r_moc", TIER)[a:z])[1]
    b1 = max(S, key=lambda nm: score(nm, "2016", "2020"))
    b2 = max(S, key=lambda nm: score(nm, "2021", "2023"))
    say(f"\n== 2. Fit/judge (QQQ, MOC, tier, Sharpe): best on 2016-20 = {b1} -> "
        f"21-23 {score(b1,'2021','2023'):+.2f}, 24-26 {score(b1,'2024','2026'):+.2f}; "
        f"best on 2021-23 = {b2} -> 16-20 {score(b2,'2016','2020'):+.2f}, 24-26 {score(b2,'2024','2026'):+.2f}")

    say("\n== 3. Overlap with the live noise leg (QQQ late leg vs QQQ noise position held from 15:30)")
    nq = npos["QQQ"].reindex(f.index).fillna(0)
    for name, sig in S.items():
        r = trade_rets(f, sig, "r_moc", TIER)
        rel = np.sign(sig) * nq
        cells = []
        for grp, m in (("same", rel > 0), ("flat", (nq == 0) & (sig != 0)), ("opposite", rel < 0)):
            parts = []
            for p, a, z in PERIODS:
                x = r[a:z][m[a:z]]
                parts.append(f"{x.mean()*1e4:+5.1f}bp t{tstat(x):+4.1f} n{len(x):4d}")
            cells.append(f"{grp:8s} " + " | ".join(parts))
        say(f"{name}\n    " + "\n    ".join(cells))

    # ---------------------------------------------------------------- book
    say("\n== 4. V7 + late leg (QQQ, MOC) in the free daytime margin at 15:30")
    s = G.load_sim()
    kb = (1.0, 0.10, 0.5, 2, None)
    g, cap, conv, mult, nz = kb
    kw = G.cfg(g, conv, mult, nz)
    Ns = B.night_days(max_corr=0.7, max_name_pct=0.10); s.N = Ns
    base = {c: s.replay(B.Params(**{**G.V7, **kw, "night_cost": c})) for c in ("tier", "tier_hi")}
    # noise gross at 15:30 as V7 sizes it: min(lev, cap) * share, per symbol with a position
    gross = pd.Series(0.0, index=f.index)
    for sym in ("QQQ", "SMH"):
        z = s.NZ[sym]
        lev = z["lev"].reindex(f.index)
        gross += (npos[sym].reindex(f.index).fillna(0).abs() * np.minimum(lev, kw["noise_cap"]) * 0.5).fillna(0)
    free = (kw["noise_cap"] - gross).clip(lower=0)
    series = {"v7": base["tier"]["r"]}
    for name in (b1, "V4 day move > 1 sigma", "V5 day move > 2 sigma", "V1 first half-hour"):
        sig = S[name]
        for c, cost in (("tier", TIER), ("tier_hi", STRESS)):
            leg = (free * trade_rets(f, sig, "r_moc", cost)).reindex(base[c].index).fillna(0)
            r = base[c]["r"] + leg
            df = base[c].assign(r=r)
            say(f"{name:22s} {c:7s} " + B.summary(df, "")
                + f"   (V7: {B.summary(base[c], '')})")
            if c == "tier_hi":
                eh_v7 = G.eh(base[c])
                eh_p = eh_v7 + leg - 0.5 * leg.mean()
                a, b = B.stats(eh_v7), B.stats(eh_p)
                say(f"{'':22s} edge-halves tier_hi: V7 {a[0]*100:.1f}%/{a[1]:.2f}/{a[2]*100:.0f}  "
                    f"+leg {b[0]*100:.1f}%/{b[1]:.2f}/{b[2]*100:.0f}")
            if c == "tier" and name == b1:
                series.update(v7_plus=r, leg_unit=trade_rets(f, sig, "r_moc", TIER))
        say(f"{'':22s} avg free margin used on trade days {free[S[name] != 0].mean():.2f}x")
    pickle.dump(series, open(SCR / "r3_series.pkl", "wb"))
    (SCR / "r3_late_momentum.out").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
