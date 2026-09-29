"""Addendum NN: scheduled macro events (FOMC / CPI / NFP / claims) as timing and sizing inputs.

    PYTHONPATH=. .venv/bin/python -m research.sim.macro_events

Calendars: research/sim/event_calendar.py. Pre-registered 2026-09-28 20:54 PDT (draft addendum).
Conventions (event day e): night leg keyed d spans a release in (d, next(d)]; IBS keyed d
(open d+1 -> open d+2) spans a release in (d+1, d+2]; the noise leg trades day e itself.

Variants (all reported):
  Q1 standalone pre-FOMC
    F1 SPY close(e-1) -> open(e) with the night leg's unused cash (auction to auction)
    F2 SPY close(e-1) -> 13:59(e)  (Lucca-Moench window; standalone only)
    F3 QQQ close(e-1) -> open(e), as F1
  Q2 night-leg sizing
    N1 CPI/NFP exit morning x0.5   N2 same x1.5   N3 claims-only Thursday x0.5   N4 FOMC eve x1.5
  Q3 IBS
    B1 IBS whose last night spans CPI/NFP x1.5 (taxable only)
  Q4 noise leg
    I1 FOMC day off   I2 FOMC day lev x1.5 (capped)   I3 CPI/NFP day off   I4 CPI/NFP day lev x1.5 (capped)
Placebo: same action on random non-event days matched by weekday and SPY vol20 tercile (d-1), 1000 draws.
"""
from __future__ import annotations

import copy
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from . import book as B
from . import data as D
from . import event_calendar as EC
from . import growth as G
from . import roth as RO
from .crash import EPISODES
from .regime_tilt import V7, cap_for
from .validate import load_sim

SCRATCH = Path(str(__import__("pathlib").Path(__file__).resolve().parents[2]) + "/data/research/program")
CACHE = SCRATCH / "cache_macro_events.pkl"
S2 = {"QQQ": 0.5, "SMH": 0.5}
COSTS = [3.0, "tier", "tier_hi"]
ETF_COST = {3.0: 3.0, "tier": B.TIERS["tier"][3], "tier_hi": B.TIERS["tier_hi"][3]}   # SPY/QQQ per side
BASE_CAP = V7["noise_cap"]            # 0.75
ROTH_CAP = 1.5
SPARE = 0.35                          # overwritten in main() from the 2021-26 base replay

# name: (kind, flag, multiplier)
VARIANTS = {
    "F1 SPY close->open, FOMC eve (spare night cash)": ("fill", "fomc_eve", "SPY"),
    "F3 QQQ close->open, FOMC eve (spare night cash)": ("fill", "fomc_eve", "QQQ"),
    "N1 night x0.5, CPI/NFP morning": ("night", "rel_night", 0.5),
    "N2 night x1.5, CPI/NFP morning": ("night", "rel_night", 1.5),
    "N3 night x0.5, claims-only Thursday": ("night", "claims_night", 0.5),
    "N4 night x1.5, FOMC eve": ("night", "fomc_eve", 1.5),
    "B1 IBS x1.5, last night spans CPI/NFP": ("ibs", "rel_ibs", 1.5),
    "I1 noise off, FOMC day": ("noise", "fomc_day", 0.0),
    "I2 noise lev x1.5 capped, FOMC day": ("noise", "fomc_day", 1.5),
    "I3 noise off, CPI/NFP day": ("noise", "rel_day", 0.0),
    "I4 noise lev x1.5 capped, CPI/NFP day": ("noise", "rel_day", 1.5),
}


