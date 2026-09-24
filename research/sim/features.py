"""Better night-leg signals? New 15:50 features for picking and sizing the
night leg, and an IBS up-weight in downtrends. RESULTS.md addendum 23.

    PYTHONPATH=. .venv/bin/python -m research.sim.features

Priors, written BEFORE looking (one line each):
  late     15:30 -> 15:50 return as a share of the day's move: forced selling
           into the close overshoots more, so a larger late share bounces more.
  rvol     volume through 15:50 / 20d average daily volume: heavier volume =
           more liquidity demanded = bigger premium to the overnight provider.
  gap      share of the day's drop made by the open gap: a gap is news priced
           at once, selling after the open is flow, so a SMALL gap share bounces more.
  spy50    SPY at 15:50: on a red market day the drop is beta and bounces with
           the market; idio (day - SPY) = the name's own overshoot.
  dist20   distance from the prior 20-day low (<= 0 = a new low): capitulation
           at fresh lows overshoots more.
  dist252  same against the 52-week low.
  prev     yesterday's return: a second down day = persistent sellers = larger premium.
  lprice   log price: cheap names carry larger spreads and bigger reversal premia (gross).
  IBS      IBS trades earn more with SPY below its 200d SMA (reversal premium is
           larger in stressed markets); size them up 1.5x / 2x then.

Everything is computed from what was known at 15:50: panel bars up to the day
BEFORE, today's open, and the 15:30-15:50 minute bars (data/research/night/lm1).
rvol is approximate: today's full-day volume minus the volume printed at or
after 15:50 in the minute file. If the 16:00 closing cross lands outside that
file, rvol leaks the auction volume; it is flagged, not trusted, for that reason.

Adoption: a feature enters the model only if its quintiles are monotone in
2021-23 (the fitting half). The model must beat the shipped tilt in BOTH halves
at tier AND tier_hi, and beat a within-day shuffle of its own weights.
"""
from __future__ import annotations

import copy
import glob
import os

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg
from . import book as B
from . import data as D
from .validate import load_sim

OUT = D.DATA / "features.pkl"
S2 = {"QQQ": 0.5, "SMH": 0.5}
# V7 with the honest 3x-ETF margin (research/sim/growth.py): 2x account,
# IBS 0.5, conviction 0.5 at 75% -> intraday cap 0.75
V7 = dict(tilt="live", noise=S2, weekend_scale=0.5, conviction_w=0.5, noise_cap=0.75)
FEATS = ["late", "rvol", "gap", "spy50", "idio", "dist20", "dist252", "prev", "lprice"]


# ------------------------------------------------------------------ data
def _minute_bits() -> pd.DataFrame:
    rows = []
    for f in sorted(glob.glob(str(D.DATA / "lm1" / "*.parquet"))):
        d = pd.Timestamp(os.path.basename(f)[:10])
        df = pd.read_parquet(f)
        if df.empty:
            continue
        t = df.timestamp.dt.tz_convert("America/New_York")
        df["hm"] = t.dt.hour * 100 + t.dt.minute
        for s, g in df.groupby("symbol"):
            pre = g[g.hm < 1550]
            if pre.empty:
                continue
            rows.append((d, s, float(pre.open.iloc[0]), int(pre.hm.iloc[0]),
                         float(g.loc[g.hm >= 1550, "volume"].sum())))
    return pd.DataFrame(rows, columns=["date", "sym", "px1530", "hm0", "vol_post"])


