"""Charge #4: fill the night leg's unused capacity with shallower losers.

    .venv/bin/python -m research.sim.fetch_depth     # once: 15:50 bars for low <= -6% names
    .venv/bin/python -m research.sim.depth

The night leg deploys ~half its allocation (addendum 17). The rejected
"overflow" put the spare money into names already held (concentration). This
tests the other way to use it: more names, from the -6%..-8% band, under the
same live rules (IBS < 0.1 at 15:50, vol20 >= 60%, 20d-corr dedupe at 0.7,
crowding, weekend half size).

Variants, all on top of V7 (V5 crash guards + TQQQ conviction, intraday 1.0x):
  plain -7 / -6   day_ret_max moved for everyone, live tilt as-is (a config change)
  fill            deep (<= -8%) book unchanged; the spare capacity goes to shallow
                  names ranked by a separately fitted edge model, 10% each, only
                  while predicted edge > that name's round-trip tier cost.
                  Model fitted on one half, judged on the other (both ways).
  placebo         same count and size of shallow names per night, drawn at random
                  from the same filtered shallow pool (no ranking, no cost gate)

Rule, fixed before looking: adopt only if both halves improve over V7, the
fill beats the placebo, at both `tier` and `tier_hi` costs.
"""
from __future__ import annotations

import copy
import glob
import os
from functools import lru_cache

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import book as B
from . import data as D
from .validate import load_sim

SHALLOW = -0.06
CORR = 0.7
S2 = {"QQQ": 0.5, "SMH": 0.5}
V7 = dict(tilt="live", noise=S2, weekend_scale=0.5, conviction_w=0.5, noise_cap=1.0)


# ------------------------------------------------------------------ data
def _rows_1550(f: str, C, L, H) -> list[dict]:
    """t1550.py's reconstruction of what was known at 15:50: last pre-15:50
    minute close, and the day's high/low unless they were set after 15:50."""
    d = pd.Timestamp(os.path.basename(f)[:10])
    df = pd.read_parquet(f)
    if df.empty or d not in C.index:
        return []
    t = df.timestamp.dt.tz_convert("America/New_York"); df["hm"] = t.dt.hour * 100 + t.dt.minute
    out = []
    for s, g in df.groupby("symbol"):
        if s not in C.columns:
            continue
        pre, post = g[g.hm < 1550], g[g.hm >= 1550]
        if pre.empty:
            continue
        p50 = pre.close.iloc[-1]
        Ld, Hd = L.at[d, s], H.at[d, s]
        L50 = Ld if (post.low.min() if len(post) else np.inf) > Ld + 1e-9 else pre.low.min()
        H50 = Hd if (post.high.max() if len(post) else -np.inf) < Hd - 1e-9 else pre.high.max()
        out.append(dict(date=d, sym=s, p50=p50, L50=L50, H50=max(H50, p50)))
    return out


@lru_cache(maxsize=1)
def candidates() -> pd.DataFrame:
    """Every name <= -6% and IBS < 0.1 at 15:50 (2021-02 on), same columns and
    definitions as night_trades.v2 (vol20/ret20/adv exactly as that file has
    them), with the addendum-14 bad-bar filter."""
    pk = D.DATA / "depth_cands.pkl"
    if pk.exists():
        return pd.read_pickle(pk)
    P = D.panel(); C, V, O, L, H = P["close"], P["volume"], P["open"], P["low"], P["high"]
    C1 = C.shift(1); lr = np.log(C / C1)
    vol20 = lr.rolling(20).std() * np.sqrt(252)
    ret20 = C1 / C.shift(21) - 1
    adv = (C * V).rolling(20).mean().shift(1)
    on = O.shift(-1) / C - 1
    rows = []
    for sub in ("lm1", "lm6"):
        for f in sorted(glob.glob(str(D.DATA / sub / "*.parquet"))):
            rows += _rows_1550(f, C, L, H)
    x = pd.DataFrame(rows).drop_duplicates(["date", "sym"])
    get = lambda M: np.array([M.at[a, b] for a, b in zip(x.date, x.sym)], float)
    x["pc"] = get(C1)
    x["day50"] = x.p50 / x.pc - 1
    x["ibs50"] = (x.p50 - x.L50) / (x.H50 - x.L50).replace(0, np.nan)
    x = x[(x.day50 <= SHALLOW) & (x.ibs50 < 0.1)].copy()
    for k, M in (("ret", on), ("vol20", vol20), ("ret20", ret20), ("adv", adv), ("C", C)):
        x[k] = get(M)
    x = x[(x.adv >= 1e7) & (x.pc >= 5)]      # live universe: night_adv_min, night_price_min
    x = x[np.isfinite(x.ret) & (x.ret.abs() <= 1)]
    twin = x.groupby(["date", "day50", "ret"]).sym.transform("count")
    x = x[twin == 1].copy()
    x.to_pickle(pk)
    return x


# --------------------------------------------------------------- edge model
FEATS = ("lvol", "day50")


def _X(g: pd.DataFrame) -> np.ndarray:
    return np.column_stack([np.ones(len(g)), np.log(np.maximum(g.vol20.values, 1e-3)), g.day50.values])