# ------------------------------------------------------------------ flags
def flags(ix: pd.DatetimeIndex) -> dict[str, pd.Series]:
    fomc = set(EC.fomc_dates())
    rel = sorted(set(EC.cpi_dates()) | set(EC.nfp_dates()))
    claims = sorted(EC.claims_dates())
    nxt = pd.Series(ix[1:].append(pd.DatetimeIndex([ix[-1] + pd.Timedelta(days=1)])), index=ix)
    nxt2 = nxt.shift(-1).fillna(nxt.iloc[-1] + pd.Timedelta(days=1))

    def spans(events, a: pd.Series, b: pd.Series) -> pd.Series:
        ev = np.array(events, dtype="datetime64[ns]")
        lo = np.searchsorted(ev, a.values.astype("datetime64[ns]"), side="right")
        hi = np.searchsorted(ev, b.values.astype("datetime64[ns]"), side="right")
        return pd.Series(hi > lo, index=ix)

    d = pd.Series(ix, index=ix)
    rel_night = spans(rel, d, nxt)
    return {
        "rel_night": rel_night,
        "rel_ibs": spans(rel, nxt, nxt2),
        "claims_night": spans(claims, d, nxt) & ~rel_night,
        "fomc_eve": pd.Series(nxt.isin(fomc).values, index=ix),
        "fomc_day": pd.Series(ix.isin(fomc), index=ix),
        "rel_day": pd.Series(ix.isin(rel), index=ix),
    }


def cells(s) -> pd.Series:
    """weekday x SPY vol20 tercile (vol known at d-1; terciles of the full history)."""
    r = s.C["SPY"].pct_change(fill_method=None)
    v = (r.rolling(20).std()).shift(1)
    t = pd.qcut(v.rank(method="first"), 3, labels=False)
    return pd.Series(s.C.index.weekday, index=s.C.index) * 10 + t.fillna(1).astype(int)


# ----------------------------------------------------------------- books
def noise_scaled(s, F: pd.Series, k: float) -> dict:
    out = {}
    for sym, z in s.NZ.items():
        z = z.copy()
        m = F.reindex(z.index).fillna(False).values
        z.loc[m, "lev"] = z.loc[m, "lev"] * k
        out[sym] = z
    return out


def taxable(s, var: str | None, F: dict, cost, start=3000.0, monthly=1000.0) -> pd.DataFrame:
    """V7 dollar replay with the variant's per-day action (whole shares, margin interest)."""
    base = B.Params(**{**V7, "night_cost": cost})
    kind, fl, k = VARIANTS[var] if var else (None, None, None)
    f = F[fl] if var else None
    sim = s
    if kind == "noise" and k > 0:
        sim = copy.copy(s); sim.NZ = noise_scaled(s, f, k)
    prev_ibs = False
    E, rows = start, []
    for i, d in enumerate(s.days):
        if i and i % 21 == 0:
            E += monthly
        q, extra = base, 0.0
        on = bool(f.get(d, False)) if var else False
        if var and (on or (kind == "ibs" and prev_ibs)):
            q = copy.copy(base)
            if kind == "night" and on:
                q.night_w = V7["night_w"] * k
            elif kind == "fill" and on:
                q.filler, q.filler_cost_bps = k, ETF_COST[cost]
            elif kind == "noise" and on and k == 0:
                q.noise_on = False
            if kind == "ibs":
                if on:
                    q.ibs_w = V7["ibs_w"] * k
                    b = s.bil.get(d, 0.0)
                    extra = (V7["ibs_w"] - q.ibs_w) * E * (float(b) if np.isfinite(b) else 0.0)
                if prev_ibs:                     # yesterday's x1.5 IBS is held today: less daytime room
                    q.noise_cap = cap_for(V7["ibs_w"] * k, V7["conviction_w"])
        if kind == "ibs":
            prev_ibs = on
        before = E
        pl, info = sim.day_pnl(E, d, q)
        pl += extra
        E += pl
        kk = before or 1.0
        rows.append((d, pl / kk, info["night"] / kk, (info["ibs"] + extra) / kk, info["noise"] / kk,
                     info["night_v"] / (V7["night_w"] * kk)))
    return pd.DataFrame(rows, columns=["date", "r", "r_night", "r_ibs", "r_noise", "night_used"]).set_index("date")


