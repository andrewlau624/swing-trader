"""Diagnostic: beta/alpha isolation of the current book, IBS, night, noise (+ IBS/TME portfolios).

Pre-registered as a diagnostic amendment (no N bump) in research/drafts/round1_prose.md BEFORE any output was read.
Reuses book.Sim/ibs_days (live signals), ibs_oos._trades, xb_alloc.load_ohlc/load_treasury, book_decomp._ols,
max_edge.BOOKS["V7"].  No live code touched.

Run: PYTHONPATH=. .venv/bin/python -m research.sim.beta_alpha_iso > research/sim/beta_alpha_iso_out.txt
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import book as B
from . import data as D
from . import ibs_oos as IO
from . import xb_alloc as XB
from .book_decomp import _ols
from .max_edge import BOOKS

FAC = ["MKT", "TECH", "SIZE", "MOM"]
FSYMS = ["SPY", "QQQ", "IWM", "MTUM", "XLK", "TQQQ", "BIL"]
FIN = 0.125
OUT: list[str] = []


def pr(s: str = "") -> None:
    print(s)


# ------------------------------------------------------------------ factors (adjusted bars, window matched)
FO, _, _, FC = XB.load_ohlc(FSYMS)


def _w(kind: str, s: str) -> pd.Series:
    O, C = FO[s], FC[s]
    return {"on": O.shift(-1) / C - 1, "oo_d": O.shift(-2) / O.shift(-1) - 1, "oo_e": O.shift(-1) / O - 1,
            "id": C / O - 1, "cc": C.pct_change(fill_method=None)}[kind]


def factors(kind: str, tech: str = "QQQ") -> pd.DataFrame:
    spy = _w(kind, "SPY")
    return pd.DataFrame({"MKT": spy, "TECH": _w(kind, tech) - spy, "SIZE": _w(kind, "IWM") - spy,
                         "MOM": _w(kind, "MTUM") - spy})


# ------------------------------------------------------------------ regression helpers
def nwt(x, lags: int = 5) -> float:
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    n = len(x)
    if n < 20:
        return np.nan
    e = x - x.mean()
    s = e @ e / n
    for k in range(1, lags + 1):
        s += 2 * (1 - k / (lags + 1)) * (e[k:] @ e[:-k]) / n
    return x.mean() / np.sqrt(s / n) if s > 0 else np.nan


def fit(y: pd.Series, X: pd.DataFrame, ppy: int = 252) -> dict:
    df = pd.concat([y.rename("y"), X], axis=1).dropna()
    cols = list(X.columns)
    yv = df["y"].values
    Xm = np.column_stack([np.ones(len(df)), df[cols].values])
    b, t, r2 = _ols(yv, Xm, 5)
    resid = pd.Series(yv - Xm[:, 1:] @ b[1:], index=df.index)       # includes alpha
    contrib = {c: b[i + 1] * df[c].mean() * ppy for i, c in enumerate(cols)}
    raw = yv.mean() * ppy
    return dict(n=len(df), raw=raw, cagr=(1 + yv).prod() ** (ppy / len(df)) - 1, alpha=b[0] * ppy, t=t[0], r2=r2,
                rvol=resid.std() * np.sqrt(ppy), beta=dict(zip(cols, b[1:])), bt=dict(zip(cols, t[1:])),
                contrib=contrib, frac=(sum(contrib.values()) / raw if raw else np.nan), resid=resid)


def fmt(lab: str, f: dict) -> str:
    bs = " ".join(f"{c}:{f['beta'][c]:+6.2f}/{f['bt'][c]:+5.1f}" for c in f["beta"])
    cs = " ".join(f"{c}:{f['contrib'][c]*100:+5.1f}" for c in f["contrib"])
    return (f"{lab:26s} n={f['n']:4d} raw={f['raw']*100:6.1f}% alpha={f['alpha']*100:6.1f}% t={f['t']:5.2f} "
            f"R2={f['r2']:4.2f} rvol={f['rvol']*100:5.1f}% | {bs} | contrib%/yr {cs} | sys={f['frac']*100:5.0f}%")


def weekly(y: pd.Series, X: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
    df = pd.concat([y.rename("y"), X], axis=1).dropna()
    g = np.arange(len(df)) // 5
    w = np.expm1(np.log1p(df.clip(lower=-0.99)).groupby(g).sum())
    w = w[df.groupby(g).size().values == 5]
    return w["y"], w[list(X.columns)]


def oos(total: pd.Series, legs: list, min_train: int = 450) -> dict:
    """Expanding-window OOS alpha: betas from rows before year Y, alpha = mean(total - sum beta.X) on year Y."""
    idx = total.dropna().index
    for _, X in legs:
        idx = idx.intersection(X.dropna().index)
    idx = idx.intersection(pd.concat([y for y, _ in legs], axis=1).dropna().index)
    tot = total.reindex(idx)
    per, pooled = {}, []
    for Y in sorted(set(idx.year)):
        tr, te = idx.year < Y, idx.year == Y
        if tr.sum() < min_train or te.sum() < 30:
            continue
        res = tot[te].copy()
        for y, X in legs:
            Xt = np.column_stack([np.ones(tr.sum()), X.reindex(idx)[tr].values])
            b = np.linalg.lstsq(Xt, y.reindex(idx)[tr].values, rcond=None)[0]
            res = res - X.reindex(idx)[te].values @ b[1:]
        per[Y] = (res.mean() * 252, tot[te].mean() * 252, nwt(res.values))
        pooled.append(res)
    if not pooled:
        return {}
    p = pd.concat(pooled)
    rawp = tot.loc[p.index].mean() * 252
    return dict(per=per, alpha=p.mean() * 252, raw=rawp, t=nwt(p.values), npos=sum(v[0] > 0 for v in per.values()),
                nwin=len(per), resid=p)


def fmt_oos(lab: str, o: dict) -> str:
    if not o:
        return f"{lab}: n/a"
    yrs = " ".join(f"{y}:{a*100:+5.1f}" for y, (a, _, _) in o["per"].items())
    return (f"{lab:26s} OOS pooled alpha={o['alpha']*100:6.1f}%/yr (raw {o['raw']*100:5.1f}%) t={o['t']:5.2f} "
            f"pos {o['npos']}/{o['nwin']} | per-year alpha% {yrs}")


def classify(o: dict, raw_ref: float | None = None) -> str:
    if not o:
        return "n/a"
    raw = raw_ref if raw_ref is not None else o["raw"]
    a, t = o["alpha"], o["t"]
    if a <= 0 or (raw > 0 and a < 0.2 * raw) or abs(t) < 1:
        return "C"
    if raw > 0 and a >= 0.6 * raw and t >= 2 and o["npos"] / o["nwin"] >= 0.75:
        return "A"
    return "B"


def perf(r: pd.Series, rf: pd.Series | None = None) -> dict:
    r = r.fillna(0.0)
    n = len(r)
    eq = (1 + r).cumprod()
    dd = eq / eq.cummax() - 1
    trough = dd.values.argmin()
    peak = eq.iloc[: trough + 1].max()
    after = np.where(eq.values[trough:] >= peak)[0]
    rec = f"{after[0]}d" if len(after) else f">{n - trough}d (open)"
    ex = r - (rf.reindex(r.index).fillna(0.0) if rf is not None else 0.0)
    roll = lambda k: ((1 + r).rolling(k).apply(np.prod, raw=True) - 1).min()  # noqa: E731
    return dict(cagr=eq.iloc[-1] ** (252 / n) - 1, vol=r.std() * np.sqrt(252), mdd=dd.min(),
                sh=ex.mean() / r.std() * np.sqrt(252) if r.std() > 0 else 0.0, w5=roll(5), w20=roll(20), rec=rec)


def pfmt(lab: str, p: dict, extra: str = "") -> str:
    return (f"{lab:30s} CAGR {p['cagr']*100:6.1f}% vol {p['vol']*100:5.1f}% maxDD {p['mdd']*100:6.1f}% "
            f"Sharpe {p['sh']:5.2f} w5d {p['w5']*100:6.1f}% w20d {p['w20']*100:6.1f}% rec {p['rec']:>12s} {extra}")


# ------------------------------------------------------------------ book replay with exposure capture
def replay_x(s: B.Sim, p: B.Params, start: float = 3000.0, monthly: float = 1000.0) -> pd.DataFrame:
    E, rows = start, []
    for i, d in enumerate(s.days):
        if i and i % 21 == 0:
            E += monthly
        before = E
        pl, info = s.day_pnl(E, d, p)
        E += pl
        k = before or 1.0
        rows.append((d, E, pl / k, info["night"] / k, info["ibs"] / k, info["noise"] / k,
                     (info["idle"] + info["margin"]) / k, info["night_v"] / k, info["ibs_v"] / k))
    return pd.DataFrame(rows, columns=["date", "E", "r", "r_night", "r_ibs", "r_noise", "r_cash", "x_night",
                                       "x_ibs"]).set_index("date")


def scaled(F: pd.DataFrame, x: pd.Series) -> pd.DataFrame:
    return F.mul(x.reindex(F.index), axis=0)


# ------------------------------------------------------------------ IBS / TME account sim
CAL = D.etf()["close"].index
CAL = CAL[CAL >= "2017-01-01"]
ADJ_RF = FC["BIL"].pct_change(fill_method=None)


def ibs_by_session() -> dict:
    I = B.ibs_days()
    pos = {d: i for i, d in enumerate(D.etf()["close"].index)}
    ix = D.etf()["close"].index
    return {ix[pos[d] + 1]: legs for d, legs in I.items() if pos[d] + 1 < len(ix)}


def tme_sessions() -> dict:
    tl = XB.load_treasury()["TLT"]
    m = tl.index.to_period("M")
    out = {}
    for mo in sorted(set(m)):
        dts = tl.index[m == mo]
        if len(dts) < 6 or (mo == m[-1] and dts[-1].day < 27):
            continue
        for k in (-3, -2, -1):                               # sessions T-2, T-1, T
            t = dts[k]
            prev = tl.loc[dts[k - 1]]
            out[t] = dict(p=float(prev), c=float(tl.loc[t]), entry=(k == -3), exit=(k == -1))
    return out


I_E = ibs_by_session()
TME = tme_sessions()


def run_acct(E0: float, whole: bool, L_ibs: float, use_tme: bool, start: str, end: str, cost_ibs=1e-4, cost_tme=2e-4):
    dates = CAL[(CAL >= start) & (CAL <= end)]
    E, rows = E0, []
    for t in dates:
        legs = I_E.get(t, []) if L_ibs > 0 else []
        tm = TME.get(t) if use_tme else None
        both = bool(legs) and tm is not None
        w_i = L_ibs * (0.5 if both else 1.0)
        w_t = 0.5 if both else 1.0
        inv_i = p_i = inv_t = p_t = 0.0
        for s, o1, r in legs:
            per = w_i * E / len(legs)
            sh = np.floor(per / o1) if whole else per / o1
            inv_i += sh * o1
            p_i += sh * o1 * (r - 2 * cost_ibs)
        if tm:
            sh = np.floor(w_t * E / tm["p"]) if whole else w_t * E / tm["p"]
            inv_t = sh * tm["p"]
            p_t = sh * (tm["c"] - tm["p"]) - (sh * tm["p"] * cost_tme if tm["entry"] else 0) \
                - (sh * tm["c"] * cost_tme if tm["exit"] else 0)
        rf = ADJ_RF.get(t, 0.0)
        rf = 0.0 if not np.isfinite(rf) else rf
        cash = max(E - inv_i - inv_t, 0.0) * rf
        fin = max(inv_i + inv_t - E, 0.0) * FIN / 252
        pl = p_i + p_t + cash - fin
        k = E
        rows.append((t, E + pl, pl / k, p_i / k, p_t / k, (cash - fin) / k, inv_i / k, inv_t / k))
        E += pl
    return pd.DataFrame(rows, columns=["date", "E", "r", "r_ibs", "r_tme", "r_cash", "x_ibs", "x_tme"]).set_index("date")


def acct_legs(a: pd.DataFrame):
    Fo, Fc = factors("oo_e"), factors("cc")
    legs = [(a["r_ibs"], scaled(Fo, a["x_ibs"])), (a["r_tme"], scaled(Fc, a["x_tme"]))]
    legs = [(y, X) for (y, X), x in zip(legs, (a["x_ibs"], a["x_tme"])) if x.abs().sum() > 0]
    return legs


def beta_alpha(a: pd.DataFrame):
    """sum-of-legs alpha (arithmetic, /yr) and average dollar-beta to SPY."""
    legs = acct_legs(a)
    res = a["r"].copy()
    for y, X in legs:
        f = fit(y, X)
        res = res.sub((X[FAC] @ pd.Series(f["beta"])).reindex(res.index).fillna(0.0))
    # average dollar beta = mean over days of sum_leg x_leg * beta_leg,MKT
    avg_beta = 0.0
    for (y, X), col in zip(legs, ("x_ibs", "x_tme")):
        f = fit(y, X)
        avg_beta += f["beta"]["MKT"] * a[col].mean()
    return res.mean() * 252, nwt(res.values), avg_beta, legs


def main() -> None:
    s = B.Sim(noise_syms=("QQQ", "SMH"))
    p = B.Params(**{**BOOKS["V7"], "night_cost": 2.5})
    R = replay_x(s, p)
    days = R.index
    pr("BETA / ALPHA ISOLATION (diagnostic, no N bump). Pre-registration: research/drafts/round1_prose.md")
    pr("Factors: window-matched, total-return adjusted bars; MKT=SPY TECH=QQQ-SPY SIZE=IWM-SPY MOM=MTUM-SPY. "
       "night/ibs factors scaled by invested fraction. alpha=mean(y-b.xf)*252 (arith), t=Newey-West(5).")
    pr(f"Book = max_edge.BOOKS['V7'] night_cost 2.5bp, replay {days[0].date()}..{days[-1].date()} "
       f"(night leg 2021-26 is FITTED; conviction is shadow so absent)")

    # ---------------------------------------------------------------- 1. decomposition
    Fon, Foo, Fid = factors("on").reindex(days), factors("oo_d").reindex(days), factors("id").reindex(days)
    Xn, Xi, Xz = scaled(Fon, R["x_night"]), scaled(Foo, R["x_ibs"]), Fid
    pr("\n=== 1. DECOMPOSITION (daily, 2021-26) ===")
    legs = {"night": (R["r_night"], Xn), "ibs": (R["r_ibs"], Xi), "noise": (R["r_noise"], Xz)}
    fits = {}
    for k, (y, X) in legs.items():
        fits[k] = fit(y, X)
        pr(fmt(f"{k} (exposure-scaled)" if k != "noise" else "noise (unscaled)", fits[k]))
    pr(fmt("night (unscaled, prior)", fit(R["r_night"], Fon)))
    pr(fmt("ibs (unscaled, prior)", fit(R["r_ibs"], Foo)))
    resid = R["r"].copy()
    for k, (y, X) in legs.items():
        resid = resid.sub((X @ pd.Series(fits[k]["beta"])).reindex(resid.index).fillna(0.0))
    rawT = R["r"].mean() * 252
    contrib_sys = sum(sum(fits[k]["contrib"].values()) for k in fits)
    pr(f"TOTAL BOOK: raw={rawT*100:.1f}%/yr CAGR={((1+R['r']).prod()**(252/len(R))-1)*100:.1f}% "
       f"alpha(incl cash)={resid.mean()*252*100:.1f}% t={nwt(resid.values):.2f} "
       f"R2={1-resid.var()/R['r'].var():.2f} resid vol={resid.std()*np.sqrt(252)*100:.1f}%  "
       f"cash+margin={R['r_cash'].mean()*252*100:.1f}%  alpha ex-cash={(resid.mean()-R['r_cash'].mean())*252*100:.1f}%")
    pr(f"  systematic contribution={contrib_sys*100:.1f}%/yr = {contrib_sys/rawT*100:.0f}% of raw; "
       "by factor: " + " ".join(f"{c}:{sum(fits[k]['contrib'][c] for k in fits)*100:+.1f}" for c in FAC))
    pr("  per-leg raw ann%: " + " ".join(f"{k}={fits[k]['raw']*100:.1f}" for k in fits)
       + f" cash={R['r_cash'].mean()*252*100:.1f}; avg exposure night={R['x_night'].mean():.2f} ibs={R['x_ibs'].mean():.2f}")
    pr("  TECH=XLK-SPY robustness (alpha/t): " + "  ".join(
        f"{k}:{fit(y, scaled(factors({'night':'on','ibs':'oo_d','noise':'id'}[k], 'XLK').reindex(days), R['x_'+k]) if k!='noise' else factors('id','XLK').reindex(days))['alpha']*100:.1f}/"
        f"{fit(y, scaled(factors({'night':'on','ibs':'oo_d','noise':'id'}[k], 'XLK').reindex(days), R['x_'+k]) if k!='noise' else factors('id','XLK').reindex(days))['t']:.2f}"
        for k, (y, _) in legs.items()))
    pr("\n--- weekly (non-overlapping 5-session blocks, x52) ---")
    for k, (y, X) in legs.items():
        yw, Xw = weekly(y, X)
        pr(fmt(f"{k} weekly", fit(yw, Xw, 52)))
    yw, _ = weekly(R["r"], Xn)
    pr("\n=== 2. CHRONOLOGICAL OOS (expanding; betas from earlier years only) ===")
    oo = {k: oos(y, [(y, X)]) for k, (y, X) in legs.items()}
    tot_o = oos(R["r"], [(y, X) for y, X in legs.values()])
    for k in legs:
        pr(fmt_oos(k, oo[k]) + f"  class={classify(oo[k])}")
    pr(fmt_oos("TOTAL BOOK (incl cash)", tot_o) + f"  class={classify(tot_o)}")
    cash_o = tot_o["raw"] - tot_o["alpha"]
    pr(f"  (total raw includes cash/margin {R['r_cash'].mean()*252*100:.1f}%/yr; classification of the book uses the "
       f"ex-cash OOS alpha {(tot_o['alpha']-R['r_cash'].mean()*252)*100:.1f}% vs raw ex-cash "
       f"{(tot_o['raw']-R['r_cash'].mean()*252)*100:.1f}%)")
    pr("  book OOS classification ex-cash: " + classify(dict(tot_o, alpha=tot_o["alpha"] - R["r_cash"].mean() * 252,
                                                         raw=tot_o["raw"] - R["r_cash"].mean() * 252)))

    # ---------------------------------------------------------------- 4. night
    pr("\n=== 4. NIGHT LEG ===")
    f = fits["night"]
    pr(f"raw={f['raw']*100:.1f}%/yr; explained by: " + " ".join(f"{c} {f['contrib'][c]/f['raw']*100:+.0f}%" for c in FAC)
       + f"; total systematic {f['frac']*100:.0f}%; residual alpha {f['alpha']*100:.1f}% (t {f['t']:.2f})")
    fm = fit(R["r_night"], Xn[["MKT"]])
    pr(f"MKT-only R2={fm['r2']:.2f} beta={fm['beta']['MKT']:.2f} alpha={fm['alpha']*100:.1f}% t={fm['t']:.2f}")
    for lo, hi, lab in (("2021", "2022", "2021-22"), ("2023", "2024", "2023-24"), ("2025", "2026", "2025-26"),
                        ("2021", "2023", "2021-23 (fit)"), ("2024", "2026", "2024-26")):
        sl = slice(f"{lo}-01-01", f"{hi}-12-31")
        fs = fit(R["r_night"].loc[sl], Xn.loc[sl])
        res = fits["night"]["resid"].loc[sl]
        pr(f"  {lab:14s} own-fit alpha={fs['alpha']*100:6.1f}% t={fs['t']:5.2f} raw={fs['raw']*100:5.1f}% sys={fs['frac']*100:4.0f}% | "
           f"full-sample-beta residual alpha={res.mean()*252*100:6.1f}%")

    # ---------------------------------------------------------------- 3. IBS
    pr("\n=== 3. IBS (open->open; 18-ETF top-3 momentum, IBS<0.2) ===")
    P = D.etf()
    O, C = P["open"], P["close"]
    ooE = (O.shift(-2) / O.shift(-1) - 1)
    betas = pd.DataFrame({sy: (ooE[sy].rolling(252).cov(ooE["SPY"]) / ooE["SPY"].rolling(252).var()).shift(2)
                          for sy in IO.EQ18})
    ibs_t, ctl_t = IO._trades("ibs_lo"), IO._trades("all")
    for t in (ibs_t, ctl_t):
        t["badj"] = [r - betas.at[d, sy] * ooE.at[d, "SPY"] if np.isfinite(betas.at[d, sy]) else np.nan
                     for d, sy, r in zip(t.index, t["sym"], t["ret"])]
    Fd = factors("oo_d")
    yc, yi = ctl_t.groupby(level=0)["ret"].mean(), ibs_t.groupby(level=0)["ret"].mean()
    dfc = pd.concat([yc.rename("y"), Fd], axis=1).dropna()
    Xc = np.column_stack([np.ones(len(dfc)), dfc[FAC].values])
    bc = np.linalg.lstsq(Xc, dfc["y"].values, rcond=None)[0]
    res_c = dfc["y"] - dfc[FAC].values @ bc[1:]
    res_i = (yi.reindex(dfc.index).dropna() - dfc.loc[yi.index.intersection(dfc.index), FAC].values @ bc[1:])
    rng = np.random.default_rng(7)
    allspy = ooE["SPY"]
    spy_adj = _w("oo_d", "SPY")
    for lab, lo, hi in (("2017-20 (IBS OOS)", "2017", "2020"), ("2021-26", "2021", "2026")):
        sl = slice(f"{lo}-01-01", f"{hi}-12-31")
        ti, tc = ibs_t.loc[sl], ctl_t.loc[sl]
        ri, rc = res_i.loc[sl], res_c.loc[sl]
        yci = yc.loc[sl]
        n = ri.size
        draws = rng.choice(len(rc), size=(1000, n))
        pl_raw = np.array([yci.reindex(rc.index).values[d].mean() for d in draws])
        pl_res = np.array([rc.values[d].mean() for d in draws])
        dayraw_i = yi.loc[sl].mean()
        pr(f"[{lab}] IBS trades n={len(ti)} on {n} days; every-top-3 control n={len(tc)}; SPY all-days mean "
           f"{allspy.loc[sl].mean()*1e4:.1f}bp")
        pr(f"   per-trade mean bp: IBS {ti['ret'].mean()*1e4:6.1f} (t {ti['ret'].mean()/ti['ret'].std()*np.sqrt(len(ti)):.2f}) | "
           f"unconditional top-3 {tc['ret'].mean()*1e4:6.1f} | premium {(ti['ret'].mean()-tc['ret'].mean())*1e4:6.1f} | "
           f"beta-adj IBS {ti['badj'].mean()*1e4:6.1f} vs beta-adj control {tc['badj'].mean()*1e4:6.1f} -> "
           f"adj premium {(ti['badj'].mean()-tc['badj'].mean())*1e4:6.1f}")
        a_i, a_c = ri.mean() * 1e4, rc.mean() * 1e4
        w = (ri.mean() - rc.mean()) / np.sqrt(ri.var() / len(ri) + rc.var() / len(rc))
        pr(f"   day-avg residual vs 4 factors (bp/day): IBS days {a_i:6.1f}, all control days {a_c:6.1f}, "
           f"IBS-specific {a_i-a_c:6.1f} (Welch t {w:.2f}); placebo (same day count, 1000): raw pct "
           f"{(pl_raw < dayraw_i).mean()*100:.0f}, residual pct {(pl_res < ri.mean()).mean()*100:.0f} "
           f"[placebo resid 5-95%: {np.percentile(pl_res,5)*1e4:.1f}..{np.percentile(pl_res,95)*1e4:.1f}bp]")

    pr("\n--- market-day timing vs ETF selection (SPY open->open, same window as the trade) ---")
    for lab, lo, hi in (("2017-20", "2017", "2020"), ("2021-26", "2021", "2026")):
        sl = slice(f"{lo}-01-01", f"{hi}-12-31")
        sp = spy_adj.loc[sl]
        di, dc = yi.loc[sl].index, yc.loc[sl].index
        ti, tc = ibs_t.loc[sl], ctl_t.loc[sl]
        rel_i = (ti["ret"] - spy_adj.reindex(ti.index).values).mean()
        rel_c = (tc["ret"] - spy_adj.reindex(tc.index).values).mean()
        pr(f"[{lab}] SPY next-day mean bp: all days {sp.mean()*1e4:5.1f} | control days {sp.reindex(dc).mean()*1e4:5.1f} | "
           f"IBS signal days {sp.reindex(di).mean()*1e4:5.1f} (timing premium vs all {(sp.reindex(di).mean()-sp.mean())*1e4:+.1f}); "
           f"trade minus same-day SPY: IBS {rel_i*1e4:+.1f} vs control {rel_c*1e4:+.1f} (selection premium {(rel_i-rel_c)*1e4:+.1f}bp)")

    # IBS sleeve vs buy-and-hold (decision-date label d; session d+1 open->d+2 open)
    I = B.ibs_days()
    sig = pd.Series({d: np.mean([r for _, _, r in legs]) - 2e-4 for d, legs in I.items()})
    ixd = CAL
    bilN = ADJ_RF.shift(-1)
    sig = sig.reindex(ixd)
    sleeve = sig.fillna(bilN.reindex(ixd).fillna(0.0))
    oo_adj = {sy: _w("oo_d", sy).reindex(ixd) for sy in ("SPY", "QQQ", "TQQQ")}
    pr("\n--- IBS sleeve (fully deployed on signal days, idle BIL, 1bp/side) vs buy&hold open->open ---")
    sleeve_oos = {}
    for lab, lo, hi in (("2017-20", "2017", "2020"), ("2021-26", "2021", "2026"), ("2017-26", "2017", "2026")):
        sl = slice(f"{lo}-01-01", f"{hi}-12-31")
        r = sleeve.loc[sl].iloc[:-2]
        act = sig.loc[sl].iloc[:-2].notna()
        u = act.mean()
        rf = bilN.reindex(r.index)
        pr(f"[{lab}] utilisation (signal days) = {u*100:.0f}% of sessions")
        pr("   " + pfmt("IBS sleeve", perf(r, rf)))
        for sy in ("SPY", "QQQ", "TQQQ"):
            pr("   " + pfmt(f"{sy} buy&hold", perf(oo_adj[sy].loc[r.index], rf)))
        sc = u * oo_adj["SPY"].loc[r.index] + (1 - u) * rf.fillna(0.0)
        pr("   " + pfmt(f"SPY scaled to {u*100:.0f}% util", perf(sc, rf)))
        d = (r - sc)
        pr(f"   IBS minus util-scaled SPY: {d.mean()*252*100:+.1f}%/yr (NW t {nwt(d.values):.2f}); "
           f"IBS excess-of-cash {(r-rf).mean()*252*100:.1f}%/yr vs scaled SPY {(sc-rf).mean()*252*100:.1f}%/yr")
        # exposure-scaled factor regression on the sleeve (excess of BIL)
        xs = act.astype(float)
        Xs = scaled(Fd.reindex(r.index), xs)
        fs = fit(r - rf, Xs)
        pr("   " + fmt("IBS sleeve excess-of-cash", fs))
    # IBS OOS (expanding) on the sleeve 2017-26
    r = sleeve.iloc[:-2]
    xs = sig.iloc[:-2].notna().astype(float)
    rf = bilN.reindex(r.index)
    ibs_leg = (r - rf, scaled(Fd.reindex(r.index), xs))
    o_ibs = oos(r - rf, [ibs_leg], 450)
    pr(fmt_oos("IBS sleeve excess-of-cash", o_ibs) + f" class={classify(o_ibs)}")

    # ---------------------------------------------------------------- 5. portfolios
    pr("\n=== 5. PORTFOLIOS (fractional for risk stats; whole shares for $) ===")
    pr("A = V7 book via Sim.replay (2021-26 only). B IBS 100%; C IBS+TME-A stacked (equal split on overlap); "
       "D = C with IBS at 1.25x margin (12.5% on excess). IBS 1bp/side, TME 2bp/side.")
    wins = {"2021-26": ("2021-02-01", "2026-09-18"), "2017-26": ("2017-01-03", "2026-09-18"),
            "2017-20 (IBS holdout)": ("2017-01-03", "2020-12-31")}
    cfgs = {"B IBS 100%": (1.0, False), "C IBS+TME": (1.0, True), "D IBS1.25x+TME": (1.25, True),
            "E TME only": (0.0, True)}
    sizes = (1000, 3000, 5000, 10000, 25000)
    # A first
    rfA = ADJ_RF.reindex(R.index)
    pA = perf(R["r"], rfA)
    # A alpha / beta (sum-of-legs, in-sample) and OOS above
    betaA = sum(fits[k]["beta"]["MKT"] * (R["x_night"].mean() if k == "night" else R["x_ibs"].mean() if k == "ibs" else 1.0)
                for k in fits)
    pr("\n[2021-26]")
    pr(pfmt("A current book (V7)", pA, f"alpha(in-sample,incl cash) {resid.mean()*252*100:5.1f}% OOS-alpha(ex-cash) "
            f"{(tot_o['alpha']-R['r_cash'].mean()*252)*100:5.1f}% avg dollar MKT beta {fits['night']['beta']['MKT']*R['x_night'].mean()+fits['ibs']['beta']['MKT']*R['x_ibs'].mean():+.2f} "
            f"util overnight {(R['x_night']+R['x_ibs']).mean()*100:.0f}%"))
    dA = {}
    for S in sizes:
        rr = s.replay(p, start=float(S), monthly=0.0)
        yrs = len(rr) / 252
        dA[S] = S * ((rr["E"].iloc[-1] / S) ** (1 / yrs) - 1)
    summ = {"A current book (V7)": dA}
    for wl, (st, en) in wins.items():
        if wl != "2021-26":
            pr(f"\n[{wl}]")
        for cl, (L, tm) in cfgs.items():
            a = run_acct(1.0, False, L, tm, st, en)
            pp = perf(a["r"], ADJ_RF.reindex(a.index))
            al, t_a, bt, lg = beta_alpha(a)
            oo_p = oos(a["r"], lg, 450)
            oo_s = (f"OOS alpha {oo_p['alpha']*100:5.1f}% t {oo_p['t']:4.2f} pos {oo_p['npos']}/{oo_p['nwin']}" if oo_p else "OOS n/a")
            util = (a["x_ibs"] + a["x_tme"]).mean()
            pr(pfmt(cl, pp, f"alpha(in-sample) {al*100:5.1f}% t {t_a:4.2f} dollar-beta {bt:+.2f} {oo_s} util {util*100:.0f}%"))
            if wl == "2021-26" or wl == "2017-26":
                dd = {}
                for S in sizes:
                    aw = run_acct(float(S), True, L, tm, st, en)
                    yrs = len(aw) / 252
                    dd[S] = S * ((aw["E"].iloc[-1] / S) ** (1 / yrs) - 1)
                summ[f"{cl} [{wl}]"] = dd
    pr("\n$/yr on a static account (S x whole-share CAGR, no deposits, PRE-TAX) -- A via Sim.replay, B-E by explicit loop")
    pr(f"{'':32s}" + "".join(f"{('$'+str(S)):>9s}" for S in sizes))
    for k, dd in summ.items():
        pr(f"{k:32s}" + "".join(f"{dd[S]:9.0f}" for S in sizes))
    pr("\nSensitivity: IBS cost 3bp/side (B, 2017-26)")
    a3 = run_acct(1.0, False, 1.0, False, "2017-01-03", "2026-09-18", cost_ibs=3e-4)
    pr(pfmt("B IBS 100% @3bp", perf(a3["r"], ADJ_RF.reindex(a3.index))))
    pr("\nDone.")


if __name__ == "__main__":
    main()
