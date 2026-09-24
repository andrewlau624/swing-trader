"""Conviction trade on SOXL: does the TQQQ strong-first-breakout rule
(addenda 8 / 19) add anything on the 3x semis ETF?

    .venv/bin/python -m research.sim.conv2

Same rule as book.breakout_days, signal on the traded ETF itself (as TQQQ
uses TQQQ); short side = SOXS bought, modelled as -SOXL intraday. The
strength threshold is SOXL's OWN 2016-23 median first-breakout strength,
fixed before 2024-26 is looked at (TQQQ's 0.341 is re-derived as a check).

Book variants on V7 (crash guards, dedupe 0.7, QQQ+SMH intraday), daytime
margin ibs_w + noise_cap + conviction <= 2:
  V7      TQQQ 0.5, intraday 1.0x                        (shipped, shadow)
  a       SOXL 0.5 instead of TQQQ, intraday 1.0x
  b       TQQQ 0.25 + SOXL 0.25, intraday 1.0x
  c       TQQQ 0.5 + SOXL 0.5, intraday 0.5x
Adoption: CAGR up in both halves, full Sharpe down <= 0.05, at tier AND tier_hi.
"""
from __future__ import annotations

import copy

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import book as B
from . import data as D
from .validate import load_sim

COST = {"TQQQ": 1.5, "SOXL": 2.5}      # per side, bps (SOXL: ~1c on $20-30 -> ~4bp quoted spread)
S2 = {"QQQ": 0.5, "SMH": 0.5}


def first_breakouts(sym: str, lookback: int = 14) -> pd.DataFrame:
    """Every day's FIRST noise-area breakout: strength and gross return of
    the trade the rule would take (before the threshold)."""
    M = D.minutes(sym)
    C, V = M["close"].values, M["volume"].values
    O = M["open"].values[:, 0]
    days = M["close"].index
    move = np.abs(C / O[:, None] - 1)
    prevc = np.r_[np.nan, C[:-1, -1]]
    vwap = np.cumsum(C * V, axis=1) / np.maximum(np.cumsum(V, axis=1), 1)
    rows = []
    for i in range(lookback + 1, len(days)):
        sig = sg.noise_sigma(move[i - lookback:i])
        ub, lb = sg.noise_bounds(O[i], prevc[i], sig)
        pos, e, strength, x = 0, None, 0.0, None
        for m in range(sg.NOISE_FIRST, 390, sg.NOISE_STEP):
            p = C[i, m]
            if pos == 0:
                pos, strength = sg.breakout_strength(p, ub[m], lb[m], sig[m])
                e = p
            elif (pos == 1 and p < max(ub[m], vwap[i, m])) or (pos == -1 and p > min(lb[m], vwap[i, m])):
                x = p; break
        if pos == 0:
            continue
        x = C[i, 389] if x is None else x
        rows.append((days[i], pos, strength, pos * (x / e - 1)))
    return pd.DataFrame(rows, columns=["date", "dir", "strength", "gross"]).set_index("date")


def trades(fb: pd.DataFrame, thr: float, cost: float) -> pd.Series:
    t = fb[fb["strength"] >= thr]
    return t["gross"] - 2 * cost / 1e4


def halves(df):
    r = df["r"]
    return [B.stats(r[:"2023-12-31"]), B.stats(r["2024-01-01":]), B.stats(r)]


def fmt(h):
    return "  ".join(f"{c*100:5.1f}/{s:4.2f}/{d*100:4.0f}" for c, s, d in h)


