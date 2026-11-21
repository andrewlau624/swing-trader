"""EXP round 4, N 1234 RFF-WG: Kelly-Malamud-Zhou "virtue of complexity" monthly market timing on Goyal-Welch predictors.

Pre-registration: research/drafts/round1_prose.md, "Amendment - EXP round 4" (N 1233 -> 1236). Program N = 1236.
  - 15 predictors (KMZ list: dfy infl svar de lty tms tbl dfr dp dy ltr ep b/m ntis + lagged market excess return),
    each divided by its trailing 36-month standard deviation (months t-35..t, known at the end of month t).
  - RFF P = 12000 (6000 Gaussian weights, sin+cos), gamma = 2; ridge on a rolling 12-month window (labels R_{s+1},
    s = t-12..t-1, all realised by the end of month t); z in {1e-3..1e3}; z = 1e3 primary.
  - Strategy: k_t * pi_t * R_{t+1}, R = CRSP VW (CRSP_SPvw) minus Rfree; k_t = sd_train(R) / sd_train(in-sample pi * R),
    i.e. the position is scaled so the training-window strategy vol equals training-window market vol (causal).
  - JUDGE: realised months 2021-01..file end. REPORT: 1960-01..2020-12 (published, touched).
  - Gate: judge Sharpe >= market Sharpe + 0.20 AND alpha vs market > 0. Linear control: same ridge on the raw 15.
Ridge as in KMZ: no intercept, no centering, beta(z) = (zI + S'S/T)^-1 S'R/T, solved in kernel form (T = 12).

Data: Goyal's "Updated data (up to 2025)" PredictorData file, Monthly sheet, fetched as CSV from its Google Sheets
gviz endpoint (openpyxl is not installed, so the xlsx itself is kept but not parsed).

    PYTHONPATH=. python3 research/sim/exp_rffwg.py     # -> research/sim/exp_rffwg_out.txt
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_v] = "2"

import math
import pathlib

import numpy as np
import pandas as pd

from research.sim.exp_rff import dsr, ols_hac

ROOT = pathlib.Path(__file__).resolve().parents[2]
CSV = ROOT / "data/research/exp_rffwg/gw_monthly.csv"
OUT = ROOT / "research/sim/exp_rffwg_out.txt"

N_TRIALS = 1236
N_W, GAMMA = 6000, 2.0               # 6000 weights -> P = 12000 features
WIN, STDWIN = 12, 36
ZS = [1e-3, 1e-2, 1e-1, 1e0, 1e1, 1e2, 1e3]
Z_PRIMARY = 1e3
NW_LAGS = 3
JUDGE_START = pd.Period("2021-01", "M")
REP_START, REP_END = pd.Period("1960-01", "M"), pd.Period("2020-12", "M")
N_SEEDS_ROBUST = 20

lines: list[str] = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    lines.append(s)


def load():
    raw = pd.read_csv(CSV, dtype=str)
    df = pd.DataFrame({c: pd.to_numeric(raw[c].str.replace(",", "", regex=False), errors="coerce") for c in raw.columns})
    df.index = pd.PeriodIndex([pd.Period(f"{int(v)//100}-{int(v)%100:02d}", "M") for v in df["yyyymm"]])
    return df


def predictors(df, pub_lag=False, expanding=False):
    """15 KMZ predictors at month-end t. pub_lag=True (report-only audit): infl, b/m, ntis lagged 1 month; E12 lagged 3."""
    L = (lambda s, k: s.shift(k)) if pub_lag else (lambda s, k: s)
    lp, ld = np.log(df["Index"]), np.log(df["D12"])
    le = L(np.log(df["E12"]), 3)
    R = df["CRSP_SPvw"] - df["Rfree"]
    P = pd.DataFrame({
        "dp": ld - lp, "dy": ld - lp.shift(1), "ep": le - lp, "de": ld - le,
        "svar": df["svar"], "bm": L(df["b/m"], 1), "ntis": L(df["ntis"], 1), "tbl": df["tbl"], "lty": df["lty"],
        "ltr": df["ltr"], "tms": df["lty"] - df["tbl"], "dfy": df["BAA"] - df["AAA"], "dfr": df["corpr"] - df["ltr"],
        "infl": L(df["infl"], 1), "mkt": R,
    })
    sdv = P.expanding(min_periods=STDWIN).std(ddof=1) if expanding else P.rolling(STDWIN, min_periods=STDWIN).std(ddof=1)
    G = P / sdv
    G = G.replace([np.inf, -np.inf], np.nan)          # zero trailing sd (tbl pegged 1945-47): undefined -> month excluded
    return G, R


def ridge_path(X, y, xnew, zs):
    """KMZ ridge, no intercept. Returns (forecast at xnew, in-sample fitted) per z."""
    T = X.shape[0]
    K = X @ X.T
    kn = X @ xnew
    s, Q = np.linalg.eigh(K)
    s = np.clip(s, 0, None)
    qy, qk = Q.T @ y, Q.T @ kn
    out = []
    for z in zs:
        a = qy / (s + z * T)
        out.append((float(qk @ a), Q @ (s * a)))
    return out


def walk(Feat, G, R, zs):
    """Feat: T x P feature matrix aligned with G rows. Returns DataFrame of strategy returns per z (index = realised month)."""
    idx = G.index
    ok = G.notna().all(1).to_numpy() & np.isfinite(Feat).all(1)
    Rv = R.to_numpy()
    rows = {z: {} for z in zs}
    raw = {z: {} for z in zs}
    pos = {z: {} for z in zs}
    for t in range(WIN, len(idx) - 1):
        tr = np.arange(t - WIN, t)
        if not (ok[tr].all() and ok[t] and np.isfinite(Rv[tr + 1]).all() and np.isfinite(Rv[t + 1])):
            continue
        y = Rv[tr + 1]
        res = ridge_path(Feat[tr], y, Feat[t], zs)
        for z, (pi, fit) in zip(zs, res):
            sdu = np.std(fit * y, ddof=1)
            k = np.std(y, ddof=1) / sdu if sdu > 0 else np.nan
            rows[z][idx[t + 1]] = k * pi * Rv[t + 1]
            raw[z][idx[t + 1]] = pi * Rv[t + 1]
            pos[z][idx[t + 1]] = k * pi
    f = lambda d: pd.DataFrame({z: pd.Series(d[z]) for z in zs})
    return f(rows), f(raw), f(pos)


def rff(G, seed):
    rng = np.random.default_rng(seed)
    W = rng.standard_normal((G.shape[1], N_W))
    A = GAMMA * (np.nan_to_num(G.to_numpy()) @ W)
    X = np.hstack([np.sin(A), np.cos(A)])
    X[~G.notna().all(1).to_numpy()] = np.nan
    return X


def stats(u, m):
    u, m = u.dropna(), m.reindex(u.dropna().index)
    sr = u.mean() / u.std(ddof=1) * math.sqrt(12)
    srm = m.mean() / m.std(ddof=1) * math.sqrt(12)
    a, t, b = ols_hac(u.to_numpy(), m.to_numpy(), lags=NW_LAGS)
    return dict(n=len(u), sr=sr, srm=srm, d=sr - srm, a=a * 12, t=t, b=b, ann=u.mean() * 12, vol=u.std(ddof=1) * math.sqrt(12))


def fmt(name, s):
    return (f"  {name:<14} n {s['n']:4d}  SR {s['sr']:+.3f}  mkt SR {s['srm']:+.3f}  dSR {s['d']:+.3f}  "
            f"alpha {s['a']*100:+6.2f}%/yr t {s['t']:+.2f}  beta {s['b']:+.2f}  ret {s['ann']*100:+6.2f}%/yr vol {s['vol']*100:5.1f}%")


def periods(U):
    j = U[U.index >= JUDGE_START]
    r = U[(U.index >= REP_START) & (U.index <= REP_END)]
    return j, r


def block(title, U, R, zs, primary_note=""):
    say(title)
    for lab, sl in zip(("JUDGE", "REPORT 1960-2020"), periods(U)):
        say(f" {lab}: {sl.index.min()}..{sl.index.max()}")
        for z in zs:
            say(fmt(f"z={z:g}" + (" *" if z == Z_PRIMARY else ""), stats(sl[z], R)))
    if primary_note:
        say(primary_note)


def main():
    df = load()
    say("N 1234 RFF-WG  (program N 1236; pre-registered in round1_prose.md 'Amendment - EXP round 4')")
    say(f"data: {CSV.relative_to(ROOT)}  rows {len(df)}  {df.index.min()}..{df.index.max()}")
    chk = df.loc[[pd.Period('2008-10', 'M'), pd.Period('2020-03', 'M'), df.index.max()], ["Index", "CRSP_SPvw", "Rfree", "tbl", "infl"]]
    say("spot-check rows:\n" + chk.to_string())
    G, R = predictors(df)
    first = G.dropna().index.min()
    say(f"15 predictors complete from {first} ({G.dropna().shape[0]} months); market excess = CRSP_SPvw - Rfree")
    say(f"missing in judge window: {int(G[G.index >= pd.Period('2020-01','M')].isna().any(axis=1).sum())} months")

    # primary: RFF seed 0
    X0 = rff(G, 0)
    U, Uraw, Pos = walk(X0, G, R, ZS)
    block("\n== RFF (P=12000, gamma=2, seed 0), vol-scaled position (REGISTERED PRIMARY = z 1e3 *) ==", U, R, ZS)
    j, _ = periods(U)
    sp = stats(j[Z_PRIMARY], R)
    gate = (sp["d"] >= 0.20) and (sp["a"] > 0)
    say(f"\nGATE (judge, z=1e3): dSR {sp['d']:+.3f} (need >= +0.20), alpha {sp['a']*100:+.2f}%/yr (need > 0), t {sp['t']:+.2f}"
        f"  -> {'PASS' if gate else 'DEAD'}")
    say(f"DSR at N {N_TRIALS} (judge, z=1e3): {dsr(j[Z_PRIMARY].dropna().to_numpy(), N_TRIALS):.3f}")
    pj = Pos[Pos.index >= JUDGE_START][Z_PRIMARY].dropna()
    say(f"judge position z=1e3: mean {pj.mean():+.2f}  share long {np.mean(pj > 0):.2f}  mean|dpos| {pj.diff().abs().mean():.2f}"
        f"  -> net at 2.5bp/side {stats(j[Z_PRIMARY] - 2.5e-4 * Pos[Z_PRIMARY].diff().abs().reindex(j.index).fillna(0), R)['sr']:+.3f} SR")

    block("\n-- sensitivity (report only): unscaled pi_t * R_{t+1} (KMZ's raw timing return), seed 0 --", Uraw, R, ZS)

    # seed robustness at z=1e3
    srs = []
    for sd in range(1, N_SEEDS_ROBUST + 1):
        Us, _, _ = walk(rff(G, sd), G, R, [Z_PRIMARY])
        js = Us[Us.index >= JUDGE_START][Z_PRIMARY]
        srs.append(stats(js, R)["d"])
    srs = np.array(srs)
    say(f"\n-- seed robustness (report only), judge dSR at z=1e3 over seeds 1..{N_SEEDS_ROBUST}: "
        f"median {np.median(srs):+.3f}  min {srs.min():+.3f}  max {srs.max():+.3f}  share >= +0.20: {np.mean(srs >= 0.2):.2f}")

    # linear control
    UL, ULraw, _ = walk(G.to_numpy(), G, R, ZS)
    block("\n== LINEAR-RIDGE CONTROL (raw 15 standardised predictors, same window/z/scaling) ==", UL, R, ZS)

    # publication-lag audit
    Gl, _ = predictors(df, pub_lag=True)
    Ul, _, _ = walk(rff(Gl, 0), Gl, R, ZS)
    block("\n-- look-ahead audit (report only): infl, b/m, ntis lagged 1m; E12 (ep, de) lagged 3m; RFF seed 0 --", Ul, R, ZS)

    # diagnostic: kernel degeneracy under the registered standardisation
    g = G.dropna()
    for lag in (1, 12):
        d2 = ((g - g.shift(lag)) ** 2).sum(1).dropna()
        say(f"\ndiag: registered 36m-trailing standardisation, lag-{lag} squared distance median {d2.median():.1f} -> "
            f"Gaussian kernel exp(-gamma^2 d2/2) median {np.exp(-GAMMA**2 * d2 / 2).median():.1e}")

    # report-only: KMZ-paper standardisation (predictors / expanding sd; return / trailing 12m sd). NOT the registered rule.
    Ge, _ = predictors(df, expanding=True)
    Rt = R / R.rolling(12, min_periods=12).std(ddof=1).shift(1)      # label R_{s+1}/sd12(s): position pi_t/sd12(t), causal
    ge = Ge.dropna()
    d2 = ((ge - ge.shift(1)) ** 2).sum(1).dropna()
    say(f"diag: KMZ-paper standardisation, lag-1 squared distance median {d2.median():.2f} -> kernel median "
        f"{np.exp(-GAMMA**2 * d2 / 2).median():.2f}")
    _, Uk, _ = walk(rff(Ge, 0), Ge, Rt, ZS)
    block("\n-- REPORT ONLY, NOT GATED: KMZ-paper standardisation (expanding-sd predictors, 12m-vol-scaled return), RFF seed 0 --", Uk, R, ZS)
    srs_j, srs_r = [], []
    for sd in range(1, N_SEEDS_ROBUST + 1):
        _, Us, _ = walk(rff(Ge, sd), Ge, Rt, [Z_PRIMARY])
        jj, rr = periods(Us)
        srs_j.append(stats(jj[Z_PRIMARY], R)["d"]); srs_r.append(stats(rr[Z_PRIMARY], R)["d"])
    say(f"   seeds 1..{N_SEEDS_ROBUST} z=1e3 dSR: judge median {np.median(srs_j):+.3f} [{min(srs_j):+.3f},{max(srs_j):+.3f}]  "
        f"1960-2020 median {np.median(srs_r):+.3f} [{min(srs_r):+.3f},{max(srs_r):+.3f}]")
    _, UkL, _ = walk(Ge.to_numpy(), Ge, Rt, ZS)
    block("-- REPORT ONLY: linear ridge under KMZ-paper standardisation --", UkL, R, ZS)

    # buy-and-hold reference
    m = R[R.index >= JUDGE_START].dropna()
    say(f"\nmarket excess judge: n {len(m)}  mean {m.mean()*1200:+.2f}%/yr  SR {m.mean()/m.std(ddof=1)*math.sqrt(12):+.3f}")
    OUT.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
