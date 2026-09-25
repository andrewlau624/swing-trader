"""Multi-day losers for the night leg's idle capacity (addendum 27 candidate).

    PYTHONPATH=. .venv/bin/python -m research.sim.multiday_night

The night leg deploys about half its allocation (addendum 17): only names down
>= 8% on the day qualify. NEXT.md's untested structural fix is "multiple
formation horizons". Addendum 20 killed the plain -6..-8% day band; this asks
whether a MULTI-DAY drop rescues those names.

Two stages:
  1. screen (daily bars, close-based, biased; a gate only): close -> next-open
     edge of names with a big 2/3/5-day drop that did NOT fall 8% today, vs the
     regular pool and vs any name closing near its low.
  2. honest book test on the 15:50 data that exists (depth.candidates: names at
     -6..-8% at 15:50, IBS < 0.1, live filters). Spare night capacity only, never
     crowding out the regular picks; deepest multi-day drop first, 10% each,
     deduped against the regular names (0.7). Placebo: the same count per night
     drawn at random from the same -6..-8% pool, 50 seeds.

Pre-registered (nothing searched):
  M2  2-day drop (p50 vs close d-2) <= -12%
  M3  3-day drop <= -15%
  M5  5-day drop <= -20%
Adopt only if both halves improve over V7 at tier AND tier_hi, and it beats
the placebo.
"""
from __future__ import annotations

import copy
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import book as B
from . import data as D
from . import depth as DP
from .growth import eh
from .validate import load_sim

VARIANTS = {"M2": (2, -0.12), "M3": (3, -0.15), "M5": (5, -0.20)}
CORR = 0.7
SEEDS = 50
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else None


# ------------------------------------------------------------- stage 1
def screen() -> list[str]:
    P = D.panel(); C, O, H, L, V = P["close"], P["open"], P["high"], P["low"], P["volume"]
    C1 = C.shift(1)
    day = C / C1 - 1
    ibs = (C - L) / (H - L).replace(0, np.nan)
    vol20 = np.log(C / C1).rolling(20).std() * np.sqrt(252)
    adv = (C * V).rolling(20).mean().shift(1)
    on = O.shift(-1) / C - 1
    base = (adv >= 1e7) & (C1 >= 5) & (C1 <= 2000) & (vol20 >= 0.6) & (on.abs() <= 0.3) & (ibs < 0.1)
    pools = {"regular (day <= -8%)": base & (day <= -0.08),
             "control: any name near its low, day > -8%": base & (day > -0.08)}
    for k, (n, th) in VARIANTS.items():
        pools[f"{k}: {n}d <= {th:.0%}, day > -8%"] = base & (day > -0.08) & (C / C.shift(n) - 1 <= th)
    lines = []
    for name, m in pools.items():
        cells = []
        for a, z in (("2021-02-01", "2023-12-31"), ("2024-01-01", "2026-09-18")):
            r = on.loc[a:z][m.loc[a:z]].stack().dropna()
            cells.append(f"{r.mean()*1e4:+6.1f}bp (median {r.median()*1e4:+5.1f}, {len(r):5d} trades, "
                         f"{m.loc[a:z].sum(axis=1).mean():4.1f}/day)")
        lines.append(f"{name:44s} {cells[0]} | {cells[1]}")
    return lines


# ------------------------------------------------------------- stage 2
def with_multiday(x: pd.DataFrame) -> pd.DataFrame:
    C = D.panel()["close"]
    x = x.copy()
    for n in sorted({n for n, _ in VARIANTS.values()}):
        Cn = C.shift(n)
        x[f"c{n}"] = x.p50.values / np.array([Cn.at[a, b] for a, b in zip(x.date, x.sym)], float) - 1
    return x


