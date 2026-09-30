"""Study Y: the whole book's rate at $25k-$5M, after tax, vs a held index (report).

    PYTHONPATH=. .venv/bin/python -m research.sim.scale_book

Stamp: research/drafts/round1_prose.md, "Round 12" (commit 29ef565). Constant equity E per run
(the rate at that size, no deposits), fractional shares. Night = Study X's per-trade table with
the Y_rule 4 cap; IBS and noise = the Sim's trades with square-root impact on the ETF ADV / sd in
scale_legs_diag.txt. Tax at constant equity: yearly $ gain = E x the year's summed daily returns.
"""
from __future__ import annotations

import time

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import book as B
from .night_filings import FULL, PER, ROOT
from .validate import load_sim

OUT = ROOT / "data/research/program/scale_book_out.txt"
SIZES = (2_300, 25_000, 100_000, 250_000, 500_000, 1_000_000, 2_500_000, 5_000_000)
G_BPS, Y_RULE = 22.0, 4.0
LIVE_COST = 1.0                                   # night bp/side (Study V/X)
AUC = (0.037, 0.016)                              # Study V: closing / opening bar share of ADV
# scale_legs_diag.txt: last-12-month ADV ($bn) and daily sd (bp)
ETF = {"MDY": (0.55, 95.75), "XLB": (0.64, 111.53), "XLU": (0.97, 95.57), "XLY": (1.14, 121.70),
       "XLP": (1.18, 89.49), "XBI": (1.21, 173.68), "EFA": (1.62, 97.75), "XLI": (1.64, 106.84),
       "XLV": (1.76, 100.24), "EEM": (1.81, 156.43), "XLE": (2.05, 137.74), "XLF": (2.15, 91.72),
       "XLK": (2.26, 163.94), "DIA": (2.66, 78.48), "SMH": (4.13, 246.95), "IWM": (8.88, 116.43),
       "QQQ": (32.80, 122.87), "SPY": (47.27, 80.30)}
# truth: (night Y, night auction shares (close, open), ETF Y, night cost model)
TRUTHS = {"OPT": (0.5, (1.0, 1.0), 0.5, None), "CENTRAL": (1.0, (1.0, 1.0), 1.0, None),
          "PESS": (0.5, AUC, 1.0, None), "CENTRAL+tier": (1.0, (1.0, 1.0), 1.0, "tier")}
BOOKS = {"B1 shipped": dict(noise={"QQQ": 0.5, "SMH": 0.5}, cap=1.5, s1256=False, tax=True),
         "B2 scale plan": dict(noise={"QQQ": 1.0}, cap=1.5, s1256=True, tax=True),
         "B3 Roth": dict(noise={"QQQ": 1.0}, cap=1.5, s1256=False, tax=False)}
BRACKETS = {"MOD": (0.32, 0.24), "TOP": (0.54, 0.37)}
H = 20


def etf_imp(sym: str, q, Y: float):
    """Impact per side, fraction, for $q in `sym`."""
    adv, sd = ETF[sym]
    return Y * sd / 1e4 * np.sqrt(np.asarray(q, float) / (adv * 1e9))


def night_table():
    N = B.night_days(raw_price=True, max_corr=0.7)
    rows = []
    for d, nd in N.items():
        c = B.cost_bps("tier", nd.price, nd.adv)
        for j in range(len(nd.syms)):
            rows.append(dict(d=pd.Timestamp(d), ret=nd.ret[j], vol=nd.vol20[j], adv=nd.adv[j],
                             w=min(nd.frac, 0.10), tier=c[j]))
    T = pd.DataFrame(rows)
    return T[(T.d >= FULL[0]) & (T.d <= FULL[1])].reset_index(drop=True)


