"""Addendum NN: the options calendar (OPEX, witching, 0DTE) as a timing input for existing legs.

    PYTHONPATH=. .venv/bin/python -m research.sim.opex          (~5 min; no heavy lock needed
                                                                 once cache_opex.pkl exists)

Not options trading: does the monthly expiry calendar tell the live legs when to size up/down?
Mechanism: dealers long gamma near big open interest hedge against the move (pinning, damped
intraday trends) into expiry; the damping is released after expiry. Intraday momentum (the
noise leg) is the opposite of pinning. Daily SPX expiries (0DTE, every day from 2022-11-14)
make every day an expiry day.

Pre-registered variants (stamped 2026-09-28 20:51 PDT, before any 2024-26 number):
  V1  noise leg x0.5 on OPEX Friday                                  (book variant)
  V2  noise leg x1.5 in the 5 sessions after OPEX, scaled before the margin cap (book);
      V2u = the same uncapped (diagnostic of the signal, not margin-feasible)
  V3  0DTE split of the noise leg's per-day edge: 2016-20 / 2021..2022-11-11 / 2022-11-14+
  V4  IBS and night legs: OPEX week vs post-OPEX week vs rest (diagnostic; a x0.5 book
      variant only if the difference passes the bar)
  V5  witching-day night entry: night per-day return, close-auction slippage (15:50 -> close)
      and SPY/QQQ close->open on witching days vs others
Pass bar: pre-registered sign in 2016-20 / 2021-23 / 2024-26, NW(5) t >= 2, beyond the 95th
pct of a vol-tercile-matched placebo (random non-event Fridays / 5-session blocks), and the V7
book better in both halves at 3bp / tier / tier_hi, EH and MC not worse, Roth not worse.

Calendar: research/sim/event_calendar.py (opex_dates: 3rd Friday, Thursday if the exchange is
closed), snapped to the research trading index (last session <= the date).
"""
from __future__ import annotations

import copy
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import book as B, growth as G, roth as RO
from . import event_calendar as EC
from .validate import load_sim

SCR = Path(str(__import__("pathlib").Path(__file__).resolve().parents[2]) + "/data/research/program")
CACHE = SCR / "cache_opex.pkl"
ZERO_DTE = pd.Timestamp("2022-11-14")
PERIODS = {"2016-20": ("2016-01-01", "2020-12-31"), "2021-23": ("2021-01-01", "2023-12-31"),
           "2024-26": ("2024-01-01", "2026-12-31")}
NCAP_TAX = 0.75          # V7 taxable intraday cap (cfg(1.0, 0.5, 2), TQQQ at 75%)
NPLAC = 2000
RNG = np.random.default_rng(11)


# ------------------------------------------------------------- calendar
def calendar(T: pd.DatetimeIndex) -> dict:
    op = []
    for d in EC.opex_dates(2016, 2026):
        k = T[T <= d]
        if len(k) and (d - k[-1]).days < 4:
            op.append(k[-1])
    op = pd.DatetimeIndex(sorted(set(op)))
    wit = op[op.month.isin([3, 6, 9, 12])]
    week, post = set(), set()
    pos = {d: i for i, d in enumerate(T)}
    for d in op:
        i = pos[d]
        j = i
        while j >= 0 and T[j].isocalendar()[1] == d.isocalendar()[1] and (d - T[j]).days < 7:
            week.add(T[j]); j -= 1
        post.update(T[i + 1:i + 6])
    return dict(opex=op, witching=wit, week=pd.DatetimeIndex(sorted(week)),
                post=pd.DatetimeIndex(sorted(post)))


# ------------------------------------------------------------- stats
def nw_t(y: pd.Series, dummy: pd.Series, lags: int = 5) -> tuple[float, float]:
    """OLS y = a + b*dummy, Newey-West(lags) t on b. Returns (b, t)."""
    y = y.values.astype(float); x = dummy.values.astype(float)
    X = np.c_[np.ones_like(x), x]
    XtX = np.linalg.inv(X.T @ X)
    b = XtX @ X.T @ y
    e = y - X @ b
    u = X * e[:, None]
    S = u.T @ u
    for L in range(1, lags + 1):
        w = 1 - L / (lags + 1)
        g = u[L:].T @ u[:-L]
        S += w * (g + g.T)
    V = XtX @ S @ XtX
    return float(b[1]), float(b[1] / np.sqrt(V[1, 1]))


