"""Addendum 27 candidate (R4): ETF patterns the IBS leg does not trade.

    PYTHONPATH=. .venv/bin/python -m research.sim.etf_xsec

The IBS leg buys the top-3 12-1 momentum ETFs of 18 when they close near the
low. Pre-registered variants here (fixed before looking; robustness grids are
reported, never picked from):

  X1  sector 1-day losers: the 2 worst 1-day returns among the 11 sector ETFs
      (XLB XLE XLF XLI XLK XLP XLU XLV XLY SMH XBI), any momentum rank. Signal
      on d's bar, bought at the d+1 open, sold at the d+2 open (IBS timing).
  X2  sector 5-day losers: 2 worst 5-day returns, held 5 sessions open->open,
      5 overlapping tranches of 1/5 each.
  X3  pairs, long the laggard only: z = 20d z-score of log(A/B) for QQQ/SPY,
      SMH/QQQ, XLK/SPY. z <= -2 -> long A, z >= +2 -> long B, 3 sessions,
      open->open. Equal share across active pair signals.
  X4  international overnight premium: EFA EEM FXI KWEB bought at the close,
      sold at the next open, every night (they reprice to Asian/European
      sessions overnight). Compared with the same ETFs open->close and with
      SPY/QQQ overnight.

Costs per side: tier 1bp (sectors/SPY/QQQ, as the IBS leg), 2bp international;
tier_hi 3bp / 5bp. Placebo (X1-X3): the same number of names drawn at random
from the same universe on the same days, 100 seeds.

Combination with V7 (shipped, conviction 0.5 at the 75% TQQQ cap): the leg
lives in the IBS half's idle SGOV cash on days the IBS leg is flat (free
capacity: inside the 1.0x overnight budget and inside the daytime margin the
executor already reserves for the IBS half). The slice's BIL return is given
up; turnover from the slice switching on/off is charged.
"""
from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from . import book as B
from . import data as D
from .growth import V7, cfg, eh
from .validate import load_sim

SECT = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY", "SMH", "XBI"]
PAIRS = [("QQQ", "SPY"), ("SMH", "QQQ"), ("XLK", "SPY")]
INTL = ["EFA", "EEM", "FXI", "KWEB"]
COST = {"tier": 1.0, "tier_hi": 3.0}
COST_INTL = {"tier": 2.0, "tier_hi": 5.0}
PER = [("2016-20 holdout", "2016-01-01", "2020-12-31"), ("2021-23", "2021-01-01", "2023-12-31"),
       ("2024-26", "2024-01-01", "2026-12-31")]
SCRATCH = Path("/private/tmp/claude-501/-Users-andrewlau-Documents-Code-Projects-swing-trader/"
               "cc100773-e955-4a4c-aa47-797c4a8c7acb/scratchpad")

P = D.etf(); O, H, L, C = P["open"], P["high"], P["low"], P["close"]
OO = O.shift(-2) / O.shift(-1) - 1            # indexed by signal day d: open d+1 -> open d+2
ON = O.shift(-1) / C - 1                      # close d -> open d+1
OC = C / O - 1                                # open d -> close d


def st(r: pd.Series):
    r = r.dropna()
    if len(r) < 50:
        return (np.nan,) * 4
    cagr, sh, dd = B.stats(r)
    t = r.mean() / (r.std(ddof=1) / np.sqrt(len(r)))
    return cagr, sh, dd, t


def fmt(r):
    c, s, d, t = st(r)
    return f"{c*100:6.1f}/{s:5.2f}/{d*100:4.0f} t{t:+4.1f}"


# ---------------------------------------------------------------- legs
def picks_from_rank(score: pd.DataFrame, k: int) -> pd.DataFrame:
    """1 for the k lowest scores per day (NaN-safe), else 0."""
    rk = score.rank(axis=1, method="first")
    return (rk <= k).astype(float).where(score.notna(), 0.0)