def roth(s, var: str | None, F: dict, cost) -> pd.Series:
    """Roth b1 (IBS + night 1.0x, intraday 1.5x via 3x ETFs on the night half's cash). Never borrows:
    night up-scales only use the leg's own unused cash; IBS up-scale not possible (returns base)."""
    base = B.Params(night_cost=cost, tilt="live", weekend_scale=0.5, noise_on=False,
                    conviction_w=0.0, margin_rate=0.0)
    kind, fl, k = VARIANTS[var] if var else (None, None, None)
    f = F[fl] if var else None
    sim = s
    if kind == "noise" and k > 0:
        sim = copy.copy(s); sim.NZ = noise_scaled(s, f, k)
    E, out = 1e5, {}
    for d in s.days:
        on = bool(f.get(d, False)) if var else False
        q, budget = base, "night"
        if on and kind == "fill":
            q = copy.copy(base); q.filler, q.filler_cost_bps = k, ETF_COST[cost]
        if on and kind == "noise" and k == 0:
            budget = None
        pl, info = RO.roth_day(sim, E, d, q, budget=budget, conv_w=0.0, noise_cap=ROTH_CAP)
        if on and kind == "night" and info["night_v"] > 0:
            room = max(0.0, V7["night_w"] * E - info["night_v"]) / info["night_v"]
            pl += (min(k, 1 + room) - 1) * info["night"]
        out[d] = pl / E
        E += pl
    return pd.Series(out)


def holdout(s, legs, var: str | None, F: dict, a="2016-02-01", b="2020-12-31") -> pd.Series:
    """2016-20 returns book (regime_tilt.holdout): night half in bills before 2020, 2020 rebuild."""
    night, ibs, bil, nz, bo = legs
    kind, fl, k = VARIANTS[var] if var else (None, None, None)
    f = F[fl] if var else pd.Series(False, index=s.C.index)
    days = s.C.index[(s.C.index >= a) & (s.C.index <= b)]
    on_ = s.O.shift(-1) / s.C - 1
    prev = False
    out = {}
    for d in days:
        on = bool(f.get(d, False))
        nw, iw, cap, nk = V7["night_w"], V7["ibs_w"], BASE_CAP, 1.0
        if on and kind == "night":
            nw *= k
        if on and kind == "ibs":
            iw *= k
        if kind == "ibs" and prev:
            cap = cap_for(V7["ibs_w"] * k, V7["conviction_w"])
        if on and kind == "noise":
            nk = k
        prev = on
        bl = float(np.nan_to_num(bil.get(d, 0.0)))
        nv = night.get(d, np.nan)
        x = nw * float(nv) if np.isfinite(nv) else V7["night_w"] * bl * (d < pd.Timestamp("2020-01-02"))
        if on and kind == "fill":
            spare = V7["night_w"] * SPARE                                 # 2021-26 mean unused night share
            if not np.isfinite(nv):
                x -= spare * bl                                           # bills money moves to the ETF
            x += spare * (float(on_.at[d, k]) - 2 * ETF_COST[3.0] / 1e4)
        iv = ibs.get(d, np.nan)
        x += iw * (float(iv) if np.isfinite(iv) else bl) + (V7["ibs_w"] - iw) * bl
        for sym, share in S2.items():
            z = nz[sym]
            if d in z.index and nk > 0:
                x += min(float(z.at[d, "lev"]) * nk, cap) * share * float(z.at[d, "ret"])
        x += V7["conviction_w"] * float(bo.get(d, 0.0))
        out[d] = x
    return pd.Series(out)


# ----------------------------------------------------- placebo (linear)
def delta_series(s, base: pd.DataFrame, var: str, F: pd.Series, cost) -> pd.Series:
    """Per-day return change the action would make on flagged days F (linear in the leg)."""
    kind, _, k = VARIANTS[var]
    ix = base.index
    f = F.reindex(ix).fillna(False)
    if kind == "night":
        dl = (k - 1) * base.r_night
    elif kind == "ibs":
        dl = (k - 1) * base.r_ibs
    elif kind == "fill":
        on_ = (s.O.shift(-1) / s.C - 1)[k].reindex(ix).fillna(0)
        spare = V7["night_w"] * (1 - base.night_used.clip(0, 1))
        dl = spare * (on_ - 2 * ETF_COST[cost] / 1e4)
    else:
        dl = pd.Series(0.0, index=ix)
        for sym, share in S2.items():
            z = s.NZ[sym].reindex(ix)
            b0 = np.minimum(z.lev, BASE_CAP) * share * z.ret
            b1 = np.minimum(z.lev * k, BASE_CAP) * share * z.ret
            dl = dl + (b1 - b0).fillna(0)
    return dl.where(f, 0.0)


