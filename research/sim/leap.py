"""Leap book research: is there a day/short-hold trade that turns $100 into $500?

    .venv/bin/python -m research.sim.leap

The ask (2026-09-24): a separate book that makes BIG leaps, "$100 to like $500".
Same standards as every addendum: tiered costs at tier and tier_hi, no
lookahead, 2021-23 and 2024-26 must both be positive, parameters picked on one
half and judged on the other (and reversed), day-clustered t, a placebo that
keeps the exit rule and randomises the entry. A cash account ($100 cannot use
margin): 1.0x equity at most, no shorting -- a down signal is a long inverse
ETF, approximated here as -1x the bull ETF's intraday return.

Already dead, not retested (RESULTS.md addenda 6 and 8): stocks-in-play ORB,
QQQ/SPY ORB, gap-and-go / gap-down squeeze / pm capitulation (stocks), ETF
gap-fill, last-half-hour momentum, afternoon capitulation, midday trend,
opening-drive fade. SOXL conviction (addendum 21): dead.

PRE-REGISTERED CANDIDATES AND PRIORS (written before any run)

A. 3x-ETF opening-range breakout, runner exit. SOXL (TQQQ shown for reference
   only: the daily book's conviction trade owns it). Opening range 5/15/30 min;
   long on a break above the range high, inverse on a break below; stop at the
   other side; no target, out at 15:57. 100% of equity.
   Prior: NEGATIVE after costs. QQQ ORB decayed to ~3% post-2021 and SPY ~0;
   3x adds variance, not edge. Right-skewed, low win rate.

B. 3x-ETF daily trend breakout, multi-day hold (Donchian). Universe SOXL, TECL,
   LABU, FAS, TNA, UPRO, SPXL, UDOW (no TQQQ). Signal: close at an N-day high
   (N = 20 / 55); buy next open, the strongest 20-day momentum name among those
   signalling; exit at the next open after a close below the M-day low (M = 10
   / 20). 100% of equity, one name.
   Prior: WEAK. Captures 2020-21 and 2023-24 runs, gives much back in 2022 and
   on whipsaws; likely positive in one half only.

C. Small-cap gap-and-go with a runner (top-40 gappers per day, minute bars).
   Gap >= 10 / 20 / 40%, price >= $3; buy a break of the 5-min high after 09:35;
   stop at the 5-min low; trail 1R under the running high; else out at 15:57.
   Top 1 or top 3 by 5-min relative volume.
   Prior: NEGATIVE both halves (addendum 8 had gap-and-go at t -2 to -8). A
   runner exit changes the payoff shape, not the mean. Survivorship (only names
   still listed in 2026) flatters longs, so a pass here would still be suspect.

D. Concentrated night leg. The shipped loser-bounce signal (V2 universe, deepest
   day return first) but top 1 at 100% or top 3 at 33% each, close -> open.
   Prior: per-trade mean positive (it is the book's edge), but concentration
   cuts growth (Kelly): lower CAGR than the diversified leg, P(-50%) high.

E. SOXL IBS, all-in. IBS < 0.10 / 0.20 at the close, buy the next open, sell the
   following open. 100% of equity in one 3x ETF.
   Prior: POSITIVE both halves (IBS works on tech ETFs, addendum 6 -- SOXL was
   in that list, so not fully out of sample), maxDD worse than -50%.

Count: A 6 (3 ranges x 2 symbols) + B 4 + C 6 + D 2 + E 2 = 20 variants.
"""
from __future__ import annotations

import pickle

import numpy as np
import pandas as pd

from swingtrader.leap import signals as LS

from . import book as B
from . import data as D

H1 = ("2021-01-01", "2023-12-31")
H2 = ("2024-01-01", "2026-12-31")
ETF_COST = {"tier": 3.0, "tier_hi": 5.0}          # bps per side, 3x ETFs (addendum 8 used 2-3)
DAILY_ETF_COST = {"tier": 5.0, "tier_hi": 7.5}    # open auction on 3x ETFs


def halves(r: pd.Series):
    return [B.stats(r[H1[0]:H1[1]]), B.stats(r[H2[0]:H2[1]]), B.stats(r[H1[0]:])]


def fmt(parts):
    return "  ".join(f"{c*100:6.1f}/{s:5.2f}/{d*100:4.0f}" for c, s, d in parts)


def tday(tr: pd.DataFrame, lo, hi) -> tuple[float, float, int]:
    """Day-clustered t of the mean trade return in [lo, hi]."""
    x = tr[(tr.date >= lo) & (tr.date <= hi)].groupby("date").r.mean()
    if len(x) < 10:
        return np.nan, np.nan, len(x)
    return x.mean() * 1e4, x.mean() / x.std() * np.sqrt(len(x)), len(x)


