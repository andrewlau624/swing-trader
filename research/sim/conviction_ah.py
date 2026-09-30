"""Round 16, Study AH: stops, targets, half-off and a pullback entry for the conviction trade
(round1_prose.md Round 16 AH).

    PYTHONPATH=. .venv/bin/python -m research.sim.conviction_ah        # ~1 min

Resting stop / target orders are checked on every TQQQ regular-hours minute after entry, on top of the shipped
band/VWAP exit at decision minutes and the 15:57 exit (minute 389 close, as book.breakout_days). A minute that
touches both is a stop. Unit u = sig[m0] x entry price.
"""
from __future__ import annotations

import pickle

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import book as B
from . import data as D
from . import program_books as PB
from . import taxable_frontier as TF
from .conviction_af import BP_RES, HALVES, SCR, SIZES

N_PROGRAM = 630
VARS = ("base", "AH1 stop 1u", "AH2 stop 2u", "AH3 target 2u", "AH4 target 4u", "AH5 half off at 2u", "AH6 pullback entry")
DEC = set(range(sg.NOISE_FIRST, 390, sg.NOISE_STEP))


def run_exit(s, e, m_start, i, C, H, L, O1, ub, lb, vw, stop=None, target=None, dec_from=None):
    """Gross return of a position opened at price e (direction s) and held from minute m_start+1. Returns (gross, exit
    minute, how). dec_from: first decision minute at which the band/VWAP exit applies."""
    dec_from = m_start + 1 if dec_from is None else dec_from
    for m in range(m_start + 1, 390):
        if stop is not None:
            hit = L[i, m] <= stop if s == 1 else H[i, m] >= stop
            if hit:
                px = min(stop, O1[i, m]) if s == 1 else max(stop, O1[i, m])
                return s * (px / e - 1), m, "stop"
        if target is not None:
            hit = H[i, m] >= target if s == 1 else L[i, m] <= target
            if hit:
                return s * (target / e - 1), m, "target"
        if m in DEC and m >= dec_from:
            p = C[i, m]
            if (s == 1 and p < max(ub[m], vw[i, m])) or (s == -1 and p > min(lb[m], vw[i, m])):
                return s * (p / e - 1), m, "band"
    return s * (C[i, 389] / e - 1), 389, "close"


def trades(sym="TQQQ", lookback=14, strength_min=B.STRENGTH_MIN) -> pd.DataFrame:
    M = D.minutes(sym)
    C, V, H, L, O1 = (M[k].values for k in ("close", "volume", "high", "low", "open"))
    O = O1[:, 0]
    days = M["close"].index
    move = np.abs(C / O[:, None] - 1)
    prevc = np.r_[np.nan, C[:-1, -1]]
    vw = np.cumsum(C * V, axis=1) / np.maximum(np.cumsum(V, axis=1), 1)
    rows = []
    for i in range(lookback + 1, len(days)):
        sig = sg.noise_sigma(move[i - lookback:i])
        ub, lb = sg.noise_bounds(O[i], prevc[i], sig)
        s, m0 = 0, None
        for m in range(sg.NOISE_FIRST, 390, sg.NOISE_STEP):
            s, strength = sg.breakout_strength(C[i, m], ub[m], lb[m], sig[m])
            if s:
                m0 = m; break
        if not s or strength < strength_min:
            continue
        e = C[i, m0]; u = sig[m0] * e
        g = {}
        g["base"] = run_exit(s, e, m0, i, C, H, L, O1, ub, lb, vw)
        g["AH1 stop 1u"] = run_exit(s, e, m0, i, C, H, L, O1, ub, lb, vw, stop=e - s * 1.0 * u)
        g["AH2 stop 2u"] = run_exit(s, e, m0, i, C, H, L, O1, ub, lb, vw, stop=e - s * 2.0 * u)
        g["AH3 target 2u"] = run_exit(s, e, m0, i, C, H, L, O1, ub, lb, vw, target=e + s * 2.0 * u)
        g["AH4 target 4u"] = run_exit(s, e, m0, i, C, H, L, O1, ub, lb, vw, target=e + s * 4.0 * u)
        t2 = g["AH3 target 2u"]
        if t2[2] == "target":
            g["AH5 half off at 2u"] = (0.5 * t2[0] + 0.5 * g["base"][0], g["base"][1], "half")
        else:
            g["AH5 half off at 2u"] = g["base"]
        lim = ub[m0] if s == 1 else lb[m0]
        fill = None
        for m in range(m0 + 1, min(m0 + 31, 390)):
            if (s == 1 and L[i, m] <= lim) or (s == -1 and H[i, m] >= lim):
                fill = m; break
        if fill is None:
            g["AH6 pullback entry"] = (np.nan, None, "skip")
        else:
            g["AH6 pullback entry"] = run_exit(s, lim, fill, i, C, H, L, O1, ub, lb, vw, dec_from=m0 + 30)
        rows.append(dict(date=days[i], dir=s, m0=m0, **{f"g_{k}": v[0] for k, v in g.items()},
                         **{f"how_{k}": v[2] for k, v in g.items()}))
    return pd.DataFrame(rows).set_index("date")