def terciles(vol: pd.Series, idx) -> pd.Series:
    v = vol.reindex(idx)
    q = v.quantile([1 / 3, 2 / 3]).values
    return pd.Series(np.where(v <= q[0], 0, np.where(v <= q[1], 1, 2)), index=idx)


def placebo_days(u: pd.Series, ev: pd.DatetimeIndex, pool: pd.DatetimeIndex, terc: pd.Series) -> np.ndarray:
    """Mean of u over random pool days, matched to the events' vol-tercile counts."""
    ev = ev.intersection(u.index); pool = pool.intersection(u.index).difference(ev)
    need = terc.reindex(ev).value_counts()
    byt = {t: pool[terc.reindex(pool).values == t] for t in need.index}
    out = np.empty(NPLAC)
    for k in range(NPLAC):
        pick = np.concatenate([RNG.choice(byt[t], n, replace=len(byt[t]) < n) for t, n in need.items()])
        out[k] = u.reindex(pick).mean()
    return out


def placebo_blocks(u: pd.Series, starts: pd.DatetimeIndex, excl: pd.DatetimeIndex, terc: pd.Series,
                   n: int = 5) -> np.ndarray:
    """Mean of u over random n-session blocks whose first day is outside excl, matched on the
    first day's vol tercile."""
    ix = u.index
    starts = starts.intersection(ix)
    cand = ix[:-n].difference(excl)
    need = terc.reindex(starts).value_counts()
    byt = {t: cand[terc.reindex(cand).values == t] for t in need.index}
    pos = {d: i for i, d in enumerate(ix)}
    out = np.empty(NPLAC)
    for k in range(NPLAC):
        firsts = np.concatenate([RNG.choice(byt[t], c) for t, c in need.items()])
        vals = np.concatenate([u.values[pos[f]:pos[f] + n] for f in firsts])
        out[k] = np.nanmean(vals)
    return out


def split_table(u: pd.Series, ev: pd.DatetimeIndex, label: str, periods=PERIODS) -> list[str]:
    rows = []
    for pn, (a, b) in periods.items():
        x = u[a:b].dropna()
        if len(x) < 50:
            continue
        m = x.index.isin(ev)
        bb, t = nw_t(x, pd.Series(m, index=x.index))
        rows.append(f"  {label:34s} {pn}  event {x[m].mean()*1e4:+6.1f}bp (n {m.sum():3d})  "
                    f"rest {x[~m].mean()*1e4:+6.1f}bp  diff {bb*1e4:+6.1f}bp  NW t {t:+5.2f}")
    x = u.dropna(); m = x.index.isin(ev)
    bb, t = nw_t(x, pd.Series(m, index=x.index))
    rows.append(f"  {label:34s} pooled   diff {bb*1e4:+6.1f}bp  NW t {t:+5.2f}  (n {m.sum()})")
    return rows


# ------------------------------------------------------------- legs, unit weight
def noise_unit(s, cap: float) -> pd.Series:
    """V7 noise leg return at unit equity: QQQ 0.5 + SMH 0.5, lev capped."""
    parts = [0.5 * s.NZ[k].lev.clip(upper=cap) * s.NZ[k].ret for k in ("QQQ", "SMH")]
    return pd.concat(parts, axis=1, sort=True).sum(axis=1, min_count=1).dropna()


def ibs_unit(s) -> pd.Series:
    """IBS leg return per unit, keyed by the ENTRY session (open d+1 -> open d+2)."""
    T = s.C.index; pos = {d: i for i, d in enumerate(T)}
    out = {T[pos[d] + 1]: float(np.mean([r for _, _, r in legs])) - 2e-4
           for d, legs in s.I.items() if pos[d] + 1 < len(T)}
    return pd.Series(out).sort_index()


def night_unit(N: dict, cost: float = 3.0, gap: dict | None = None) -> pd.Series:
    out = {}
    for d, nd in N.items():
        w = sg.night_tilt(nd.vol20, nd.day_ret)
        x = nd.frac * w * (0.5 if gap and gap.get(d, 1) > 1 else 1.0)
        out[d] = float((x * (nd.ret - 2 * cost / 1e4)).sum())
    return pd.Series(out).sort_index()


