"""ROTH-STACK (N 897): PREF-EX + ETDX funded from the idle cash of the AL1 cash-Roth book. Pre-reg: round1_prose.md.

    PYTHONPATH=. .venv/bin/python -m research.sim.roth_stack
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import book as B
from .etdx_exec import rows
from .roth_cash import PROBE_USD, nw_t
from .validate import load_sim

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/roth_stack_out.txt"
RT = 0.0010
P = 0.05


def book_day(s, N, E, d, w_n, w_i, probe, cost, pref_first_alloc=None, lenient=False):
    """AL1 cash day. pref_first_alloc(avail_pre)->$ reserved for PREF before the night buys (None = night first).
    Returns pnl, iused, tb, nused, free-cash-after-night (strict), reserved."""
    pnl = 0.0
    iused = 0.0
    legs = s.I.get(d, [])
    if legs:
        for sym, o1, r in legs:
            sh = np.floor(w_i * E / len(legs) / o1)
            iused += sh * o1
            pnl += sh * o1 * (r - 2 * 1.0 / 1e4)
    idle = max(0.0, w_i * E - iused)
    b = s.bil.get(d, 0.0); b = float(b) if np.isfinite(b) else 0.0
    px = float(s.C.at[d, "BIL"]) if d in s.C.index and np.isfinite(s.C.at[d, "BIL"]) else np.nan
    tb = np.floor(idle / px) * px if (np.isfinite(px) and idle >= 50) else 0.0
    pnl += tb * b
    reserve = 0.0
    if pref_first_alloc is not None:
        reserve = pref_first_alloc(E - iused - tb + (tb if lenient else 0.0))
    cash = E - iused - tb - max(0.0, reserve - (tb if lenient else 0.0))
    nused = 0.0
    nd = N.get(d)
    if nd is not None:
        leg = min(w_n * E, max(0.0, cash))
        w = sg.night_tilt(nd.vol20, nd.day_ret, 0.25)
        c = B.cost_bps(cost, nd.price, nd.adv)
        per = leg * nd.frac * w
        if s._gap(d) > 1:
            per = per * 0.5
        for i in range(len(per)):
            q = np.floor(per[i] / nd.price[i])
            if q < 1 and probe and nd.price[i] <= probe:
                q = 1.0
            if q < 1 or cash - q * nd.price[i] < 0:
                continue
            cash -= q * nd.price[i]
            v = q * nd.close[i]
            nused += v
            pnl += v * (nd.ret[i] - 2 * c[i] / 1e4)
    free = E - iused - tb - nused + (tb if lenient else 0.0)
    return pnl, free, reserve


def alloc(avail, g, col="co"):
    """Equal split across the night's events, 5% of min(ex-ante auction $), whole shares at pc."""
    cap = np.minimum(g.cap_close_ea.values, g.cap_open_ea.values) * P
    a_, rem = np.zeros(len(g)), max(avail, 0.0)
    for k, i in enumerate(np.argsort(cap)):
        a = min(cap[i], rem / (len(g) - k))
        a_[i] = np.floor(a / g.pc.values[i]) * g.pc.values[i]
        rem -= a_[i]
    return a_


def load_groups():
    both = pd.concat([rows("pref"), rows("etdx")], ignore_index=True).dropna(subset=["pc", "cap_close_ea", "cap_open_ea"])
    ev = pd.concat([pd.read_parquet(ROOT / f"data/research/{s}/events.parquet")[["ticker", "date", "d0"]]
                    for s in ("pref", "etdx")]).rename(columns={"ticker": "t", "date": "d"}).drop_duplicates(["t", "d"])
    both = both.merge(ev, on=["t", "d"], how="left").dropna(subset=["d0"])
    both["d0"] = pd.to_datetime(both.d0)
    return {pd.Timestamp(k): g.reset_index(drop=True) for k, g in both.groupby("d0")}


