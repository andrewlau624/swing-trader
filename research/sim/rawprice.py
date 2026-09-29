"""Addendum 30: the night pool used split-adjusted prices. Every night number, restated.

    # once, under the heavy lock (night_days needs the SIP panel; the 2020 rebuild panel2020):
    PYTHONPATH=. .venv/bin/python -m research.sim.rawprice --cache
    # everything else (no panel):
    PYTHONPATH=. .venv/bin/python -m research.sim.rawprice

The research panel and night_candidates() carry adjustment='all' prices, adjusted as of the
fetch (2026-09). A name that reverse-split later looks like a $20-$1,600 stock on days it really
traded under $1 (TDIC 2025-10-16: $66.81 adjusted, $0.535 raw). The live executor sees real
quotes, so three things in the backtest used the wrong price: the $5 night_price_min floor (and
the $2,000 ceiling), the price tier in book.cost_bps, and whole-share rounding. Returns are
split-invariant and unchanged.

Raw daily closes: data/research/night/raw_close.parquet (Alpaca SIP, adjustment='raw' and 'all'
from the same request batch, so raw/adj is the exact cumulative factor on that date), every
night_candidates() symbol 2020-10 -> 2026-09 plus every 2020 close-signal candidate symbol
(panel2020) 2019-10 -> 2020-11.

Sections
  A. coverage of the raw factor; how many pool trades were really < $5
  B. books, adjusted vs raw, 3bp / tier / tier_hi: 2021-23 | 2024-26 | full, EH, 5y MC P(DD>30/50)
     taxable (Sim.replay, addendum 29 style): V7 shipped 1.0x cap .10, gate 1.3x cap .10,
     moderate 1.3x cap .15, moderate as built 1.0x cap .15, aggressive 1.3x cap .20 intraday .6,
     live today 1.0x cap .10 no conviction;  Roth (roth_opt.Roth): b1 as modelled (asis), live M3
  C. 2020 close-signal rebuild (COVID): night leg unit weight, adjusted vs raw
  D. post-hoc diagnostic (the verifier's): raw < $5 trades in the ADJUSTED pool, net by cost model
  E. PRE-REGISTERED floor test (SHADOW-ONLY; stamped Mon Sep 28 22:13:28 PDT 2026 in
     scratchpad addenda/rawprice.md before any number): night_price_min in {5, 3, 2, 1} on raw
     prices, cost "tier+tick" (tier on raw price, floored at half a $0.01 tick / price per side),
     sensitivity tier_hi+tick / flat3+tick; V7 and moderate; both halves; placebo = same-count
     draws of raw >= $5 trades from the same vol20 deciles (500 draws).
"""
from __future__ import annotations

import copy
import pickle
import sys

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import book as B
from . import data as D
from . import growth as G

SCR = str(__import__("pathlib").Path(__file__).resolve().parents[2]) + "/data/research/program"
CACHE = f"{SCR}/cache_rawprice.pkl"
COSTS = (3.0, "tier", "tier_hi")
CAPS = (0.10, 0.15, 0.20)
FLOORS = (5.0, 3.0, 2.0, 1.0)
PER = (("2021-23", "2021-01-01", "2023-12-31"), ("2024-26", "2024-01-01", "2026-12-31"))
TAX = {  # label: (gross, cap, conviction, intraday cap)
    "V7 shipped 1.0x cap.10": (1.0, 0.10, 0.5, None),
    "gate 1.3x cap.10": (1.3, 0.10, 0.5, None),
    "moderate 1.3x cap.15": (1.3, 0.15, 0.5, None),
    "moderate as built 1.0x cap.15": (1.0, 0.15, 0.5, None),
    "aggressive 1.3x cap.20 i.6": (1.3, 0.20, 0.5, 0.6),
    "live today 1.0x cap.10 no conv": (1.0, 0.10, 0.0, None),
}