def night_leg(T, E, truth, days, bil):
    """Daily night-leg return on equity E (cap-freed money in BIL)."""
    Yn, (fc, fo), _, cost = TRUTHS[truth]
    want = 0.5 * E * T.w.values
    q = np.minimum(want, sg.night_impact_cap(T.adv.values, T.vol.values, G_BPS, Y_RULE))
    sig = (T.vol / np.sqrt(252)).values
    imp = Yn * sig * (np.sqrt(q / (T.adv.values * fc)) + np.sqrt(q / (T.adv.values * fo)))
    side = LIVE_COST if cost is None else T.tier.values
    pnl = pd.Series(q * (T.ret.values - 2 * side / 1e4 - imp)).groupby(T.d.values).sum()
    freed = pd.Series(want - q).groupby(T.d.values).sum()
    r = pnl.reindex(days).fillna(0) / E
    r += freed.reindex(days).fillna(0) / E * bil.reindex(days).fillna(0)
    return r, float(np.mean(q < want - 1e-9))


def ibs_leg(s, E, Y, days):
    out = {}
    for d in days:
        tr = s.I.get(d, [])
        if not tr:
            out[d] = 0.0; continue
        q = 0.5 * E / len(tr)
        x = sum(q * (r - 2 * 1.0 / 1e4 - 2 * etf_imp(sym, q, Y)) for sym, _, r in tr)
        out[d] = x / E
    return pd.Series(out)


def noise_leg(s, E, Y, days, noise, cap):
    r = pd.Series(0.0, index=days)
    for sym, share in noise.items():
        z = s.NZ[sym].reindex(days)
        lev = np.minimum(z.lev.fillna(0), cap) * share
        q = E * lev
        r += (lev * (z.ret.fillna(0) - z.trades.fillna(0) * etf_imp(sym, q, Y))).fillna(0)
    return r


def idle(s, days):
    """IBS half's idle money in BIL (as Sim)."""
    out = {}
    for d in days:
        n = len(s.I.get(d, []))
        b = s.bil.get(d, 0.0)
        out[d] = (0.0 if n else 0.5) * (float(b) if np.isfinite(b) else 0.0)
    return pd.Series(out)


def after_tax(parts: dict, st: float, lt: float, s1256: bool) -> float:
    """Mean yearly after-tax return at constant equity; losses net across buckets and carry."""
    fut = parts["noise"] if s1256 else 0 * parts["noise"]
    rest = sum(parts.values()) - fut
    r1256 = 0.6 * lt + 0.4 * st
    carry, out = 0.0, []
    for y, g in rest.groupby(rest.index.year):
        a, b = float(g.sum()), float(fut[g.index].sum())
        tot = a + b
        taxable = tot - carry
        if taxable <= 0:
            carry = -taxable; out.append(tot); continue
        carry = 0.0
        # the loss carried and any negative bucket reduce the positive buckets pro rata
        pos_a, pos_b = max(a, 0.0), max(b, 0.0)
        k = taxable / (pos_a + pos_b)
        out.append(tot - k * (pos_a * st + pos_b * r1256))
    yrs = rest.groupby(rest.index.year).size() / 252
    return float(np.sum(out) / yrs.sum())


