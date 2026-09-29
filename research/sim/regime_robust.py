"""Regime robustness: walk-forward refits, edge-decay detectors, drift monitor spec.

    # once, under the heavy lock (slices the SIP panel's daily returns for the dedupe):
    PYTHONPATH=. .venv/bin/python -m research.sim.regime_robust --extract
    PYTHONPATH=. .venv/bin/python -m research.sim.regime_robust          # ~10 min, caches legs

Pre-registered 2026-09-28 20:52 PDT (draft addendum "Pre-registration"), before any 2024-26
number was computed. Nothing here changes live trading.

Q1 walk-forward (expanding window, value for year Y chosen on data <= Y-1 by the highest Sharpe
   of the unit leg's daily return, 3bp night cost; ties within 0.02 -> shipped value). One
   parameter at a time, then all together. Grids (* = shipped):
     night depth     -0.06 -0.07 -0.08* -0.09 -0.10   (honest 15:50 pool, depth_cands)
     night IBS max    0.05 0.075 0.10*                 (pool built at < 0.10: only tighter)
     night vol20 min  0.40 0.50 0.60* 0.70 0.80
     night tilt k     0 0.125 0.25* 0.375 0.50
     ETF IBS max      0.10 0.15 0.20* 0.25 0.30
     ETF IBS top_k    2 3* 4 5 6
     noise lookback   7 10 14* 20 28                   (QQQ and SMH separately)
   Night trade years 2022-26, ETF legs 2018-26. Book: V7 via Sim.replay (3bp/tier/tier_hi) with
   the walk-forward legs stitched in, 2022-26, vs fixed; placebo = a random grid value per year
   (20 draws). Robust if |WF - fixed| <= 2pp/yr in both 2022-23 and 2024-26.
Q2 detectors per leg (night per-night, IBS per held day, noise QQQ/SMH per active session,
   conviction per trade, oversold V6 per trade):
     D1 CUSUM S = max(0, S + (mu0/2 - x)/sd0); warn h/2, alarm h; h from
        {2,3,4,6,8,10,12,16,20,25,30}, smallest with <= 1 false alarm / 5y on 500 21-block
        bootstraps of the intact fit span
     D2 rolling 60-event t vs mu0 < -c, c from {1.5,2,2.5,3,3.5}, same target
     K  live kill emulation (cumulative t < -1 and mean < 0 after 100/120/60/60 events)
   Fit 2021-23 (night) / 2016-20 (ETF legs, oversold); false alarms judged on the other span;
   delay when the edge -> 0 or halves after a random changepoint (200 taus on real data, and
   bootstrap paths with the change after 1y). Scenario "edge flips to -mu" added for K only
   (it cannot see 0 or half: it needs a losing mean).
   De-risk rule (pure function `derisk_step`) scored on the V7 book 2021-26: cost when nothing
   decayed, and loss saved when one leg's edge is removed from 2024-01-02.
Q3 calendar-year Sharpe per leg, OLS trend with Newey-West(21) t; noise 2016-21 vs 2022-26.
Q4 drift monitor spec (text in the addendum; `drift_report` is the reference function).
POST-HOC (added after seeing results, reported as such): WF with a mean-return criterion; a softer
de-risk (`derisk_soft`, 0.5 only while S >= h); noise QQQ trend inside 2022-26. The book-injection
test removes the POST-tau mean (2024-26 ran above average), a correction of a first draft.
Result: WF haircut -5.8pp/yr (3bp) .. -8.0 (tier_hi); de-risk rules dead; no leg decaying.
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
from . import growth as G
from . import oversold as OV
from . import roth as RO
from .validate import load_sim

SCR = Path(str(__import__("pathlib").Path(__file__).resolve().parents[2]) + "/data/research/program")
RCACHE = SCR / "cache_regime_robust.pkl"
LCACHE = SCR / "cache_regime_robust_legs.pkl"
CORR = 0.7
NIGHT_COST = 3.0          # bps per side, "measured" stand-in (addendum 29)

GRID = {
    "night_depth": ([-0.06, -0.07, -0.08, -0.09, -0.10], -0.08),
    "night_ibs": ([0.05, 0.075, 0.10], 0.10),
    "night_vol": ([0.40, 0.50, 0.60, 0.70, 0.80], 0.60),
    "tilt_k": ([0.0, 0.125, 0.25, 0.375, 0.50], 0.25),
    "ibs_max": ([0.10, 0.15, 0.20, 0.25, 0.30], 0.20),
    "ibs_topk": ([2, 3, 4, 5, 6], 3),
    "noise_lb_QQQ": ([7, 10, 14, 20, 28], 14),
    "noise_lb_SMH": ([7, 10, 14, 20, 28], 14),
}
NIGHT_KEYS = ("night_depth", "night_ibs", "night_vol", "tilt_k")
V7KW = {**G.V7, **G.cfg(1.0, 0.5, 2)}          # shipped V7, TQQQ at 75%: intraday cap 0.75
NCAP = V7KW["noise_cap"]


# ----------------------------------------------------------------- data
def extract():
    """Heavy (hold the lock): 20d dedupe returns for the depth pool's symbols."""
    from . import data as D
    x = pd.read_pickle(D.DATA / "depth_cands.pkl")
    R = D.returns20()
    cols = sorted(set(x.sym) & set(R.columns))
    pickle.dump(R.loc["2020-09-01":, cols].astype("float32"), open(RCACHE, "wb"))