# ------------------------------------------------------------- book
def scaled_sim(s, days: pd.DatetimeIndex, k: float, how: str):
    """Copy of the sim whose noise leg is scaled x k on `days`.
    how = "lev": scale the vol-target leverage before the cap (margin-feasible);
          "ret": scale the return (i.e. after the cap; uncapped / exact down-scaling)."""
    t = copy.copy(s); t.NZ = {}
    for sym, z in s.NZ.items():
        z = z.copy(); m = z.index.isin(days)
        z.loc[m, how] = z.loc[m, how] * k
        t.NZ[sym] = z
    return t


def book(t, cost) -> pd.DataFrame:
    return t.replay(B.Params(**{**G.V7, **G.cfg(1.0, 0.5, 2), "night_cost": cost}))


def fmt(r: pd.Series) -> str:
    a, b, f = B.stats(r[:"2023-12-31"]), B.stats(r["2024-01-01":]), B.stats(r)
    return (f"{a[0]*100:5.1f}/{a[1]:4.2f}/{a[2]*100:4.0f}  {b[0]*100:5.1f}/{b[1]:4.2f}/{b[2]*100:4.0f}  "
            f"{f[0]*100:5.1f}/{f[1]:4.2f}/{f[2]*100:4.0f}")


def episodes(r: pd.Series) -> str:
    eps = {"2022": ("2022-01-03", "2022-10-12"), "Apr25": ("2025-04-02", "2025-04-08")}
    wm = ((1 + r).resample("ME").prod() - 1).min()
    return ("  ".join(f"{k} {((1 + r[a:b]).prod() - 1)*100:+6.1f}%" for k, (a, b) in eps.items())
            + f"  worst day {r.min()*100:5.1f}%  worst mo {wm*100:5.1f}%")


