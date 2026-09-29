"""Adversarial verifier for addendum NN (new_listings), Q2 F1 up-weight. All checks POST-HOC.

    PYTHONPATH=. .venv/bin/python -m research.sim.new_listings_verify

Works from the study's slim cache (no heavy lock needed).
V1 reproduce the F1 per-trade table and the V7 book numbers.
V2 cluster the t-stat by SYMBOL and two-way (day + symbol): the same names recur on many days.
V3 leave-top-names-out: drop the top-5 / top-10 flagged names by 2024-26 P&L (flag -> off) and
   re-run the up-weight book at tier_hi.
V4 proxy (2017-20) coverage: symbols with bars per year in the 2016-20 file vs the 2021+ panel.
V5 F1 flagged-name characteristics (price, ADV, cost tier) in 2024-26.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import book as B
from . import new_listings as NL


def twoway_t(y, flag, g1, g2):
    """OLS y = a + b*flag with clustered SE by g1, by g2, and two-way (CGM)."""
    X = np.column_stack([np.ones(len(y)), flag.astype(float)])
    XtX = np.linalg.inv(X.T @ X)
    beta = XtX @ X.T @ y
    u = y - X @ beta
    def meat(g):
        df = pd.DataFrame({"g": g, "a": u, "b": u * X[:, 1]})
        S = df.groupby("g")[["a", "b"]].sum().values
        return S.T @ S, len(S)
    m1, n1 = meat(g1); m2, n2 = meat(g2)
    m12, _ = meat(pd.Series(g1).astype(str).values + "|" + pd.Series(g2).astype(str).values)
    out = {}
    for lab, M, G in (("day", m1, n1), ("sym", m2, n2), ("2way", m1 + m2 - m12, min(n1, n2))):
        V = XtX @ M @ XtX * G / max(G - 1, 1)
        out[lab] = beta[1] / np.sqrt(V[1, 1]) if V[1, 1] > 0 else np.nan
    return beta[1], out


def main():
    from .validate import load_sim
    c = NL.load_cache()
    s = load_sim(); s.N = c["N"]
    A = NL.Ages(c)
    T, P = NL.q2_tables(c, A)
    N = c["N"]
    print("== V1/V2 F1 per-trade diff net tier (bp): t by day / sym / two-way")
    halves = {"2021-23": T[T.date <= "2023-12-31"], "2024-26": T[T.date >= "2024-01-01"], "2021-26": T,
              "proxy 2017-20": P[(P.date >= "2017-01-01") & (P.date < "2020-10-01")]}
    for lab, X in halves.items():
        fl = X.F1.fillna(False).values.astype(bool)
        b, t = twoway_t(X.net_t.values, fl, X.date.values, X.sym.values)
        print(f"  {lab:14s} n_flag {fl.sum():5d} names {X[fl].sym.nunique():4d} diff {b*1e4:7.1f}  "
              + "  ".join(f"t_{k} {v:5.2f}" for k, v in t.items()))
        if lab != "proxy 2017-20":
            bh, th = twoway_t(X.net_h.values, fl, X.date.values, X.sym.values)
            print(f"  {'':14s} @tier_hi diff {bh*1e4:7.1f}  " + "  ".join(f"t_{k} {v:5.2f}" for k, v in th.items()))
    # V3 leave top names out
    X = T[T.date >= "2024-01-01"]
    g = X[X.F1].groupby("sym").net_t.sum().sort_values(ascending=False)
    print("\n== V3 top flagged names 2024-26 (sum net tier, n trades):")
    print("  " + ", ".join(f"{k} {v*100:.0f}% ({(X.sym == k).sum()})" for k, v in g.head(10).items()))
    s.N = N
    base = {cost: NL.v7(s, cost).r for cost in (3.0, "tier", "tier_hi")}
    for k_drop in (0, 5, 10):
        drop = set(g.head(k_drop).index)
        T2 = T.copy(); T2.loc[T2.sym.isin(drop), "F1"] = False
        Xh = T2[T2.date >= "2024-01-01"]
        fl = Xh.F1.values.astype(bool)
        b, t = twoway_t(Xh.net_t.values, fl, Xh.date.values, Xh.sym.values)
        Nf = NL.with_flags(N, T2, "F1")
        s.N = Nf
        line = []
        for cost in (3.0, "tier", "tier_hi"):
            r = NL.v7(s, cost, tilt=NL.upweight_tilt).r
            d1 = B.stats(r[:"2023-12-31"])[0] - B.stats(base[cost][:"2023-12-31"])[0]
            d2 = B.stats(r["2024-01-01":])[0] - B.stats(base[cost]["2024-01-01":])[0]
            line.append(f"@{cost} {d1*100:+5.2f}/{d2*100:+5.2f}pp")
        print(f"  drop top-{k_drop:2d} from flag: 2024-26 diff {b*1e4:6.1f}bp t_2way {t['2way']:5.2f} | up2x book gain "
              + "  ".join(line))
    s.N = N
    # V4 proxy coverage
    print("\n== V4 proxy universe per year: trades / distinct symbols")
    for y, gp in P.groupby(P.date.dt.year):
        print(f"  {y}: {len(gp):6d} trades {gp.sym.nunique():5d} syms  flagged {int(gp.F1.fillna(False).sum()):4d}")
    # V5 characteristics
    X = T[T.date >= "2024-01-01"].copy()
    px = {}
    for d, nd in N.items():
        if d < pd.Timestamp("2024-01-01"):
            continue
        for j, sy in enumerate(nd.syms):
            px[(d, sy)] = (nd.price[j], nd.adv[j], float(B.cost_bps("tier_hi", nd.price[j:j+1], nd.adv[j:j+1])[0]))
    X[["price", "adv", "c_hi"]] = [px.get((d, sy), (np.nan,) * 3) for d, sy in zip(X.date, X.sym)]
    print("\n== V5 2024-26 medians flagged vs seasoned: price, ADV $M, tier_hi bp/side")
    for f, gX in X.groupby("F1"):
        print(f"  F1={f}: n {len(gX)} price {gX.price.median():6.2f} adv {gX.adv.median()/1e6:6.1f} c_hi {gX.c_hi.median():5.1f}"
              f"  gross ret {gX.ret.mean()*1e4:6.1f}bp  net_h {gX.net_h.mean()*1e4:6.1f}bp")


if __name__ == "__main__" and "--raw" not in __import__("sys").argv:
    main()


# ---------------------------------------------------------------- V6: split-adjustment lookahead
def raw_price_check():
    """V6. The panel is fetched with adjustment='all' (split-adjusted as of 2026-09), so a name
    that later reverse-split looks like a $20-$1,600 stock when it really traded under $1.
    Live, the night pool's price >= $5 filter sees the RAW price. Raw SIP daily closes for every
    pool symbol were fetched once (scratchpad nl_rawclose.pkl, alpaca adjustment='raw').
    Drop pool names whose raw close on the decision day < $5; re-run V7 and the F1 tests."""
    from .validate import load_sim
    raw = pd.read_pickle(f"{NL.SP}/nl_rawclose.pkl").set_index(["date", "symbol"])["close"]
    c = NL.load_cache(); s = load_sim(); N = c["N"]
    A = NL.Ages(c); T, _ = NL.q2_tables(c, A)
    T["raw"] = [raw.get((d, sy), np.nan) for d, sy in zip(T.date, T.sym)]
    adjc = {(d, sy): nd.close[j] for d, nd in N.items() for j, sy in enumerate(nd.syms)}
    T["adjc"] = [adjc[(d, sy)] for d, sy in zip(T.date, T.sym)]
    T["factor"] = T.adjc / T.raw
    T["sub5"] = T.raw < 5
    print("\n== V6 raw-price check (split-adjustment lookahead)")
    print(f"  pool trades {len(T)}, raw price missing {T.raw.isna().mean():.1%}, adj/raw factor > 1.5: {(T.factor > 1.5).mean():.1%},"
          f" raw < $5: {T.sub5.mean():.1%}")
    for lab, X in {"2021-23": T[T.date <= "2023-12-31"], "2024-26": T[T.date >= "2024-01-01"]}.items():
        for f in (False, True):
            g = X[X.F1 == f]
            print(f"  {lab} F1={f}: n {len(g)} raw<$5 {g.sub5.mean():5.1%}  net_t mean all {g.net_t.mean()*1e4:6.1f}bp | "
                  f"raw<$5 {g[g.sub5].net_t.mean()*1e4:7.1f}bp (n {g.sub5.sum()}) | raw>=$5 {g[~g.sub5].net_t.mean()*1e4:6.1f}bp")
        Y = X[~X.sub5]
        b, t = twoway_t(Y.net_t.values, Y.F1.values.astype(bool), Y.date.values, Y.sym.values)
        print(f"  {lab} F1 diff on raw>=$5 trades: {b*1e4:6.1f}bp  t_day {t['day']:5.2f} t_2way {t['2way']:5.2f}")
    bad = set(zip(T.date[T.sub5], T.sym[T.sub5]))
    Nr = NL.exclude(N, lambda d, nd: np.array([(d, sy) in bad for sy in nd.syms]))
    T2 = T[~T.sub5]
    for cost in (3.0, "tier", "tier_hi"):
        s.N = N; b0 = NL.v7(s, cost).r
        s.N = Nr; b1 = NL.v7(s, cost).r
        s.N = NL.with_flags(Nr, T2, "F1"); u1 = NL.v7(s, cost, tilt=NL.upweight_tilt).r
        s.N = NL.exclude(NL.with_flags(Nr, T2, "F1"), lambda d, nd: nd.flag); e1 = NL.v7(s, cost).r
        f = lambda r: f"{B.stats(r[:'2023-12-31'])[0]*100:5.1f}/{B.stats(r['2024-01-01':])[0]*100:5.1f}"
        print(f"  V7 @{str(cost):7s} shipped(adj) {f(b0)} | raw>=$5 pool {f(b1)} | +F1 up2x {f(u1)} | +F1 excl {f(e1)}")
    s.N = N


if __name__ == "__main__" and "--raw" in __import__("sys").argv:
    raw_price_check()