# ================================================================== cache (heavy lock)
def days_2020(raw: pd.DataFrame | None, max_corr=0.7, price_min=5.0):
    """crash.days_2020 with the price floor on raw prices when `raw` (symbol, date, raw_close,
    adj_close) is given. Returns ({date: (rets, vol20, day_ret, n_raw, gap)}, picks table)."""
    P = pd.read_pickle(D.DATA / "panel2020.pkl")
    O, H, L, C, V = (P[k] for k in ["open", "high", "low", "close", "volume"])
    R = C.pct_change(fill_method=None)
    adv = (C * V).rolling(20).mean().shift(1)
    vol20 = R.rolling(20).std().shift(1) * np.sqrt(252)
    nxt = O.shift(-1) / C - 1
    F = None
    if raw is not None:     # factor = raw close / this panel's own close (same basis by construction)
        rc = raw[raw.raw_close > 0].pivot(index="date", columns="symbol", values="raw_close")
        F = (rc.reindex(index=C.index, columns=C.columns) / C).replace([np.inf, -np.inf], np.nan)
        F = F.ffill().bfill().fillna(1.0)
    idx = C.index
    out, tab = {}, []
    for i in range(21, len(idx) - 1):
        d = idx[i]
        f = F.iloc[i] if F is not None else 1.0
        rows = pd.DataFrame({"price": C.iloc[i] * f, "prev_close": C.iloc[i - 1] * f,
                             "high": H.iloc[i] * f, "low": L.iloc[i] * f})
        ok = (adv.iloc[i] >= 1e7) & nxt.iloc[i].abs().le(1)
        picks = sg.loser_picks(rows[ok.reindex(rows.index, fill_value=False)].dropna(),
                               day_ret_max=-0.08, ibs_max=0.10, price_min=price_min, price_max=2000)
        if picks.empty:
            continue
        win = R.iloc[i - 20:i][picks.index]
        picks, _ = sg.dedupe_correlated(picks, {s: win[s].dropna().tolist() for s in picks.index}, max_corr)
        out[d] = (nxt.iloc[i][picks.index].values, vol20.iloc[i][picks.index].values,
                  picks.day_ret.values, len(picks), (idx[i + 1] - d).days)
        tab += [(d, s, p, C.iloc[i][s]) for s, p in zip(picks.index, picks.price)]
    return out, pd.DataFrame(tab, columns=["date", "sym", "price", "adj"])


def build_cache():
    x = D.night_candidates(raw=True)
    out = {"cands": x[["date", "sym", "p50", "C", "raw_f", "raw_src", "raw_p50", "vol20", "ret", "adv"]].copy()}
    out["adj"] = {c: B.night_days(max_corr=0.7, max_name_pct=c) for c in CAPS}
    out["raw"] = {c: B.night_days(max_corr=0.7, max_name_pct=c, raw_price=True) for c in CAPS}
    out["floor"] = {(f, c): B.night_days(max_corr=0.7, max_name_pct=c, raw_price=True, price_min=f)
                    for f in FLOORS[1:] for c in (0.10, 0.15)}
    raw = pd.read_parquet(D.RAW_CLOSE)
    out["y2020"] = {"adj": days_2020(None), "raw": days_2020(raw)}
    pickle.dump(out, open(CACHE, "wb"))
    print("wrote", CACHE)
    from .validate import load_sim
    load_sim(raw_price=True, refresh=True)
    print("wrote", "sim_cache_raw.pkl")


# ================================================================== helpers
def cell(r):
    c, s, d = B.stats(r)
    return f"{c*100:5.1f}/{s:4.2f}/{d*100:4.0f}"


def halves(r):
    return " | ".join(cell(r[a:b]) for _, a, b in PER) + " | " + cell(r)


def tax_run(s, N, g, cap, conv, nz, cost):
    s.N = N
    return s.replay(B.Params(**{**G.V7, **G.cfg(g, conv, 2, nz), "night_cost": cost}))


