"""Pick-quality PQ1: leveraged / inverse ETFs among the night picks (rule: round1_prose.md "Pick quality, Study PQ1").

    PYTHONPATH=. .venv/bin/python -m research.sim.pq1 names       # classifier check (names only, no outcomes)
    PYTHONPATH=. .venv/bin/python -m research.sim.pq1 run         # select + judge, once, after registration
"""
from __future__ import annotations

import copy
import pickle
import re
import sys
from collections import Counter

import numpy as np
import pandas as pd

from .roundup import alpaca_names

LEV = re.compile(r"(?:\b|-)(?:1\.25|1\.5|1\.75|2|3|4)[xX]\b|\b(?:Ultra|UltraPro|Daily Target|Daily (?:Bull|Bear)|Leveraged|Inverse|"
                 r"Bear \d|Bull \d|-1[xX]|-2[xX]|-3[xX]|Short)\b", re.I)
FUNDY = re.compile(r"\b(ETFs?|ETNs?|Fund|Trust|ProShares|Direxion|MicroSectors|GraniteShares|Tradr|Defiance|T-REX|"
                   r"Leverage Shares|Volatility Shares|Tuttle|AXS|Roundhill|YieldMax|Kurv|Cyber Hornet|Rex)\b", re.I)
UND = re.compile(r"(?:Long|Short|Inverse|Bull|Bear)\s+([A-Z][A-Z.]{0,5})\b|\b([A-Z][A-Z.]{0,5})\s+(?:Bull|Bear)\b")
STOP = {"ETF", "ETN", "LONG", "SHORT", "DAILY", "BULL", "BEAR", "TARGET", "INC", "TRUST", "FUND", "SHARES", "THE", "AND", "USD",
        "ULTRA", "PRO", "II", "III", "X", "T", "REX", "MSCI", "S&P", "NASDAQ", "DOW", "CBOE", "VIX", "AI", "US", "SPAC"}


def classify(syms, names=None):
    """sym -> (is_letf, underlying or None)."""
    names = names or alpaca_names()
    out = {}
    for s in set(syms):
        n = names.get(s, "") or ""
        is_l = bool(FUNDY.search(n) and LEV.search(n))
        und = None
        if is_l:
            toks = [a or b for a, b in UND.findall(n)]
            toks = [t for t in toks if t not in STOP and t != s and t in names]
            und = toks[0] if toks else None
        out[s] = (is_l, und)
    return out


def pool():
    return pickle.load(open("data/research/program/cache_rawprice.pkl", "rb"))["raw"]


def filtered(N, cls, mode, cap=0.10, crowd=30):
    """mode 'excl': drop LETF picks (they leave the raw signal count too); 'dedupe': drop an LETF when its underlying (or an
    earlier LETF on the same underlying) is also a pick that night; 'placebo:<seed>:<mode>' drops the same number of random picks."""
    out = {}
    rng = None
    for d, nd in N.items():
        syms = list(nd.syms)
        drop = np.zeros(len(syms), bool)
        if mode in ("excl", "dedupe") or mode.startswith("placebo"):
            base = mode.split(":")[-1] if mode.startswith("placebo") else mode
            want = np.zeros(len(syms), bool)
            if base == "excl":
                want = np.array([cls.get(x, (False, None))[0] for x in syms])
            else:
                seen = set(x for x in syms if not cls.get(x, (False, None))[0])
                for i, x in enumerate(syms):
                    l, u = cls.get(x, (False, None))
                    if l and u:
                        if u in seen:
                            want[i] = True
                        seen.add(u)
            if mode.startswith("placebo"):
                if rng is None:
                    rng = np.random.default_rng(int(mode.split(":")[1]))
                k = int(want.sum())
                if k:
                    drop[rng.choice(len(syms), k, replace=False)] = True
            else:
                drop = want
        keep = ~drop
        if not keep.any():
            continue
        x = copy.copy(nd)
        for f in ("syms", "price", "close", "ret", "adv", "vol20", "ret20", "day_ret"):
            v = getattr(nd, f)
            setattr(x, f, np.asarray(v)[keep] if not hasattr(v, "iloc") else v[keep])
        x.n_raw = max(1, nd.n_raw - int(drop.sum()))
        x.frac = min(1.0 / keep.sum(), cap) * min(1.0, crowd / x.n_raw)
        out[d] = x
    return out


