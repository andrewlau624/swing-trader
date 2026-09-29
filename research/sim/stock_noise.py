"""Addendum NN (stock_noise): the live noise-area momentum rule on the most liquid SINGLE stocks.

    # 1. universe (LOCKED: loads the SIP panel), ~1 min
    until mkdir $SCR/heavy.lock 2>/dev/null; do sleep 10; done; \
      PYTHONPATH=. .venv/bin/python -m research.sim.stock_noise_univ; rmdir $SCR/heavy.lock
    # 2. 1-minute SIP bars (raw) + daily raw/all, then quoted-spread samples (~25 + ~20 min, resumable)
    PYTHONPATH=. .venv/bin/python -m research.sim.stock_noise_fetch
    PYTHONPATH=. .venv/bin/python -m research.sim.stock_noise_fetch --quotes
    # 3. per-name legs (cache) and every table (~10 min, no lock)
    PYTHONPATH=. .venv/bin/python -m research.sim.stock_noise [--rebuild]

Pre-registration: scratchpad addenda/stock_noise.md (stamped before any return was computed).

Universe: each month the top N common stocks by trailing 63-session median dollar volume
(point in time, no tickers; stock_noise_univ.py). Rule per name = the live leg through
swingtrader.daily.signals: noise_sigma (14 sessions), noise_bounds (day open, prev close on the
day's basis), noise_decide at minutes 30..360 on the completed 1-minute bar, flat at the close,
noise_leverage (adjusted daily closes, target 2%/day), capped by the live intraday cap.

Book variants (basket inside the SAME intraday budget and cap):
  S5r / S10r / S20r  N = 5 / 10 / 20, the basket replaces the SMH half (QQQ .5, basket .5)
  S10t / S20t        N = 10 / 20, third stream at equal share (QQQ, SMH, basket 1/3 each)
Controls: P1 random-direction placebo (same segments, sizes, costs; 200 draws);
          CTRL10r = the rule on 10 random liquid names from ranks 41-100 (drawn each January).
Costs per side on stock trades: C1 3bp, C2 spread-aware (max(.5, half median quoted spread + .25)),
C3 tier_hi (book.cost_bps on raw price / 63d dollar volume). QQQ/SMH 0.5bp as published.
"""
from __future__ import annotations

import glob
import os
import pickle
import sys

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import book as B
from . import growth as G
from . import taxable_frontier as TF
from .validate import load_sim

SP = str(__import__("pathlib").Path(__file__).resolve().parents[2]) + "/data/research/program"
M1 = f"{SP}/stock_m1"
UNIV = f"{SP}/stock_noise_univ.pkl"
LEGS = f"{SP}/cache_stock_noise_legs.pkl"
RES = f"{SP}/res_stock_noise.pkl"
ET = "America/New_York"
LOOKBACK, TV = 14, 0.02
CAPS = (0.75, 1.5)                  # live intraday cap with conviction on / off (growth.cfg, 2x)
NMAX = 20
VARIANTS = {  # label: (N, universe, shares (QQQ, SMH, basket))
    "S5r": (5, "top", (0.5, 0.0, 0.5)),
    "S10r": (10, "top", (0.5, 0.0, 0.5)),
    "S20r": (20, "top", (0.5, 0.0, 0.5)),
    "S10t": (10, "top", (1 / 3, 1 / 3, 1 / 3)),
    "S20t": (20, "top", (1 / 3, 1 / 3, 1 / 3)),
}
CONTROLS = {"CTRL10r": (10, "ctrl", (0.5, 0.0, 0.5))}
N_PRE = len(VARIANTS)
BASES = {  # label: (gross, night name cap, conviction)
    "V7 (T0) conv": (1.0, 0.10, 0.5),
    "moderate10c (T2b)": (1.0, 0.15, 0.5),
    "V7 no conv (T0L)": (1.0, 0.10, 0.0),
    "moderate10 no conv": (1.0, 0.15, 0.0),
}
PRIMARY = ("V7 (T0) conv", "moderate10c (T2b)")
SCOST = ("C1", "C2", "C3")
PER = (("2021-23", "2021-01-01", "2023-12-31"), ("2024-26", "2024-01-01", "2026-12-31"))
HO = ("2016-06-01", "2020-12-31")