def features() -> pd.DataFrame:
    if OUT.exists():
        return pd.read_pickle(OUT)
    x = D.night_candidates().copy()
    P = D.panel(); C, V, O, L = P["close"], P["volume"], P["open"], P["low"]
    get = lambda M: np.array([M.at[a, b] if (a in M.index and b in M.columns) else np.nan
                              for a, b in zip(x.date, x.sym)], float)
    m = _minute_bits()
    x = x.merge(m, on=["date", "sym"], how="left")
    ok = x.hm0 <= 1535                           # the window really starts near 15:30
    x["late"] = np.where(ok, (x.p50 / x.px1530 - 1) / x.day50, np.nan)
    avgv = V.rolling(20).mean().shift(1)
    x["rvol"] = (get(V) - x.vol_post.fillna(0)) / get(avgv)
    x["gap"] = (get(O) / x.pc - 1) / x.day50
    spy = D.minutes("SPY")["close"]
    spy_pc = spy.iloc[:, 389].shift(1)
    spy50 = spy.iloc[:, 379] / spy_pc - 1        # close of the 15:49 bar
    x["spy50"] = x.date.map(spy50).astype(float)
    x["idio"] = x.day50 - x.spy50
    lo20 = L.rolling(20).min().shift(1); lo252 = L.rolling(252, min_periods=200).min().shift(1)
    x["dist20"] = x.p50 / get(lo20) - 1
    x["dist252"] = x.p50 / get(lo252) - 1
    x["prev"] = get(C.shift(1) / C.shift(2) - 1)
    x["lprice"] = np.log(x.p50)
    x.to_pickle(OUT)
    return x


def traded(s: B.Sim, x: pd.DataFrame, cost: str) -> pd.DataFrame:
    """The names the live rules actually trade (sim night days), with net return."""
    keys = {(d, sym) for d, nd in s.N.items() for sym in nd.syms}
    t = x[[(d, sy) in keys for d, sy in zip(x.date, x.sym)]].copy()
    c = B.cost_bps(cost, t.p50.values, t.adv.values)
    t["net"] = t.ret - 2 * c / 1e4
    t["half"] = np.where(t.date <= "2023-12-31", "21-23", "24-26")
    return t


# -------------------------------------------------------------- buckets
def buckets(t: pd.DataFrame, f: str) -> tuple[pd.DataFrame, dict]:
    out, mono = [], {}
    for h, g in t.groupby("half"):
        g = g[np.isfinite(g[f])]
        q = pd.qcut(g[f].rank(method="first"), 5, labels=False)
        for k, b in g.groupby(q):
            r = b.net.values
            out.append(dict(feat=f, half=h, q=k + 1, lo=b[f].min(), hi=b[f].max(), n=len(r),
                            bp=r.mean() * 1e4, t=r.mean() / (r.std(ddof=1) / np.sqrt(len(r))),
                            win=(r > 0).mean(), avg_win=r[r > 0].mean() * 1e4,
                            avg_loss=r[r <= 0].mean() * 1e4))
        m = np.array([o["bp"] for o in out if o["half"] == h and o["feat"] == f])
        d = np.sign(np.diff(m))
        top_bot = g.net[q == 4].values, g.net[q == 0].values
        diff = top_bot[0].mean() - top_bot[1].mean()
        se = np.sqrt(top_bot[0].var(ddof=1) / len(top_bot[0]) + top_bot[1].var(ddof=1) / len(top_bot[1]))
        mono[h] = (int(abs(d.sum())) == 4, np.corrcoef(np.arange(5), m)[0, 1], diff * 1e4, diff / se)
    return pd.DataFrame(out), mono


# ---------------------------------------------------------------- model
BASE = ["lvol", "day"]


def design(t: pd.DataFrame, feats: list[str]) -> np.ndarray:
    cols = [np.log(np.maximum(t.vol20.values, 1e-3)), t.day50.values]
    cols += [t[f].values for f in feats]
    return np.nan_to_num(np.column_stack(cols).astype(float))