def night_days(x: pd.DataFrame, variant: str | None, *, placebo_seed: int | None = None,
               counts: dict | None = None) -> tuple[dict, dict, dict]:
    """V7 regular pool, plus spare capacity -> multi-day shallow names (variant),
    or `counts[d]` random shallow names (placebo). Weights ride on nd.w."""
    R = D.returns20()
    idx = {d: i for i, d in enumerate(R.index)}
    rng = np.random.default_rng(placebo_seed) if placebo_seed is not None else None
    n, th = VARIANTS.get(variant, (None, None))
    out, picked, extra = {}, {}, {}
    for d, g in x.groupby("date"):
        if d < B.START:
            continue
        rows = pd.DataFrame({"price": g.p50.values, "prev_close": g.pc.values,
                             "high": g.H50.values, "low": g.L50.values}, index=g.sym.values)
        keep = g.set_index("sym")
        i = idx.get(pd.Timestamp(d))
        win = R.iloc[max(0, i - 20):i] if i is not None else None
        rets_of = lambda syms: {s: win[s].dropna().tolist() for s in syms
                                if win is not None and s in win.columns}
        allp = sg.loser_picks(rows, day_ret_max=DP.SHALLOW, ibs_max=0.10, price_min=5.0, price_max=2000.0)
        if allp.empty:
            continue
        deep = allp[allp.day_ret <= -0.08]
        shal = allp[allp.day_ret > -0.08]
        deep, _ = sg.dedupe_correlated(deep, rets_of(deep.index), CORR) if len(deep) else (deep, [])
        deep = deep.assign(vol20=keep.loc[deep.index, "vol20"].values)
        n_raw = len(deep)
        dk, frac = sg.night_sizing(deep, vol_min=0.60, crowd_n=30, max_name_pct=0.10) if n_raw else (deep, 0.0)
        w_deep = sg.night_tilt(dk.vol20.values, dk.day_ret.values, 0.25) * frac if len(dk) else np.array([])
        sel = []
        if len(shal) and (variant or placebo_seed is not None):
            shal = shal.assign(vol20=keep.loc[shal.index, "vol20"].values)
            shal = shal[shal.vol20 >= 0.60]
            cap = min(1.0, 30 / max(n_raw + len(shal), 1)) - float(w_deep.sum())
            if len(shal) and cap > 0.02:
                if variant:
                    cn = keep.loc[shal.index, f"c{n}"]
                    cand = list(cn[cn <= th].sort_values().index)      # deepest multi-day drop first
                else:
                    cand = list(shal.index[rng.permutation(len(shal))])
                if cand:
                    both = pd.concat([dk[["price"]], shal.loc[cand, ["price"]]])
                    kept, _ = sg.dedupe_correlated(both, rets_of(both.index), CORR)
                    cand = [s for s in kept.index if s in set(cand)]
                    n_take = int(min(len(cand), np.ceil(cap / 0.10 - 1e-9)))
                    if placebo_seed is not None:
                        n_take = min(n_take, (counts or {}).get(d, 0))
                    left = cap
                    for s in cand[:n_take]:
                        f = min(0.10, left)
                        if f <= 0.005:
                            break
                        sel.append((s, f)); left -= f
        picked[d] = len(sel)
        extra[d] = [(s, float(keep.at[s, "ret"]), float(keep.at[s, "C"]), float(keep.at[s, "adv"]))
                    for s, _ in sel]
        names = list(dk.index) + [s for s, _ in sel]
        if not names:
            continue
        k = keep.loc[names]
        w = np.r_[w_deep, [f for _, f in sel]]
        dr = np.r_[dk.day_ret.values, [shal.at[s, "day_ret"] for s, _ in sel]] if sel else dk.day_ret.values
        pr = np.r_[dk.price.values, [shal.at[s, "price"] for s, _ in sel]] if sel else dk.price.values
        nd = B.NightDay(np.array(names), pr, k.C.values, k.ret.values, k.adv.values, k.vol20.values,
                        k.ret20.values, dr, 1.0, n_raw)
        nd.w = w
        out[d] = nd
    return out, picked, extra


def run(s, N, cost):
    sim = copy.copy(s); sim.N = N
    kw = dict(DP.V7); kw["tilt"] = lambda nd: nd.w
    return sim.replay(B.Params(night_cost=cost, **kw))


def st3(r):
    return [B.stats(r[:"2023-12-31"]), B.stats(r["2024-01-01":]), B.stats(r)]


def fmt3(parts):
    return "  ".join(f"{c*100:5.1f}/{sh:4.2f}/{dd*100:4.0f}" for c, sh, dd in parts)