def night_build(x: pd.DataFrame, R: pd.DataFrame, thresh=-0.08, ibs_max=0.10, vol_min=0.60) -> dict:
    """depth.night_days('plain') with the IBS and vol filters as parameters."""
    idx = {d: i for i, d in enumerate(R.index)}
    out = {}
    for d, g in x.groupby("date"):
        if d < B.START:
            continue
        rows = pd.DataFrame({"price": g.p50.values, "prev_close": g.pc.values,
                             "high": g.H50.values, "low": g.L50.values}, index=g.sym.values)
        keep = g.set_index("sym")
        p = sg.loser_picks(rows, day_ret_max=thresh, ibs_max=ibs_max, price_min=5.0, price_max=2000.0)
        if p.empty:
            continue
        i = idx.get(pd.Timestamp(d))
        win = R.iloc[max(0, i - 20):i] if i is not None else None
        if win is not None:
            p, _ = sg.dedupe_correlated(p, {s: win[s].dropna().tolist() for s in p.index if s in win.columns}, CORR)
        p = p.assign(vol20=keep.loc[p.index, "vol20"].values)
        n_raw = len(p)
        k, frac = sg.night_sizing(p, vol_min=vol_min, crowd_n=30, max_name_pct=0.10)
        if k.empty:
            continue
        kk = keep.loc[k.index]
        out[pd.Timestamp(d)] = B.NightDay(k.index.values, k.price.values, kk.C.values, kk.ret.values,
                                          kk.adv.values, kk.vol20.values, kk.ret20.values,
                                          k.day_ret.values, frac, n_raw)
    return out


def gaps(s) -> dict:
    ix = s.C.index
    return {a: (b - a).days for a, b in zip(ix[:-1], ix[1:])}


def night_unit(N: dict, gp: dict, k=0.25, cost=NIGHT_COST, per_name=False):
    """Unit night leg (its own capital, fractional), live tilt, weekend half size."""
    out, names = {}, []
    for d, nd in N.items():
        kk = getattr(nd, "k", k)
        w = sg.night_tilt(nd.vol20, nd.day_ret, kk) if kk else np.ones(len(nd.syms))
        per = nd.frac * w * (0.5 if gp.get(d, 1) > 1 else 1.0)
        c = B.cost_bps(cost, nd.price, nd.adv)
        net = nd.ret - 2 * c / 1e4
        out[d] = float((per * net).sum())
        if per_name:
            names += [(d, x) for x in net]
    s = pd.Series(out).sort_index()
    return (s, pd.DataFrame(names, columns=["date", "ret"])) if per_name else s


def ibs_unit(I: dict, bil: pd.Series, days) -> pd.Series:
    out = {}
    for d in days:
        L = I.get(d)
        if L:
            out[d] = float(np.mean([r for _, _, r in L])) - 2 * 1.0 / 1e4
        else:
            b = bil.get(d, 0.0); out[d] = float(b) if np.isfinite(b) else 0.0
    return pd.Series(out)


def noise_unit(z: pd.DataFrame) -> pd.Series:
    return z.lev.clip(upper=NCAP) * z.ret


def sharpe(r: pd.Series) -> float:
    r = r.dropna()
    return float(r.mean() / r.std() * np.sqrt(252)) if len(r) > 20 and r.std() > 0 else np.nan


def ann(r: pd.Series) -> float:
    r = r.fillna(0)
    return float((1 + r).prod() ** (252 / max(len(r), 1)) - 1) if len(r) else np.nan


# ------------------------------------------------------------ build legs
def build_legs(s):
    if LCACHE.exists():
        return pickle.load(open(LCACHE, "rb"))
    x = pd.read_pickle(B.D.DATA / "depth_cands.pkl")
    R = pickle.load(open(RCACHE, "rb"))
    L = {"night_depth": {}, "night_ibs": {}, "night_vol": {}, "ibs_max": {}, "ibs_topk": {},
         "noise_lb_QQQ": {}, "noise_lb_SMH": {}}
    base = night_build(x, R)
    for key, (grid, ship) in GRID.items():
        for v in grid:
            if key == "tilt_k":
                continue
            if v == ship and key.startswith("night"):
                L[key][v] = base; continue
            print(f"  build {key}={v}", flush=True)
            if key == "night_depth":
                L[key][v] = night_build(x, R, thresh=v)
            elif key == "night_ibs":
                L[key][v] = night_build(x, R, ibs_max=v)
            elif key == "night_vol":
                L[key][v] = night_build(x, R, vol_min=v)
            elif key == "ibs_max":
                L[key][v] = s.I if v == ship else B.ibs_days(top_k=3, ibs_max=v)
            elif key == "ibs_topk":
                L[key][v] = s.I if v == ship else B.ibs_days(top_k=v, ibs_max=0.2)
            else:
                sym = key[-3:]
                L[key][v] = s.NZ[sym] if v == ship else B.noise_days(sym, lookback=v, cost=0.5)
    L["BO"] = B.breakout_days()
    sig = OV.honest_1540(s)
    L["OV"] = OV.schedule_ovn(s, sig)
    pickle.dump(L, open(LCACHE, "wb"))
    return L


def unit_series(key, v, L, s, gp, days_etf):
    if key == "tilt_k":
        return night_unit(L["night_depth"][-0.08], gp, k=v)
    if key.startswith("night"):
        return night_unit(L[key][v], gp)
    if key.startswith("ibs"):
        return ibs_unit(L[key][v], s.bil, days_etf)
    return noise_unit(L[key][v])