def placebo_flags(F: pd.Series, cell: pd.Series, ix, excl: pd.Series, n: int, seed=11) -> list[pd.Series]:
    rng = np.random.default_rng(seed)
    f = F.reindex(ix).fillna(False)
    c = cell.reindex(ix)
    pool = {g: np.where((c.values == g) & ~excl.reindex(ix).fillna(False).values)[0] for g in c.unique()}
    need = c[f].value_counts()
    out = []
    for _ in range(n):
        m = np.zeros(len(ix), bool)
        for g, cnt in need.items():
            p = pool[g]
            m[rng.choice(p, size=min(cnt, len(p)), replace=False)] = True
        out.append(pd.Series(m, index=ix))
    return out


def sharpe(r):
    r = r.fillna(0)
    return float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0.0


# ------------------------------------------------------------- leg level
def nw_diff(y: pd.Series, dmy: pd.Series, lag=5) -> tuple[float, float]:
    """OLS y = a + b*dummy, Newey-West t of b. Returns (b in bp, t)."""
    y = y.fillna(0).values; x = np.c_[np.ones(len(y)), dmy.astype(float).values]
    XtX = np.linalg.inv(x.T @ x); b = XtX @ x.T @ y; e = y - x @ b
    n = len(y)
    S = np.zeros((2, 2))
    for L in range(lag + 1):
        g = (x[L:] * e[L:, None]).T @ (x[:n - L] * e[:n - L, None])
        w = 1 if L == 0 else 2 * (1 - L / (lag + 1))
        S += w * (g if L == 0 else (g + g.T) / 2)
    V = XtX @ S @ XtX
    return float(b[1] * 1e4), float(b[1] / np.sqrt(V[1, 1]))


def st(r):
    c, sh, dd = B.stats(r)
    return f"{c*100:6.1f}/{sh:4.2f}/{dd*100:4.0f}"


def halves(r):
    return f"{st(r[:'2023-12-31'])}  {st(r['2024-01-01':])}"