# ================================================================ data
def daily():
    out = {}
    for adj in ("raw", "all"):
        d = pd.read_parquet(f"{M1}/daily_{adj}.parquet")
        d["date"] = d.timestamp.dt.tz_convert(ET).dt.tz_localize(None).dt.normalize()
        out[adj] = d.pivot_table(index="date", columns="symbol", values="close", aggfunc="last")
    return out["raw"], out["all"]


def mats(sym: str) -> dict | None:
    fs = sorted(glob.glob(f"{M1}/{sym.replace('.', '_')}_20*.parquet"))
    if not fs:
        return None
    df = pd.concat([pd.read_parquet(f) for f in fs])
    if not len(df):
        return None
    t = df.timestamp.dt.tz_convert(ET)
    df["date"] = t.dt.tz_localize(None).dt.normalize()
    df["m"] = t.dt.hour * 60 + t.dt.minute - 570
    df = df[(df.m >= 0) & (df.m < 390)]
    M = {f: df.pivot_table(index="date", columns="m", values=f, aggfunc="last").reindex(columns=range(390))
         for f in ("open", "close", "volume")}
    M["close"] = M["close"].ffill(axis=1)
    M["open"] = M["open"].fillna(M["close"])
    M["volume"] = M["volume"].fillna(0)
    full = (M["volume"].iloc[:, 300:].sum(axis=1) > 0) & M["close"].iloc[:, 0].notna()
    first = M["open"].bfill(axis=1).iloc[:, 0]                   # first traded open of the session
    return {"O": first[full].values, "C": M["close"][full].values, "V": M["volume"][full].values,
            "days": M["close"].index[full]}


def name_days(sym: str, M: dict, raw: pd.DataFrame, adj: pd.DataFrame) -> pd.DataFrame:
    """Per session of one name: gross unlevered return of the live rule, trades, vol-target
    leverage (uncapped), raw open, and the segments (move, index) for the placebo."""
    C, V, O, days = M["C"], M["V"], M["O"], M["days"]
    if sym not in adj.columns:
        return pd.DataFrame()
    ca = adj[sym].dropna(); cr = raw[sym].reindex(ca.index)
    cal = ca.index
    pos = {d: i for i, d in enumerate(cal)}
    move = np.abs(C / O[:, None] - 1)
    vwap = np.cumsum(C * V, axis=1) / np.maximum(np.cumsum(V, axis=1), 1)
    rows, segs = [], []
    for i in range(LOOKBACK, len(days)):
        d = days[i]
        k = pos.get(d)
        if k is None or k < 15:
            continue
        # sigma needs the previous 14 sessions (half days are skipped, as for QQQ): not older than 20
        if k - pos.get(days[i - LOOKBACK], -999) > LOOKBACK + 6:
            continue
        f_today = cr.iloc[k] / ca.iloc[k]
        if not np.isfinite(f_today) or f_today <= 0:
            continue
        prevc = float(ca.iloc[k - 1] * f_today)                 # live: adjustment='all' prev close
        sigma = sg.noise_sigma(move[i - LOOKBACK:i])
        ub, lb = sg.noise_bounds(O[i], prevc, sigma)
        lev = sg.noise_leverage(ca.iloc[:k], TV, 1e9)
        p_, entry, pnl, trades, seg = 0, None, 0.0, 0, []
        for m in range(sg.NOISE_FIRST, 390, sg.NOISE_STEP):
            p = C[i, m]
            new = sg.noise_decide(p_, p, ub[m], lb[m], vwap[i, m])
            if new != p_:
                if p_ != 0:
                    pnl += p_ * (p / entry - 1); trades += 1; seg.append(p / entry - 1)
                if new != 0:
                    entry = p; trades += 1
                p_ = new
        if p_ != 0:
            p = C[i, 389]
            pnl += p_ * (p / entry - 1); trades += 1; seg.append(p / entry - 1)
        rows.append((d, sym, pnl, trades, lev, O[i], len(seg)))
        segs.extend(seg)
    df = pd.DataFrame(rows, columns=["date", "sym", "gross", "trades", "lev", "open_raw", "nseg"])
    df.attrs["segs"] = np.asarray(segs, float)
    return df


