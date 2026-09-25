"""Addendum 26b candidate: a cross-asset trend (TSMOM) sleeve as a diversifier.

    PYTHONPATH=. .venv/bin/python -m research.sim.trend_sleeve

Question: can a genuinely different return stream raise the daily book's
Sharpe? Every leg today is US equity, short-horizon, mean-reversion or
intraday momentum. Time-series momentum across asset classes is the textbook
low-correlation stream (Moskowitz-Ooi-Pedersen 2012).

Universe (fixed before looking; everything in etf_daily.parquet that is not
a sector, a leveraged ETF or VIX): SPY QQQ IWM EFA EEM TLT IEF GLD SLV USO HYG.
Prices are split- and dividend-adjusted (total return). 2016-01 -> 2026-09,
so 12-month signals start 2017-01: holdout 2017-20, fit 2021-23, judge 2024-26.

Four variants, pre-registered, monthly rebalance:
  A  12-1 sign, long-only, 1/N per positive asset, rest in BIL
  B  3/6/12-month sign blend, long-only, weight = max(score, 0) / N
  C  B scaled by inverse 60d vol, ex-ante sleeve vol 10%, gross <= 1
  D  C long/short (score in [-1, 1]): needs a brokerage account, not the Roth
Robustness only (not a variant to pick): C with weekly rebalance.

Timing: signal at close t, trade at the close of t+1, earn from t+1 on.
Costs per side on turnover: tier 2bp, tier_hi 5bp (the IBS leg pays 1bp).
D pays 0.5%/yr borrow on shorts and gets no interest on short proceeds.

Placebo: at each rebalance the score vector is shuffled across assets
(200 seeds): same exposure profile, wrong assets.

Combination with V7 (shipped rules + conviction 0.5 at the 75% TQQQ margin cap):
  idle     the sleeve lives in the IBS half's idle SGOV cash (free capacity)
  carve    k of equity moves from ibs+night into the sleeve (overnight stays 1.0x)
  overlay  V7 + k sleeve on margin (brokerage 1.3x budget, 12%/yr debit),
           compared with spending the same budget on 1.3x ibs+night
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import book as B
from . import data as D
from .growth import V7, cfg, eh
from .validate import load_sim

U = ["SPY", "QQQ", "IWM", "EFA", "EEM", "TLT", "IEF", "GLD", "SLV", "USO", "HYG"]
COST = {"tier": 2.0, "tier_hi": 5.0}
TARGET_VOL = 0.10
BORROW = 0.005
HALVES = [("2017-20 holdout", "2017-01-01", "2020-12-31"),
          ("2021-23", "2021-01-01", "2023-12-31"),
          ("2024-26", "2024-01-01", "2026-12-31")]


# ------------------------------------------------------------- signals
def prices():
    P = D.etf()
    C = P["close"]
    return C[U], C["BIL"]


def rebal_dates(idx: pd.DatetimeIndex, freq: str) -> pd.DatetimeIndex:
    s = pd.Series(idx, index=idx)
    key = [idx.year, idx.month] if freq == "M" else [idx.isocalendar().year.values,
                                                     idx.isocalendar().week.values]
    return pd.DatetimeIndex(s.groupby(key).max().values)


def scores(C: pd.DataFrame, kind: str) -> pd.DataFrame:
    if kind == "12-1":
        return np.sign(C.shift(21) / C.shift(252) - 1)
    return sum(np.sign(C / C.shift(n) - 1) for n in (63, 126, 252)) / 3


def weights(C: pd.DataFrame, variant: str, freq: str = "M", shuffle_seed: int | None = None):
    """Target weights decided at each rebalance close (rows = rebalance dates)."""
    r = C.pct_change(fill_method=None)
    sc = scores(C, "12-1" if variant == "A" else "blend")
    vol = r.rolling(60).std() * np.sqrt(252)
    dates = [d for d in rebal_dates(C.index, freq) if d >= pd.Timestamp("2017-01-01")]
    rng = np.random.default_rng(shuffle_seed) if shuffle_seed is not None else None
    n = len(U)
    rows = {}
    for d in dates:
        s = sc.loc[d].values.astype(float)
        if not np.isfinite(s).all():
            continue
        if rng is not None:
            s = rng.permutation(s)
        if variant in ("A", "B"):
            w = np.maximum(s, 0) / n
        else:
            if variant == "C":
                s = np.maximum(s, 0)
            v = vol.loc[d].values
            raw = s / v
            if not np.any(raw):
                rows[d] = np.zeros(n); continue
            cov = r.loc[:d].iloc[-60:].cov().values * 252
            ex = float(np.sqrt(raw @ cov @ raw))
            w = raw * TARGET_VOL / ex if ex > 0 else raw * 0
            g = np.abs(w).sum()
            if g > 1:
                w = w / g
        rows[d] = w
    return pd.DataFrame(rows, index=U).T


def sleeve(variant: str, cost: str = "tier", freq: str = "M", shuffle_seed=None,
           scale: pd.Series | None = None) -> pd.DataFrame:
    """Daily sleeve returns, forward-labelled like Sim.bil: row d = close d -> close d+1.

    scale: fraction of equity held in the sleeve each day (default 1). Returns are then
    per unit of EQUITY, costs included, cash inside the sleeve at BIL."""
    C, bil = prices()
    fwd = C.pct_change(fill_method=None).shift(-1)
    bfwd = bil.pct_change(fill_method=None).shift(-1).fillna(0)
    W = weights(C, variant, freq, shuffle_seed)
    idx = C.index[C.index >= W.index[0]]
    # decided at close t, traded at close t+1, so it earns from row t+1 on
    Weff = W.reindex(idx).ffill().shift(1).fillna(0)
    k = pd.Series(1.0, index=idx) if scale is None else scale.reindex(idx).fillna(0)
    H = Weff.mul(k, axis=0)
    R = fwd.reindex(idx).fillna(0)
    long_g = H.clip(lower=0).sum(axis=1)
    short_g = (-H.clip(upper=0)).sum(axis=1)
    gross = (H * R).sum(axis=1)
    cash = (k - long_g).clip(lower=0) * bfwd.reindex(idx)
    turn = H.diff().abs().sum(axis=1).fillna(H.abs().sum(axis=1))
    r = gross + cash - turn * COST[cost] / 1e4 - short_g * BORROW / 252
    return pd.DataFrame({"r": r, "long": long_g, "short": short_g, "turn": turn})


# --------------------------------------------------------------- stats
def row(r: pd.Series) -> str:
    out = []
    for _, a, b in HALVES:
        c, s, d = B.stats(r[a:b])
        out.append(f"{c*100:5.1f}/{s:5.2f}/{d*100:4.0f}" if np.isfinite(c) else f"{'-':>16s}")
    c, s, d = B.stats(r)
    return "  ".join(out) + f"  |  {c*100:5.1f}/{s:5.2f}/{d*100:4.0f}"


def row2(r: pd.Series) -> str:
    out = []
    for _, a, b in HALVES[1:]:
        c, s, d = B.stats(r[a:b]); out.append(f"{c*100:5.1f}/{s:4.2f}/{d*100:4.0f}")
    c, s, d = B.stats(r)
    return "  ".join(out) + f"  |  {c*100:5.1f}/{s:4.2f}/{d*100:4.0f}"


def sharpe(r):
    return B.stats(r)[1]


def ceiling(s1, s2, rho):
    zero = np.sqrt(s1 ** 2 + s2 ** 2)
    opt = np.sqrt(max(0.0, (s1 ** 2 + s2 ** 2 - 2 * rho * s1 * s2) / (1 - rho ** 2)))
    return zero, opt


# ---------------------------------------------------------------- main
def main():
    print("== 1. standalone sleeve (sleeve = 100% of its own capital)")
    hdr = f"{'':34s} {'2017-20 holdout':>16s}  {'2021-23':>16s}  {'2024-26':>16s}  |  {'full CAGR/Sh/DD':>16s}"
    print(hdr)
    SL = {}
    for v in "ABCD":
        for c in ("tier", "tier_hi"):
            x = sleeve(v, c)
            SL[(v, c)] = x
            print(f"{v + ' ' + c:34s} {row(x.r)}   avg long {x.long.mean():.2f} "
                  f"short {x.short.mean():.2f} turn/yr {x.turn.sum() / (len(x) / 252):.1f}")
    xw = sleeve("C", "tier", "W")
    print(f"{'C weekly (robustness) tier':34s} {row(xw.r)}   turn/yr {xw.turn.sum() / (len(xw) / 252):.1f}")
    C, bil = prices()
    ew = C.pct_change(fill_method=None).shift(-1).loc["2017-01-01":].mean(axis=1)
    print(f"{'buy & hold equal-weight 11':34s} {row(ew)}")
    spy = C["SPY"].pct_change(fill_method=None).shift(-1).loc["2017-01-01":]
    print(f"{'SPY':34s} {row(spy)}")

    print("\n== 2. placebo: scores shuffled across assets at each rebalance, 200 seeds (tier)")
    for v in "BCD":
        real = [B.stats(SL[(v, 'tier')].r[a:b])[1] for _, a, b in HALVES]
        ps = np.array([[B.stats(sleeve(v, "tier", shuffle_seed=k).r[a:b])[1] for _, a, b in HALVES]
                       for k in range(200)])
        beat = (ps < np.array(real)).mean(axis=0)
        print(f"{v}: real Sharpe " + " / ".join(f"{x:.2f}" for x in real)
              + "   placebo median " + " / ".join(f"{x:.2f}" for x in np.median(ps, axis=0))
              + "   beats " + " / ".join(f"{b:.0%}" for b in beat))

    # ------------------------------------------------ V7 and combinations
    s = load_sim()
    s.N = B.night_days(max_corr=0.7, max_name_pct=0.10)

    def v7(g=1.0, extra_day=0.0, cost="tier"):
        kw = cfg(g, 0.5, 2)
        room = kw["noise_cap"] - extra_day                    # sleeve uses daytime margin too
        kw["noise_cap"] = max(0.0, room)
        return s.replay(B.Params(**{**V7, **kw, "night_cost": cost}))

    base = {c: v7(cost=c) for c in ("tier", "tier_hi")}
    days = base["tier"].index
    r7 = base["tier"].r

    print("\n== 3. correlation with V7 (2021-02 -> 2026-09, tier)")
    spy_d = s.spy.reindex(days)
    crash = spy_d <= -0.03
    for v in "ABCD":
        x = SL[(v, "tier")].r.reindex(days).fillna(0)
        rho = r7.corr(x)
        rho_c = r7[crash].corr(x[crash])
        s1, s2 = sharpe(r7), sharpe(x)
        z, o = ceiling(s1, s2, rho)
        print(f"{v}: rho {rho:+.2f}  on SPY<=-3% days (n={crash.sum()}) rho {rho_c:+.2f}, "
              f"sleeve mean {x[crash].mean()*1e4:+.0f}bp vs V7 {r7[crash].mean()*1e4:+.0f}bp  |  "
              f"Sharpe V7 {s1:.2f}, sleeve {s2:.2f}: ceiling zero-rho {z:.2f}, at this rho {o:.2f}")

    print("\n== 4. combined book, 2021-23 / 2024-26 | full, CAGR/Sharpe/maxDD")
    hdr = f"{'':46s} {'2021-23':>15s}  {'2024-26':>15s}  |  {'full':>15s}"
    print(hdr)
    for c in ("tier", "tier_hi"):
        print(f"{'V7 shipped ' + c:46s} {row2(base[c].r)}")

    # idle: the sleeve sits in the IBS half's SGOV cash on days the IBS leg is flat
    ibs_flat = pd.Series({d: 0.0 if s.I.get(d) else 1.0 for d in days})
    bfwd = s.bil.reindex(days).fillna(0)
    print("-- idle: sleeve in the IBS half's idle cash (replaces SGOV; no extra margin)")
    for v in "BCD":
        for k in (0.25, 0.5):
            for c in ("tier", "tier_hi"):
                a = ibs_flat * k
                x = sleeve(v, c, scale=a).r.reindex(days).fillna(0)
                comb = base[c].r + x - a * bfwd                 # the sleeve replaces BIL on that slice
                print(f"{f'V7 + {v} in idle IBS cash, up to {k:.2f} ' + c:46s} {row2(comb)}"
                      f"   avg in sleeve {a.mean():.2f}")
    print("-- carve: k of equity from ibs+night into the sleeve (overnight 1.0x, day cap shrinks)")
    for v in "BCD":
        for k in (0.1, 0.2, 0.3, 0.5):
            for c in ("tier", "tier_hi"):
                g = v7(g=1.0 - k, extra_day=k, cost=c)
                x = sleeve(v, c, scale=pd.Series(k, index=days)).r.reindex(days).fillna(0)
                print(f"{f'V7 carve {k:.1f} -> {v} ' + c:46s} {row2(g.r + x)}")
    print("-- overlay: brokerage 1.3x budget, the extra 0.3 in the sleeve vs in ibs+night")
    for c in ("tier", "tier_hi"):
        lev = v7(g=1.3, cost=c)
        print(f"{'V7 at 1.3x overnight (ibs+night 0.65) ' + c:46s} {row2(lev.r)}")
        for v in "BCD":
            for k in (0.15, 0.3):
                g = v7(g=1.0, extra_day=k, cost=c)
                sl = sleeve(v, c, scale=pd.Series(k, index=days)).reindex(days).fillna(0)
                # on margin: the invested part is borrowed at 12%/yr, and there is no free cash
                x = sl.r - (k - sl.long).clip(lower=0) * bfwd - sl.long * 0.12 / 252
                print(f"{f'V7 + {k:.2f} {v} on margin ' + c:46s} {row2(g.r + x)}")

    print("\n== 5. edge-halves (V7 legs' mean halved; sleeve excess over BIL halved too), tier_hi")
    for v in "BC":
        for k in (0.2, 0.3):
            g = v7(g=1.0 - k, extra_day=k, cost="tier_hi")
            sl = sleeve(v, "tier_hi", scale=pd.Series(k, index=days)).r.reindex(days).fillna(0)
            ex = sl - k * bfwd
            x = sl - 0.5 * ex.mean()
            print(f"{f'EH V7 carve {k:.1f} -> {v}':46s} {row2(eh(g) + x)}")
    print(f"{'EH V7 shipped':46s} {row2(eh(base['tier_hi']))}")


if __name__ == "__main__":
    main()