def to_daily(tr: pd.DataFrame, idx: pd.DatetimeIndex, w: float = 1.0) -> pd.Series:
    """Equity return per day; several trades on a day split the equity (w each)."""
    return (tr.r * w).groupby(tr.date).sum().reindex(idx).fillna(0.0)


# ------------------------------------------------------------------ A. ETF ORB
def etf_orb(sym: str, orm: int, cost: float, rng=None, delay: int = 0,
            side: int = 0) -> pd.DataFrame:
    """delay: fill at the open of the bar `delay` minutes after the break
    (0 = a stop order filled at the level). side: +1 longs only, -1 inverse only."""
    M = D.minutes(sym)
    O, H, L, C = (M[k].values for k in ("open", "high", "low", "close"))
    days = M["close"].index
    T = []
    for i in range(len(days)):
        b = LS.orb_break(H[i], L[i], orm)             # the shadow book's own function
        if b is None:
            continue
        d, m, level, stop = b
        if side and d != side:
            continue
        e = LS.orb_fill(d, level, O[i, m])
        if rng is not None:                         # placebo: same day, minute and price, random side
            d = rng.choice((-1, 1))
            stop = e * (1 - d * abs(level - stop) / e)
        if delay:
            m = min(m + delay, 386); e = O[i, m]
        x = C[i, 386]
        for k in range(m, LS.LAST_MINUTE):
            if LS.orb_stopped(d, stop, H[i, k], L[i, k]):
                x = (min(stop, O[i, k]) if d == 1 else max(stop, O[i, k])) if k > m else stop
                break
        T.append((days[i], d * (x / e - 1) - 2 * cost / 1e4, e))
    return pd.DataFrame(T, columns=["date", "r", "px"])


# -------------------------------------------------------- B. Donchian, 3x ETFs
B_UNIV = ["SOXL", "TECL", "LABU", "FAS", "TNA", "UPRO", "SPXL", "UDOW"]


def donchian(N: int, Mx: int, cost: float, rng=None) -> pd.DataFrame:
    E = D.etf()
    O, C = E["open"][B_UNIV], E["close"][B_UNIV]
    sig = C >= C.rolling(N).max()
    low = C <= C.rolling(Mx).min()
    mom = C / C.shift(20) - 1
    days = C.index
    T, pos, ent, ed = [], None, None, None
    for i in range(N, len(days) - 1):
        if pos is not None and low.iloc[i][pos]:
            x = O.iloc[i + 1][pos]
            T.append((ed, x / ent - 1 - 2 * cost / 1e4, days[i + 1], ent)); pos = None
            continue
        if pos is None:
            s = sig.iloc[i]
            if rng is not None:                     # placebo: enter on random days at the base rate
                s = pd.Series(rng.random(len(B_UNIV)) < 0.04, index=B_UNIV)
            cand = s[s].index
            if len(cand):
                pos = mom.iloc[i][cand].idxmax() if rng is None else rng.choice(cand)
                ent, ed = O.iloc[i + 1][pos], days[i + 1]
                if not np.isfinite(ent):
                    pos = None
    return pd.DataFrame(T, columns=["date", "r", "exit", "px"])


def daily_hold(tr: pd.DataFrame) -> pd.Series:
    """Spread a multi-day trade's return over its holding days (for CAGR/DD/MC)."""
    E = D.etf()["close"]
    idx = E.index
    out = pd.Series(0.0, index=idx)
    for _, t in tr.iterrows():
        span = idx[(idx >= t.date) & (idx < t.exit)]
        if len(span):
            out[span] += (1 + t.r) ** (1 / len(span)) - 1
    return out


# ------------------------------------------------------- C. gap-and-go runner
_GAP = None


def gap_data():
    global _GAP
    if _GAP is None:
        _GAP = pickle.load(open(D.DATA / "gap_arr.pkl", "rb"))
    return _GAP