def build_legs():
    from .stock_noise_fetch import control_draws
    u = pickle.load(open(UNIV, "rb"))
    raw, adj = daily()
    syms = sorted({s for s in raw.columns})
    parts, segs = [], []
    for j, s in enumerate(syms):
        M = mats(s)
        if M is None:
            continue
        df = name_days(s, M, raw, adj)
        if len(df):
            segs.append(df.attrs["segs"]); df.attrs = {}
            parts.append(df)
        print(f"  {j+1}/{len(syms)} {s} {len(df)} days", flush=True)
    X = pd.concat(parts, ignore_index=True)
    X["seg0"] = np.r_[0, np.cumsum(X.nseg.values)[:-1]]
    S = np.concatenate(segs)
    # 63d median dollar volume (prior sessions) for the tier cost
    dv = (u["close"] * u["volume"]).rolling(63, min_periods=40).median().shift(1)
    X["dv"] = [float(dv.at[d, s]) if (d in dv.index and s in dv.columns) else np.nan
               for d, s in zip(X.date, X.sym)]
    pickle.dump(dict(X=X, S=S, rank=u["rank"], ctrl=control_draws(u["rank"])), open(LEGS, "wb"), protocol=4)
    print("legs cached", LEGS, len(X), "name-days", len(S), "segments", flush=True)


# ================================================================ costs
def spreads():
    q = pd.read_parquet(f"{M1}/quote_spreads.parquet")
    return {(s, int(y)): float(v) for s, y, v in zip(q.symbol, q.year, q.spread_bps) if np.isfinite(v)}


def add_costs(X: pd.DataFrame) -> pd.DataFrame:
    sp = spreads()
    yr = X.date.dt.year.values
    med = np.nanmedian(list(sp.values())) if sp else 1.0
    s2 = np.array([sp.get((s, int(y)), np.nan) for s, y in zip(X.sym, yr)])
    X["spread"] = np.where(np.isfinite(s2), s2, med)
    X["C1"] = 3.0
    X["C2"] = np.maximum(0.5, 0.5 * X.spread + 0.25)
    X["C3"] = B.cost_bps("tier_hi", X.open_raw.values, np.nan_to_num(X.dv.values, nan=1e9))
    return X


# ================================================================ baskets
def members(L, N, kind) -> dict:
    """month start -> names."""
    if kind == "top":
        return {d: list(row.loc[1:N].values) for d, row in L["rank"].iterrows()}
    return dict(L["ctrl"])


def basket_gross(X, mem):
    """mask of the name-days inside the month's membership list."""
    ms = pd.DatetimeIndex(sorted(mem))
    mstart = ms[np.clip(np.searchsorted(ms, X.date.values, side="right") - 1, 0, None)]
    return np.array([s in mem[m] for s, m in zip(X.sym.values, mstart)]) & (X.date.values >= ms[0])


_CODES = {}


def basket(X: pd.DataFrame, mask: np.ndarray, cap: float, cost: str | None = None,
           net: np.ndarray | None = None) -> pd.Series:
    """Daily return per unit of the basket's share: mean over the day's member names of
    min(lev_i, cap) x net_i (net overrides the per-name-day net return: placebo)."""
    if id(X) not in _CODES:
        _CODES.clear(); _CODES[id(X)] = pd.factorize(X.date, sort=True)
    codes, uniq = _CODES[id(X)]
    if net is None:
        net = X.gross.values - X.trades.values * X[cost].values / 1e4
    y = np.minimum(X.lev.values, cap) * net
    c = codes[mask]
    num = np.bincount(c, weights=y[mask], minlength=len(uniq))
    den = np.bincount(c, minlength=len(uniq))
    ok = den > 0
    return pd.Series(num[ok] / den[ok], index=pd.DatetimeIndex(uniq[ok]))


# ================================================================ book
def params(g, cap, conv, night_cost, shares):
    p = TF._params(g, cap, conv, None, night_cost)
    sq, ss, _ = shares
    p.noise = {k: v for k, v in (("QQQ", sq), ("SMH", ss)) if v > 0}
    return p