def fit(t: pd.DataFrame, feats: list[str], lo: str, hi: str) -> dict:
    g = t[(t.date >= lo) & (t.date <= hi)]
    X = design(g, feats)
    # winsorize each column at 1/99 of the fit set so one bad bar cannot steer it
    q1, q99 = np.nanpercentile(X, 1, axis=0), np.nanpercentile(X, 99, axis=0)
    X = np.clip(X, q1, q99)
    mu, sd = X.mean(0), X.std(0)
    Z = (X - mu) / np.where(sd > 0, sd, 1)
    A = np.column_stack([np.ones(len(Z)), Z])
    beta, *_ = np.linalg.lstsq(A, g.ret.values * 1e4, rcond=None)
    pred = Z @ beta[1:]
    return dict(feats=feats, mu=mu, sd=sd, q1=q1, q99=q99, beta=beta[1:], pred_sd=pred.std())


def weights_fn(model: dict, t: pd.DataFrame, k: float = 0.25, shuffle_seed: int | None = None):
    """A tilt f(NightDay) in the same shape as signals.night_tilt: 1 + k *
    pred / pred_sd, clipped [0.25, 2], mean 1 per day."""
    idx = {(d, s): i for i, (d, s) in enumerate(zip(t.date, t.sym))}
    X = np.clip(design(t, model["feats"]), model["q1"], model["q99"])
    Z = (X - model["mu"]) / np.where(model["sd"] > 0, model["sd"], 1)
    P = Z @ model["beta"] / model["pred_sd"]
    rng = np.random.default_rng(shuffle_seed) if shuffle_seed is not None else None

    def f(nd):
        z = np.array([P[idx[(nd.date, s)]] if (nd.date, s) in idx else 0.0 for s in nd.syms])
        w = np.clip(1 + k * z, 0.25, 2.0)
        if rng is not None:
            w = rng.permutation(w)
        return w / w.mean()
    return f


def book(s: B.Sim, cost: str, tilt) -> pd.DataFrame:
    return s.replay(B.Params(**{**V7, "tilt": tilt, "night_cost": cost}))


def line(df: pd.DataFrame, lab: str) -> str:
    return B.summary(df, lab)


# ------------------------------------------------------------ IBS lead
def ibs_downtrend(s: B.Sim, cost: str, mult: float) -> pd.DataFrame:
    """IBS leg x mult on days SPY closed below its 200d SMA (known at d's close,
    IBS entered at d+1's open). The extra IBS gross is borrowed overnight
    (margin interest in the sim) and takes daytime room from the intraday
    leg: noise cap = 2 x (1 - ibs_w / 2 - 0.5 x 0.75)."""
    spy = s.C["SPY"]; down = spy < spy.rolling(200).mean()
    base = B.Params(**{**V7, "night_cost": cost})
    hi = copy.copy(base)
    hi.ibs_w = 0.5 * mult
    hi.noise_cap = max(0.0, 2 * (1 - hi.ibs_w / 2 - 0.5 * 0.75))
    orig = s.day_pnl

    def day_pnl(E, d, p):
        use = hi if (bool(down.get(d, False)) and s.I.get(d)) else p
        return orig(E, d, use)
    s.day_pnl = day_pnl
    try:
        return s.replay(base)
    finally:
        s.day_pnl = orig