def fit_edge(x: pd.DataFrame, lo: str, hi: str) -> np.ndarray:
    """OLS of the close -> next-open return (bp, gross) on (1, log vol20, day
    return) over shallow-band names that pass the vol filter, in [lo, hi]."""
    g = x[(x.date >= lo) & (x.date <= hi) & (x.day50 > -0.08) & (x.vol20 >= 0.60)]
    beta, *_ = np.linalg.lstsq(_X(g), g.ret.values * 1e4, rcond=None)
    return beta


# ------------------------------------------------------------- night days
def night_days(x: pd.DataFrame, mode: str, *, thresh: float = -0.08, beta=None,
               cost: str = "tier", placebo_seed: int | None = None, counts: dict | None = None) -> dict:
    """NightDay per session. mode:
      "plain"  one pool at day_ret <= thresh, live pipeline, live tilt in Sim
      "fill"   deep pool as V7; spare capacity -> shallow names by predicted edge
      "placebo" deep pool as V7; `counts[d]` random shallow names instead
    For fill/placebo the per-name leg fraction is carried in nd.w (Sim tilt=callable)."""
    R = D.returns20()
    idx = {d: i for i, d in enumerate(R.index)}
    rng = np.random.default_rng(placebo_seed) if placebo_seed is not None else None
    out, picked = {}, {}
    for d, g in x.groupby("date"):
        if d < B.START:
            continue
        rows = pd.DataFrame({"price": g.p50.values, "prev_close": g.pc.values,
                             "high": g.H50.values, "low": g.L50.values}, index=g.sym.values)
        keep = g.set_index("sym")
        i = idx.get(pd.Timestamp(d))
        win = R.iloc[max(0, i - 20):i] if i is not None else None
        rets_of = lambda syms: {s: win[s].dropna().tolist() for s in syms if win is not None and s in win.columns}

        allp = sg.loser_picks(rows, day_ret_max=(thresh if mode == "plain" else SHALLOW), ibs_max=0.10,
                              price_min=5.0, price_max=2000.0)
        if allp.empty:
            continue
        deep = allp[allp.day_ret <= (thresh if mode == "plain" else -0.08)]
        shal = allp[allp.day_ret > -0.08] if mode != "plain" else allp.iloc[0:0]
        # deep: exactly the V7 pipeline
        deep, _ = sg.dedupe_correlated(deep, rets_of(deep.index), CORR) if len(deep) else (deep, [])
        deep = deep.assign(vol20=keep.loc[deep.index, "vol20"].values)
        n_raw = len(deep)
        dk, frac = sg.night_sizing(deep, vol_min=0.60, crowd_n=30, max_name_pct=0.10) if n_raw else (deep, 0.0)
        if mode == "plain":
            if dk.empty:
                continue
            k = keep.loc[dk.index]
            out[d] = B.NightDay(dk.index.values, dk.price.values, k.C.values, k.ret.values, k.adv.values,
                                k.vol20.values, k.ret20.values, dk.day_ret.values, frac, n_raw)
            continue
        # shallow: same filters, deduped against the deep names kept and each other
        w_deep = sg.night_tilt(dk.vol20.values, dk.day_ret.values, 0.25) * frac if len(dk) else np.array([])
        sel = []
        if len(shal):
            shal = shal.assign(vol20=keep.loc[shal.index, "vol20"].values)
            shal = shal[shal.vol20 >= 0.60]
            n_all = n_raw + len(shal)
            cap = min(1.0, 30 / max(n_all, 1)) - float(w_deep.sum())
            if len(shal) and cap > 0.02:
                c = B.cost_bps(cost, shal.price.values, keep.loc[shal.index, "adv"].values)
                if mode == "fill":
                    pred = _X(keep.loc[shal.index].assign(day50=shal.day_ret.values)) @ beta
                    order = np.argsort(-pred)
                    cand = [shal.index[j] for j in order if pred[j] > 2 * c[j]]
                else:
                    cand = list(shal.index[rng.permutation(len(shal))])
                # dedupe: walk candidates after the deep names already kept
                both = pd.concat([dk[["price"]], shal.loc[cand, ["price"]]])
                kept, _ = sg.dedupe_correlated(both, rets_of(both.index), CORR)
                cand = [s for s in kept.index if s in set(cand)]
                n_take = int(min(len(cand), np.ceil(cap / 0.10 - 1e-9)))
                if mode == "placebo":
                    n_take = min(n_take, (counts or {}).get(d, 0))
                left = cap
                for s in cand[:n_take]:
                    f = min(0.10, left)
                    if f <= 0.005:
                        break
                    sel.append((s, f)); left -= f
        picked[d] = len(sel)
        names = list(dk.index) + [s for s, _ in sel]
        if not names:
            continue
        w = np.r_[w_deep, [f for _, f in sel]]
        k = keep.loc[names]
        dr = np.r_[dk.day_ret.values, [shal.at[s, "day_ret"] for s, _ in sel]] if sel else dk.day_ret.values
        pr = np.r_[dk.price.values, [shal.at[s, "price"] for s, _ in sel]] if sel else dk.price.values
        nd = B.NightDay(np.array(names), pr, k.C.values, k.ret.values, k.adv.values, k.vol20.values,
                        k.ret20.values, dr, 1.0, n_raw)
        nd.w = w
        out[d] = nd
    return (out, picked) if mode == "fill" else out