def main():
    T = trades()
    chk = (T["g_base"] - 3e-4) - B.breakout_days()
    print(f"base reproduces book.breakout_days: n {len(T)}, max |diff| {np.nanmax(np.abs(chk.values)):.2e}")
    bp = pickle.load(open(BP_RES, "rb"))["res"]
    b3 = bp[("B3 moderate10c", "M2 base", "tier_hi")]
    days = pd.DatetimeIndex(D.minutes("QQQ")["close"].index[15:])
    for side in (1.5, 3.0):
        c = 2 * side / 1e4
        print(f"\n== per trade at {side}bp/side: n / win / mean win / mean loss / EV / worst / exit mix")
        for v in VARS:
            g = T[f"g_{v}"]; net = (g - c).dropna()
            how = T[f"how_{v}"].value_counts(normalize=True)
            print(f"  {v:20s} n {len(net):4d} win {(net>0).mean():4.0%} W {net[net>0].mean()*1e4:+6.1f} L {net[net<=0].mean()*1e4:+6.1f} "
                  f"EV {net.mean()*1e4:+6.1f}bp worst {net.min()*100:+5.1f}% | " + " ".join(f"{k} {x:.0%}" for k, x in how.items()))
            for lab, a, z in HALVES:
                pass
    print("\n== EV per trade by half (3bp/side)")
    for v in VARS:
        net = (T[f"g_{v}"] - 6e-4)
        print(f"  {v:20s} " + "  ".join(f"{lab} {net[a:z].dropna().mean()*1e4:+6.1f}bp (n {net[a:z].notna().sum()})" for lab, a, z in HALVES))

    base_net = T["g_base"] - 6e-4
    cut_share = {}
    print("\n== increments vs the shipped exit, 0.5 of equity, 3bp/side")
    res = {}
    for v in VARS[1:]:
        vn = (T[f"g_{v}"] - 6e-4).fillna(0.0)          # AH6 skip -> no trade
        per = 0.5 * (vn - base_net)
        inc = pd.Series(0.0, index=days); inc.loc[per.index.intersection(days)] = per.reindex(days).dropna()
        rng = np.random.default_rng(18)
        X = per.values
        sims = np.array([(X * rng.choice([-1, 1], size=len(X))).sum() / len(days) for _ in range(1000)])
        pct = float((sims < inc.mean()).mean() * 100)
        r0, e0 = b3["r"], b3["eh"]
        i2 = inc.reindex(r0.index).fillna(0.0)
        rv, ev = r0 + i2, e0 + i2 - 0.5 * i2.mean()
        mc = TF.mc_tax(ev, 0.35, start=3000, monthly=1000)
        ds = PB.dsr(inc, n_trials=N_PROGRAM)
        changed = T[f"how_{v}"] != T["how_base"]
        cut_share[v] = float(base_net[changed].sum() / base_net.sum())
        res[v] = dict(inc=inc, pct=pct, mc=mc, dsr=ds)
        print(f"  {v:20s} " + "  ".join(f"{lab} {inc[a:z].mean()*252*100:+5.2f}pp" for lab, a, z in HALVES) +
              f" | NW t {TF.nw_t(inc):+5.2f} | placebo {pct:5.1f} | B3 maxDD {B.stats(rv)[2]*100:5.1f} (base {B.stats(r0)[2]*100:5.1f}) "
              f"| P50 {mc['dd50']:.1%} | DSR {ds['dsr']:.2f} | base P&L on changed trades {cut_share[v]:+.0%}")
        a, b = inc.mean() * 252, inc["2024":].mean() * 252
        print("      $/yr " + " | ".join(f"${E/1e3:g}k {a*E:+7,.0f} ({b*E:+7,.0f})" for E in SIZES))
    pickle.dump(dict(T=T, res=res), open(SCR / "conviction_ah_res.pkl", "wb"))


if __name__ == "__main__":
    main()