def gap_go(gmin: float, top: int, model: str, rng=None) -> pd.DataFrame:
    meta, A = gap_data()
    ok = (meta.pc >= 3) & (meta.adv >= 5e6) & (meta.gap >= gmin)
    sub = meta[ok].sort_values("rv5", ascending=False).groupby("date").head(top)
    T = []
    for i in sub.index:
        O, H, L, C = A[i, 0], A[i, 1], A[i, 2], A[i, 3]
        hi, lo = H[:5].max(), L[:5].min()
        br = np.where(H[5:387] > hi)[0]
        if rng is not None:                         # placebo: enter at a random minute 5..120
            br = np.array([rng.integers(0, 116)])
        if not len(br):
            continue
        m = br[0] + 5
        e = max(hi, O[m]) if rng is None else O[m]
        R = e - lo
        if R <= 0 or not np.isfinite(e):
            continue
        stop, run = lo, e
        x = C[386]
        for k in range(m, 387):
            if L[k] <= stop:
                x = min(stop, O[k]) if k > m else stop; break
            run = max(run, H[k]); stop = max(stop, run - R)
        c = B.cost_bps(model, np.array([e]), np.array([meta.adv[i]]))[0]
        T.append((meta.date[i], x / e - 1 - 2 * c / 1e4, e))
    return pd.DataFrame(T, columns=["date", "r", "px"])


# ------------------------------------------------ D. concentrated night leg
def night_conc(top: int, model: str, rng=None) -> pd.DataFrame:
    nd = B.night_days(max_name_pct=1.0)
    T = []
    for d, n in nd.items():
        order = np.argsort(n.day_ret)
        if rng is not None:
            order = rng.permutation(len(n.syms))
        for j in order[:top]:
            c = B.cost_bps(model, n.close[j:j + 1], n.adv[j:j + 1])[0]
            T.append((d, n.ret[j] - 2 * c / 1e4, n.close[j]))
    return pd.DataFrame(T, columns=["date", "r", "px"])


# ------------------------------------------------------------ E. SOXL IBS
def soxl_ibs(th: float, cost: float, rng=None) -> pd.DataFrame:
    E = D.etf()
    o, h, l, c = (E[k]["SOXL"] for k in ("open", "high", "low", "close"))
    ibs = (c - l) / (h - l)
    s = ibs < th
    if rng is not None:
        s = pd.Series(rng.random(len(s)) < s.mean(), index=s.index)
    r = o.shift(-2) / o.shift(-1) - 1                # next open -> following open
    idx = s[s].index[:-2]
    tr = pd.DataFrame({"date": [c.index[c.index.get_loc(d) + 1] for d in idx],
                       "r": (r[idx] - 2 * cost / 1e4).values, "px": o.shift(-1)[idx].values})
    return tr.dropna()


# --------------------------------------------------------------- Monte Carlo
def time_to_5x(r: pd.Series, start: float, px: float | None, n: int = 4000,
               days: int = 252, block: int = 21, seed: int = 7) -> dict:
    """Block bootstrap of the daily equity return, one year. With a share
    price, only whole shares are invested (a $100 account buys what it can)."""
    rng = np.random.default_rng(seed)
    x = r.fillna(0).values
    nb = days // block
    st = rng.integers(0, len(x) - block, size=(n, nb))
    R = x[(st[:, :, None] + np.arange(block)[None, None, :]).reshape(n, -1)]
    E = np.full(n, float(start))
    hit = np.full(n, np.inf); lose50 = np.zeros(n, bool); lose90 = np.zeros(n, bool)
    for t in range(R.shape[1]):
        f = np.minimum(1.0, np.floor(E / px) * px / E) if px else 1.0
        E = E * (1 + f * R[:, t])
        first = (E >= 5 * start) & ~np.isfinite(hit) & ~lose50
        hit[first] = t + 1
        lose50 |= (E <= 0.5 * start) & ~np.isfinite(hit)
        lose90 |= (E <= 0.1 * start) & ~np.isfinite(hit)
    return dict(p3=(hit <= 63).mean(), p6=(hit <= 126).mean(), p12=(hit <= 252).mean(),
                l50=lose50.mean(), l90=lose90.mean(), med=np.median(E))