# -------------------------------------------------------------- Q1 walk-forward
def wf_select(r_by_v: dict, ship, years, crit="sharpe") -> dict:
    """year -> value chosen on all data before that year (max Sharpe, ties -> shipped).
    crit="mean" (POST-HOC sensitivity): highest mean daily return, ties within 2% -> shipped."""
    sel = {}
    for y in years:
        f = sharpe if crit == "sharpe" else (lambda r: float(r.mean()) * 252)
        sc = {v: f(r[r.index.year < y]) for v, r in r_by_v.items()}
        best = max(sc, key=lambda v: -np.inf if not np.isfinite(sc[v]) else sc[v])
        tol = 0.02 if crit == "sharpe" else 0.02 * abs(sc.get(ship, 0.0))
        sel[y] = ship if sc[best] - sc.get(ship, -np.inf) <= tol else best
    return sel


def stitch(series_by_v: dict, sel: dict) -> pd.Series:
    parts = [series_by_v[v][series_by_v[v].index.year == y] for y, v in sel.items()]
    return pd.concat(parts).sort_index()


def stitch_dict(d_by_v: dict, sel: dict, ship) -> dict:
    """day dicts (N, I) or DataFrames (NZ): years before the WF start use shipped."""
    first = min(sel)
    if isinstance(d_by_v[ship], pd.DataFrame):
        parts = [d_by_v[ship][d_by_v[ship].index.year < first]] + \
                [d_by_v[v][d_by_v[v].index.year == y] for y, v in sel.items()]
        return pd.concat(parts).sort_index()
    out = {d: x for d, x in d_by_v[ship].items() if d.year < first}
    for y, v in sel.items():
        out.update({d: x for d, x in d_by_v[v].items() if d.year == y})
    return out


def make_sim(s, L, sel_all: dict):
    """A Sim copy with the per-year walk-forward selections in place (missing key = shipped).
    Returns (sim, tilt) for Params."""
    sim = copy.copy(s)
    sim.BO = L["BO"]
    N = dict(L["night_depth"][-0.08])
    nk = ("night_depth", "night_ibs", "night_vol")
    years = sorted({y for k in nk if k in sel_all for y in sel_all[k]})
    for y in years:
        combo = {k: sel_all.get(k, {}).get(y, GRID[k][1]) for k in nk}
        moved = [k for k in nk if combo[k] != GRID[k][1]]
        if not moved:
            continue
        src = L[moved[0]][combo[moved[0]]] if len(moved) == 1 else sim_joint_night(L, combo)
        for d in [d for d in N if d.year == y]:
            del N[d]
        N.update({d: nd for d, nd in src.items() if d.year == y})
    tilt = "live"
    if "tilt_k" in sel_all:
        N2 = {}
        for d, nd in N.items():
            nd = copy.copy(nd); nd.k = sel_all["tilt_k"].get(d.year, 0.25); N2[d] = nd
        N = N2
        tilt = _tilt_k
    sim.N = N
    I = dict(s.I)
    ys = sorted({y for k in ("ibs_max", "ibs_topk") if k in sel_all for y in sel_all[k]})
    for y in ys:
        vm = sel_all.get("ibs_max", {}).get(y, 0.2)
        vk = sel_all.get("ibs_topk", {}).get(y, 3)
        if vm != 0.2 and vk != 3:
            raise ValueError("joint IBS values need a joint build")
        src = L["ibs_max"][vm] if vm != 0.2 else (L["ibs_topk"][vk] if vk != 3 else None)
        if src is None:
            continue
        for d in [d for d in I if d.year == y]:
            del I[d]
        I.update({d: x for d, x in src.items() if d.year == y})
    sim.I = I
    NZ = dict(s.NZ)
    for sym in ("QQQ", "SMH"):
        k = f"noise_lb_{sym}"
        if k in sel_all:
            NZ[sym] = stitch_dict(L[k], sel_all[k], 14)
    sim.NZ = NZ
    return sim, tilt


def _tilt_k(nd):
    return sg.night_tilt(nd.vol20, nd.day_ret, nd.k) if nd.k else np.ones(len(nd.syms))


def book_with(s, L, sel_all: dict, cost, dates):
    sim, tilt = make_sim(s, L, sel_all)
    return sim.replay(B.Params(**{**V7KW, "tilt": tilt, "night_cost": cost}), dates=dates)


_JOINT = {}


def sim_joint_night(L, combo):
    key = tuple(sorted(combo.items()))
    if key not in _JOINT:
        x = pd.read_pickle(B.D.DATA / "depth_cands.pkl")
        R = pickle.load(open(RCACHE, "rb"))
        _JOINT[key] = night_build(x, R, thresh=combo["night_depth"], ibs_max=combo["night_ibs"],
                                  vol_min=combo["night_vol"])
    return _JOINT[key]


def halves(r: pd.Series):
    return (B.stats(r["2022-01-01":"2023-12-31"]), B.stats(r["2024-01-01":]))


def fmt3(r):
    a, b = halves(r); f = B.stats(r["2022-01-01":])
    return f"{a[0]*100:6.1f}/{a[1]:4.2f}  {b[0]*100:6.1f}/{b[1]:4.2f}  {f[0]*100:6.1f}/{f[1]:4.2f}/{f[2]*100:4.0f}"


# ------------------------------------------------------------ Q2 detectors
def cusum_path(x: np.ndarray, mu0, sd0, h, reset=True):
    """Alarm indices of S = max(0, S + (mu0/2 - x)/sd0) crossing h (reset to 0 after)."""
    S, al = 0.0, []
    inc = (mu0 / 2 - x) / sd0
    for i, z in enumerate(inc):
        S = max(0.0, S + z)
        if S >= h:
            al.append(i)
            if reset:
                S = 0.0
    return al


def roll_t_path(x: np.ndarray, mu0, c, n=60):
    if len(x) < n:
        return []
    cs, cs2 = np.r_[0, np.cumsum(x)], np.r_[0, np.cumsum(x * x)]
    m = (cs[n:] - cs[:-n]) / n
    v = np.maximum((cs2[n:] - cs2[:-n]) / n - m * m, 1e-18) * n / (n - 1)
    t = (m - mu0) / np.sqrt(v / n)
    al, last = [], -10 ** 9
    for j in np.where(t < -c)[0]:
        if j - last >= n:                      # one alarm per non-overlapping window
            al.append(j + n - 1); last = j
    return al