def main():
    s = load_sim()
    N07 = pickle.load(open(CACHE, "rb"))["N07"]
    s.N = N07
    T = s.C.index
    cal = calendar(T)
    print(f"calendar: {len(cal['opex'])} OPEX days {cal['opex'][0]:%Y-%m-%d}..{cal['opex'][-1]:%Y-%m-%d}, "
          f"{len(cal['witching'])} witching, {len(cal['week'])} OPEX-week sessions, "
          f"{len(cal['post'])} post-OPEX sessions; non-Friday OPEX: "
          f"{[d.strftime('%Y-%m-%d') for d in cal['opex'] if d.dayofweek != 4]}")
    qv = s.C["QQQ"].pct_change(fill_method=None).rolling(20).std().shift(1) * np.sqrt(252)
    fridays = T[T.dayofweek == 4]

    # ------------------------------------------------ V1 / V2 / V3: noise leg
    u = noise_unit(s, NCAP_TAX)
    ur = noise_unit(s, 1.5)
    print("\n== noise leg (V7 taxable: QQQ+SMH, cap 0.75), per-day net return at unit equity")
    for lab, ev in (("V1 OPEX Friday", cal["opex"]), ("   OPEX week (Mon..OPEX)", cal["week"]),
                    ("V2 post-OPEX 5 sessions", cal["post"]), ("   witching day", cal["witching"])):
        for line in split_table(u, ev, lab):
            print(line)
    print("-- same, Roth cap 1.5 (3x ETFs on the night half's cash)")
    for lab, ev in (("V1 OPEX Friday", cal["opex"]), ("V2 post-OPEX 5 sessions", cal["post"])):
        for line in split_table(ur, ev, lab):
            print(line)

    print("\n-- placebo (vol-tercile matched): event mean vs placebo distribution, bp/day")
    plac = {}
    for pn, (a, b) in {**PERIODS, "pooled": ("2016-01-01", "2026-12-31")}.items():
        x = u[a:b]; terc = terciles(qv, x.index)
        ev1 = cal["opex"].intersection(x.index)
        p1 = placebo_days(x, ev1, fridays.difference(cal["opex"]), terc)
        m1 = x.reindex(ev1).mean()
        post = cal["post"].intersection(x.index)
        firsts = pd.DatetimeIndex([T[T > d][0] for d in cal["opex"] if (T > d).any()]).intersection(x.index)
        p2 = placebo_blocks(x, firsts, post, terc)
        m2 = x.reindex(post).mean()
        plac[pn] = (m1, p1, m2, p2)
        print(f"  {pn:8s} V1 OPEX Fri {m1*1e4:+6.1f}bp  placebo p5/p50/p95 {np.percentile(p1,5)*1e4:+6.1f}/"
              f"{np.median(p1)*1e4:+6.1f}/{np.percentile(p1,95)*1e4:+6.1f}  pct {(p1 < m1).mean():4.0%}   |  "
              f"V2 post {m2*1e4:+6.1f}bp  placebo p5/p50/p95 {np.percentile(p2,5)*1e4:+6.1f}/"
              f"{np.median(p2)*1e4:+6.1f}/{np.percentile(p2,95)*1e4:+6.1f}  pct {(p2 < m2).mean():4.0%}")

    print("\n== V3 0DTE era: noise leg per-day edge (net, unit equity, cap 0.75)")
    eras = {"2016-20": ("2016-01-01", "2020-12-31"), "2021..2022-11-11": ("2021-01-01", "2022-11-11"),
            "2022-11-14+ (0DTE daily)": ("2022-11-14", "2026-12-31")}
    for lab, (a, b) in eras.items():
        x = u[a:b]
        print(f"  {lab:26s} mean {x.mean()*1e4:+6.1f}bp/day  Sharpe {x.mean()/x.std()*np.sqrt(252):5.2f}  "
              f"hit {(x > 0).mean():4.0%}  n {len(x)}")
    x = u["2021-01-01":]
    b0, t0 = nw_t(x, pd.Series(x.index >= ZERO_DTE, index=x.index))
    b1, t1 = nw_t(u, pd.Series(u.index >= ZERO_DTE, index=u.index))
    print(f"  0DTE dummy: vs 2021-22 {b0*1e4:+.1f}bp (NW t {t0:+.2f}); vs all pre {b1*1e4:+.1f}bp (NW t {t1:+.2f})")
    for sym in ("QQQ", "SMH"):
        z = s.NZ[sym]; y = (z.ret * z.lev.clip(upper=NCAP_TAX))
        print(f"  {sym} by year (bp/day, cap 0.75): " + "  ".join(
            f"{yy} {g.mean()*1e4:+5.1f}" for yy, g in y.groupby(y.index.year)))
    # noise leg Sharpe by year normalised: return per unit of |move| (lev 1, gross of scaling)
    y = pd.concat([s.NZ[k].ret for k in ("QQQ", "SMH")], axis=1, sort=True).mean(axis=1)
    print("  unlevered QQQ/SMH mean by year (bp/day): " + "  ".join(
        f"{yy} {g.mean()*1e4:+5.1f}" for yy, g in y.groupby(y.index.year)))

    # ------------------------------------------------ V4: IBS and night legs
    print("\n== V4 IBS and night legs by options-calendar window (unit weight; night at 3bp)")
    iu = ibs_unit(s)
    s._gap(T[0])
    nu = night_unit(N07, 3.0, s._gaps)
    v4 = {}
    for leg, x, per in (("IBS", iu, PERIODS),
                        ("night", nu, {"2021-23": ("2020-11-01", "2023-12-31"),
                                       "2024-26": ("2024-01-01", "2026-12-31")})):
        for lab, ev in (("OPEX week", cal["week"]), ("post-OPEX 5 sessions", cal["post"])):
            for line in split_table(x, ev, f"{leg} {lab}", per):
                print(line)
        # week vs post directly
        both = x[x.index.isin(cal["week"]) | x.index.isin(cal["post"])]
        for pn, (a, b) in per.items():
            y = both[a:b]
            if len(y) < 20:
                continue
            bb, t = nw_t(y, pd.Series(y.index.isin(cal["post"]), index=y.index))
            v4[(leg, pn)] = (bb, t)
            print(f"  {leg + ' post minus OPEX week':34s} {pn}  {bb*1e4:+6.1f}bp  NW t {t:+5.2f}")

    # ------------------------------------------------ V5: witching close auction
    print("\n== V5 witching days: the close auction and the night entry")
    wit = cal["witching"]
    slip = pd.Series({d: float(np.mean(nd.close / nd.price - 1)) for d, nd in N07.items()})
    for lab, x in (("night per-day ret (3bp)", nu), ("night 15:50->close drift", slip)):
        m = x.index.isin(wit)
        bb, t = nw_t(x, pd.Series(m, index=x.index))
        print(f"  {lab:28s} witching {x[m].mean()*1e4:+7.1f}bp (n {m.sum():2d})  other {x[~m].mean()*1e4:+7.1f}bp"
              f"  NW t {t:+5.2f}")
    # verifier: witching is (almost) always a Friday -> weekend hold at weekend_scale 0.5; the
    # honest control is other pre-weekend/holiday entries, not all days
    g = pd.Series(s._gaps).reindex(nu.index).fillna(1)
    fri = nu[(nu.index.dayofweek == 4) | (g > 1).values]
    for pn, (a, b) in {"2021-23": ("2020-11-01", "2023-12-31"), "2024-26": ("2024-01-01", "2026-12-31"),
                       "pooled": ("2020-01-01", "2026-12-31")}.items():
        y = fri[a:b]; m = y.index.isin(wit)
        bb, t = nw_t(y, pd.Series(m, index=y.index))
        print(f"  night vs other pre-gap entries {pn}: witching {y[m].mean()*1e4:+6.1f}bp (n {m.sum():2d})  "
              f"other {y[~m].mean()*1e4:+6.1f}bp  diff {bb*1e4:+6.1f}  NW t {t:+5.2f}")
    on = s.O.shift(-1) / s.C - 1
    for sym in ("SPY", "QQQ", "IWM"):
        x = on[sym]["2016-01-01":].dropna()
        for pn, (a, b) in PERIODS.items():
            y = x[a:b]; m = y.index.isin(wit)
            print(f"  {sym} close->open {pn}: witching {y[m].mean()*1e4:+6.1f}bp (n {m.sum():2d})  "
                  f"other {y[~m].mean()*1e4:+6.1f}bp")

    # ------------------------------------------------ book: V1, V2, V2u on V7 and Roth
    print("\n== V7 book (taxable, cfg 1.0x / conv 0.5 / intraday 0.75), 2021-23 | 2024-26 | full "
          "CAGR/Sharpe/maxDD")
    vars_ = {"V7 baseline": s,
             "V1 noise x0.5 OPEX Fri": scaled_sim(s, cal["opex"], 0.5, "ret"),
             "V2 noise x1.5 post-OPEX (margin-capped)": scaled_sim(s, cal["post"], 1.5, "lev"),
             "V2u noise x1.5 post-OPEX (uncapped)": scaled_sim(s, cal["post"], 1.5, "ret")}
    res = {}
    for c in (3.0, "tier", "tier_hi"):
        for name, t in vars_.items():
            df = book(t, c); res[(name, c)] = df
            print(f"  {name:42s} {str(c):>8s}  {fmt(df['r'])}")
    print("-- edge-halves and 5y MC (21-day blocks) at 3bp and tier_hi")
    for c in (3.0, "tier_hi"):
        for name in vars_:
            df = res[(name, c)]
            e = G.eh(df)
            m1, m2 = G.mc(e, 3000, 1000), G.mc(e, 10000, 0)
            es = B.stats(e)
            print(f"  {name:42s} {str(c):>8s}  EH {es[0]*100:5.1f}/{es[1]:4.2f}/{es[2]*100:4.0f}  "
                  f"$3k+1k med ${m1['med']:>8,.0f} P30 {m1['dd30']:4.0%} P50 {m1['dd50']:4.0%}  "
                  f"$10k med ${m2['med']:>8,.0f} P30 {m2['dd30']:4.0%}  | {episodes(df['r'])}")
    # COVID (noise leg only moves; the change is linear in the scaled days)
    a, b = "2020-02-19", "2020-03-23"
    for lab, ev, k in (("V1", cal["opex"], 0.5), ("V2u", cal["post"], 1.5)):
        d = u[a:b]; delta = ((k - 1) * d[d.index.isin(ev)]).sum()
        print(f"  COVID {a}..{b}: {lab} changes the book by {delta*100:+.2f}pp (noise leg, additive)")

    print("\n== Roth b1 (IBS + night 1.0x, intraday 1.5x via 3x ETFs on night cash), tier / tier_hi / 3bp")
    base = dict(tilt="live", weekend_scale=0.5, noise_on=False, conviction_w=0.0, margin_rate=0.0)
    for name, t in vars_.items():
        t = copy.copy(t); t.BO = getattr(s, "BO", None) if hasattr(s, "BO") else None
        if t.BO is None:
            if not hasattr(main, "_bo"):
                main._bo = B.breakout_days()
            t.BO = main._bo
        out = []
        for c in (3.0, "tier_hi"):
            r = RO.replay(t, s.days, B.Params(night_cost=c, **base), budget="night", noise_cap=1.5).r
            out.append(fmt(r))
        print(f"  {name:42s} 3bp {out[0]}   tier_hi {out[1]}")


if __name__ == "__main__":
    main()
