"""NOISE-DIAG (diagnostic, no N): WHERE does the intraday breakout leg lose in 2025-26? Per-trade anatomy by year
(entry hour, direction, exit reason, hold) and QQQ intraday persistence metrics by year. Nothing is judged here.

    PYTHONPATH=. .venv/bin/python -m research.sim.noise_diag   # -> data/research/program/noise_diag_out.txt
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from research.sim.noise_recent import W, cfg
from swingtrader.daybook import shadow as sh
from swingtrader.daybook.signals import breakout_strength, noise_bounds, vol_leverage

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/noise_diag_out.txt"
LAG, COST = 30, 0.5
lines: list[str] = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    lines.append(s)


def trades_feat(S, sym, w, lag):
    """trades_for with anatomy: entry/exit minute, reason, strength, and the move from entry to the close (follow-through)."""
    out = []; days = list(S)
    for k, day in enumerate(days):
        prev = days[:k]
        if len(prev) < 5: continue
        hist = prev[-cfg.lookback:]; T = S[day]; C, V = T["close"], T["volume"]
        if not np.isfinite(C).any(): continue
        moves = np.array([np.abs(S[d]["close"] / S[d]["open"] - 1.0) for d in hist])
        sigma = np.nanmean(moves, axis=0)
        ub, lb = noise_bounds(T["open"], S[prev[-1]]["close"][-1], sigma)
        pv = np.cumsum(C * V) / np.maximum(np.cumsum(V), 1); pv = np.where(np.isfinite(pv), pv, C)
        closes = np.array([S[d]["close"][-1] for d in days[:k + 1]])
        lev = vol_leverage(closes, cfg.target_vol, cfg.max_lev)
        if lev <= 0: continue
        pos = 0; ep = 0.0; em = 0; stg = 0.0
        def fm(m): return min(m + lag, cfg.close_min)
        def rec(mx, reason):
            xp = float(C[mx]); cl = float(C[cfg.close_min])
            out.append(dict(date=day, sym=sym, dir=pos, gross=(xp / ep - 1) * pos * 1e4, lev=lev * w, entry_m=em, exit_m=mx,
                            hold=mx - em, reason=reason, strength=stg, to_close=(cl / ep - 1) * pos * 1e4,
                            day_oc=(float(C[-1]) / float(T["open"]) - 1) * 1e4))
        for m in sh.DEC:
            p = float(C[m])
            if pos == 1 and p < max(ub[m], pv[m]): rec(fm(m), "band/vwap"); pos = 0
            elif pos == -1 and p > min(lb[m], pv[m]): rec(fm(m), "band/vwap"); pos = 0
            if pos == 0:
                d, s_ = breakout_strength(p, ub[m], lb[m], sigma[m])
                if d: pos, ep, em, stg = d, float(C[fm(m)]), fm(m), float(s_)
        if pos: rec(cfg.close_min, "close")
    return pd.DataFrame(out)


def persistence(S_qqq):
    """Per year: 30-min return lag-1 autocorr, variance ratio (daily var / 13 x 30-min var), share of V-days, first-hour continuation."""
    rows = []
    for day, T in S_qqq.items():
        C = T["close"]
        if not np.isfinite(C).any(): continue
        o = float(T["open"]); cl = float(C[-1])
        half = [float(C[m]) for m in range(29, 390, 30)] + [cl]          # 30-min closes
        r30 = np.diff(np.log(np.array([o] + half)))
        exc = max(abs(np.nanmax(C) / o - 1), abs(np.nanmin(C) / o - 1)) * 1e4
        rows.append(dict(year=pd.Timestamp(day).year, oc=np.log(cl / o), r30=r30, exc=exc, oc_bp=(cl / o - 1) * 1e4,
                         first=float(C[59]) / o - 1, rest=cl / float(C[59]) - 1))
    D = pd.DataFrame(rows)
    say("\nQQQ intraday persistence by year: AC1(30m) | VR(day/13x30m) | V-days (excursion>=75bp & |close-open|<25bp) | corr(first hour, rest) | mean |o->c| bp")
    for y, g in D.groupby("year"):
        r = np.concatenate(g["r30"].to_list())
        ac = np.corrcoef(r[:-1], r[1:])[0, 1]
        vr = g["oc"].var() / (13 * r.var())
        vd = ((g["exc"] >= 75) & (g["oc_bp"].abs() < 25)).mean()
        fc = np.corrcoef(g["first"], g["rest"])[0, 1]
        say(f"  {y}: {ac:+.3f} | {vr:.2f} | {vd:4.0%} | {fc:+.2f} | {g['oc_bp'].abs().mean():5.0f}")


def main() -> int:
    S = {s: sh._sessions_cache(s, 14, None) for s in W}
    T = pd.concat([trades_feat(S[s], s, W[s], LAG) for s in W]).reset_index(drop=True)
    T["date"] = pd.to_datetime(T["date"]); T["net"] = T["gross"] - 2 * COST; T["year"] = T["date"].dt.year
    T["hour"] = pd.cut(T["entry_m"], [0, 90, 180, 300, 390], labels=["10:00-11:00", "11:00-12:30", "12:30-14:30", "14:30-close"])
    say(f"NOISE-DIAG: lag {LAG}, {COST}bp/fill, trades {len(T)}, {T['date'].min().date()}..{T['date'].max().date()}")

    def blk(title, keys):
        say(f"\n{title}  (cells: n / mean net bp / hit%)")
        piv = T.groupby(["year"] + keys)["net"].agg(["size", "mean", lambda x: (x > 0).mean() * 100])
        for y in sorted(T["year"].unique()):
            g = piv.loc[y]
            say(f"  {y}: " + " | ".join(f"{str(k):>12s} {int(r.iloc[0]):4d}/{r.iloc[1]:+6.1f}/{r.iloc[2]:3.0f}" for k, r in g.iterrows()))
    blk("by direction", ["dir"])
    blk("by entry hour", ["hour"])
    blk("by exit reason", ["reason"])
    say("\nfollow-through: mean net bp (as traded) vs mean to-close bp (if held to 15:57), by year, with median hold minutes")
    for y, g in T.groupby("year"):
        say(f"  {y}: traded {g['net'].mean():+6.1f} | to close {g['to_close'].mean():+6.1f} | hold med {g['hold'].median():4.0f}m | "
            f"stopped-then-reversed (band exit, to_close > 0) {((g['reason'] == 'band/vwap') & (g['to_close'] > 0)).mean():4.0%} | "
            f"trades/day {len(g) / g['date'].nunique():.2f} | 2+ trades same day & sym {(g.groupby(['date', 'sym']).size() >= 2).mean():4.0%}")
    say("\n2025-26 vs 2021-24, by (direction, hour): n / mean net bp")
    for lab, m in (("2021-24", (T.year >= 2021) & (T.year <= 2024)), ("2025-26", T.year >= 2025)):
        g = T[m].groupby(["dir", "hour"], observed=True)["net"].agg(["size", "mean"])
        say(f"  {lab}: " + " | ".join(f"{'L' if d == 1 else 'S'} {h} {int(r['size'])}/{r['mean']:+.1f}" for (d, h), r in g.iterrows()))
    persistence(S["QQQ"])
    OUT.write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