def kill_path(x: np.ndarray, n_min):
    cs, cs2 = np.cumsum(x), np.cumsum(x * x)
    k = np.arange(1, len(x) + 1)
    m = cs / k
    v = np.maximum(cs2 / k - m * m, 1e-18) * k / np.maximum(k - 1, 1)
    t = m / np.sqrt(v / k)
    hit = np.where((k >= n_min) & (m < 0) & (t < -1.0))[0]
    return [int(hit[0])] if len(hit) else []


def boot(x: np.ndarray, n_events: int, rng, block=21) -> np.ndarray:
    nb = int(np.ceil(n_events / block))
    st = rng.integers(0, max(1, len(x) - block), nb)
    return x[(st[:, None] + np.arange(block)[None]).ravel()][:n_events]


H_GRID = [2, 3, 4, 6, 8, 10, 12, 16, 20, 25, 30]
C_GRID = [1.5, 2.0, 2.5, 3.0, 3.5]


def calibrate(x_fit, per_year, rng, n_paths=500):
    """h (CUSUM) and c (rolling t) with mean false alarms per 5y <= 1 on intact bootstraps."""
    mu0, sd0 = float(x_fit.mean()), float(x_fit.std())
    n5 = int(5 * per_year)
    paths = [boot(x_fit, n5, rng) for _ in range(n_paths)]
    h = next((h for h in H_GRID if np.mean([len(cusum_path(p, mu0, sd0, h)) for p in paths]) <= 1.0), H_GRID[-1])
    c = next((c for c in C_GRID if np.mean([len(roll_t_path(p, mu0, c)) for p in paths]) <= 1.0), C_GRID[-1])
    pa_h = np.mean([len(cusum_path(p, mu0, sd0, h)) > 0 for p in paths])
    pa_c = np.mean([len(roll_t_path(p, mu0, c)) > 0 for p in paths])
    return dict(mu0=mu0, sd0=sd0, h=h, c=c, pany_h=pa_h, pany_c=pa_c)


def delays(x_all, cal, per_year, n_kill, rng, shift_frac, n=200, mode="real"):
    """Years from the changepoint to the first alarm (inf = never within the data/path).
    shift_frac: fraction of the TRUE mean removed after tau (1 = edge 0, 0.5 = halved, 2 = flips)."""
    mu = float(x_all.mean())
    out = {"cusum": [], "rollt": [], "kill": []}
    for _ in range(n):
        if mode == "real":
            tau = int(rng.integers(int(0.1 * len(x_all)), int(0.7 * len(x_all))))
            x = x_all.copy()
        else:                                   # 1y intact then 5y decayed, bootstrapped
            tau = int(per_year)
            x = boot(x_all, int(6 * per_year), rng)
        x[tau:] = x[tau:] - shift_frac * mu
        for name, al in (("cusum", cusum_path(x, cal["mu0"], cal["sd0"], cal["h"])),
                         ("rollt", roll_t_path(x, cal["mu0"], cal["c"])),
                         ("kill", kill_path(x, n_kill))):
            aft = [a for a in al if a >= tau]
            out[name].append((aft[0] - tau) / per_year if aft else np.inf)
    return {k: np.array(v) for k, v in out.items()}


def dstat(a):
    fin = np.isfinite(a)
    med = np.median(a) if fin.mean() >= 0.5 else np.inf
    return f"med {med:4.2f}y  P(<1y) {np.mean(a < 1):4.0%}  never {1 - fin.mean():4.0%}"


# -------------------------------------------------------- the de-risk rule
DERISK_DEFAULT = dict(mu0=0.0, sd0=1.0, h=10.0)


def derisk_step(state: dict | None, x: float, prm: dict) -> tuple[dict, float]:
    """PURE de-risk rule, one leg, one event.

    inputs  state  {"S": float, "latched": bool, "prob": int} or None (fresh)
            x      the leg's newest event return (net, the same unit the backtest used:
                   night = unit-leg return of one night; IBS = one held day; noise = one
                   active session, unlevered; conviction / oversold = one trade). While the
                   leg is scaled to 0 the event is its SHADOW (paper) return.
            prm    {"mu0", "sd0", "h", "n_prob"}: backtest mean/sd per event, calibrated alarm
                   level, probation length (events)
    output  (new state, scale for the NEXT event: 1.0 | 0.5 | 0.0)
    rule    S = max(0, S + (mu0/2 - x)/sd0)  (one-sided CUSUM: evidence the mean is below mu0/2)
            not latched: scale 1.0 if S < h/2, 0.5 if h/2 <= S < h; S >= h -> latched, scale 0
            latched: S is capped at h; the leg trades in shadow; when S returns to 0 (the shadow
                   P&L earned back h sd-units above mu0/2) -> unlatched, probation: 0.5 for
                   n_prob events, then the normal rule
            never overrides signals.kill_check / HALT_DRAWDOWN (a killed leg stays killed)."""
    st = dict(state or {"S": 0.0, "latched": False, "prob": 0})
    h = prm["h"]
    st["S"] = max(0.0, st["S"] + (prm["mu0"] / 2 - x) / prm["sd0"])
    if st["latched"]:
        st["S"] = min(st["S"], h)
        if st["S"] <= 0.0:
            st["latched"], st["prob"] = False, int(prm.get("n_prob", 60))
            return st, 0.5
        return st, 0.0
    if st["S"] >= h:
        st["latched"] = True
        return st, 0.0
    if st["prob"] > 0:
        st["prob"] -= 1
        return st, 0.5
    return st, (1.0 if st["S"] < h / 2 else 0.5)


