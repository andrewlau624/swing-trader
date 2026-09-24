"""More income per unit of time: faster decisions and more intraday signals.

    PYTHONPATH=. .venv/bin/python -m research.sim.cadence

Priors, written before running:
  1. Noise-leg decision step (5/10/15/30/60 min). Zarattini et al. tested
     30-min on SPY. Faster checks catch trends earlier but mostly add
     whipsaw: every extra re-test at the band is a round trip with no new
     information. Expect 15 >= 30 >= 5 on gross, 30 best net; 60 loses
     entries. First decision at 09:45 instead of 10:00: the band is widest
     relative to noise early on, so early breakouts should be weaker (addendum 8:
     59% of conviction entries at 10:00 already). Weak prior either way.
  2. Conviction: a SECOND strong breakout after the first was stopped out.
     The first-breakout rule works because the first break carries the day's
     information; a second break after a failed one is closer to chop.
     Expect weaker per trade; may still add if positive after costs.
     15-min conviction step: same whipsaw prior as (1).
  3. Exits: VWAP exit (shipped) cuts losers early; band-only holds longer
     (bigger wins, bigger losses); hold-to-close is pure trend. Expect the
     shipped exit to be best risk-adjusted; hold-to-close may raise CAGR.

Everything runs through swingtrader.daily.signals (noise_sigma, noise_bounds,
noise_decide, breakout_strength). Functions are copied from book.py with
step / first / exit parameters; book.py is not edited. Pick on 2016-23
standalone, judge on 2024-26; adoption = both book halves improve at 1x and
2x intraday costs.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg
from . import book as B
from . import data as D
from .validate import load_sim

_M = {}


def _mins(sym):
    if sym not in _M:
        M = D.minutes(sym)
        C, V = M["close"].values, M["volume"].values
        O = M["open"].values[:, 0]
        _M[sym] = (M["close"].index, C, V, O,
                   np.abs(C / O[:, None] - 1), np.r_[np.nan, C[:-1, -1]],
                   np.cumsum(C * V, axis=1) / np.maximum(np.cumsum(V, axis=1), 1))
    return _M[sym]


def noise_days(sym, step=30, first=30, exit="vwap", cost=0.5, lookback=14, target_vol=0.02):
    days, C, V, O, move, prevc, vwap = _mins(sym)
    dclose = pd.Series(C[:, -1], index=days)
    rows = []
    for i in range(lookback + 1, len(days)):
        sigma = sg.noise_sigma(move[i - lookback:i])
        ub, lb = sg.noise_bounds(O[i], prevc[i], sigma)
        lev = sg.noise_leverage(dclose.iloc[:i], target_vol, 1e9)
        pos, entry, pnl, trades, nrt = 0, None, 0.0, 0, 0
        for m in range(first, 390, step):
            p = C[i, m]
            if exit == "vwap":
                new = sg.noise_decide(pos, p, ub[m], lb[m], vwap[i, m])
            elif exit == "band":
                new = sg.noise_decide(pos, p, ub[m], lb[m], ub[m] if pos == 1 else lb[m])
            else:                           # hold to close: first entry only
                new = pos if pos != 0 else (1 if p > ub[m] else -1 if p < lb[m] else 0)
            if new != pos:
                if pos != 0:
                    pnl += pos * (p / entry - 1); trades += 1; nrt += 1
                if new != 0:
                    entry = p; trades += 1
                pos = new
        if pos != 0:
            pnl += pos * (C[i, 389] / entry - 1); trades += 1; nrt += 1
        rows.append((days[i], pnl - trades * cost / 1e4, lev, trades, nrt,
                     pnl))
    return pd.DataFrame(rows, columns=["date", "ret", "lev", "trades", "rt", "gross"]).set_index("date")


def breakout_days(sym="TQQQ", step=30, first=30, max_trades=1, cost=1.5, lookback=14,
                  smin=B.STRENGTH_MIN):
    """Day's FIRST breakout if strong; with max_trades=2, after a stop-out the
    NEXT breakout is taken too if it is strong (a weak one ends the day)."""
    days, C, V, O, move, prevc, vwap = _mins(sym)
    out, ntr = {}, {}
    for i in range(lookback + 1, len(days)):
        sig = sg.noise_sigma(move[i - lookback:i])
        ub, lb = sg.noise_bounds(O[i], prevc[i], sig)
        pos, e, tot, n, done = 0, None, 0.0, 0, False
        for m in range(first, 390, step):
            p = C[i, m]
            if pos == 0:
                if done:
                    break
                d, s = sg.breakout_strength(p, ub[m], lb[m], sig[m])
                if d == 0:
                    continue
                if s < smin:
                    break
                pos, e = d, p
            elif (pos == 1 and p < max(ub[m], vwap[i, m])) or (pos == -1 and p > min(lb[m], vwap[i, m])):
                tot += pos * (p / e - 1) - 2 * cost / 1e4; n += 1; pos = 0
                done = n >= max_trades
        if pos != 0:
            tot += pos * (C[i, 389] / e - 1) - 2 * cost / 1e4; n += 1
        if n:
            out[days[i]] = tot; ntr[days[i]] = n
    return pd.Series(out), pd.Series(ntr)


def _yrs(ix):
    return max(len(ix), 1) / 252


def sa_noise(dfs, a, b, cap=1.0):
    """Standalone QQQ+SMH half/half at the V7 cap: CAGR/Sharpe, bp per round trip, rt/yr."""
    parts = []
    for df in dfs:
        x = df[a:b]
        parts.append(np.minimum(x["lev"], cap) * 0.5 * x["ret"])
    r = pd.concat(parts, axis=1).fillna(0).sum(axis=1)
    c, s, _ = B.stats(r)
    rt = sum(df[a:b]["rt"].sum() for df in dfs)
    net = sum((df[a:b]["ret"]).sum() for df in dfs)
    return f"{c*100:5.1f}/{s:4.2f}  {net/rt*1e4:+5.1f}bp  {rt/len(dfs)/_yrs(r.index):5.0f}rt/yr"


def sa_conv(ser, n, a, b):
    x = ser[a:b]; k = n[a:b]
    t = x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else np.nan
    return f"{x.sum()/k.sum()*1e4:+5.1f}bp/trade (day t {t:4.2f}) {k.sum()/_yrs(pd.bdate_range(a, min(pd.Timestamp(b), x.index[-1]))):5.0f}/yr"


S2 = {"QQQ": 0.5, "SMH": 0.5}


def book(sim, nz=None, bo=None, cost_mult=1.0):
    old_nz, old_bo = dict(sim.NZ), getattr(sim, "BO", None)
    try:
        if nz:
            for k, v in nz.items():
                sim.NZ[k] = v
        sim.BO = bo if bo is not None else B.breakout_days(cost=1.5 * cost_mult)
        p = B.Params(tilt="live", noise=S2, weekend_scale=0.5, conviction_w=0.5, noise_cap=1.0)
        p.night_cost = "tier"
        r = sim.replay(p)["r"]
        f = lambda z: "%5.1f/%4.2f" % (B.stats(z)[0] * 100, B.stats(z)[1])
        return f(r[:"2023-12-31"]), f(r["2024-01-01":]), f(r), B.stats(r[:"2023-12-31"])[0], B.stats(r["2024-01-01":])[0]
    finally:
        sim.NZ.clear(); sim.NZ.update(old_nz); sim.BO = old_bo


def main():
    sim = load_sim()
    out = []
    for cm in (1.0, 2.0):
        print(f"\n===== intraday costs x{cm:g} (QQQ/SMH {0.5*cm:g}bp, TQQQ {1.5*cm:g}bp per side) =====")
        print("NOISE LEG standalone (QQQ+SMH, cap 1.0x)  2016-23 | 2024-26    ;  V7 book 2021-23 | 2024-26 | full")
        base = None
        for step, first, ex in [(30, 30, "vwap"), (5, 30, "vwap"), (10, 30, "vwap"), (15, 30, "vwap"),
                                (60, 30, "vwap"), (30, 15, "vwap"), (15, 15, "vwap"),
                                (30, 30, "band"), (30, 30, "close")]:
            dfs = {s: noise_days(s, step, first, ex, cost=0.5 * cm) for s in ("QQQ", "SMH")}
            bk = book(sim, nz=dfs, cost_mult=cm)
            if base is None:
                base = bk
            ok = bk[3] > base[3] and bk[4] > base[4]
            tag = f"step {step:2d} first {'10:00' if first == 30 else '09:45'} exit {ex:5}"
            print(f"{tag}: {sa_noise(dfs.values(), '2016', '2023')} | {sa_noise(dfs.values(), '2024', '2026')}"
                  f"  ;  {bk[0]} | {bk[1]} | {bk[2]}{'  <- both halves up' if ok and step != 30 or ok and ex != 'vwap' else ''}")
        print("CONVICTION TQQQ standalone  2016-23 | 2024-26    ;  V7 book 2021-23 | 2024-26 | full")
        for step, mt in [(30, 1), (30, 2), (15, 1), (15, 2)]:
            s, n = breakout_days(step=step, max_trades=mt, cost=1.5 * cm)
            bk = book(sim, bo=s, cost_mult=cm)
            print(f"step {step} max {mt}/day: {sa_conv(s, n, '2016', '2023')} | {sa_conv(s, n, '2024', '2026')}"
                  f"  ;  {bk[0]} | {bk[1]} | {bk[2]}")


if __name__ == "__main__":
    main()
