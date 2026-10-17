"""TAX-STACK (N 1017): PREF-EX + ETDX stacked on the live taxable book (night .65 name cap .15, IBS .5 = 1.15x gross), after tax and margin interest.
Reuses roth_stack (events, alloc, groups, book cash logic). Pre-reg: round1_prose.md "Study TAX-STACK".

    PYTHONPATH=. .venv/bin/python -m research.sim.tax_stack
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import book as B
from .roth_cash import PROBE_USD, nw_t
from .roth_stack import ROOT, alloc, load_groups
from .validate import load_sim

_orig = pd.StringDtype.__init__  # cache pickled under pandas 3, venv has 2.2.3


def _sd(self, storage=None, na_value=None):
    _orig(self, storage if storage in ("python", "pyarrow") else None)


pd.StringDtype.__init__ = _sd

OUT = ROOT / "data/research/program/tax_stack_out.txt"
WN, WI, GROSS, TAX, MRATE = 0.65, 0.5, 1.15, 0.35, 0.125


def day(s, N, E, d, cost, pref_first, g, margin, rt, gap=1):
    """One book day. Returns (book_pnl, pref_pnl, interest_incr, bil_lost, debit, div_usd, events)."""
    pnl = iused = 0.0
    for sym, o1, r in s.I.get(d, []):
        sh = np.floor(WI * E / len(s.I[d]) / o1); iused += sh * o1; pnl += sh * o1 * (r - 2e-4)
    idle = max(0.0, WI * E - iused)
    b = s.bil.get(d, 0.0); b = float(b) if np.isfinite(b) else 0.0
    px = float(s.C.at[d, "BIL"]) if d in s.C.index and np.isfinite(s.C.at[d, "BIL"]) else np.nan
    tb = np.floor(idle / px) * px if (np.isfinite(px) and idle >= 50) else 0.0
    pnl += tb * b
    a = None; reserve = 0.0
    if g is not None and pref_first and not margin:
        a = alloc(max(0.0, E - iused - tb), g); reserve = a.sum()
    cash = GROSS * E - iused - tb - reserve
    nused = 0.0
    nd = N.get(d)
    if nd is not None:
        leg = min(WN * E, max(0.0, cash)); w = sg.night_tilt(nd.vol20, nd.day_ret, 0.25)
        c = B.cost_bps(cost, nd.price, nd.adv); per = leg * nd.frac * w
        if s._gap(d) > 1: per = per * 0.5
        for i in range(len(per)):
            q = np.floor(per[i] / nd.price[i])
            if q < 1 and nd.price[i] <= PROBE_USD: q = 1.0
            if q < 1 or cash - q * nd.price[i] < 0: continue
            cash -= q * nd.price[i]; v = q * nd.close[i]; nused += v; pnl += v * (nd.ret[i] - 2 * c[i] / 1e4)
    debit_base = max(0.0, iused + tb + nused - E)
    pp = lost = divu = 0.0; ev = []
    if g is not None:
        if a is None:
            budget = (2 * E - iused - tb - nused + tb) if margin else max(0.0, E - iused - tb - nused)
            a = alloc(max(budget, 0.0), g)
        tot = a.sum()
        if tot > 0:
            x = a * (g.co.values - rt); pp = x.sum(); divu = (a * g["dy"].values).sum()
            for j in np.nonzero(a)[0]: ev.append((d, a[j], x[j], g.co.values[j] - rt))
        own = max(0.0, E - iused - tb - nused)
        sold = min(tb, max(0.0, tot - own)) if margin else 0.0
        lost = sold * b
        debit = max(0.0, iused + tb - sold + nused + tot - E)
    else:
        debit = debit_base
    return pnl, pp, (debit - debit_base) * MRATE * gap / 365.0, lost, divu, ev


def run(s, N, groups, E, cost, pref_first, margin, rt=0.0010, pref=True):
    rows, evs = [], []
    nxt = dict(zip(s.days[:-1], s.days[1:]))
    for d in s.days:
        g = groups.get(d) if pref else None
        pnl, pp, intr, lost, divu, ev = day(s, N, E, d, cost, pref_first, g, margin, rt, (nxt[d] - d).days if d in nxt else 1)
        rows.append((pnl, pp, intr, lost, divu)); evs += ev
    r = pd.DataFrame(rows, columns=["book", "pref", "intr", "lost", "div"], index=pd.Index(s.days)) / E
    return r, pd.DataFrame(evs, columns=["d", "usd", "pnl", "ret"])


def summarize(base, r, ev, E, yrs, h1, h2):
    d_book = r.book - base.book
    pre = r.pref - r.intr - r.lost + d_book           # incremental pre-tax
    t1 = (1 - TAX) * pre                              # losses offset book's STCG
    t2 = pre - TAX * r["div"] - TAX * d_book          # dividends taxed, pref losses unusable
    def a(x): return x.sum() / yrs * 100
    def hv(x, h): return x[h].sum() / (((x.index[h][-1] - x.index[h][0]).days) / 365.25) * 100
    return pre, t1, t2, a, hv


def main():
    s = load_sim(raw_price=True)
    N = s.N  # cached raw night pool (night_days pickles are pandas-3, unreadable in this venv)
    s.days = list(s.days)
    groups = load_groups()
    divs = []
    for src in ("pref", "etdx"):
        e = pd.read_parquet(ROOT / f"data/research/{src}/events.parquet")[["ticker", "date", "div", "pc"]].rename(columns={"ticker": "t", "date": "d"})
        divs.append(e.drop_duplicates(["t", "d"]))
    dv = pd.concat(divs).rename(columns={"pc": "pc_e"})
    for k, g in groups.items():
        m = g.merge(dv[["t", "d", "div"]], on=["t", "d"], how="left")
        g["dy"] = (m["div"].fillna(0).values / g.pc.values)
    ix = pd.DatetimeIndex(s.days); yrs = (ix[-1] - ix[0]).days / 365.25
    h1 = ix < "2024-01-01"; h2 = ~h1
    L = [f"TAX-STACK N 1017: PREF+ETDX CO stacked on taxable book (night {WN}, IBS {WI}, {GROSS}x), tax {TAX:.0%}, margin {MRATE:.1%}, tier costs, whole shares",
         f"book days {ix[0].date()}..{ix[-1].date()}; events {sum(len(g) for g in groups.values())}; yrs {yrs:.2f}"]
    arms = [("CASH night-first", False, False), ("CASH pref-first", True, False), ("MARGIN 2x night-undisturbed", False, True)]
    for E in (2300.0, 10000.0, 25000.0, 100000.0):
        L.append(f"\n== equity ${E:,.0f} ==")
        base, _ = run(s, N, groups, E, "tier", False, False, pref=False)
        for nm, pf, mg in arms:
            r, ev = run(s, N, groups, E, "tier", pf, mg)
            r3, ev3 = run(s, N, groups, E, "tier", pf, mg, rt=0.0030)
            pre, t1, t2, a, hv = summarize(base, r, ev, E, yrs, h1, h2)
            pre3, t13, _, _, _ = summarize(base, r3, ev3, E, yrs, h1, h2)
            top5 = ev.pnl.nlargest(5).sum() / yrs / E * 100 if len(ev) else 0
            L.append(f"{nm:28s}: pre-tax {a(pre):+5.1f}pp (${a(pre)*E/100:,.0f}) | after-tax A(loss offsets STCG) {a(t1):+5.1f} | B(loss unusable) {a(t2):+5.1f} | "
                     f"halves(pre) {hv(pre,h1):+5.1f}/{hv(pre,h2):+5.1f} (after A {hv(t1,h1):+5.1f}/{hv(t1,h2):+5.1f}) | 3x cost pre {a(pre3):+5.1f} afterA {a(t13):+5.1f} | "
                     f"ex-top5 pre {a(pre)-top5:+5.1f} | interest drag {a(-r.intr):+5.1f}pp, BIL lost {a(-r.lost):+5.1f}pp, book displacement {a(r.book-base.book):+5.1f}pp | "
                     f"events {len(ev)}, median {ev.ret.median()*1e4 if len(ev) else 0:+.0f}bp, hit {(ev.ret>0).mean()*100 if len(ev) else 0:.0f}% | NW t(pre) {nw_t(pd.Series(pre.values)):.2f}")
    OUT.write_text("\n".join(L) + "\n"); print("\n".join(L))


if __name__ == "__main__":
    main()