def main():
    t0 = time.time()
    fs = open(OUT, "w")

    def log(*a):
        s_ = " ".join(str(x) for x in a)
        print(s_, flush=True)
        fs.write(s_ + "\n")
        fs.flush()

    log("== Study Y: the whole book's rate at size, after tax, vs a held index, started",
        pd.Timestamp.now(), "\n")
    s = load_sim(raw_price=True)
    T = night_table()
    days = s.days[(s.days >= FULL[0]) & (s.days <= FULL[1])]
    yrs = len(days) / 252
    spy = s.C["SPY"].reindex(days)
    g = (spy.iloc[-1] / spy.iloc[0]) ** (1 / yrs) - 1
    idx = {k: ((1 + g) ** H * (1 - lt) + lt) ** (1 / H) - 1 for k, (_, lt) in BRACKETS.items()}
    log(f"window {days[0]:%Y-%m-%d}..{days[-1]:%Y-%m-%d} ({yrs:.2f} yrs); SPY held {g:+.1%}/yr pre-tax; "
        f"after-tax equivalent over {H}y: MOD {idx['MOD']:+.1%}, TOP {idx['TOP']:+.1%}")
    for _, a, b in PER:
        sp = spy[a:b]
        log(f"  SPY {a[:4]}-{b[:4]}: {(sp.iloc[-1] / sp.iloc[0]) ** (252 / len(sp)) - 1:+.1%}/yr")
    ib = idle(s, days)
    log("")

    res = {}
    for truth in TRUTHS:
        Yetf = TRUTHS[truth][2]
        log(f"## truth {truth}  (night Y {TRUTHS[truth][0]}, auction shares {TRUTHS[truth][1]}, "
            f"ETF Y {Yetf}, night cost {TRUTHS[truth][3] or '1bp/side'})")
        log(f"{'book':14s} {'equity':>11s} {'pre %/yr':>9s} {'21-23':>7s} {'24-26':>7s}"
            f" {'MOD at':>7s} {'TOP at':>7s}  {'night':>6s} {'ibs':>6s} {'noise':>6s} {'cash':>5s}"
            f" {'cap binds':>9s}")
        for E in SIZES:
            nr, bind = night_leg(T, E, truth, days, s.bil)
            ir = ibs_leg(s, E, Yetf, days)
            for bname, bk in BOOKS.items():
                zr = noise_leg(s, E, Yetf, days, bk["noise"], bk["cap"])
                parts = {"night": nr, "ibs": ir, "noise": zr, "cash": ib}
                r = sum(parts.values())
                pre = r.sum() / yrs
                hv = [r[a:b].sum() / (len(r[a:b]) / 252) for _, a, b in PER]
                at = {k: (after_tax(parts, st, lt, bk["s1256"]) if bk["tax"] else pre)
                      for k, (st, lt) in BRACKETS.items()}
                res[(truth, bname, E)] = dict(pre=pre, h=hv, **at)
                legs = [p.sum() / yrs * 100 for p in parts.values()]
                log(f"{bname:14s} ${E:>10,} {pre * 100:+9.1f} {hv[0] * 100:+7.1f} {hv[1] * 100:+7.1f}"
                    f" {at['MOD'] * 100:+7.1f} {at['TOP'] * 100:+7.1f}  "
                    + " ".join(f"{x:+6.1f}" for x in legs[:3]) + f" {legs[3]:+5.1f} {bind:9.0%}")
        log("")

    log("## pre-registered readings (rates are simple %/yr at constant equity)")
    for bname, bench in (("B2 scale plan", "MOD"), ("B3 Roth", None)):
        for E in (500_000, 1_000_000):
            x = res[("CENTRAL", bname, E)]
            log(f"1. planning rate {bname} CENTRAL at ${E:,}: pre-tax {x['pre']:+.1%}, "
                f"after-tax MOD {x['MOD']:+.1%}, TOP {x['TOP']:+.1%}")
    for bname, key, ref, lab in (("B2 scale plan", "MOD", idx["MOD"], "2. taxable"),
                                 ("B3 Roth", "pre", g, "3. Roth")):
        for truth in ("CENTRAL", "PESS", "OPT"):
            below = [E for E in SIZES if res[(truth, bname, E)][key] < ref]
            e_star = below[0] if below else None
            first_half = [E for E in SIZES
                          if res[(truth, bname, E)]["h"][0] < ref <= res[(truth, bname, E)][key]]
            log(f"{lab} crossover ({truth}, {bname} {key} vs index {ref:+.1%}): "
                f"{'none on the grid (above the index at $5M)' if e_star is None else f'${e_star:,}'}"
                + (f"; above the index only thanks to 2024-26 at: {', '.join(f'${e:,}' for e in first_half)}"
                   if first_half else ""))
    log(f"\ndone in {time.time() - t0:4.0f} s")


if __name__ == "__main__":
    main()