def run(s: B.Sim, N: dict, cost: str, tilt="live"):
    sim = copy.copy(s); sim.N = N
    kw = dict(V7); kw["tilt"] = tilt
    return sim.replay(B.Params(night_cost=cost, **kw))


def row(df: pd.DataFrame, lab: str) -> str:
    r = df.r
    parts = [B.stats(r[:"2023-12-31"]), B.stats(r["2024-01-01":]), B.stats(r)]
    body = "  ".join(f"{c*100:5.1f}/{sh:4.2f}/{dd*100:4.0f}" for c, sh, dd in parts)
    return f"{lab:34s} {body}   use {df.night_used.mean()*100:4.0f}%   end ${df.E.iloc[-1]:>9,.0f}"


def main():
    x = candidates()
    s = load_sim()
    xs = x[(x.day50 > -0.08)]
    print(f"candidates: {len(x):,} rows, {len(xs):,} in the -6..-8% band "
          f"({(xs.vol20 >= .6).sum():,} pass vol20)")
    # sanity: the deep subset must reproduce night_trades.v2 on the same dates
    v2 = D.night_candidates(); v2 = v2[v2.date >= B.START]
    mine = x[(x.day50 <= -0.08)]
    a = set(zip(v2.date, v2.sym)); b = set(zip(mine.date, mine.sym))
    print(f"deep parity vs night_trades.v2: {len(a & b):,} shared, {len(a - b)} only v2, {len(b - a)} only here")

    b1 = fit_edge(x, "2021-01-01", "2023-12-31"); b2 = fit_edge(x, "2024-01-01", "2026-12-31")
    print(f"shallow edge model (bp = b0 + b1 log vol20 + b2 day_ret): fit 21-23 {np.round(b1, 1)}, "
          f"fit 24-26 {np.round(b2, 1)}")
    g = xs[xs.vol20 >= .6]
    for lo, hi in (("2021", "2023"), ("2024", "2026")):
        h = g[(g.date >= lo) & (g.date <= hi + "-12-31")]
        print(f"  shallow band {lo}-{hi}: n {len(h):,}, mean close->open {h.ret.mean()*1e4:+.1f}bp gross "
              f"(t {h.ret.mean()/h.ret.std()*np.sqrt(len(h)):.1f})")
    tiltw = lambda nd: nd.w
    for cost in ("tier", "tier_hi"):
        print(f"\n=== {cost} costs   2021-23 / 2024-26 / full  CAGR/Sharpe/maxDD ===")
        base = night_days(x, "plain", thresh=-0.08)
        print(row(run(s, base, cost), "V7 baseline (<= -8%)"))
        s07 = copy.copy(s); s07.N = B.night_days(max_corr=CORR)
        print(row(s07.replay(B.Params(night_cost=cost, **V7)), "  (V7 on the sim's own night data)"))
        for t in (-0.07, -0.06):
            print(row(run(s, night_days(x, "plain", thresh=t), cost), f"plain day_ret_max {t:+.0%}"))
        res = {}
        for lab, beta in (("fit 21-23", b1), ("fit 24-26", b2)):
            N, cnt = night_days(x, "fill", beta=beta, cost=cost)
            df = run(s, N, cost, tilt=tiltw); res[lab] = (df, cnt)
            print(row(df, f"fill, model {lab}") + f"   +{np.mean(list(cnt.values())):.2f} names/night")
        # honest out-of-sample splice: each half judged with the model fitted on the other
        oos = pd.concat([res["fit 24-26"][0].r[:"2023-12-31"], res["fit 21-23"][0].r["2024-01-01":]])
        print(row(res["fit 21-23"][0].assign(r=oos), "fill, out-of-sample splice"))
        for lab in ("fit 21-23", "fit 24-26"):
            cnt = res[lab][1]
            P = [run(s, night_days(x, "placebo", cost=cost, placebo_seed=k, counts=cnt), cost, tilt=tiltw)
                 for k in range(10)]
            st = np.array([[B.stats(p.r[:"2023-12-31"]), B.stats(p.r["2024-01-01":]), B.stats(p.r)] for p in P])
            m = st.mean(axis=0)
            body = "  ".join(f"{c*100:5.1f}/{sh:4.2f}/{dd*100:4.0f}" for c, sh, dd in m)
            use = np.mean([p.night_used.mean() for p in P]) * 100
            print(f"{'placebo, counts of ' + lab + ' (10 seeds)':34s} {body}   use {use:4.0f}%   "
                  f"end ${np.mean([p.E.iloc[-1] for p in P]):>9,.0f}   "
                  f"(full CAGR seeds {st[:, 2, 0].min()*100:.1f}-{st[:, 2, 0].max()*100:.1f})")


if __name__ == "__main__":
    main()