def main():
    fb = {s: first_breakouts(s) for s in COST}
    thr = {s: float(fb[s].loc[:"2023-12-31", "strength"].median()) for s in COST}
    print("in-sample (2016-23) median first-breakout strength:",
          {s: round(v, 3) for s, v in thr.items()}, "(TQQQ shipped 0.341)")
    thr["TQQQ"] = B.STRENGTH_MIN

    print("\n== standalone, per trade net of costs (bp), by year")
    T = {s: trades(fb[s], thr[s], COST[s]) for s in COST}
    yrs = sorted(set(T["TQQQ"].index.year) | set(T["SOXL"].index.year))
    print("      " + " ".join(f"{y:>6d}" for y in yrs) + "   16-23   24-26  win  n/yr")
    for s, t in T.items():
        by = t.groupby(t.index.year).mean() * 1e4
        a, b = t[:"2023-12-31"], t["2024-01-01":]
        print(f"{s:5s} " + " ".join(f"{by.get(y, np.nan):+6.0f}" for y in yrs)
              + f"  {a.mean()*1e4:+6.1f}  {b.mean()*1e4:+6.1f}  {(t > 0).mean():.0%}"
              f"  {len(t) / (len(fb[s]) and (fb[s].index[-1] - fb[s].index[0]).days / 365.25):4.0f}")
        for lab, x in (("16-23", a), ("24-26", b)):
            tt = x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))
            print(f"      {lab}: n {len(x)}, t {tt:+.2f}")
    j = pd.concat([T["TQQQ"], T["SOXL"]], axis=1, join="inner")
    both = T["TQQQ"].index.intersection(T["SOXL"].index)
    same = (fb["TQQQ"].loc[both, "dir"] == fb["SOXL"].loc[both, "dir"]).mean()
    cr = pd.concat([T["TQQQ"], T["SOXL"]], axis=1).fillna(0).corr().iloc[0, 1]
    print(f"days both trade: {len(both)} (same direction {same:.0%}); "
          f"corr of daily P&L (0 on no-trade days) {cr:.2f}")
    print("SOXL cost sensitivity (bp/trade 16-23 / 24-26):",
          ", ".join(f"{c}bp: {trades(fb['SOXL'], thr['SOXL'], c)[:'2023'].mean()*1e4:+.0f} / "
                    f"{trades(fb['SOXL'], thr['SOXL'], c)['2024':].mean()*1e4:+.0f}" for c in (1.5, 2.5, 4.0)))

    s = load_sim()
    s7 = copy.copy(s); s7.N = B.night_days(max_corr=0.7)
    V7 = dict(tilt="live", noise=S2, weekend_scale=0.5, conviction_w=0.5, noise_cap=1.0)

    def run(bo: pd.Series, cost: str, **kw):
        z = copy.copy(s7); z.BO = bo
        return z.replay(B.Params(**{**V7, **kw, "night_cost": cost}))

    def combo(wt: float, ws: float, soxl_cost: float = COST["SOXL"]):
        sx = trades(fb["SOXL"], thr["SOXL"], soxl_cost)
        return (wt * T["TQQQ"]).add(ws * sx, fill_value=0.0)

    variants = {
        "V7: TQQQ 0.5, intraday 1.0x": (combo(1.0, 0.0), {}),
        "a: SOXL 0.5 instead": (combo(0.0, 1.0), {}),
        "b: TQQQ .25 + SOXL .25": (combo(0.5, 0.5), {}),
        "c: TQQQ .5 + SOXL .5, intraday 0.5x": (combo(1.0, 1.0), {"noise_cap": 0.5}),
        "c@4bp SOXL": (combo(1.0, 1.0, 4.0), {"noise_cap": 0.5}),
    }
    print(f"\n== book, $3k + $1k/21 sessions   {'2021-23':>16s} {'2024-26':>16s} {'full':>16s}   end $")
    for cost in ("tier", "tier_hi"):
        print(f"-- night costs {cost}")
        base = None
        for lab, (bo, kw) in variants.items():
            df = run(bo, cost, **kw); h = halves(df)
            base = base or h
            ok = (h[0][0] > base[0][0] and h[1][0] > base[1][0] and h[2][1] >= base[2][1] - 0.05)
            print(f"{lab:38s} {fmt(h)}   ${df.E.iloc[-1]:>9,.0f}"
                  + ("" if h is base else f"   {'PASS' if ok else 'fail'}"))


if __name__ == "__main__":
    main()