def main():
    rng = np.random.default_rng(11)
    etf_idx = D.etf()["close"].index
    etf_idx = etf_idx[etf_idx >= "2016-01-01"]
    rows, daily, prices = {}, {}, {}

    def record(name, tr, r, px):
        rows[name] = tr; daily[name] = r; prices[name] = px

    for sym in ("SOXL", "TQQQ"):
        for orm in (5, 15, 30):
            for cm in ("tier", "tier_hi"):
                tr = etf_orb(sym, orm, ETF_COST[cm])
                record(f"A {sym} ORB{orm} {cm}", tr, to_daily(tr, etf_idx), tr.px.median())
    for N in (20, 55):
        for Mx in (10, 20):
            for cm in ("tier", "tier_hi"):
                tr = donchian(N, Mx, DAILY_ETF_COST[cm])
                record(f"B Donch{N}/{Mx} {cm}", tr, daily_hold(tr), tr.px.median())
    gidx = pd.DatetimeIndex(sorted(gap_data()[0].date.unique()))
    for g in (0.10, 0.20, 0.40):
        for top in (1, 3):
            for cm in ("tier", "tier_hi"):
                tr = gap_go(g, top, cm)
                record(f"C gap>={g:.0%} top{top} {cm}", tr, to_daily(tr, gidx, 1 / top), tr.px.median() / top)
    nidx = gidx
    for top in (1, 3):
        for cm in ("tier", "tier_hi"):
            tr = night_conc(top, cm)
            record(f"D night top{top} {cm}", tr, to_daily(tr, nidx, 1 / top), tr.px.median() / top)
    for th in (0.10, 0.20):
        for cm in ("tier", "tier_hi"):
            tr = soxl_ibs(th, DAILY_ETF_COST[cm])
            record(f"E SOXL IBS<{th:.2f} {cm}", tr, to_daily(tr, etf_idx), tr.px.median())

    print(f"{'variant':32s} {'2021-23 CAGR/Sh/DD':>20s} {'2024-26':>20s} {'2021-26':>20s}"
          f" | trades  bp/tr(t) H1        H2        win%")
    for k, tr in rows.items():
        a = tday(tr, *H1); b = tday(tr, *H2)
        print(f"{k:32s} {fmt(halves(daily[k]))} | {len(tr):6d} {a[0]:+6.1f}({a[1]:+4.1f}) "
              f"{b[0]:+6.1f}({b[1]:+4.1f})  {100*(tr.r>0).mean():4.0f}")

    # pick-on-one-half, judge-on-the-other within each family (tier costs)
    print("\n== cross-half selection (tier): pick the best variant on one half by CAGR, report it on the other")
    fams = {f: [k for k in rows if k.startswith(f) and k.endswith(" tier")] for f in "ABCDE"}
    passed = []
    for f, ks in fams.items():
        for fit, judge, lab in ((H1, H2, "fit 21-23 -> judge 24-26"), (H2, H1, "fit 24-26 -> judge 21-23")):
            best = max(ks, key=lambda k: B.stats(daily[k][fit[0]:fit[1]])[0])
            cj = B.stats(daily[best][judge[0]:judge[1]])
            cjh = B.stats(daily[best.replace(" tier", " tier_hi")][judge[0]:judge[1]])
            print(f"  {f}: {lab}: {best:28s} judged {cj[0]*100:6.1f}%/{cj[1]:5.2f}  tier_hi {cjh[0]*100:6.1f}%")
        both = [k for k in ks if all(B.stats(daily[x][h[0]:h[1]])[0] > 0
                                      for x in (k, k.replace(' tier', ' tier_hi')) for h in (H1, H2))]
        passed += both

    print("\n== placebo (keep exit rule, randomise entry): real mean bp/trade vs 20 placebo seeds, 2021-26")
    plac = {
        "A SOXL ORB5 tier": lambda g: etf_orb("SOXL", 5, ETF_COST["tier"], g),
        "A SOXL ORB15 tier": lambda g: etf_orb("SOXL", 15, ETF_COST["tier"], g),
        "B Donch20/10 tier": lambda g: donchian(20, 10, DAILY_ETF_COST["tier"], g),
        "C gap>=20% top1 tier": lambda g: gap_go(0.20, 1, "tier", g),
        "D night top1 tier": lambda g: night_conc(1, "tier", g),
        "E SOXL IBS<0.20 tier": lambda g: soxl_ibs(0.20, DAILY_ETF_COST["tier"], g),
    }
    for k, fn in plac.items():
        real = rows[k]; real = real[real.date >= H1[0]].r.mean() * 1e4
        ps = []
        for s in range(20):
            t = fn(np.random.default_rng(100 + s)); ps.append(t[t.date >= H1[0]].r.mean() * 1e4)
        ps = np.array(ps)
        print(f"  {k:26s} real {real:+7.1f}  placebo mean {ps.mean():+7.1f}  max {ps.max():+7.1f}  "
              f"beats {100*(real > ps).mean():3.0f}%")

    print("\n== $100 / $1k -> 5x within 1 year (block bootstrap 2021-26, whole shares at the median price)")
    print(f"{'variant':32s} {'start':>6s}  P(5x 3m) P(5x 6m) P(5x 12m)  P(-50% first) P(-90% first)  median 1y")
    show = [k for k in rows if k.endswith(" tier")]
    for k in show:
        for start in (100, 1000):
            m = time_to_5x(daily[k][H1[0]:], start, prices[k])
            print(f"{k:32s} {start:6d}  {m['p3']*100:7.1f}% {m['p6']*100:7.1f}% {m['p12']*100:8.1f}%  "
                  f"{m['l50']*100:12.1f}% {m['l90']*100:12.1f}%  ${m['med']:9,.0f}")
    print("\nboth halves positive at tier AND tier_hi:", passed or "none")
    robustness(etf_idx)
    return rows, daily, passed