def derisk_soft(state: dict | None, x: float, prm: dict) -> tuple[dict, float]:
    """POST-HOC softer variant: same CUSUM, no warning level, no latch: 0.5 while S >= h."""
    st = dict(state or {"S": 0.0})
    st["S"] = max(0.0, st["S"] + (prm["mu0"] / 2 - x) / prm["sd0"])
    return st, (0.5 if st["S"] >= prm["h"] else 1.0)


def scale_series(ev: pd.Series, prm: dict, index, rule=None) -> pd.Series:
    """Scale in force on each date (decided from events strictly before it)."""
    st, sc, out = None, 1.0, {}
    evd = ev.to_dict()
    for d in index:
        out[d] = sc
        if d in evd:
            st, sc = (rule or derisk_step)(st, evd[d], prm)
    return pd.Series(out)


# ------------------------------------------------------------ Q3 trend
def nw_t(y: np.ndarray, X: np.ndarray, lags=21):
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    e = y - X @ beta
    XtX_inv = np.linalg.inv(X.T @ X)
    u = X * e[:, None]
    Sm = u.T @ u
    for L_ in range(1, lags + 1):
        w = 1 - L_ / (lags + 1)
        g = u[L_:].T @ u[:-L_]
        Sm += w * (g + g.T)
    V = XtX_inv @ Sm @ XtX_inv
    return beta, beta / np.sqrt(np.diag(V))


# ------------------------------------------------------------ Q4 drift
def drift_report(live: list[dict], backtest: dict) -> pd.DataFrame:
    """Reference for the review's drift section. live: closed round trips
    ({leg, sym, entry_date, ret}); backtest: {(leg, entry_date, sym): ret} replayed by this
    simulator for the SAME dates and names. Returns per leg: n paired, mean live, mean
    backtest, mean paired gap (bp) with its t, share of live trades with no backtest twin."""
    rows = []
    for leg in sorted({c.get("leg") for c in live}):
        L_ = [c for c in live if c.get("leg") == leg and not c.get("note")]
        pr = [(c["ret"], backtest[(leg, c["entry_date"], c["sym"])]) for c in L_
              if (leg, c["entry_date"], c["sym"]) in backtest]
        if not pr:
            rows.append((leg, 0, np.nan, np.nan, np.nan, np.nan, 1.0)); continue
        a = np.array(pr); g = a[:, 0] - a[:, 1]
        t = g.mean() / (g.std(ddof=1) / np.sqrt(len(g))) if len(g) > 2 and g.std() > 0 else np.nan
        rows.append((leg, len(g), a[:, 0].mean() * 1e4, a[:, 1].mean() * 1e4, g.mean() * 1e4, t,
                     1 - len(pr) / len(L_)))
    return pd.DataFrame(rows, columns=["leg", "n", "live_bp", "bt_bp", "gap_bp", "gap_t", "unmatched"])