def trade_stats(extra: dict, cost: str) -> str:
    rows = [(d, r, c, a) for d, v in extra.items() for (_, r, c, a) in v]
    if not rows:
        return "no trades"
    df = pd.DataFrame(rows, columns=["d", "ret", "C", "adv"])
    df["net"] = df.ret - 2 * B.cost_bps(cost, df.C.values, df.adv.values) / 1e4
    out = []
    for a, z in (("2021-02-01", "2023-12-31"), ("2024-01-01", "2026-09-18")):
        h = df[(df.d >= a) & (df.d <= z)]
        dly = h.groupby("d").net.mean()
        t = dly.mean() / dly.std() * np.sqrt(len(dly)) if len(dly) > 5 else np.nan
        out.append(f"{len(h):4d} trades, gross {h.ret.mean()*1e4:+6.1f}bp, net {h.net.mean()*1e4:+6.1f}bp (day-t {t:+.2f})")
    return " | ".join(out)


def main():
    print("== 1. screen (daily bars, close-based: biased, a gate only), close -> next open, gross")
    print(f"{'':44s} {'2021-23':>52s} | {'2024-26':>50s}")
    for l in screen():
        print(l)

    x = with_multiday(DP.candidates())
    s = load_sim()
    base_N, _, _ = night_days(x, None)
    xs = x[(x.day50 > -0.08) & (x.vol20 >= 0.6)]
    print(f"\n== 2. honest 15:50 pool: {len(xs):,} names at -6..-8% (vol20 >= 60%); regular pool "
          f"per-trade reference: night_trades.v2")
    for k, (n, th) in VARIANTS.items():
        m = xs[xs[f"c{n}"] <= th]
        print(f"  {k}: {len(m):,} qualify ({len(m)/len(xs):.0%} of the band)")
    series = {}
    for cost in ("tier", "tier_hi"):
        print(f"\n=== {cost}   2021-23 / 2024-26 / full  CAGR/Sharpe/maxDD   night use")
        b = run(s, base_N, cost)
        series[("v7", cost)] = b
        print(f"{'V7 (regular pool only)':34s} {fmt3(st3(b.r))}   use {b.night_used.mean()*100:4.0f}%")
        for k in VARIANTS:
            N, cnt, extra = night_days(x, k)
            df = run(s, N, cost); series[(k, cost)] = df
            print(f"{k + ' fill':34s} {fmt3(st3(df.r))}   use {df.night_used.mean()*100:4.0f}%   "
                  f"+{np.mean(list(cnt.values())):.2f} names/night")
            print(f"{'   per trade':34s} {trade_stats(extra, cost)}")
            P = [run(s, night_days(x, None, placebo_seed=j, counts=cnt)[0], cost) for j in range(SEEDS)]
            sh = np.array([[p[1] for p in st3(p.r)] for p in P])            # Sharpe per half, full
            real = np.array([p[1] for p in st3(df.r)])
            beats = (real[None, :] > sh).mean(axis=0)
            print(f"{'   placebo (' + str(SEEDS) + ' seeds)':34s} mean Sharpe {sh.mean(axis=0).round(2)}; "
                  f"real beats {beats[0]:.0%} / {beats[1]:.0%} / {beats[2]:.0%}")
    print("\n== edge-halves (tier_hi): each leg's mean contribution cut by half")
    for k in ["v7"] + list(VARIANTS):
        print(f"{k:34s} {fmt3(st3(eh(series[(k, 'tier_hi')])))}")
    print("\n== episodes, tier (%): 2022 bear (Jan-Oct 2022), Aug 2024 unwind, Apr 2025 tariffs")
    ep = [("2022-01-03", "2022-10-14"), ("2024-07-31", "2024-08-09"), ("2025-04-01", "2025-04-11")]
    for k in ["v7"] + list(VARIANTS):
        r = series[(k, "tier")].r
        print(f"{k:34s} " + "  ".join(f"{((1 + r[a:z]).prod() - 1)*100:+6.1f}" for a, z in ep))
    if OUT:
        best = max(VARIANTS, key=lambda k: B.stats(series[(k, "tier_hi")].r)[1])
        with open(OUT, "wb") as fh:
            pickle.dump({"v7": series[("v7", "tier")].r, "v7_plus": series[(best, "tier")].r,
                         "best": best}, fh)
        print(f"\nseries saved -> {OUT} (best by tier_hi Sharpe: {best})")


if __name__ == "__main__":
    main()