def run(s, N, groups, E, cost, mode, lenient, rt=RT, remap=None):
    """mode 'night' or 'pref'. remap: {book_day: group_key} (placebo). Returns daily series (book, pref pnl/E) + event rows."""
    book, pref, ev = [], [], []
    for d in s.days:
        g = groups.get(remap.get(d) if remap is not None else d)
        holder = {}
        if g is not None and mode == "pref":
            def f(avail, g=g, holder=holder):
                holder["a"] = alloc(avail, g); return holder["a"].sum()
            pnl, free, res = book_day(s, N, E, d, 0.5, 0.5, PROBE_USD, cost, f, lenient)
            a = holder["a"]
        else:
            pnl, free, res = book_day(s, N, E, d, 0.5, 0.5, PROBE_USD, cost, None, lenient)
            a = alloc(free, g) if g is not None else None
        pp = 0.0
        if a is not None and a.sum() > 0:
            x = a * (g.co.values - rt)
            pp = x.sum()
            for j in np.nonzero(a)[0]:
                ev.append((d, a[j], x[j], g.co.values[j] - rt))
        book.append(pnl / E); pref.append(pp / E)
    ix = pd.Index(s.days)
    return pd.Series(book, ix), pd.Series(pref, ix), pd.DataFrame(ev, columns=["d", "usd", "pnl", "ret"])


def ann(x, yrs):
    return x.sum() / yrs


def main():
    s = load_sim(raw_price=True)
    N = B.night_days(raw_price=True, max_corr=0.7)
    s.N = N
    groups = load_groups()
    days = pd.DatetimeIndex(s.days)
    L = ["ROTH-STACK N 897: PREF+ETDX CO on idle cash of the AL1 cash-Roth book (tier costs, whole shares), fixed equity",
         f"book days {days[0].date()}..{days[-1].date()}; ex-night groups {len(groups)}; events {sum(len(g) for g in groups.values())}"]
    yrs = (days[-1] - days[0]).days / 365.25
    h1, h2 = days <= "2023-12-31", days >= "2024-01-01"
    print("\n".join(L))
    for E in (1000.0, 3000.0, 7800.0, 10000.0, 25000.0):
        L.append(f"\n== equity ${E:,.0f} ==")
        res = {}
        for name, mode, len_ in [("STRICT night-first", "night", False), ("STRICT pref-first", "pref", False),
                                 ("LENIENT night-first", "night", True), ("LENIENT pref-first", "pref", True)]:
            bk, pf, ev = run(s, N, groups, E, "tier", mode, len_)
            res[name] = (bk, pf, ev)
        base_bk, _, _ = res["STRICT night-first"]
        for name, (bk, pf, ev) in res.items():
            inc = pf + (bk - base_bk if "pref-first" in name and name.startswith("STRICT") else 0)
            if name.startswith("LENIENT"):
                inc = pf  # book drift from BIL sale ignored (upper bound)
            m = pd.Series(inc.values, index=days)
            t = nw_t(m[inc.abs() > -1])
            top5 = ev.pnl.nlargest(5).sum() if len(ev) else 0
            # 3x cost = 30bp round trip
            _, pf3, ev3 = run(s, N, groups, E, "tier", "night" if "night" in name else "pref", name.startswith("LENIENT"), rt=0.0030)
            L.append(f"{name:20s}: {ann(inc, yrs)*100:+5.1f}pp/yr (${ann(inc, yrs)*E:,.0f}) | halves {inc[h1].sum()/ (((days[h1][-1]-days[h1][0]).days)/365.25)*100:+5.1f} / "
                     f"{inc[h2].sum()/(((days[h2][-1]-days[h2][0]).days)/365.25)*100:+5.1f} | 3x cost {ann(pf3, yrs)*100:+5.1f} | "
                     f"ex-top5 {(ev.pnl.sum()-top5)/yrs/E*100:+5.1f} | events {len(ev)}, median {ev.ret.median()*1e4:+.0f}bp, hit {(ev.ret>0).mean()*100:.0f}%, "
                     f"mean usd {ev.usd.mean():,.0f} | NW t {nw_t(pd.Series(inc.values)):.2f}")
        if E in (3000.0, 10000.0):
            rng = np.random.default_rng(897)
            keys = list(groups.keys())
            real = ann(res["STRICT night-first"][1], yrs)
            out = []
            for r in range(100):
                sh = rng.permutation(keys)
                tgt = rng.choice(len(days), len(keys), replace=False)
                remap = {days[i]: k for i, k in zip(tgt, sh)}
                _, pfp, _ = run(s, N, groups, E, "tier", "night", False, remap=remap)
                out.append(ann(pfp, yrs))
            L.append(f"placebo (events' returns on random book days, 100 reps): mean {np.mean(out)*100:+.1f}pp  p95 {np.percentile(out,95)*100:+.1f}pp  "
                     f"real {real*100:+.1f}pp  pct {np.mean(np.array(out) < real)*100:.0f}")
        print("\n".join(L[-7:]))
    OUT.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