def main():
    s = load_sim()
    s.N = B.night_days(max_corr=0.7)
    for d, nd in s.N.items():
        nd.date = d
    x = features()
    t = traded(s, x, "tier")
    print(f"traded names with features: {len(t)} "
          f"({t.date.min().date()} - {t.date.max().date()}); late missing {t.late.isna().mean():.0%}")

    # 1. buckets, per half (net at tier costs)
    print("\n=== quintiles of next-open NET return (tier), per half: bp (t) | win% | avg win / avg loss bp")
    mono_all, tabs = {}, []
    for f in ["day50", "vol20"] + FEATS:
        tb, mono = buckets(t, f)
        tabs.append(tb); mono_all[f] = mono
        for h in ("21-23", "24-26"):
            r = tb[tb.half == h]
            cells = "  ".join(f"{b.bp:+5.0f}({b.t:+.1f}) {b.win*100:3.0f}% {b.avg_win:+4.0f}/{b.avg_loss:+4.0f}"
                              for b in r.itertuples())
            m = mono[h]
            print(f"{f:8s} {h}  {cells}   mono {'Y' if m[0] else 'n'} rho {m[1]:+.2f} Q5-Q1 {m[2]:+5.0f}bp (t {m[3]:+.1f})")
    pd.concat(tabs).to_pickle(D.DATA / "features_buckets.pkl")

    # 2. model: new features monotone in 2021-23 only
    pick = [f for f in FEATS if mono_all[f]["21-23"][0] or abs(mono_all[f]["21-23"][3]) >= 3]
    both = [f for f in FEATS if mono_all[f]["21-23"][0] and mono_all[f]["24-26"][0]
            and np.sign(mono_all[f]["21-23"][1]) == np.sign(mono_all[f]["24-26"][1])]
    pick_b = [f for f in FEATS if mono_all[f]["24-26"][0] or abs(mono_all[f]["24-26"][3]) >= 3]
    print(f"\nfeatures passing the 2021-23 screen: {pick or 'none'}")
    print(f"features passing the 2024-26 screen (reverse fit): {pick_b or 'none'}")
    print(f"monotone, same sign, BOTH halves: {both or 'none'}")

    res = {}
    for cost in ("tier", "tier_hi"):
        tc = traded(s, x, cost)
        print(f"\n=== V7 book (honest 0.75 intraday cap), {cost}          2021-23          2024-26          full")
        res[(cost, "base")] = book(s, cost, "live")
        print(line(res[(cost, "base")], "shipped tilt (depth + vol20)"))
        for lab, feats, lo, hi in (("fit 2021-23", pick, "2020-01-01", "2023-12-31"),
                                   ("fit 2024-26 (reverse)", pick_b, "2024-01-01", "2026-12-31")):
            if not feats:
                continue
            mdl = fit(tc, feats, lo, hi)
            print("   beta (bp per sd): " + ", ".join(f"{n} {b:+.1f}" for n, b in zip(BASE + feats, mdl["beta"])))
            res[(cost, lab)] = book(s, cost, weights_fn(mdl, tc))
            print(line(res[(cost, lab)], f"+ {'/'.join(feats)} [{lab}]"))
            plc = [book(s, cost, weights_fn(mdl, tc, shuffle_seed=k)) for k in range(5)]
            r = pd.concat([p["r"] for p in plc], axis=1).mean(axis=1)
            pdf = plc[0].copy(); pdf["r"] = r
            print(line(pdf, f"  placebo: same weights shuffled in-day (5)"))
        # every single feature added alone to the base model, fit 21-23: for the record
        for f in FEATS:
            mdl = fit(tc, [f], "2020-01-01", "2023-12-31")
            print(line(book(s, cost, weights_fn(mdl, tc)), f"  alone: + {f} [fit 21-23]"))

    # 3. IBS up-weight in downtrends
    spy = s.C["SPY"]; down = spy < spy.rolling(200).mean()
    ib = [(d, r) for d, v in s.I.items() for _, _, r in v]
    ibdf = pd.DataFrame(ib, columns=["date", "r"]).set_index("date")
    ibdf["down"] = down.reindex(ibdf.index).fillna(False).values
    print("\n=== IBS trades by SPY regime (gross open->open, bp): n, mean, t")
    for (lo, hi) in (("2016", "2023"), ("2024", "2026")):
        g = ibdf[lo:hi]
        for k, b in g.groupby("down"):
            print(f"  {lo}-{hi} {'below 200d' if k else 'above 200d'}: n {len(b)}  "
                  f"{b.r.mean()*1e4:+.1f}bp (t {b.r.mean()/(b.r.std(ddof=1)/np.sqrt(len(b))):.2f})")
    for cost in ("tier", "tier_hi"):
        print(f"\n=== IBS x mult below SPY 200d, {cost}")
        print(line(book(s, cost, "live"), "shipped"))
        for m in (1.5, 2.0):
            print(line(ibs_downtrend(s, cost, m), f"IBS x{m} in downtrends"))


if __name__ == "__main__":
    main()