# ---------------------------------------------------------------- main
def main():
    s = load_sim()
    c = pickle.load(open(CACHE, "rb"))
    s = copy.copy(s); s.N, s.BO = c["N"], c["BO"]
    legs = c["legs"]
    ix = s.C.index
    F = flags(ix)
    cell = cells(s)
    anyev = F["rel_night"] | F["fomc_eve"] | F["fomc_day"] | F["rel_day"] | F["rel_ibs"]
    print("flag counts 2021-02..2026-09 / 2016-20:",
          {k: (int(v[s.days].sum()), int(v["2016-02-01":"2020-12-31"].sum())) for k, v in F.items()})

    # ---------- Q1 standalone legs
    print("\n== Q1 standalone pre-FOMC legs: per-trade mean bp (net 3bp/side) | n | NW t full | placebo pct")
    on_ = s.O.shift(-1) / s.C - 1
    M = D.minutes("SPY")["close"]
    spy_c = s.C["SPY"]
    f2 = (M[268].reindex(ix).shift(-1) / spy_c - 1)          # close d -> 13:59 of d+1
    stand = {"F1 SPY close->open": on_["SPY"], "F2 SPY close->13:59": f2, "F3 QQQ close->open": on_["QQQ"]}
    fe = F["fomc_eve"]
    for name, x in stand.items():
        x = (x - 2 * 3.0 / 1e4).dropna()
        x = x["2016-02-01":]
        fl = fe.reindex(x.index).fillna(False)
        parts = [(a, b) for a, b in (("2016-02-01", "2020-12-31"), ("2021-01-01", "2023-12-31"), ("2024-01-01", "2026-12-31"))]
        ms = [x[a:b][fl[a:b]].mean() * 1e4 for a, b in parts]
        ns = [int(fl[a:b].sum()) for a, b in parts]
        bdiff, t = nw_diff(x, fl)
        pl = placebo_flags(fl, cell, x.index, anyev, 1000, seed=3)
        pm = np.array([x[p].mean() for p in pl]) * 1e4
        act = x[fl].mean() * 1e4
        tr = x[fl].values
        tt = tr.mean() / tr.std(ddof=1) * np.sqrt(len(tr))
        print(f"  {name:22s} 2016-20 {ms[0]:6.1f} (n{ns[0]})  2021-23 {ms[1]:6.1f} (n{ns[1]})  2024-26 {ms[2]:6.1f} (n{ns[2]})"
              f"  | all {act:5.1f}bp t(trades) {tt:4.2f}  diff-vs-other {bdiff:5.1f}bp NW t {t:4.2f}"
              f"  | placebo pct {np.mean(pm < act)*100:4.0f}  (placebo mean {pm.mean():4.1f})")

    # ---------- leg-level effects
    print("\n== leg-level event effects (event minus other days, bp of equity per day, NW t lag 5)")
    b3 = taxable(s, None, F, 3.0)
    global SPARE
    SPARE = float(1 - b3.night_used.clip(0, 1).mean())
    print(f"  (mean unused night share 2021-26: {SPARE:.2f}; used for the F-legs' 2016-20 holdout)")
    ho0 = holdout(s, legs, None, F)
    nz_ho = sum(np.minimum(legs[3][sym].lev, BASE_CAP) * sh * legs[3][sym].ret for sym, sh in S2.items())
    ibs_ho = pd.Series({d: np.mean([r - 2e-4 for _, _, r in v]) for d, v in s.I.items()}).sort_index()
    rows = [("night leg (2021-26 book)", b3.r_night, "rel_night"), ("night leg (2021-26 book)", b3.r_night, "claims_night"),
            ("night leg (2021-26 book)", b3.r_night, "fomc_eve"), ("night leg 2020 rebuild (unit)", legs[0], "rel_night"),
            ("night leg 2020 rebuild (unit)", legs[0], "fomc_eve"),
            ("IBS (2021-26 book)", b3.r_ibs, "rel_ibs"), ("IBS unit, 2016-20", ibs_ho["2016-02-01":"2020-12-31"], "rel_ibs"),
            ("noise (2021-26 book)", b3.r_noise, "fomc_day"), ("noise (2021-26 book)", b3.r_noise, "rel_day"),
            ("noise V7-cap, 2016-20", nz_ho["2016-02-01":"2020-12-31"], "fomc_day"),
            ("noise V7-cap, 2016-20", nz_ho["2016-02-01":"2020-12-31"], "rel_day")]
    for lab, y, fl in rows:
        dm = F[fl].reindex(y.index).fillna(False)
        out = []
        for a, b in (("2016-01-01", "2023-12-31"), ("2024-01-01", "2026-12-31")):
            yy, dd = y[a:b], dm[a:b]
            if dd.sum() < 3:
                out.append("        n/a         "); continue
            bb, t = nw_diff(yy, dd)
            sd_e, sd_o = yy[dd].std() * 1e4, yy[~dd].std() * 1e4
            out.append(f"{bb:6.1f}bp t{t:5.2f} n{int(dd.sum()):3d} sd {sd_e:5.0f}/{sd_o:4.0f}")
        bb, t = nw_diff(y, dm)
        print(f"  {lab:32s} {fl:13s} early {out[0]} | 2024-26 {out[1]} | all {bb:6.1f}bp t{t:5.2f}")

    # ---------- book effects
    print("\n== V7 book: 2021-23 | 2024-26 CAGR/Sharpe/maxDD (dollar replay), 2016-20 holdout, Roth b1 full")
    base = {cst: taxable(s, None, F, cst) for cst in COSTS}
    rbase = {cst: roth(s, None, F, cst) for cst in (3.0, "tier_hi")}
    print(f"  {'V7 base':48s}" + "".join(f" [{cst}] {halves(base[cst].r)}" for cst in COSTS)
          + f" | HO {st(ho0)} | Roth3 {st(rbase[3.0])} RothHi {st(rbase['tier_hi'])}")
    res = {}
    for var, (kind, fl, k) in VARIANTS.items():
        R = {cst: taxable(s, var, F, cst) for cst in COSTS}
        ho = holdout(s, legs, var, F)
        rr = {cst: roth(s, var, F, cst) for cst in (3.0, "tier_hi")}
        # placebo on the 2021-26 book at 3bp
        dl = delta_series(s, base[3.0], var, F[fl], 3.0)
        s0 = sharpe(base[3.0].r)
        act = sharpe(base[3.0].r + dl) - s0
        pls = placebo_flags(F[fl], cell, base[3.0].index, anyev | F[fl], 1000, seed=5)
        pd_ = np.array([sharpe(base[3.0].r + delta_series(s, base[3.0], var, p, 3.0)) - s0 for p in pls])
        pct = float(np.mean(pd_ < act) * 100)
        d_sh = {cst: [B.stats(R[cst].r[a:b])[1] - B.stats(base[cst].r[a:b])[1] for a, b in
                      ((None, "2023-12-31"), ("2024-01-01", None))] for cst in COSTS}
        d_cg = {cst: [B.stats(R[cst].r[a:b])[0] - B.stats(base[cst].r[a:b])[0] for a, b in
                      ((None, "2023-12-31"), ("2024-01-01", None))] for cst in COSTS}
        res[var] = dict(R=R, ho=ho, rr=rr, pct=pct, act=act, d_sh=d_sh, d_cg=d_cg)
        print(f"  {var:48s}" + "".join(f" [{cst}] {halves(R[cst].r)}" for cst in COSTS)
              + f" | HO {st(ho)} | Roth3 {st(rr[3.0])} RothHi {st(rr['tier_hi'])}")
        print(f"  {'':48s} dSharpe 21-23/24-26 @3bp {d_sh[3.0][0]:+.3f}/{d_sh[3.0][1]:+.3f} @tier_hi "
              f"{d_sh['tier_hi'][0]:+.3f}/{d_sh['tier_hi'][1]:+.3f}  dCAGR @3bp {d_cg[3.0][0]*100:+.2f}/{d_cg[3.0][1]*100:+.2f}"
              f"pp @hi {d_cg['tier_hi'][0]*100:+.2f}/{d_cg['tier_hi'][1]*100:+.2f}pp | HO dSh "
              f"{B.stats(ho)[1]-B.stats(ho0)[1]:+.3f} dCAGR {(B.stats(ho)[0]-B.stats(ho0)[0])*100:+.2f}pp"
              f" | Roth dSh {B.stats(rr[3.0])[1]-B.stats(rbase[3.0])[1]:+.3f}"
              f" | placebo: act dSh {act:+.3f} pct {pct:3.0f} (p95 {np.percentile(pd_, 95):+.3f})")

    pickle.dump({"res": {k: {"pct": v["pct"], "act": v["act"], "d_sh": v["d_sh"], "d_cg": v["d_cg"]}
                         for k, v in res.items()}}, open(SCRATCH / "macro_events_res.pkl", "wb"))

    # ---------- N3 is weekday-confounded (claims = nearly every Thursday): vol-only placebo (sensitivity)
    fl = "claims_night"; var = "N3 night x0.5, claims-only Thursday"
    s0 = sharpe(base[3.0].r)
    volcell = cell % 10
    pls = placebo_flags(F[fl], volcell, base[3.0].index, anyev | F[fl], 1000, seed=5)
    pd_ = np.array([sharpe(base[3.0].r + delta_series(s, base[3.0], var, p, 3.0)) - s0 for p in pls])
    print(f"\n== N3 sensitivity: vol-tercile-only placebo (any weekday): act {res[var]['act']:+.3f} pct "
          f"{np.mean(pd_ < res[var]['act'])*100:3.0f}  (weekday-matched pool is the same Wednesdays)")
    wed = pd.Series(ix.weekday == 2, index=ix) & ~F["claims_night"] & ~anyev
    print(f"   Wednesday nights not before claims (non-claims Wed): n={int(wed[s.days].sum())}")

    # ---------- F3 detail: per year, hit rate, median, outliers
    x = (on_["QQQ"] - 2 * 3.0 / 1e4)["2016-02-01":]
    t = x[fe.reindex(x.index).fillna(False)].dropna()
    print("\n== F3 QQQ close->open on FOMC eves, net 3bp/side: per year mean bp (n)")
    print("  " + "  ".join(f"{y}: {g.mean()*1e4:5.1f} ({len(g)})" for y, g in t.groupby(t.index.year)))
    print(f"  hit {np.mean(t > 0):.0%}  median {t.median()*1e4:.1f}bp  mean ex top-3 {t.sort_values().iloc[:-3].mean()*1e4:.1f}bp"
          f"  worst {t.min()*1e4:.0f}bp  best {t.max()*1e4:.0f}bp")
    oth = x[~fe.reindex(x.index).fillna(False) & ~anyev.reindex(x.index).fillna(False)].dropna()
    print(f"  all other non-event nights: mean {oth.mean()*1e4:.1f}bp  hit {np.mean(oth > 0):.0%}")

    # ---------- stress (pre-registered candidates that cleared bar 1 somewhere)
    print("\n== stress at tier_hi: EH, 5y MC (21d blocks), episodes, worst day/month")
    for lab, df in [("V7 base", base["tier_hi"])] + [(v, res[v]["R"]["tier_hi"]) for v in
                    ("F3 QQQ close->open, FOMC eve (spare night cash)", "F1 SPY close->open, FOMC eve (spare night cash)",
                     "N2 night x1.5, CPI/NFP morning", "B1 IBS x1.5, last night spans CPI/NFP")]:
        e = G.eh(df)
        m1, m2 = G.mc(e, 3000, 1000), G.mc(e, 10000, 0)
        eps = {k: (1 + df.r[a:b]).prod() - 1 for k, (a, b) in EPISODES.items() if len(df.r[a:b])}
        ap = (1 + df.r["2025-04-02":"2025-04-08"]).prod() - 1
        print(f"  {lab[:40]:40s} EH {st(e)} | MC $3k+1k med ${m1['med']:,.0f} P30 {m1['dd30']:.1%} P50 {m1['dd50']:.1%}"
              f" | $10k med ${m2['med']:,.0f} P30 {m2['dd30']:.1%} P50 {m2['dd50']:.1%} | wd {df.r.min()*100:.1f}% wm "
              f"{G.monthly_worst(df.r)*100:.1f}% | Apr2-8'25 {ap*100:.1f}% | "
              + " ".join(f"{k} {v*100:.1f}%" for k, v in eps.items()))
        eh_d = (e.mean() - G.eh(base["tier_hi"]).mean()) * 252
        print(f"  {'':40s} EH extra return vs base {eh_d*100:+.2f}%/yr (taxable, tier_hi)")
    for v in ("F3 QQQ close->open, FOMC eve (spare night cash)", "N2 night x1.5, CPI/NFP morning"):
        ho = res[v]["ho"]
        print(f"  {v[:40]:40s} COVID 2020-02-19..03-23 holdout: base {((1+ho0['2020-02-19':'2020-03-23']).prod()-1)*100:.1f}%"
              f"  variant {((1+ho['2020-02-19':'2020-03-23']).prod()-1)*100:.1f}%   2018Q4 base "
              f"{((1+ho0['2018-10-01':'2018-12-24']).prod()-1)*100:.1f}% var {((1+ho['2018-10-01':'2018-12-24']).prod()-1)*100:.1f}%")
        for cst in (3.0, "tier_hi"):
            dr = (res[v]["rr"][cst].mean() - rbase[cst].mean()) * 252
            print(f"  {'':40s} Roth b1 [{cst}] extra {dr*100:+.2f}%/yr, EH-halved {dr*50:+.2f}%/yr")

if __name__ == "__main__":
    main()