def years_to_5x(r: pd.Series, start: float, px: float | None, years: int = 8,
                n: int = 2000, seed: int = 7) -> tuple[float, float]:
    """Median years to 5x (inf if not reached by `years`) and P(reached)."""
    rng = np.random.default_rng(seed)
    x = r.fillna(0).values
    days = 252 * years; nb = days // 21
    st = rng.integers(0, len(x) - 21, size=(n, nb))
    R = x[(st[:, :, None] + np.arange(21)[None, None, :]).reshape(n, -1)]
    E = np.full(n, float(start)); hit = np.full(n, np.inf)
    for t in range(R.shape[1]):
        f = np.minimum(1.0, np.floor(E / px) * px / E) if px else 1.0
        E = E * (1 + f * R[:, t])
        hit[(E >= 5 * start) & ~np.isfinite(hit)] = (t + 1) / 252
    return float(np.median(hit)), float(np.isfinite(hit).mean())


def robustness(idx):
    """The candidates that passed: the untouched 2016-20 period, execution and
    cost stress, the two sides, and how long 5x actually takes."""
    W = (("2016-01-01", "2020-12-31"), H1, H2)
    print("\n== robustness of the passers: 2016-20 (never used for selection) | 2021-23 | 2024-26")
    cases = {}
    for orm in (5, 15, 30):
        cases[f"SOXL ORB{orm} 3bp"] = etf_orb("SOXL", orm, 3.0)
        cases[f"SOXL ORB{orm} 10bp"] = etf_orb("SOXL", orm, 10.0)
        cases[f"SOXL ORB{orm} fill +1 min"] = etf_orb("SOXL", orm, 3.0, delay=1)
        cases[f"SOXL ORB{orm} fill +3 min"] = etf_orb("SOXL", orm, 3.0, delay=3)
        cases[f"SOXL ORB{orm} longs only"] = etf_orb("SOXL", orm, 3.0, side=1)
        cases[f"SOXL ORB{orm} inverse only"] = etf_orb("SOXL", orm, 3.0, side=-1)
        cases[f"SMH ORB{orm} (1x underlying, 1bp)"] = etf_orb("SMH", orm, 1.0)
    for th in (0.10, 0.20):
        cases[f"SOXL IBS<{th:.2f} 5bp"] = soxl_ibs(th, 5.0)
        cases[f"SOXL IBS<{th:.2f} 15bp"] = soxl_ibs(th, 15.0)
    for k, tr in cases.items():
        r = to_daily(tr, idx)
        st = [B.stats(r[a:b]) for a, b in W]; ts = [tday(tr, a, b) for a, b in W]
        print(f"  {k:34s} " + "  ".join(f"{c*100:6.1f}/{s_:5.2f}/{d*100:4.0f}" for c, s_, d in st)
              + "  | t " + " ".join(f"{t[1]:+4.1f}" for t in ts))
    tr = cases["SOXL ORB15 3bp"]
    by = tr.groupby(tr.date.dt.year).r.mean() * 1e4
    print("  SOXL ORB15 bp/trade by year: " + "  ".join(f"{y} {v:+.0f}" for y, v in by.items()))
    print("\n== how long 5x takes (block bootstrap 2016-26, whole shares; EH = edge halved)")
    for k in ("SOXL ORB15 3bp", "SOXL ORB15 fill +1 min", "SOXL ORB5 3bp", "SOXL IBS<0.20 5bp"):
        tr = cases[k]; r = to_daily(tr, idx); px = tr.px.median()
        eh = r - 0.5 * r.mean()
        out = []
        for lab, x in (("hist", r), ("EH", eh)):
            for start in (100, 1000):
                med, p = years_to_5x(x, start, px)
                out.append(f"{lab} ${start}: {med:4.1f}y (P by 8y {p*100:3.0f}%)")
        print(f"  {k:26s} " + "   ".join(out))
    agg = np.log(5) / np.log(1.711); agg_eh = np.log(5) / np.log(1.222)
    print(f"  aggressive profile (addendum 22): {agg:.1f}y at 71.1%/yr, {agg_eh:.1f}y at 22.2%/yr (EH), smooth-growth math")


if __name__ == "__main__":
    main()