def replay(s, N, g, cap, conv, night_cost, shares=(0.5, 0.5, 0.0), bk: dict | None = None,
           start=3000.0, monthly=1000.0, trades=True, whole: dict | None = None):
    """TF.replay with the noise shares as a parameter and the basket as an extra intraday stream.
    bk: {intraday cap: daily basket return per unit share}. whole: per-day name arrays for the
    whole-share replay {d: (w_i, lev_i, net_i, open_raw_i)} (basket only)."""
    s.N = N
    ix = s.C.index
    pos = {d: i for i, d in enumerate(ix)}
    nxt = lambda d, k: ix[min(pos[d] + k, len(ix) - 1)]  # noqa: E731
    p = params(g, cap, conv, night_cost, shares)
    sb = shares[2]
    b = bk.get(round(p.noise_cap, 2)) if bk else None
    E, rows, T, fill = start, [], [], []
    for i, d in enumerate(s.days):
        if i and i % 21 == 0:
            E += monthly
        pl, info = s.day_pnl(E, d, p)
        x = 0.0
        if sb and whole is not None and d in whole:
            w, lev, net, px = whole[d]
            tgt = E * sb * w * np.minimum(lev, p.noise_cap)
            sh = np.floor(tgt / px)
            f = np.where(tgt > 0, sh * px / np.maximum(tgt, 1e-9), 0.0)
            x = float((tgt * f * net).sum()); fill.append(float((tgt * f).sum() / max(tgt.sum(), 1e-9)))
        elif sb and b is not None and d in b.index:
            x = E * sb * float(b.at[d])
        pl += x; info["noise"] += x
        if trades:
            for t in TF.day_trades(s, E, d, p, nxt):
                T.append((d,) + t + (E,))
            if x:
                T.append((d, "BASKET", d, d, E * sb * p.noise_cap, x, E))
        k = E if E else 1.0
        rows.append((d, E, pl / k, info["night"] / k, info["ibs"] / k, info["noise"] / k,
                     (info["idle"] + info["margin"]) / k))
        E += pl
    df = pd.DataFrame(rows, columns=["date", "E", "r", "r_night", "r_ibs", "r_noise", "r_cash"]).set_index("date")
    tr = pd.DataFrame(T, columns=["book", "sym", "buy", "sell", "qty", "pnl", "E"]) if trades else None
    if tr is not None:
        tr["frac"] = tr.pnl / tr.E
    if whole is not None:
        df.attrs["fill"] = float(np.mean(fill)) if fill else np.nan
    return df, tr


def holdout(legs, n2020, g, conv, shares, bk, a=HO[0], b=HO[1]):
    """program_books.tax_holdout with the noise shares as a parameter and the basket added."""
    night, ibs, bil, nz, bo = legs
    p = G.cfg(g, conv, 2)
    ix = bil.index
    days = ix[(ix >= a) & (ix <= b)]
    sq, ss, sb = shares
    bb = bk.get(round(p["noise_cap"], 2)) if bk else None
    out = {}
    for d in days:
        bl = float(np.nan_to_num(bil.get(d, 0.0)))
        nv = n2020.get(d, np.nan)
        x = p["night_w"] * float(nv) if np.isfinite(nv) else p["night_w"] * bl * (d < pd.Timestamp("2020-01-02"))
        iv = ibs.get(d, np.nan)
        x += p["ibs_w"] * (float(iv) if np.isfinite(iv) else bl)
        for sym, share in (("QQQ", sq), ("SMH", ss)):
            z = nz[sym]
            if share and d in z.index:
                x += min(float(z.at[d, "lev"]), p["noise_cap"]) * share * float(z.at[d, "ret"])
        if sb and bb is not None and d in bb.index:
            x += sb * float(bb.at[d])
        x += p["conviction_w"] * float(bo.get(d, 0.0))
        x -= max(0.0, p["ibs_w"] + p["night_w"] - 1) * 0.12 / 252
        out[d] = x
    return pd.Series(out)


# ================================================================ stats helpers
def cell(r):
    c, s_, d = B.stats(r)
    return f"{c*100:5.1f}/{s_:4.2f}/{d*100:4.0f}"


