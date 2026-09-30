"""Round 16, Study AK: more rare setups for the conviction trade + a latency report (round1_prose.md Round 16 AK).

    PYTHONPATH=. .venv/bin/python -m research.sim.conviction_ak        # ~20 s

One conviction trade per day at most, weight 0.5 (the allowance reserved at the open is unchanged, so the noise leg is
unchanged). AK1: a second TQQQ breakout after a failed strong first one. AK2-4: SMH / SPY / IWM first breakouts on days
with no TQQQ trade, 3x notional of the 1x ETF. AK5: the three together, earliest first.
"""
from __future__ import annotations

import pickle

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import book as B
from . import conv2 as CV
from . import data as D
from . import program_books as PB
from . import taxable_frontier as TF
from .conviction_af import BP_RES, HALVES, SCR, SIZES

N_PROGRAM = 642
SIDE = {"TQQQ": (1.5, 3.0), "ETF": (1.5, 3.0)}   # per side, per unit weight (1x ETFs: 0.5 / 1bp on 3x notional)
FILL = ("SMH", "SPY", "IWM")
LATE_EXIT = 330                                  # 15:00


class Day:
    def __init__(self, sym, lookback=14):
        M = D.minutes(sym)
        self.C, V = M["close"].values, M["volume"].values
        self.O = M["open"].values[:, 0]
        self.days = M["close"].index
        self.pos = {d: i for i, d in enumerate(self.days)}
        self.move = np.abs(self.C / self.O[:, None] - 1)
        self.prevc = np.r_[np.nan, self.C[:-1, -1]]
        self.vwap = np.cumsum(self.C * V, axis=1) / np.maximum(np.cumsum(V, axis=1), 1)
        self.lb_ = lookback

    def bands(self, i):
        sig = sg.noise_sigma(self.move[i - self.lb_:i])
        ub, lb = sg.noise_bounds(self.O[i], self.prevc[i], sig)
        return sig, ub, lb

    def trade(self, d, strength_min, after=None, delay=0):
        """First breakout at a decision minute > after (None: the day's first); None if none or too weak.
        Returns (m0, xm, dir, gross, how). Fills at the close of minute m + delay (15:57 exit at minute 389)."""
        i = self.pos.get(d)
        if i is None or i <= self.lb_:
            return None
        C = self.C
        sig, ub, lb = self.bands(i)
        s, m0 = 0, None
        for m in range(sg.NOISE_FIRST, 390, sg.NOISE_STEP):
            if after is not None and m <= after:
                continue
            s, st = sg.breakout_strength(C[i, m], ub[m], lb[m], sig[m])
            if s:
                m0 = m; break
        if not s or st < strength_min:
            return None
        e = C[i, min(m0 + delay, 389)]
        for m in range(m0 + sg.NOISE_STEP, 390, sg.NOISE_STEP):
            p = C[i, m]
            if (s == 1 and p < max(ub[m], self.vwap[i, m])) or (s == -1 and p > min(lb[m], self.vwap[i, m])):
                return m0, m, s, s * (C[i, min(m + delay, 389)] / e - 1), "band"
        return m0, 389, s, s * (C[i, 389] / e - 1), "close"


def evaluate(lab, per_trade, days, b3, rng_seed=21):
    """per_trade: Series date -> 0.5 x net (added trades only)."""
    inc = pd.Series(0.0, index=days)
    k = per_trade.index.intersection(days)
    inc.loc[k] = per_trade.loc[k]
    rng = np.random.default_rng(rng_seed)
    X = per_trade.values
    sims = np.array([(X * rng.choice([-1, 1], size=len(X))).sum() / len(days) for _ in range(1000)])
    pct = float((sims < inc.mean()).mean() * 100)
    r0, e0 = b3["r"], b3["eh"]
    i2 = inc.reindex(r0.index).fillna(0.0)
    rv, ev = r0 + i2, e0 + i2 - 0.5 * i2.mean()
    mc = TF.mc_tax(ev, 0.35, start=3000, monthly=1000)
    ds = PB.dsr(inc, n_trials=N_PROGRAM)
    print(f"  {lab:22s} n {len(per_trade):4d} ({len(per_trade)/10.7:4.1f}/yr) " +
          "  ".join(f"{h} {inc[a:z].mean()*252*100:+5.2f}pp" for h, a, z in HALVES) +
          f" | NW t {TF.nw_t(inc):+5.2f} | placebo {pct:5.1f} | B3 maxDD {B.stats(rv)[2]*100:5.1f} (base {B.stats(r0)[2]*100:5.1f}) "
          f"| P50 {mc['dd50']:.1%} (base {b3['mc']['dd50']:.1%}) | DSR {ds['dsr']:.2f}", flush=True)
    a, b = inc.mean() * 252, inc["2024":].mean() * 252
    print("      $/yr " + " | ".join(f"${E/1e3:g}k {a*E:+7,.0f} ({b*E:+7,.0f})" for E in SIZES))
    return dict(inc=inc, pct=pct, mc=mc, dsr=ds)


