"""Broker economics: cheaper margin and a real market-on-open order.

    .venv/bin/python -m research.sim.broker

Two questions from the hostile review (charge 2):
  1. Does overnight leverage (1.3x / 1.5x / 1.8x) pass the adoption rule --
     CAGR up in BOTH halves, Sharpe not much worse, at BOTH tier and tier_hi
     costs -- once margin costs ~6%/yr (IBKR-like) instead of Schwab's 12%?
  2. What is the night leg worth at 3 / 7.5 / 15 / 25bp per side on the OPEN
     SELL (true MOO vs emulated), with the close-auction buy kept on the tier?

Baseline is V7 = V5 (tilt, QQQ+SMH, weekend x0.5, dedupe 0.7) + the TQQQ
conviction trade at 0.5 with the intraday leg at 1.0x. Daytime buying power
is 2x, so at overnight weight w per leg the intraday cap is 2 - w - 0.5,
exactly what executor._gate computes.

book.py is not edited: exit-only costs go in through a wrapped cost_bps
(model = (entry_model, exit_bps) -> per-side mean, so 2c = entry + exit).
"""
from __future__ import annotations

import copy

import numpy as np

from . import book as B
from .validate import load_sim

_cost = B.cost_bps


def _cost_split(model, price, adv):
    if isinstance(model, tuple):
        entry, exit_bps = model
        return (_cost(entry, price, adv) + float(exit_bps)) / 2.0
    return _cost(model, price, adv)


B.cost_bps = _cost_split

S2 = {"QQQ": 0.5, "SMH": 0.5}
V7 = dict(tilt="live", noise=S2, weekend_scale=0.5, conviction_w=0.5, noise_cap=1.0)


def lev_kw(gross: float) -> dict:
    w = gross / 2
    return dict(night_w=w, ibs_w=w, noise_cap=max(0.0, 2.0 - w - 0.5))


def halves(df):
    r = df["r"]
    return [B.stats(r[:"2023-12-31"]), B.stats(r["2024-01-01":]), B.stats(r)]


def fmt(parts):
    return "  ".join(f"{c*100:5.1f}/{s:4.2f}/{d*100:4.0f}" for c, s, d in parts)


def main():
    s = load_sim()
    s7 = copy.copy(s); s7.N = B.night_days(max_corr=0.7)
    hdr = f"{'':34s} {'2021-23':>16s} {'2024-26':>16s} {'full':>16s}   end $ (dep)"
    print("== 1. overnight leverage x margin rate (V7 baseline, CAGR%/Sharpe/maxDD%)")
    res = {}
    for cost in ("tier", "tier_hi"):
        print(f"\n-- night costs: {cost}\n{hdr}")
        for m in (0.12, 0.06):
            for g in (1.0, 1.3, 1.5, 1.8):
                df = s7.replay(B.Params(**{**V7, **lev_kw(g), "night_cost": cost, "margin_rate": m}))
                h = halves(df); res[(cost, m, g)] = h
                mc = -df["r_cash"].clip(upper=0).sum()
                print(f"{f'margin {m:.0%}  overnight {g:.1f}x':34s} {fmt(h)}   "
                      f"${df.E.iloc[-1]:>9,.0f} ({df.dep.iloc[-1]:,.0f})")
    print("\n-- adoption rule vs 1.0x at the same margin rate and cost (both halves CAGR up; "
          "full Sharpe drop <= 0.10)")
    for cost in ("tier", "tier_hi"):
        for m in (0.12, 0.06):
            b = res[(cost, m, 1.0)]
            for g in (1.3, 1.5, 1.8):
                h = res[(cost, m, g)]
                d1, d2 = (h[0][0] - b[0][0]) * 100, (h[1][0] - b[1][0]) * 100
                dsh = h[2][1] - b[2][1]
                ok = d1 > 0 and d2 > 0 and dsh >= -0.10
                print(f"  {cost:7s} margin {m:.0%} {g:.1f}x: dCAGR {d1:+5.1f} / {d2:+5.1f}pp, "
                      f"dSharpe {dsh:+.2f}, dDD {(h[2][2]-b[2][2])*100:+.0f}pp -> {'PASS' if ok else 'fail'}")

    print("\n== 2. open-sell cost per side (entry at the close auction stays on 'tier'), V7 at 1.0x")
    print(hdr)
    base = None
    for x in (3.0, 7.5, 15.0, 25.0):
        df = s7.replay(B.Params(**{**V7, "night_cost": ("tier", x)}))
        base = base if base is not None else df
        rn = df["r_night"]
        print(f"{f'exit {x:4.1f}bp/side':34s} {fmt(halves(df))}   ${df.E.iloc[-1]:>9,.0f} "
              f"| night leg {rn.mean()*252*100:4.1f}%/yr of book")
    df = s7.replay(B.Params(**{**V7, "night_cost": "tier"}))
    print(f"{'reference: tier both sides':34s} {fmt(halves(df))}   ${df.E.iloc[-1]:>9,.0f}")

    print("\n== 2b. same, at 1.3x overnight and 6% margin (a broker with MOO AND cheap margin)")
    for x in (3.0, 7.5, 15.0, 25.0):
        df = s7.replay(B.Params(**{**V7, **lev_kw(1.3), "margin_rate": 0.06,
                                   "night_cost": ("tier", x)}))
        print(f"{f'exit {x:4.1f}bp/side':34s} {fmt(halves(df))}   ${df.E.iloc[-1]:>9,.0f}")


if __name__ == "__main__":
    main()