def cagr(r):
    return B.stats(r)[0]


def ep(r, a, b):
    x = r[a:b]
    return float((1 + x).prod() - 1) if len(x) else np.nan


def worst_month(r):
    return float((1 + r.fillna(0)).groupby([r.index.year, r.index.month]).prod().min() - 1)


def dct(y: pd.Series) -> float:
    """t of the daily mean (the day-clustered t of name-day returns averaged within a day)."""
    y = y.dropna()
    return float(y.mean() / (y.std(ddof=1) / np.sqrt(len(y)))) if len(y) > 2 else np.nan


# ================================================================ main
def main():
    if "--rebuild" in sys.argv or not os.path.exists(LEGS):
        build_legs()
    L = pickle.load(open(LEGS, "rb"))
    X = add_costs(L["X"])
    S = L["S"]
    out = []

    def P(*a):
        line = " ".join(str(x) for x in a)
        print(line, flush=True); out.append(line)

    P(f"name-days {len(X):,}, symbols {X.sym.nunique()}, segments {len(S):,}")
    q = pd.read_parquet(f"{M1}/quote_spreads.parquet")
    P(f"quoted spread samples: {len(q)} symbol-years, median {q.spread_bps.median():.2f}bp, "
      f"p90 {q.spread_bps.quantile(.9):.2f}bp; NBBO-style records (bid exch != ask exch) {q.nbbo_share.mean():.0%}")
    for kind, lab in (("top", "top20"), ("ctrl", "ctrl")):
        mem = members(L, NMAX if kind == "top" else 10, kind)
        m = basket_gross(X, mem)
        x = X[m]
        P(f"  {lab}: C2 per side median {x.C2.median():.2f}bp (p90 {x.C2.quantile(.9):.2f}), C3 median {x.C3.median():.1f}bp, "
          f"trades/day {x.trades.mean():.2f}, lev median {x.lev.median():.2f}")

    # ---------------- Q1 standalone per name-day (unit leverage) and baskets
    P("\n== Q1. per name-day, unit leverage: mean net bp/day (day-clustered t)  2016-20 | 2021-23 | 2024-26")
    per3 = (("2016-20", "2016-01-01", "2020-12-31"),) + PER
    nz = load_sim(raw_price=True).NZ
    for sym in ("QQQ", "SMH", "SPY", "IWM"):
        z = B.noise_days(sym, cost=0.0)
        P(f"  {sym:8s} ETF gross " + " | ".join(
            f"{z.ret[a:b].mean()*1e4:+6.2f} (t {dct(z.ret[a:b]):+5.2f})" for _, a, b in per3)
          + f"   trades/day {z.trades.mean():.2f}")
        w = np.minimum(z.lev, 0.75) * (z.ret - z.trades * 0.5 / 1e4)
        P(f"  {sym:8s} book-wtd min(lev,.75) x net 0.5bp " + " | ".join(
            f"{w[a:b].mean()*1e4:+6.2f} (t {dct(w[a:b]):+5.2f})" for _, a, b in per3))
    for kind, N in (("top", 5), ("top", 10), ("top", 20), ("ctrl", 10)):
        m = basket_gross(X, members(L, N, kind))
        for cost in ("gross",) + SCOST:
            net = X.gross - (0 if cost == "gross" else X.trades * X[cost] / 1e4)
            y = pd.Series(net.values[m], index=X.date.values[m]).groupby(level=0).mean()
            P(f"  {kind}{N:<3d} {cost:6s} " + " | ".join(
                f"{y[a:b].mean()*1e4:+6.2f} (t {dct(y[a:b]):+5.2f})" for _, a, b in per3))
            if cost != "gross":
                w = basket(X, m, 0.75, cost)
                P(f"  {kind}{N:<3d} {cost:6s} book-wtd min(lev,.75) " + " | ".join(
                    f"{w[a:b].mean()*1e4:+6.2f} (t {dct(w[a:b]):+5.2f})" for _, a, b in per3))

    # D1 cross-section: name-year gross edge vs dollar volume and vol
    X["yr"] = X.date.dt.year
    mem20 = members(L, NMAX, "top"); memc = members(L, 10, "ctrl")
    inb = basket_gross(X, mem20) | basket_gross(X, memc)
    ny = X[inb].groupby(["sym", "yr"]).agg(g=("gross", "mean"), n=("gross", "size"), dv=("dv", "median"),
                                           lev=("lev", "median"))
    ny = ny[(ny.n >= 60) & np.isfinite(ny.dv)]
    A = np.c_[np.ones(len(ny)), np.log(ny.dv) - np.log(ny.dv).mean(), np.log(TV / ny.lev) - np.log(TV / ny.lev).mean()]
    beta, *_ = np.linalg.lstsq(A, ny.g.values * 1e4, rcond=None)
    res = ny.g.values * 1e4 - A @ beta
    se = np.sqrt(np.diag(np.linalg.inv(A.T @ A)) * res.var(ddof=3))
    P(f"\n== D1. name-year gross bp/day (n={len(ny)}) on log $vol and log daily vol: const {beta[0]:+.2f} (t {beta[0]/se[0]:+.1f}), "
      f"log$vol {beta[1]:+.2f} (t {beta[1]/se[1]:+.1f}), logvol {beta[2]:+.2f} (t {beta[2]/se[2]:+.1f})")
    top = ny.groupby(level=0).g.mean().sort_values()
    P(f"  per-name mean gross bp/day, share > 0: {(top > 0).mean():.0%} of {len(top)} names; "
      f"median {top.median()*1e4:+.2f}")

    # ---------------- baskets for the book
    bks, MASK = {}, {}
    for lab, (N, kind, sh) in {**VARIANTS, **CONTROLS}.items():
        MASK[lab] = basket_gross(X, members(L, N, kind))
        for cost in SCOST:
            bks[(lab, cost)] = {cap: basket(X, MASK[lab], cap, cost) for cap in CAPS}
    # correlation with the QQQ noise leg
    zq = nz["QQQ"]; qd = np.minimum(zq.lev, 0.75) * zq.ret
    for lab in ("S10r", "S20r", "CTRL10r"):
        bb = bks[(lab, "C2")][0.75]
        j = bb.index.intersection(qd.index)
        P(f"  corr(basket {lab}, QQQ leg) daily 2016-26: {np.corrcoef(bb[j], qd[j])[0,1]:+.2f}")

    # ---------------- Q2 book
    s = load_sim(raw_price=True)
    s.BO = B.breakout_days()
    rp = pickle.load(open(f"{SP}/cache_rawprice.pkl", "rb"))
    Ns = rp["raw"]
    me = pickle.load(open(f"{SP}/cache_macro_events.pkl", "rb"))
    legs = me["legs"]
    from . import program_books as PB
    n2020 = {cap: PB.night2020(rp["y2020"]["raw"][0], cap) for cap in (0.10, 0.15)}
    n2020 = {c: v[v.index < "2020-11-05"] for c, v in n2020.items()}
    R = {}
    P("\n== Q2. books (raw prices): 2016-20 HO | 2021-23 | 2024-26 | full ; increments in pp CAGR")
    for blab, (g, cap, conv) in BASES.items():
        for nc in (3.0, "tier_hi"):
            df, tr = replay(s, Ns[cap], g, cap, conv, nc)
            ho = holdout(legs, n2020[cap], g, conv, (0.5, 0.5, 0.0), None)
            R[(blab, nc, "base")] = dict(df=df, tr=tr, ho=ho)
            P(f"  {blab:22s} {str(nc):7s} base      HO {cell(ho)} | " + " | ".join(cell(df.r[a:b]) for _, a, b in PER) + f" | {cell(df.r)}")
            for lab, (N, kind, sh) in {**VARIANTS, **CONTROLS}.items():
                for sc in SCOST:
                    dv_, trv = replay(s, Ns[cap], g, cap, conv, nc, sh, bks[(lab, sc)], trades=(sc == "C2"))
                    hv = holdout(legs, n2020[cap], g, conv, sh, bks[(lab, sc)])
                    R[(blab, nc, lab, sc)] = dict(df=dv_, tr=trv, ho=hv)
                    inc = [cagr(dv_.r[a:b]) - cagr(df.r[a:b]) for _, a, b in PER]
                    P(f"  {blab:22s} {str(nc):7s} {lab:8s}{sc} HO {cell(hv)} ({(cagr(hv)-cagr(ho))*100:+5.1f}) | "
                      + " | ".join(f"{cell(dv_.r[a:b])} ({i*100:+5.1f})" for (_, a, b), i in zip(PER, inc))
                      + f" | {cell(dv_.r)} ({(cagr(dv_.r)-cagr(df.r))*100:+5.1f}) NW t {TF.nw_t(dv_.r - df.r):+5.2f}")
    pickle.dump({k: {kk: vv for kk, vv in v.items() if kk != "tr"} for k, v in R.items()}, open(RES, "wb"))

    # ---------------- placebo P1 (increment of the daily book return, 2021-26, C2, night 3bp)
    P("\n== P1. random-direction placebo (200 draws): mean daily increment 2021-26, C2; actual pct")
    rng = np.random.default_rng(11)
    segi = np.repeat(np.arange(len(X)), X.nseg.values)
    cstn = X.trades.values * X.C2.values / 1e4
    jobs = {}
    for blab in PRIMARY:
        g, cap, conv = BASES[blab]
        capi = round(G.cfg(g, conv, 2)["noise_cap"], 2)
        base = R[(blab, 3.0, "base")]["df"]
        for lab, (N, kind, sh) in {**VARIANTS, **CONTROLS}.items():
            dv_ = R[(blab, 3.0, lab, "C2")]["df"]
            b_act = bks[(lab, "C2")][capi].reindex(dv_.index).fillna(0)
            rest = (dv_.r - sh[2] * b_act - base.r)["2021-01-01":]
            jobs[(blab, lab)] = (capi, sh[2], rest, (dv_.r - base.r)["2021-01-01":].mean(), [])
    for k in range(200):
        g_pl = np.bincount(segi, weights=rng.choice([-1.0, 1.0], size=len(S)) * S, minlength=len(X))
        net = g_pl - cstn
        for (blab, lab), (capi, sb, rest, act, pl) in jobs.items():
            bp = basket(X, MASK[lab], capi, net=net).reindex(rest.index).fillna(0)
            pl.append((rest + sb * bp).mean())
    pcts = {}
    for (blab, lab), (capi, sb, rest, act, pl) in jobs.items():
        pl = np.array(pl)
        pcts[(blab, lab)] = (act > pl).mean()
        P(f"  {blab:22s} {lab:8s} actual {act*1e4:+6.2f}bp/day  placebo median {np.median(pl)*1e4:+6.2f} "
          f"p95 {np.percentile(pl, 95)*1e4:+6.2f}  pct {pcts[(blab, lab)]:.0%}")

    # ---------------- walk-forward pick
    P("\n== WF. best variant by increment in one half (C2, night 3bp), judged in the other")
    for blab in PRIMARY:
        base = R[(blab, 3.0, "base")]["df"].r
        for (fa, a0, b0), (ja, a1, b1) in ((PER[0], PER[1]), (PER[1], PER[0])):
            inc = {lab: cagr(R[(blab, 3.0, lab, "C2")]["df"].r[a0:b0]) - cagr(base[a0:b0]) for lab in VARIANTS}
            pick = max(inc, key=inc.get)
            j = cagr(R[(blab, 3.0, pick, "C2")]["df"].r[a1:b1]) - cagr(base[a1:b1])
            P(f"  {blab:22s} fit {fa}: {pick} ({inc[pick]*100:+.1f}pp) -> {ja} {j*100:+.1f}pp")

    # ---------------- EH, after tax, MC, episodes (primary baselines, C2)
    P("\n== EH / after tax (35%) / 5y MC ($3k + $1k/mo, EH, after tax) / episodes; stock cost C2")
    for blab in PRIMARY:
        for nc in (3.0, "tier_hi"):
            keys = [("base", R[(blab, nc, "base")])] + [(lab, R[(blab, nc, lab, "C2")]) for lab in {**VARIANTS, **CONTROLS}]
            for lab, x in keys:
                df, tr, ho = x["df"], x["tr"], x["ho"]
                at, _ = TF.after_tax(df.r, 0.35, trades=tr)
                e = G.eh(df)
                eat, _ = TF.after_tax(e, 0.35, trades=tr)
                m = TF.mc_tax(e, 0.35, start=3000, monthly=1000)
                x.update(at=at, eh=e, eh_at=eat, mc=m)
                P(f"  {blab:22s} {str(nc):7s} {lab:8s} AT {cagr(at)*100:5.1f} EH {cagr(e)*100:5.1f} EH-AT {cagr(eat)*100:5.1f} | "
                  f"MC med ${m['med']:,.0f} P30 {m['dd30']:.0%} ({m['dd30_acct']:.0%}) P50 {m['dd50']:.0%} ({m['dd50_acct']:.0%}) | "
                  f"COVID {ep(ho, '2020-02-19', '2020-03-23')*100:+5.1f}% 2022 {ep(df.r, '2022-01-01', '2022-12-31')*100:+5.1f}% "
                  f"Apr25 {ep(df.r, '2025-04-02', '2025-04-08')*100:+4.1f}% worst day {df.r.min()*100:5.1f}% month {worst_month(df.r)*100:5.1f}%")

    # ---------------- dollars at user size and 100k (EH-AT, night tier_hi, C2)
    P("\n== $ per year: delta EH-AT CAGR x capital (night tier_hi, C2) at $3k and $100k")
    for blab in PRIMARY:
        b0 = cagr(R[(blab, "tier_hi", "base")]["eh_at"])
        for lab in VARIANTS:
            d_ = cagr(R[(blab, "tier_hi", lab, "C2")]["eh_at"]) - b0
            P(f"  {blab:22s} {lab:8s} dEH-AT {d_*100:+5.2f}pp  ${d_*3000:+,.0f}/yr at $3k  ${d_*1e5:+,.0f}/yr at $100k")

    # ---------------- deflated Sharpe of the increments
    ntr = 546 + N_PRE + len(CONTROLS)
    P(f"\n== DSR of daily increments 2021-26 (C2, night 3bp), N = {ntr}")
    for blab in PRIMARY:
        base = R[(blab, 3.0, "base")]["df"].r
        for lab in VARIANTS:
            inc = R[(blab, 3.0, lab, "C2")]["df"].r - base
            d_ = PB.dsr(inc, n_trials=ntr)
            P(f"  {blab:22s} {lab:8s} SR {d_['sr_ann']:+.2f} t {d_['t']:+.2f} DSR {d_['dsr']:.3f}")

    # ---------------- whole shares at user size
    P("\n== whole shares, $3k + $1k/mo (basket only rounded; QQQ/SMH fractional as published), night 3bp, C2")
    for blab in PRIMARY:
        g, cap, conv = BASES[blab]
        capi = G.cfg(g, conv, 2)["noise_cap"]
        base = R[(blab, 3.0, "base")]["df"]
        for lab in ("S10r", "S10t"):
            N, kind, sh = VARIANTS[lab]
            m = basket_gross(X, members(L, N, kind))
            Y = X[m].assign(net=(X.gross - X.trades * X.C2 / 1e4)[m])
            cnt = Y.groupby("date").sym.transform("size")
            Y = Y.assign(w=1.0 / cnt)
            whole = {d: (gg.w.values, gg.lev.values, gg.net.values, gg.open_raw.values) for d, gg in Y.groupby("date")}
            dw, _ = replay(s, Ns[cap], g, cap, conv, 3.0, sh, None, trades=False, whole=whole)
            P(f"  {blab:22s} {lab:8s} whole-share fill {dw.attrs['fill']:.0%} of target; full {cell(dw.r)} "
              f"({(cagr(dw.r)-cagr(base.r))*100:+5.1f}pp vs base)")
    open(f"{SP}/stock_noise_out.txt", "w").write("\n".join(out) + "\n")
    pickle.dump({k: {kk: vv for kk, vv in v.items() if kk not in ("tr",)} for k, v in R.items()}, open(RES, "wb"))


if __name__ == "__main__":
    main()