def main():
    tq = Day("TQQQ")
    days = pd.DatetimeIndex(D.minutes("QQQ")["close"].index[15:])
    base = {d: tq.trade(d, B.STRENGTH_MIN) for d in tq.days}
    base = {d: t for d, t in base.items() if t is not None}
    bo = B.breakout_days()
    chk = pd.Series({d: t[3] - 3e-4 for d, t in base.items()}) - bo
    print(f"base reproduces book.breakout_days: n {len(base)} vs {len(bo)}, max |diff| {np.nanmax(np.abs(chk.values)):.2e}")
    bp = pickle.load(open(BP_RES, "rb"))["res"]
    b3 = bp[("B3 moderate10c", "M2 base", "tier_hi")]

    # ---------------- latency report
    print("\n== latency report: shipped trade, fills at the close of minute m+k (EV/trade at 3bp/side; $/yr at $100k, w .5)")
    for k in (0, 1, 2):
        g = pd.Series({d: t[3] for d in base if (t := tq.trade(d, B.STRENGTH_MIN, delay=k)) is not None}) - 6e-4
        print(f"  delay {k} min: " + "  ".join(f"{h} {g[a:z].mean()*1e4:+6.1f}bp" for h, a, z in HALVES) +
              f" | full {g.mean()*1e4:+6.1f}bp | ${0.5*g.sum()/10.7*1e5:+,.0f}/yr")

    # ---------------- AK1 second breakout
    print("\n== variants (stressed costs, 0.5 of equity per added trade)")
    res = {}
    sec = {}
    for d, t in base.items():
        m0, xm, s, g, how = t
        if how == "band" and xm < LATE_EXIT:
            t2 = tq.trade(d, B.STRENGTH_MIN, after=xm)
            if t2 is not None:
                sec[d] = 0.5 * (t2[3] - 2 * SIDE["TQQQ"][1] / 1e4)
    sec = pd.Series(sec)
    print(f"  AK1: second trades same direction as the first: "
          f"{np.mean([tq.trade(d, B.STRENGTH_MIN, after=base[d][1])[2] == base[d][2] for d in sec.index]):.0%}")
    res["AK1 second breakout"] = evaluate("AK1 second breakout", sec, days, b3)

    # ---------------- fill-in ETFs
    etf = {s: Day(s) for s in FILL}
    thr = {}
    for s in FILL:
        fb = CV.first_breakouts(s)
        thr[s] = float(fb.loc[:"2023-12-31", "strength"].median())
    print("  fill-in thresholds (2016-23 median first-breakout strength): " + ", ".join(f"{s} {v:.3f}" for s, v in thr.items()))
    trades = {s: {} for s in FILL}
    for s in FILL:
        for d in etf[s].days:
            t = etf[s].trade(d, thr[s])
            if t is not None:
                trades[s][d] = t
        both = [d for d in trades[s] if d in base]
        a = np.array([base[d][3] for d in both]); b = np.array([3 * trades[s][d][3] for d in both])
        print(f"  {s}: {len(trades[s])} strong first breakouts; on {len(both)} TQQQ-trade days corr with the TQQQ trade "
              f"{np.corrcoef(a, b)[0, 1]:+.2f}, same direction {np.mean([base[d][2] == trades[s][d][2] for d in both]):.0%}")
    for k, s in zip(("AK2", "AK3", "AK4"), FILL):
        x = pd.Series({d: 0.5 * (3 * t[3] - 2 * SIDE["ETF"][1] / 1e4) for d, t in trades[s].items() if d not in base})
        res[f"{k} {s} fill-in"] = evaluate(f"{k} {s} fill-in", x, days, b3)
    x = {}
    for d in sorted(set().union(*[trades[s].keys() for s in FILL])):
        if d in base:
            continue
        c = [(trades[s][d][0], j, s) for j, s in enumerate(FILL) if d in trades[s]]
        m, _, s = min(c)
        x[d] = 0.5 * (3 * trades[s][d][3] - 2 * SIDE["ETF"][1] / 1e4)
    res["AK5 all three"] = evaluate("AK5 all three", pd.Series(x), days, b3)
    print("\n== per added trade, net at stressed cost (0.5 weight excluded): EV by half")
    for lab, r in res.items():
        pt = r["inc"][r["inc"] != 0] * 2
        print(f"  {lab:22s} " + "  ".join(f"{h} {pt[a:z].mean()*1e4:+6.1f}bp (n {len(pt[a:z])})" for h, a, z in HALVES))
    pickle.dump(res, open(SCR / "conviction_ak_res.pkl", "wb"))


if __name__ == "__main__":
    main()