def names_check():
    N = pool()[0.10]
    syms = [s for nd in N.values() for s in nd.syms]
    cls = classify(syms)
    nm = alpaca_names()
    L = [s for s, (l, u) in cls.items() if l]
    print(f"{len(cls)} distinct pick symbols, {len(L)} classified leveraged/inverse ETFs; with an underlying found: "
          f"{sum(1 for s in L if cls[s][1])}")
    for s in sorted(L)[:40]:
        print(f"  {s:6s} -> {str(cls[s][1]):6s} | {nm.get(s, '')[:70]}")
    # false-positive check: non-LETF names containing 'Short'/'Ultra' etc.
    fp = [s for s in cls if not cls[s][0] and LEV.search(nm.get(s, "") or "")]
    print("LEV-word names NOT classified (no fund word):", [(s, nm.get(s, '')[:40]) for s in fp[:10]])


if __name__ == "__main__":
    names_check() if sys.argv[1] == "names" else None


def run_study():
    from . import book as B, growth as G
    from .validate import load_sim
    from .taxable_frontier import nw_t
    from .program_books import dsr
    s = load_sim(raw_price=True)
    N = pool()[0.10]
    cls = classify([x for nd in N.values() for x in nd.syms])
    H = (("select 2021-23", "2021-02-01", "2023-12-31"), ("judge 2024-26", "2024-01-01", "2026-09-18"))
    res = {}

    def book(pool_, cost, a, b, E0=10000.0, whole=True):
        s.N = pool_
        p = B.Params(**{**G.V7, "night_cost": cost, "whole": whole})
        d = s.days[(s.days >= a) & (s.days <= b)]
        return s.replay(p, start=E0, monthly=0.0, dates=d).r

    base = {}
    for cost in ("tier", "tier_hi"):
        for hl, a, b in H:
            base[(cost, hl)] = book(N, cost, a, b)
    for v in ("excl", "dedupe"):
        P = filtered(N, cls, v)
        nd = sum(len(x.syms) for x in N.values()) - sum(len(x.syms) for x in P.values())
        print(f"== PQ1{'a' if v == 'excl' else 'b'} {v}: picks removed {nd}")
        for cost in ("tier", "tier_hi"):
            for hl, a, b in H:
                r = book(P, cost, a, b); r0 = base[(cost, hl)]
                inc = (r - r0).dropna()
                yrs = len(inc) / 252
                cg = lambda x: ((1 + x).prod() ** (1 / yrs) - 1) * 100
                line = f"   {cost:8s} {hl}: book {cg(r0):5.1f}% -> {cg(r):5.1f}% ({cg(r) - cg(r0):+5.2f}pp), NW t {nw_t(inc):+.2f}"
                if cost == "tier" and hl.startswith("judge"):
                    pl = []
                    for seed in range(50):
                        rp = book(filtered(N, cls, f"placebo:{seed}:{v}"), cost, a, b)
                        pl.append(cg(rp) - cg(r0))
                    pct = (np.array(pl) < cg(r) - cg(r0)).mean() * 100
                    line += f", placebo pct {pct:.0f} (median placebo {np.median(pl):+.2f}pp)"
                    res[v] = (cg(r) - cg(r0), nw_t(inc), pct)
                print(line, flush=True)
        r23 = book(P, "tier", *H[1][1:], E0=2300.0); r23b = book(N, "tier", *H[1][1:], E0=2300.0)
        yrs = len(r23) / 252
        print(f"   $2.3k whole shares, judge, tier: {(((1 + r23).prod()) ** (1 / yrs) - 1) * 100 - (((1 + r23b).prod()) ** (1 / yrs) - 1) * 100:+.2f}pp")
    print("results", res)


if __name__ == "__main__" and sys.argv[1] == "run":
    run_study()