def pool_trades(N, cands, cost):
    """Per-trade net (ret - 2 x cost on the NightDay's own price) for every pool name."""
    rows = []
    for d, nd in N.items():
        c = B.cost_bps(cost, nd.price, nd.adv)
        for j, sy in enumerate(nd.syms):
            rows.append((d, sy, nd.price[j], nd.ret[j], nd.vol20[j], nd.adv[j], c[j]))
    t = pd.DataFrame(rows, columns=["date", "sym", "price", "ret", "vol20", "adv", "c"])
    t["net"] = t.ret - 2 * t.c / 1e4
    k = cands.set_index(["date", "sym"])
    t["raw_p50"] = k.raw_p50.reindex(pd.MultiIndex.from_frame(t[["date", "sym"]])).values
    t["raw_src"] = k.raw_src.reindex(pd.MultiIndex.from_frame(t[["date", "sym"]])).values
    return t


# ================================================================== main
def main():
    from . import roth_opt as RO
    c = pickle.load(open(CACHE, "rb"))
    s, c_ro, nzx, held = RO.load_ctx()
    x = c["cands"]

    # ---------------------------------------------------------- A. coverage
    print("== A. raw-price coverage (night_candidates, 2020-11 -> 2026-09)")
    print(f"  candidates {len(x):,} ({x.sym.nunique():,} symbols): exact {np.mean(x.raw_src == 'exact'):.1%}, "
          f"rebased {np.mean(x.raw_src == 'rebased'):.1%}, nearest-date factor {np.mean(x.raw_src == 'nearest'):.1%}, no raw data (factor 1) {np.mean(x.raw_src == 'none'):.1%}")
    for y, g in x.groupby(x.date.dt.year):
        print(f"  {y}: n {len(g):5d} exact {np.mean(g.raw_src == 'exact'):6.1%} nearest {np.mean(g.raw_src == 'nearest'):5.1%} "
              f"none {np.mean(g.raw_src == 'none'):5.1%} | adj/raw > 1.5 {np.mean(1 / g.raw_f > 1.5):5.1%} "
              f"| adj >= $5 but raw < $5 {np.mean((g.p50 >= 5) & (g.raw_p50 < 5)):5.1%} "
              f"| adj < $5 but raw >= $5 {np.mean((g.p50 < 5) & (g.raw_p50 >= 5)):5.1%}")
    ta = pool_trades(c["adj"][0.10], x, "tier")
    print(f"  V7 pool (adjusted, corr .7 cap .10): {len(ta):,} trades; really < $5 raw: {np.mean(ta.raw_p50 < 5):.1%}; "
          f"raw factor from 'none': {np.mean(ta.raw_src == 'none'):.1%}")
    for y, g in ta.groupby(ta.date.dt.year):
        print(f"    {y}: {len(g):5d} trades, raw < $5 {np.mean(g.raw_p50 < 5):5.1%}, raw < $1 {np.mean(g.raw_p50 < 1):5.1%}")
    tr = pool_trades(c["raw"][0.10], x, "tier")
    print(f"  V7 pool (raw):      {len(tr):,} trades; names in raw not adj {len(set(zip(tr.date, tr.sym)) - set(zip(ta.date, ta.sym))):,} "
          f"(forward splits: adjusted < $5, raw >= $5), in adj not raw {len(set(zip(ta.date, ta.sym)) - set(zip(tr.date, tr.sym))):,}")

    # ---------------------------------------------------------- B. books
    res = {}
    print("\n== B. books, ADJUSTED vs RAW prices. CAGR/Sharpe/maxDD 2021-23 | 2024-26 | full; EH; 5y MC $3k+$1k/mo under EH")
    for lab, (g, cap, conv, nz) in TAX.items():
        for cost in COSTS:
            for pool in ("adj", "raw"):
                df = tax_run(s, c[pool][cap], g, cap, conv, nz, cost)
                e = G.eh(df); m = G.mc(e, 3000, 1000)
                res[(lab, cost, pool)] = dict(r=df.r, eh=e, mc=m)
                print(f"  {lab:32s}{str(cost):>8s} {pool}  {halves(df.r)} | EH {cell(e)} | med ${m['med']:>9,.0f} "
                      f"P30 {m['dd30']:4.0%} P50 {m['dd50']:4.0%}", flush=True)
    ctx = (copy.copy(s), c_ro, nzx, held)
    for lab, v in (("Roth b1 as modelled (asis)", RO.RV(mech="asis")), ("Roth live-accurate M3", RO.RV(mech="M3"))):
        for cost in COSTS:
            for pool in ("adj", "raw"):
                ctx[0].N = c[pool][0.10]
                df = RO.run_roth(ctx, v, cost)
                e = RO.eh(df); m = G.mc(e, 7800, 625)
                res[(lab, cost, pool)] = dict(r=df.r, eh=e, mc=m)
                print(f"  {lab:32s}{str(cost):>8s} {pool}  {halves(df.r)} | EH {cell(e)} | "
                      f"P30 {m['dd30']:4.0%} P50 {m['dd50']:4.0%}", flush=True)
    s.N = c["adj"][0.10]
    print("\n  full-period CAGR change, raw - adjusted (pp): 3bp / tier / tier_hi")
    for lab in list(TAX) + ["Roth b1 as modelled (asis)", "Roth live-accurate M3"]:
        dd = []
        for cost in COSTS:
            a, b = res[(lab, cost, "adj")]["r"], res[(lab, cost, "raw")]["r"]
            dd.append(f"{(B.stats(b)[0] - B.stats(a)[0])*100:+5.1f} (EH {(B.stats(res[(lab, cost, 'raw')]['eh'])[0] - B.stats(res[(lab, cost, 'adj')]['eh'])[0])*100:+5.1f})")
        print(f"  {lab:32s} " + "  ".join(dd))

    # ---------------------------------------------------------- C. 2020
    from . import crash as CR
    print("\n== C. 2020 close-signal rebuild (panel2020), night leg unit weight, cap .10, 10bp flat, bias-corrected")
    spy_vol = s.spy.rolling(20).std() * np.sqrt(252)
    for pool in ("adj", "raw"):
        d20, tab = c["y2020"][pool]
        n = CR.night_series(d20, weekend=0.5, spy_vol=spy_vol)
        n = n[n.index < "2020-11-05"]; n = n - 9.1e-4 * (n != 0)
        cv = (1 + n["2020-02-19":"2020-03-23"]).prod() - 1
        print(f"  {pool}: picks {len(tab):5d} "
              f"2020-01..11 {cell(n['2020-01-01':])}  COVID {cv*100:+.1f}%")
    ta20, tr20 = c["y2020"]["adj"][1], c["y2020"]["raw"][1]
    print(f"  adj picks {len(ta20)} vs raw picks {len(tr20)}; only adj (really < $5 raw, or a raw floor/ceiling flip) {len(set(zip(ta20.date, ta20.sym)) - set(zip(tr20.date, tr20.sym)))}, "
          f"only raw {len(set(zip(tr20.date, tr20.sym)) - set(zip(ta20.date, ta20.sym)))}")

    # ---------------------------------------------------------- D. diagnostic
    print("\n== D. POST-HOC diagnostic: V7 ADJUSTED pool, trades really < $5 raw vs >= $5, mean net per trade (bp)")
    print("   (the +tick floor uses a $0.01 tick as pre-registered; sub-$1 names quote in $0.0001 (Rule 612), so it overstates <$1 costs)")
    for cost_lab, fn in (("tier on ADJ price (as published)", lambda t: B.cost_bps("tier", t.price.values, t.adv.values)),
                         ("tier on RAW price", lambda t: B.cost_bps("tier", t.raw_p50.values, t.adv.values)),
                         ("tier+tick on RAW price", lambda t: B.cost_bps("tier+tick", t.raw_p50.values, t.adv.values)),
                         ("tier_hi+tick on RAW price", lambda t: B.cost_bps("tier_hi+tick", t.raw_p50.values, t.adv.values))):
        t = ta.copy()
        t["net"] = t.ret - 2 * fn(t) / 1e4
        parts = []
        for h, a, b in PER:
            g = t[(t.date >= a) & (t.date <= b)]
            lo, hi = g[g.raw_p50 < 5], g[g.raw_p50 >= 5]
            l1, l5 = g[g.raw_p50 < 1], g[(g.raw_p50 >= 1) & (g.raw_p50 < 5)]
            parts.append(f"{h}: <$5 {lo.net.mean()*1e4:6.1f} (n {len(lo)}; <$1 {l1.net.mean()*1e4:7.1f} n {len(l1)}, "
                         f"$1-5 {l5.net.mean()*1e4:6.1f} n {len(l5)}) >=$5 {hi.net.mean()*1e4:6.1f}")
        print(f"  {cost_lab:34s} " + " | ".join(parts))

    # ---------------------------------------------------------- E. floor test
    print("\n== E. PRE-REGISTERED floor test (SHADOW-ONLY). raw prices; books 2021-23 | 2024-26 | full; EH")
    pools = {(5.0, cap): c["raw"][cap] for cap in (0.10, 0.15)}
    pools.update(c["floor"])
    fres = {}
    for lab, (g, cap, conv, nz) in (("V7 shipped 1.0x cap.10", TAX["V7 shipped 1.0x cap.10"]),
                                    ("moderate 1.3x cap.15", TAX["moderate 1.3x cap.15"])):
        for cost in ("tier+tick", "tier_hi+tick", "flat3+tick"):
            for f in FLOORS:
                df = tax_run(s, pools[(f, cap)], g, cap, conv, nz, cost)
                fres[(lab, cost, f)] = df.r
                gain = ""
                if f != 5.0:
                    b0 = fres[(lab, cost, 5.0)]
                    gain = "  gain " + " / ".join(f"{(B.stats(df.r[a:b])[0] - B.stats(b0[a:b])[0])*100:+5.1f}" for _, a, b in PER)
                print(f"  {lab:24s}{cost:>14s} floor ${f:.0f}  {halves(df.r)} | EH {cell(G.eh(df))}{gain}", flush=True)
    s.N = c["adj"][0.10]
    print("\n  added trades (raw price in [floor, $5)), net tier+tick per trade, vs placebo (500 same-vol-decile draws of raw >= $5 trades)")
    t5 = pool_trades(pools[(5.0, 0.10)], x, "tier+tick")
    allp = pool_trades(pools[(1.0, 0.10)], x, "tier+tick")
    edges = np.quantile(allp.vol20, np.linspace(0, 1, 11))
    dec = lambda v: np.clip(np.searchsorted(edges, v, side="right") - 1, 0, 9)
    t5["dec"] = dec(t5.vol20.values)
    rng = np.random.default_rng(30)
    for f in FLOORS[1:]:
        tf = pool_trades(pools[(f, 0.10)], x, "tier+tick")
        add = tf[tf.price < 5].copy(); add["dec"] = dec(add.vol20.values)
        parts = []
        for h, a, b in PER:
            A_ = add[(add.date >= a) & (add.date <= b)]
            base = t5[(t5.date >= a) & (t5.date <= b)]
            byd = {k: gb.net.values for k, gb in base.groupby("dec")}
            cnt = A_.dec.value_counts()
            draws = np.zeros(500)
            for k, n in cnt.items():
                pool_k = byd.get(k, base.net.values)
                draws += rng.choice(pool_k, size=(500, n), replace=True).sum(axis=1)
            draws /= max(len(A_), 1)
            pct = (draws < A_.net.mean()).mean()
            parts.append(f"{h}: n {len(A_):4d} net {A_.net.mean()*1e4:6.1f}bp (tier_hi+tick "
                         f"{(A_.ret - 2 * B.cost_bps('tier_hi+tick', A_.price.values, A_.adv.values) / 1e4).mean()*1e4:6.1f}) "
                         f"placebo mean {draws.mean()*1e4:6.1f} pct {pct:4.0%}")
        print(f"  floor ${f:.0f}: " + " | ".join(parts))
    pickle.dump({"books": res, "floor": fres}, open(f"{SCR}/rawprice_res.pkl", "wb"))


if __name__ == "__main__":
    if "--cache" in sys.argv:
        build_cache()
    else:
        main()