def tranche_returns(sel: pd.DataFrame, hold: int, cost: float) -> pd.Series:
    """Daily open->open return (indexed by signal day d, earning open d+1 -> d+2)
    of `hold` overlapping tranches, each 1/hold of the leg, equal weight inside.
    Tranche started on signal day s holds for d in [s, s+hold-1]. Turnover cost
    on weight changes."""
    w_t = sel.div(sel.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    W = sum(w_t.shift(i).fillna(0.0) for i in range(hold)) / hold
    gross = (W * OO[W.columns]).sum(axis=1, min_count=1).fillna(0.0)
    turn = W.diff().abs().sum(axis=1).fillna(W.abs().sum(axis=1))
    return gross - turn * cost / 1e4, W


def x1(k=2, cost="tier", sel=None):
    sel = picks_from_rank(C[SECT].pct_change(fill_method=None), k) if sel is None else sel
    return tranche_returns(sel, 1, COST[cost])


def x2(k=2, hold=5, look=5, cost="tier", sel=None):
    sel = picks_from_rank(C[SECT].pct_change(look, fill_method=None), k) if sel is None else sel
    return tranche_returns(sel, hold, COST[cost])


def x3_sel(z_in=2.0, win=20):
    cols = sorted({s for p in PAIRS for s in p})
    sel = pd.DataFrame(0.0, index=C.index, columns=cols)
    for a, b in PAIRS:
        sp = np.log(C[a] / C[b])
        z = (sp - sp.rolling(win).mean()) / sp.rolling(win).std()
        sel.loc[z <= -z_in, a] += 1
        sel.loc[z >= z_in, b] += 1
    return sel


def x3(hold=3, cost="tier", sel=None, z_in=2.0):
    sel = x3_sel(z_in) if sel is None else sel
    return tranche_returns(sel, hold, COST[cost])


def placebo(sel: pd.DataFrame, univ: list, fn, seeds=100):
    """Same count of names per day, drawn at random from `univ`."""
    n = sel.sum(axis=1).astype(int)
    out = []
    for sd in range(seeds):
        rng = np.random.default_rng(sd)
        ps = pd.DataFrame(0.0, index=sel.index, columns=univ)
        avail = C[univ].notna().values
        for i, (d, m) in enumerate(n.items()):
            if m <= 0:
                continue
            ok = np.flatnonzero(avail[i])
            if len(ok) == 0:
                continue
            ch = rng.choice(ok, size=min(m, len(ok)), replace=False)
            ps.iloc[i, ch] = 1.0
        out.append(fn(ps))
    return out


def main():
    print("== 1. standalone legs, CAGR/Sharpe/maxDD t (daily, leg fully invested when active)")
    print(f"{'':44s}" + "".join(f"{p[0]:>27s}" for p in PER))
    def line(name, r):
        print(f"{name:44s}" + "".join(f"{fmt(r[a:z]):>27s}" for _, a, z in PER))
        return r
    legs = {}
    for c in ("tier", "tier_hi"):
        legs[("X1", c)] = line(f"X1 sector 1d losers k2 h1 {c}", x1(cost=c)[0])
        legs[("X2", c)] = line(f"X2 sector 5d losers k2 h5 {c}", x2(cost=c)[0])
        legs[("X3", c)] = line(f"X3 pairs laggard z2 h3 {c}", x3(cost=c)[0])
    # activity
    s1 = picks_from_rank(C[SECT].pct_change(fill_method=None), 2)
    s3 = x3_sel()
    print(f"   X3 active on {100*(s3.sum(axis=1)>0).mean():.0f}% of days; X1/X2 always active")
    print(f"{'equal-weight 11 sectors, open->open':44s}" + "".join(
        f"{fmt(OO[SECT].mean(axis=1)[a:z]):>27s}" for _, a, z in PER))
    print(f"{'SPY open->open':44s}" + "".join(f"{fmt(OO['SPY'][a:z]):>27s}" for _, a, z in PER))

    print("\n-- robustness grids (reported, not picked from), tier")
    for k in (1, 2, 3):
        for h in (1, 3, 5):
            line(f"   1d losers k{k} h{h}", tranche_returns(picks_from_rank(C[SECT].pct_change(fill_method=None), k), h, 1.0)[0])
    for k in (1, 3):
        line(f"   5d losers k{k} h5", x2(k=k)[0])
    for z in (1.5, 2.5):
        line(f"   pairs z{z} h3", x3(z_in=z)[0])
    for h in (1, 5):
        line(f"   pairs z2 h{h}", x3(hold=h)[0])

    print("\n-- X4 international overnight premium (close -> open, 2x cost per night)")
    for c in ("tier", "tier_hi"):
        cc = COST_INTL[c] * 2 / 1e4
        legs[("X4", c)] = line(f"X4 EFA/EEM/FXI/KWEB overnight {c}", ON[INTL].mean(axis=1) - cc)
    for s in INTL + ["SPY", "QQQ"]:
        line(f"   {s} overnight (gross)", ON[s])
        line(f"   {s} intraday open->close (gross)", OC[s].shift(-1))
    for s in INTL:
        cc = COST_INTL["tier"] * 2 / 1e4
        line(f"   {s} overnight net tier", ON[s] - cc)

    print("\n== 2. placebo: random names from the same universe, same count, 100 seeds (tier)")
    for name, sel, univ, fn in (
            ("X1", s1, SECT, lambda ps: x1(sel=ps)[0]),
            ("X2", picks_from_rank(C[SECT].pct_change(5, fill_method=None), 2), SECT, lambda ps: x2(sel=ps)[0]),
            ("X3", s3, sorted(s3.columns), lambda ps: x3(sel=ps)[0])):
        real = legs[(name, "tier")]
        pl = placebo(sel, univ, fn)
        msg = []
        for lab, a, z in PER:
            rv = real[a:z].mean()
            pv = np.array([p[a:z].mean() for p in pl])
            msg.append(f"{lab}: real {rv*1e4:+.2f}bp/day vs placebo {pv.mean()*1e4:+.2f} "
                       f"(beats {100*(rv > pv).mean():.0f}%)")
        print(f"{name}: " + " | ".join(msg))

    # --------------------------------------------------- V7 combination
    print("\n== 3. against V7 (2021-02 -> 2026-09)")
    s = load_sim()
    s.N = B.night_days(max_corr=0.7, max_name_pct=0.10)
    base = {c: s.replay(B.Params(**{**V7, **cfg(1.0, 0.5, 2), "night_cost": c})) for c in ("tier", "tier_hi")}
    days = base["tier"].index
    r7 = base["tier"].r
    flat = pd.Series({d: 0.0 if s.I.get(d) else 1.0 for d in days})
    flat_prev = flat.shift(1).fillna(1.0)       # X4 holds the night of d: the IBS slot of d-1
    bil = s.bil.reindex(days).fillna(0)
    spy = s.spy.reindex(days)
    crash = spy <= -0.03
    print(f"IBS half idle on {100*flat.mean():.0f}% of days")
    for name in ("X1", "X2", "X3", "X4"):
        x = legs[(name, "tier")].reindex(days).fillna(0)
        print(f"{name}: rho with V7 {r7.corr(x):+.2f}; on SPY<=-3% days (n={int(crash.sum())}) "
              f"leg {x[crash].mean()*1e4:+.0f}bp vs V7 {r7[crash].mean()*1e4:+.0f}bp")
    hdr = f"{'':50s} {'2021-23':>20s} {'2024-26':>20s} {'full':>20s}"
    print(hdr)
    def row(r):
        return " ".join(f"{fmt(r[a:z])[:15]:>20s}" for a, z in (("2021", "2023"), ("2024", "2026"), ("2021", "2026")))
    for c in ("tier", "tier_hi"):
        print(f"{'V7 shipped ' + c:50s} {row(base[c].r)}")
    combos = {}
    for name in ("X1", "X2", "X3", "X4"):
        for c in ("tier", "tier_hi"):
            cst = (COST_INTL if name == "X4" else COST)[c] / 1e4
            a = 0.5 * (flat_prev if name == "X4" else flat)
            x = legs[(name, c)].reindex(days).fillna(0)
            switch = a.diff().abs().fillna(0) * cst * (0 if name == "X4" else 1)
            comb = base[c].r + a * x - a * bil - switch
            combos[(name, c)] = (comb, a * x - a * bil - switch)
            print(f"{f'V7 + {name} in idle IBS cash ' + c:50s} {row(comb)}")
    print("-- edge halves at tier_hi (each V7 leg and the new leg lose half their mean)")
    print(f"{'V7 EH tier_hi':50s} {row(eh(base['tier_hi']))}")
    for name in ("X1", "X2", "X3", "X4"):
        comb, add = combos[(name, "tier_hi")]
        print(f"{f'V7 + {name} EH tier_hi':50s} {row(eh(base['tier_hi']) + add - 0.5 * add.mean())}")
    return legs, base, combos


if __name__ == "__main__":
    legs, base, combos = main()
    pickle.dump({"legs": {f"{k[0]}_{k[1]}": v for k, v in legs.items()},
                 "v7": base["tier"].r, "combos": {f"{k[0]}_{k[1]}": v[0] for k, v in combos.items()}},
                open(SCRATCH / "r4_all.pkl", "wb"))