# ------------------------------------------------------------------ main
def main():
    s = load_sim()
    gp = gaps(s)
    L = build_legs(s)
    days_etf = s.C.index[(s.C.index >= "2017-01-01") & (s.C.index <= B.END)]
    print("legs ready", flush=True)

    # ---------------------------------------------------------------- Q1
    print("\n== Q1. walk-forward refits: chosen value per year (fit = expanding, max Sharpe)")
    U, SEL = {}, {}
    for key, (grid, ship) in GRID.items():
        U[key] = {v: unit_series(key, v, L, s, gp, days_etf) for v in grid}
        yrs = list(range(2022, 2027)) if key in NIGHT_KEYS else list(range(2018, 2027))
        SEL[key] = wf_select(U[key], ship, yrs)
        wf, fx = stitch(U[key], SEL[key]), U[key][ship]
        fx = fx[fx.index.year >= yrs[0]]
        per = " ".join(f"{y % 100:02d}:{v}" for y, v in SEL[key].items())
        full = " ".join(f"{v}:{sharpe(r):.2f}" for v, r in U[key].items())
        print(f"  {key:13s} [{per}]\n    leg WF {ann(wf)*100:6.1f}%/{sharpe(wf):4.2f}  fixed {ann(fx)*100:6.1f}%/"
              f"{sharpe(fx):4.2f}  diff {(ann(wf)-ann(fx))*100:+5.1f}pp/yr   full-sample Sharpe by value: {full}")
        if key in ("ibs_max", "ibs_topk", "noise_lb_QQQ", "noise_lb_SMH"):
            for a, b in (("2018", "2020"), ("2021", "2023"), ("2024", "2026")):
                print(f"      {a}-{b}: WF {ann(wf[a:b])*100:6.1f}/{sharpe(wf[a:b]):4.2f}  fixed "
                      f"{ann(fx[a:b])*100:6.1f}/{sharpe(fx[a:b]):4.2f}")
    dates = s.days[s.days >= "2022-01-01"]
    print(f"\n-- V7 book 2022-26 with walk-forward legs  {'2022-23':>11s}  {'2024-26':>11s}  {'2022-26 CAGR/Sh/DD':>18s}")
    BK = {}
    for cost in (3.0, "tier", "tier_hi"):
        BK[(cost, "fixed")] = book_with(s, L, {}, cost, dates)
        print(f"  {'fixed (shipped)':30s} {str(cost):>7s} {fmt3(BK[(cost, 'fixed')]['r'])}")
        for key in GRID:
            sel = {key: {y: v for y, v in SEL[key].items() if y >= 2022}}
            BK[(cost, key)] = book_with(s, L, sel, cost, dates)
            print(f"  {'WF ' + key:30s} {str(cost):>7s} {fmt3(BK[(cost, key)]['r'])}")
        joint = {k: {y: v for y, v in SEL[k].items() if y >= 2022} for k in GRID}
        # the IBS pair is refit one-at-a-time: if both moved in the same year keep top_k shipped
        for y in joint["ibs_max"]:
            if joint["ibs_max"][y] != 0.2 and joint["ibs_topk"][y] != 3:
                joint["ibs_topk"][y] = 3
        BK[(cost, "joint")] = book_with(s, L, joint, cost, dates)
        print(f"  {'WF all parameters (joint)':30s} {str(cost):>7s} {fmt3(BK[(cost, 'joint')]['r'])}")
    # placebo: random grid value per year for every parameter (20 draws), 3bp
    rng = np.random.default_rng(11)
    pl = []
    for i in range(20):
        sel = {k: {y: GRID[k][0][rng.integers(len(GRID[k][0]))] for y in range(2022, 2027)} for k in GRID}
        for y in sel["ibs_max"]:
            if sel["ibs_max"][y] != 0.2 and sel["ibs_topk"][y] != 3:
                sel["ibs_topk"][y] = 3
        r = book_with(s, L, sel, 3.0, dates)["r"]
        pl.append((B.stats(r["2022":"2023"])[0], B.stats(r["2024":])[0], B.stats(r)[0], B.stats(r)[1]))
    pl = np.array(pl)
    print(f"  {'placebo: random value/yr (20)':30s} {'3.0':>7s} {pl[:,0].mean()*100:6.1f}       "
          f"{pl[:,1].mean()*100:6.1f}       {pl[:,2].mean()*100:6.1f}/{pl[:,3].mean():4.2f}   "
          f"(range full {pl[:,2].min()*100:.1f}..{pl[:,2].max()*100:.1f})")
    # Roth b1 (IBS + night 1.0x + intraday 1.5x via 3x ETFs on the night cash), fixed vs joint WF
    roth_rows = {}
    for lab, sel in (("fixed", {}), ("WF joint", joint)):
        for cost in (3.0, "tier_hi"):
            sim, tilt = make_sim(s, L, sel)
            base = dict(tilt=tilt, weekend_scale=0.5, noise_on=False, conviction_w=0.0, margin_rate=0.0)
            r = RO.replay(sim, dates, B.Params(night_cost=cost, **base), budget="night", noise_cap=1.5)["r"]
            roth_rows[(lab, cost)] = r
            print(f"  Roth b1 {lab:10s} {str(cost):>7s} {fmt3(r)}")

    # ---------------------------------------------------------------- Q2
    print("\n== Q2. edge-decay detectors (fit span -> calibrate; other span -> false alarms)")
    nightN = L["night_depth"][-0.08]
    ev = {}
    nu, nn = night_unit(nightN, gp, per_name=True)
    ev["night"] = nu
    ev["ibs"] = pd.Series({d: float(np.mean([r for _, _, r in l])) - 2e-4 for d, l in s.I.items() if l}).sort_index()
    for sym in ("QQQ", "SMH"):
        z = s.NZ[sym]; ev[f"noise_{sym}"] = z.ret[z.trades > 0]
    ev["conv"] = L["BO"].sort_index()
    ev["oversold"] = pd.Series({d: float(np.mean([r for _, r in cur.values()])) - 2e-4
                                for d, cur in L["OV"].items()}).sort_index()
    nkill = {"night": 100, "ibs": 60, "noise_QQQ": 120, "noise_SMH": 120, "conv": 60, "oversold": 60}
    spans = {"night": (("2020-11-01", "2023-12-31"), ("2024-01-01", "2026-12-31"))}
    for k in ev:
        if k != "night":
            spans[k] = (("2016-01-01", "2020-12-31"), ("2021-01-01", "2026-12-31"))
    CAL = {}
    rng = np.random.default_rng(5)
    for k, x in ev.items():
        (fa, fb), (oa, ob) = spans[k]
        xf, xo = x[fa:fb].values, x[oa:ob].values
        py = len(x) / ((x.index[-1] - x.index[0]).days / 365.25)
        cal = calibrate(xf, py, rng)
        CAL[k] = {**cal, "per_year": py}
        mu_o = xo.mean()
        fo_h = len(cusum_path(xo, cal["mu0"], cal["sd0"], cal["h"])) / (len(xo) / py) * 5
        fo_c = len(roll_t_path(xo, cal["mu0"], cal["c"])) / (len(xo) / py) * 5
        # the reverse: calibrate on the later span, judge the earlier
        calr = calibrate(xo, py, rng)
        fr_h = len(cusum_path(xf, calr["mu0"], calr["sd0"], calr["h"])) / (len(xf) / py) * 5
        full_mu, full_t = x.mean(), x.mean() / (x.std() / np.sqrt(len(x)))
        print(f"  {k:10s} {py:5.0f} ev/yr  fit mu {cal['mu0']*1e4:+6.1f}bp sd {cal['sd0']*1e4:6.1f}bp "
              f"(t/event {cal['mu0']/cal['sd0']:.3f})  OOS mu {mu_o*1e4:+6.1f}bp  full t {full_t:4.1f}\n"
              f"      CUSUM h={cal['h']:<3} P(any FA/5y) {cal['pany_h']:.0%}  OOS FA/5y {fo_h:4.1f} "
              f"(reverse-fit h={calr['h']}: {fr_h:4.1f})   rolling-60 t c={cal['c']}: P(any) "
              f"{cal['pany_c']:.0%}  OOS FA/5y {fo_c:4.1f}")
    print("\n-- detection delay after a changepoint (years; real data 200 taus | bootstrap 1y intact + 5y decayed)")
    DEL = {}
    for k, x in ev.items():
        for frac, lab in ((1.0, "edge->0"), (0.5, "halved"), (2.0, "flips -mu")):
            a = delays(x.values, CAL[k], CAL[k]["per_year"], nkill[k], rng, frac, mode="real")
            b = delays(x.values, CAL[k], CAL[k]["per_year"], nkill[k], rng, frac, n=200, mode="boot")
            DEL[(k, lab)] = (a, b)
            print(f"  {k:10s} {lab:9s} CUSUM {dstat(a['cusum'])} | {dstat(b['cusum'])}\n"
                  f"  {'':20s} roll-t {dstat(a['rollt'])} | {dstat(b['rollt'])}\n"
                  f"  {'':20s} KILL   {dstat(a['kill'])} | {dstat(b['kill'])}")
    # live kill as coded: per-NAME night round trips (not day-clustered)
    tn = nn.ret.values
    print(f"\n  night per-name trades: {len(tn)} ({len(tn)/5.8:.0f}/yr), mean {tn.mean()*1e4:+.1f}bp, "
          f"naive t {tn.mean()/(tn.std()/np.sqrt(len(tn))):.1f} vs day-clustered t "
          f"{nu.mean()/(nu.std()/np.sqrt(len(nu))):.1f}")

    # ------------------------------------------------ de-risk rule on the V7 book
    print("\n== Q2b. de-risk rule (derisk_step, CUSUM params from the fit span, n_prob 60) on V7 2021-26")
    s7 = copy.copy(s); s7.N = nightN; s7.BO = L["BO"]
    for cost, rule, rlab in ((3.0, derisk_step, "pre-reg"), ("tier_hi", derisk_step, "pre-reg"),
                             (3.0, derisk_soft, "POST-HOC soft"), ("tier_hi", derisk_soft, "POST-HOC soft")):
        df = s7.replay(B.Params(**{**V7KW, "night_cost": cost}))
        contrib = leg_contrib(s7, df)
        evc = {"night": night_unit(nightN, gp, cost=cost), "ibs": ev["ibs"], "noise_QQQ": ev["noise_QQQ"],
               "noise_SMH": ev["noise_SMH"], "conv": ev["conv"]}
        CALc = dict(CAL)
        if cost != NIGHT_COST:        # the backtest mean the live leg is judged against is at ITS cost
            xn = evc["night"]["2020-11-01":"2023-12-31"].values
            CALc["night"] = {**calibrate(xn, CAL["night"]["per_year"], np.random.default_rng(5)),
                             "per_year": CAL["night"]["per_year"]}
        sc = {k: scale_series(evc[k], {**CALc[k], "n_prob": 60}, df.index, rule) for k in evc}
        adj = df.r - sum((1 - sc[k]) * contrib[k] for k in evc)
        frac_off = {k: float((sc[k] < 1).mean()) for k in sc}
        print(f"  {str(cost):7s} V7        {fmt_full(df.r)}\n  {rlab[:7]:7s} +de-risk  {fmt_full(adj)}   "
              f"days below 1.0: " + " ".join(f"{k} {v:.0%}" for k, v in frac_off.items()))
        e0, e1 = B.stats(G.eh(df)), B.stats(G.eh(df) - (df.r - adj))
        m0, m1 = G.mc(G.eh(df), 3000, 1000), G.mc(G.eh(df) - (df.r - adj), 3000, 1000)
        l0, l1 = G.mc(G.eh(df), 10000, 0), G.mc(G.eh(df) - (df.r - adj), 10000, 0)
        print(f"  {'':7s} EH V7 {e0[0]*100:5.1f}/{e0[1]:4.2f}/{e0[2]*100:4.0f}  EH +de-risk "
              f"{e1[0]*100:5.1f}/{e1[1]:4.2f}/{e1[2]*100:4.0f}   MC $3k+1k: med ${m0['med']:,.0f} -> "
              f"${m1['med']:,.0f}, P(DD>30) {m0['dd30']:.0%} -> {m1['dd30']:.0%}, P(DD>50) {m0['dd50']:.0%} -> "
              f"{m1['dd50']:.0%};  $10k: med ${l0['med']:,.0f} -> ${l1['med']:,.0f}")
        for a, b, nm in (("2022-01-03", "2022-10-12", "2022 bear"), ("2025-04-02", "2025-04-08", "Apr 2025")):
            print(f"  {'':7s} {nm}: V7 {((1+df.r[a:b]).prod()-1)*100:+5.1f}%  +de-risk "
                  f"{((1+adj[a:b]).prod()-1)*100:+5.1f}%")
        print(f"  {'':7s} worst day {df.r.min()*100:.1f}% -> {adj.min()*100:.1f}%, worst month "
              f"{G.monthly_worst(df.r)*100:.1f}% -> {G.monthly_worst(adj)*100:.1f}%")
        # injected decay: one leg's edge removed from 2024-01-02
        tau = pd.Timestamp("2024-01-02")
        for k in evc:
            # edge exactly 0 after tau: remove the POST-tau mean (2024-26 ran above the average)
            post = contrib[k][tau:]; act = post != 0
            mu_c = post[act].mean() if act.any() else 0.0
            dec_c = contrib[k].where(contrib[k].index < tau, contrib[k] - mu_c * (contrib[k] != 0))
            ev_k = evc[k].where(evc[k].index < tau, evc[k] - evc[k][tau:].mean())
            r_dec = df.r - contrib[k] + dec_c
            sck = scale_series(ev_k, {**CALc[k], "n_prob": 60}, df.index, rule)
            r_der = r_dec - (1 - sck) * dec_c
            first = sck[(sck.index >= tau) & (sck < 1)]
            print(f"  {'':7s} {k:9s} edge->0 from 2024: 2024-26 CAGR {B.stats(r_dec[tau:])[0]*100:5.1f}% -> "
                  f"de-risk {B.stats(r_der[tau:])[0]*100:5.1f}%  (first de-risk "
                  f"{first.index[0].date() if len(first) else 'never'}; off {float((sck[tau:] == 0).mean()):.0%} of days)")

    # ---------------------------------------------------------------- Q3
    print("\n== Q3. is any leg decaying? calendar-year Sharpe (unit leg), NW(21) trend t on daily returns")
    legs_d = {"night": night_unit(nightN, gp), "ibs": ibs_unit(s.I, s.bil, days_etf),
              "noise_QQQ": noise_unit(s.NZ["QQQ"]), "noise_SMH": noise_unit(s.NZ["SMH"]),
              "conv": L["BO"].reindex(s.C.index[s.C.index >= "2016-02-01"]).fillna(0.0),
              "oversold": ev["oversold"].reindex(s.C.index[s.C.index >= "2017-01-01"]).fillna(0.0)}
    yrs = list(range(2016, 2027))
    print(f"  {'leg':10s} " + " ".join(f"{y:>6d}" for y in yrs) + "   slope/yr(bp/day)  NW t   pre/post-2022 diff bp/day (NW t)")
    for k, r in legs_d.items():
        r = r[r.index <= B.END].dropna()
        ys = " ".join(f"{sharpe(r[str(y)]):6.2f}" if (r.index.year == y).sum() > 60 else f"{'':>6s}" for y in yrs)
        tt = (r.index - r.index[0]).days.values / 365.25
        b, t = nw_t(r.values, np.column_stack([np.ones(len(r)), tt]))
        post = (r.index >= "2022-01-01").astype(float)
        b2, t2 = nw_t(r.values, np.column_stack([np.ones(len(r)), post])) if 0 < post.mean() < 1 else ([0, 0], [0, 0])
        print(f"  {k:10s} {ys}   {b[1]*1e4:+7.2f}  {t[1]:+5.2f}   {b2[1]*1e4:+7.2f} ({t2[1]:+5.2f})")
    # POST-HOC: the Sharpe criterion is blind to filters that change how much capital deploys
    print("\n== Q1-posthoc. walk-forward with a MEAN-return criterion (not pre-registered)")
    SELm = {}
    for key, (grid, ship) in GRID.items():
        yrs = list(range(2022, 2027)) if key in NIGHT_KEYS else list(range(2018, 2027))
        SELm[key] = wf_select(U[key], ship, yrs, crit="mean")
        print(f"  {key:13s} [" + " ".join(f"{y % 100:02d}:{v}" for y, v in SELm[key].items()) + "]")
    jm = {k: {y: v for y, v in SELm[k].items() if y >= 2022} for k in GRID}
    for y in jm["ibs_max"]:
        if jm["ibs_max"][y] != 0.2 and jm["ibs_topk"][y] != 3:
            jm["ibs_topk"][y] = 3
    for cost in (3.0, "tier_hi"):
        print(f"  {'fixed (shipped)':30s} {str(cost):>7s} {fmt3(BK[(cost, 'fixed')]['r'])}")
        for key in ("night_ibs", "tilt_k"):
            r = book_with(s, L, {key: jm[key]}, cost, dates)["r"]
            print(f"  {'WF-mean ' + key:30s} {str(cost):>7s} {fmt3(r)}")
        r = book_with(s, L, jm, cost, dates)["r"]
        print(f"  {'WF-mean all (joint)':30s} {str(cost):>7s} {fmt3(r)}")
    # POST-HOC descriptive: noise QQQ inside the 0DTE era only
    r = noise_unit(s.NZ["QQQ"])["2022-01-01":B.END]
    tt = (r.index - r.index[0]).days.values / 365.25
    b, t_ = nw_t(r.values, np.column_stack([np.ones(len(r)), tt]))
    print(f"\n  noise_QQQ 2022-26 only: trend {b[1]*1e4:+.2f}bp/day per yr, NW t {t_[1]:+.2f}; "
          f"2021-23 Sharpe {sharpe(noise_unit(s.NZ['QQQ'])['2021':'2023']):.2f}, 2024-26 "
          f"{sharpe(noise_unit(s.NZ['QQQ'])['2024':'2026']):.2f}")
    pickle.dump(dict(SEL=SEL, SELm=SELm, CAL=CAL), open(SCR / "cache_regime_robust_out.pkl", "wb"))


def leg_contrib(s7, df) -> dict:
    """Per-leg daily contribution (fraction of equity) inside the V7 replay."""
    out = {"night": df.r_night, "ibs": df.r_ibs}
    tot = pd.Series(0.0, index=df.index)
    for sym, share in G.S2.items():
        z = s7.NZ[sym]
        c = (z.lev.clip(upper=NCAP) * share * z.ret).reindex(df.index).fillna(0.0)
        out[f"noise_{sym}"] = c; tot += c
    out["conv"] = df.r_noise - tot
    return out


def fmt_full(r):
    a, b, f = B.stats(r[:"2023-12-31"]), B.stats(r["2024-01-01":]), B.stats(r)
    return f"{a[0]*100:5.1f}/{a[1]:4.2f}  {b[0]*100:5.1f}/{b[1]:4.2f}  {f[0]*100:5.1f}/{f[1]:4.2f}/{f[2]*100:4.0f}"


if __name__ == "__main__":
    if "--extract" in sys.argv:
        extract()
    else:
        main()
