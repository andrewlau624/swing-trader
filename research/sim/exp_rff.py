"""EXP round A1 RFF-TIME (N 1212) and A2 RFF-ROT (N 1213): random-Fourier-feature ridge timing / rotation on 8 ETFs.

Pre-registration: research/drafts/round1_prose.md, "Amendment - EXP round (user 2026-11-20 ...)", Common frame + A1 + A2.
FIT 2002-08..2010-12 (lambda, z-score stats, sd(f_fit) frozen there), JUDGE 2011-01..2020-12, REPORT 2021-01..2026-09
(Alpaca, descriptive). Program N = 1218.

Data: Sharadar SFP (split-adjusted OHLC, NOT dividend-adjusted -> dividends from cache_ACTIONS are added to build a
total-return close; O/H/L scaled by the same factor) through 2020-12-31, chained with Alpaca etf_daily (split+dividend
adjusted) close-to-close returns from 2021-01-04.

Ridge is solved in kernel form (K = X X', n x n with n <= ~5,900 < P = 6,000); one eigendecomposition per refit serves all
lambdas and all placebo label vectors (seed 0); Cholesky per distinct lambda elsewhere.

    PYTHONPATH=. python3 research/sim/exp_rff.py     # -> research/sim/exp_rff_out.txt
"""
from __future__ import annotations

import math
import pathlib
import time

import numpy as np
import pandas as pd
import scipy.stats as SS

ROOT = pathlib.Path(__file__).resolve().parents[2]
SFP = ROOT / "data/research/nx/cache_SFP.parquet"
ACT = ROOT / "data/research/nx/cache_ACTIONS.parquet"
ALP = ROOT / "data/research/night/etf_daily.parquet"
OUT = ROOT / "research/sim/exp_rff_out.txt"

ETFS = ["SPY", "QQQ", "IWM", "TLT", "XLK", "XLF", "XLE", "XLU"]
N_TRIALS = 1218
P_BASE, N_RFF, GAMMA = 400, 3000, 2.0
LAMS = 10.0 ** np.arange(-1.0, 5.01, 0.5)          # 1e-1..1e5, half-decade log grid (13 values)
REFIT = 21
C1, C3 = 1e-4, 3e-4
N_PLACEBO = 200
NW_LAGS = 5
FIT_START, FIT_SPLIT, FIT_END = pd.Timestamp("2002-08-01"), pd.Timestamp("2008-12-31"), pd.Timestamp("2010-12-31")
JUDGE_END = pd.Timestamp("2020-12-31")
SPLICE = pd.Timestamp("2020-12-31")

lines: list[str] = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    lines.append(s)


# ----------------------------------------------------------------------------- data
def load_panel():
    d = pd.read_parquet(SFP, filters=[("ticker", "in", ETFS)])
    d["date"] = pd.to_datetime(d.date)
    a = pd.read_parquet(ACT, filters=[("ticker", "in", ETFS)])
    a = a[a.action == "dividend"].copy()
    a["date"] = pd.to_datetime(a.date)
    div = a.groupby(["ticker", "date"]).value.sum()
    O, H, L, C = {}, {}, {}, {}
    for tk in ETFS:
        g = d[d.ticker == tk].sort_values("date").drop_duplicates("date").set_index("date")
        g = g[(g.index >= pd.Timestamp("2002-07-30")) & (g.index <= SPLICE)]
        dv = div.get(tk, pd.Series(dtype=float)).reindex(g.index).fillna(0.0)
        tr = (g.close + dv) / g.close.shift(1)               # total-return gross (div assumed split-adjusted)
        tr.iloc[0] = 1.0
        f = tr.cumprod() / g.close * g.close.iloc[0]          # factor mapping raw -> TR level
        C[tk], H[tk], L[tk] = g.close * f, g.high * f, g.low * f
    sh = pd.DataFrame(C).dropna(), pd.DataFrame(H), pd.DataFrame(L)
    idx = sh[0].index
    Cs, Hs, Ls = sh[0], sh[1].reindex(idx), sh[2].reindex(idx)
    # Alpaca after the splice: chain close-to-close returns; scale H/L by the same per-day factor
    e = pd.read_parquet(ALP)
    e = e[e.symbol.isin(ETFS)].copy()
    e["date"] = e.timestamp.dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
    pc = e.pivot_table(index="date", columns="symbol", values="close").sort_index()[ETFS]
    ph = e.pivot_table(index="date", columns="symbol", values="high").sort_index()[ETFS]
    pl = e.pivot_table(index="date", columns="symbol", values="low").sort_index()[ETFS]
    # overlap check (Alpaca vs Sharadar-TR close-to-close returns, 2016-2020)
    ov = pd.concat([Cs.pct_change().stack(), pc.pct_change().stack()], axis=1, keys=["s", "a"]).dropna()
    ov = ov[ov.index.get_level_values(0) > pd.Timestamp("2016-01-05")]
    dif = (ov.s - ov.a).abs()
    say(f"Alpaca vs Sharadar-TR overlap 2016-2020: n {len(ov)}, median |ret diff| {dif.median()*1e4:.2f}bp, "
        f"mean {dif.mean()*1e4:.2f}bp, share >5bp {(dif > 5e-4).mean():.3f}")
    pc, ph, pl = pc[pc.index >= pd.Timestamp("2020-12-31")], ph[ph.index >= pd.Timestamp("2020-12-31")], pl[pl.index >= pd.Timestamp("2020-12-31")]
    pc, ph, pl = pc.dropna(), ph.reindex(pc.dropna().index), pl.reindex(pc.dropna().index)
    scale = Cs.iloc[-1] / pc.iloc[0]
    assert pc.index[0] == Cs.index[-1], (pc.index[0], Cs.index[-1])
    Ca, Ha, La = pc.iloc[1:] * scale, ph.iloc[1:] * scale, pl.iloc[1:] * scale
    C = pd.concat([Cs, Ca]); H = pd.concat([Hs, Ha]); L = pd.concat([Ls, La])
    return C, H, L


def base_features(C, H, L, rng):
    lc = np.log(C)
    r = lc.diff()
    rng_hl = (H - L)
    ibs = ((C - L) / rng_hl.where(rng_hl > 0)).fillna(0.5).clip(0, 1)
    assets = rng.integers(0, 8, P_BASE)
    Ls = rng.integers(2, 121, P_BASE)
    offs = rng.integers(0, 21, P_BASE)
    stats = rng.integers(0, 4, P_BASE)
    cache = {}
    cols = []
    for a, Lw, o, s in zip(assets, Ls, offs, stats):
        key = (a, Lw, s)
        if key not in cache:
            tk = ETFS[a]
            if s == 0:
                v = lc[tk] - lc[tk].shift(Lw)
            elif s == 1:
                v = r[tk].rolling(Lw).std(ddof=0)
            elif s == 2:
                v = lc[tk] - lc[tk].rolling(Lw + 1).max()
            else:
                v = ibs[tk].rolling(Lw + 1).mean()
            cache[key] = v
        cols.append(cache[key].shift(o).to_numpy())
    Z = np.column_stack(cols)
    desc = dict(stat_counts=np.bincount(stats, minlength=4).tolist(), asset_counts=np.bincount(assets, minlength=8).tolist())
    return Z, desc


# ----------------------------------------------------------------------------- stats
def ols_hac(y, x, lags=NW_LAGS):
    y = np.asarray(y, float); x = np.asarray(x, float)
    X = np.column_stack([np.ones_like(x), x])
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    e = y - X @ b
    u = X * e[:, None]
    S = u.T @ u
    for l in range(1, lags + 1):
        w = 1 - l / (lags + 1)
        G = u[l:].T @ u[:-l]
        S += w * (G + G.T)
    XtXi = np.linalg.inv(X.T @ X)
    V = XtXi @ S @ XtXi
    return b[0], b[0] / math.sqrt(V[0, 0]), b[1]


def alpha_only(y, x):
    X = np.column_stack([np.ones_like(x), x])
    return np.linalg.lstsq(X, y, rcond=None)[0][0]


def sharpe(x):
    x = np.asarray(x, float)
    return x.mean() / x.std(ddof=1) * math.sqrt(252)


def maxdd(x):
    w = np.cumprod(1 + np.asarray(x, float))
    return float((w / np.maximum.accumulate(w) - 1).min())


def dsr(x, n_trials):
    x = np.asarray(x, float)
    T = len(x)
    sr = x.mean() / x.std(ddof=1)
    sk = SS.skew(x); ku = SS.kurtosis(x, fisher=False)
    g = 0.5772156649
    sr0 = math.sqrt(1.0 / T) * ((1 - g) * SS.norm.ppf(1 - 1 / n_trials) + g * SS.norm.ppf(1 - 1 / (n_trials * math.e)))
    z = (sr - sr0) * math.sqrt(T - 1) / math.sqrt(max(1e-12, 1 - sk * sr + (ku - 1) / 4 * sr ** 2))
    return float(SS.norm.cdf(z))


# ----------------------------------------------------------------------------- kernel ridge
def center(Ktt, Knt):
    m = Ktt.mean(0)
    mu = m.mean()
    Kc = Ktt - m[None, :] - m[:, None] + mu
    Knc = Knt - Knt.mean(1)[:, None] - m[None, :] + mu
    return Kc, Knc


def krr_predict(Ktt, Knt, Y, lam_cols, use_eig):
    """f (demeaned forecasts) for each column of Y with its own lambda. Y: n x m, lam_cols: m."""
    Kc, Knc = center(Ktt, Knt)
    Yc = Y - Y.mean(0)
    n = Kc.shape[0]
    out = np.empty((Knt.shape[0], Y.shape[1]))
    if use_eig:
        s, Q = np.linalg.eigh(Kc)
        s = np.clip(s, 0, None)
        B = Q.T @ Yc
        B /= (s[:, None] + lam_cols[None, :])
        out[:] = (Knc @ Q) @ B
    else:
        for lam in np.unique(lam_cols):
            j = np.where(lam_cols == lam)[0]
            cf = np.linalg.cholesky(Kc + lam * np.eye(n))
            A = np.linalg.solve(cf.T, np.linalg.solve(cf, Yc[:, j]))
            out[:, j] = Knc @ A
    return out


def select_lambda(K, Y, tr_n, va_rows):
    """single split: train rows [0,tr_n), validate va_rows; returns lambda index per column (ties -> larger lambda)."""
    Kc, Knc = center(K[:tr_n, :tr_n], K[np.ix_(va_rows, np.arange(tr_n))])
    ybar = Y[:tr_n].mean(0)
    Yc = Y[:tr_n] - ybar
    s, Q = np.linalg.eigh(Kc)
    s = np.clip(s, 0, None)
    B0 = Q.T @ Yc
    KQ = Knc @ Q
    Yv = Y[va_rows]
    mse = np.empty((len(LAMS), Y.shape[1]))
    for i, lam in enumerate(LAMS):
        F = KQ @ (B0 / (s[:, None] + lam))
        mse[i] = ((Yv - ybar - F) ** 2).mean(0)
    # argmin with ties to larger lambda
    best = len(LAMS) - 1 - np.argmin(mse[::-1], axis=0)
    return best, mse


# ----------------------------------------------------------------------------- pipeline
def run_seed(seed, C, H, L, dates, Rlog, Rsimple, want_placebo, want_a2, end_row_judge, placebo_shifts):
    t0 = time.time()
    rng = np.random.default_rng(seed)
    Z, desc = base_features(C, H, L, rng)
    valid = np.isfinite(Z).all(1)
    first = int(np.argmax(valid))
    assert valid[first:].all()
    Z = Z[first:]
    dts = dates[first:]
    fitmask = dts <= FIT_END
    mu, sd = Z[fitmask].mean(0), Z[fitmask].std(0)
    sd[sd == 0] = 1.0
    Z = (Z - mu) / sd
    W = rng.standard_normal((P_BASE, N_RFF))
    S = GAMMA * (Z @ W)
    X = np.hstack([np.sin(S), np.cos(S)])
    del S
    K = X @ X.T
    del X
    T = len(dts)
    # labels: row t -> log return t->t+1 (last row has none)
    ylog = Rlog[first:]                                    # ylog[t] = log ret realised at t+1 (NaN for last row)
    targ_cols = [0] if not want_a2 else list(range(8))     # A1 uses SPY = column 0
    Ytrue = ylog[:, targ_cols]
    # lambda split
    dnext = np.append(dts[1:], np.datetime64("NaT"))
    tr_n = int(np.sum(dnext <= np.datetime64(FIT_SPLIT)))  # rows whose target realised by 2008-12-31 (contiguous from 0)
    va_rows = np.where((dts > np.datetime64(FIT_SPLIT)) & (dnext <= np.datetime64(FIT_END)))[0]
    # label matrices: true + placebos (placebo: circular shift of the label segment through the judge end)
    seg = end_row_judge - first                             # rows [0, seg) have labels realised <= JUDGE_END
    Ys = [Ytrue]
    if want_placebo:
        for k in placebo_shifts:
            Yp = Ytrue.copy()
            Yp[:seg] = np.roll(Ytrue[:seg], k, axis=0)
            Ys.append(Yp)
    Yall = np.hstack(Ys)                                    # T x (m * (1+npl))
    m = len(targ_cols)
    bi, mse = select_lambda(K, np.nan_to_num(Yall), tr_n, va_rows)
    lam_cols = LAMS[bi]
    # walk-forward from first 2009 row, every 21 rows
    r0 = int(np.argmax(dts > np.datetime64(FIT_SPLIT)))
    F = np.full((T, Yall.shape[1]), np.nan)
    judge_last_pred = seg - 1                               # last row whose position earns a judge-period return
    tau = r0
    n_eig = 0
    while tau < T:
        blk = np.arange(tau, min(tau + REFIT, T))
        Ktt = K[:tau, :tau]
        Knt = K[np.ix_(blk, np.arange(tau))]
        if tau <= judge_last_pred:
            cols = np.arange(Yall.shape[1])
        else:
            cols = np.arange(m)                             # report period: true labels only
        Yt = Yall[:tau][:, cols]
        assert np.isfinite(Yt).all()
        lc = lam_cols[cols]
        use_eig = len(np.unique(lc)) > 4
        n_eig += use_eig
        F[np.ix_(blk, cols)] = krr_predict(Ktt, Knt, Yt, lc, use_eig)
        tau += REFIT
    say(f"  seed {seed}: rows {T} from {pd.Timestamp(dts[0]).date()}, lambda-split train {tr_n} val {len(va_rows)}, "
        f"refits {(T - r0 + REFIT - 1)//REFIT} (eig {n_eig}), {time.time()-t0:.0f}s; base stats {desc['stat_counts']} assets {desc['asset_counts']}")
    return dict(first=first, dts=dts, F=F, lam_cols=lam_cols, bi=bi, mse=mse, m=m, r0=r0, seg=seg, K_T=T, ylog=ylog)


def a1_positions(F_col, dts, r0):
    fit_rows = (dts > np.datetime64(FIT_SPLIT)) & (dts <= np.datetime64(FIT_END))
    sdf = np.nanstd(F_col[fit_rows], ddof=1)
    pos = np.clip(1 + F_col / sdf, 0, 1.5)
    return pos, sdf


def a2_weights(Fc, ybar):
    fc = Fc + ybar
    w = np.zeros_like(fc)
    ok = np.isfinite(fc).all(1)
    top = np.argsort(-np.where(ok[:, None], fc, 0), axis=1)[:, :2]
    rows = np.where(ok)[0]
    w[rows[:, None], top[rows]] = 0.5
    w[~ok] = np.nan
    return w


def pnl_series(pos, Rnext, c):
    """pos: T x k (or T); Rnext[t] = simple return t->t+1. net[t] realised at t+1."""
    pos = pos if pos.ndim == 2 else pos[:, None]
    Rn = Rnext if Rnext.ndim == 2 else Rnext[:, None]
    turn = np.abs(np.diff(pos, axis=0, prepend=np.nan)).sum(1)
    gross = (pos * Rn).sum(1)
    return gross - c * turn, turn


def evaluate(name, net1, net3, bench, real_dates, pos_exp, placebo_alphas=None, label_bench="SPY"):
    """net*, bench: arrays over judge realisation dates."""
    res = {}
    a, t, b = ols_hac(net1, bench)
    res.update(alpha=a, t=t, beta=b)
    h1 = real_dates <= np.datetime64("2015-12-31")
    res["a_h1"] = alpha_only(net1[h1], bench[h1]); res["a_h2"] = alpha_only(net1[~h1], bench[~h1])
    res["sr"], res["sr_b"] = sharpe(net1), sharpe(bench)
    a3, t3, _ = ols_hac(net3, bench)
    res["a3"], res["t3"] = a3, t3
    o = np.argsort(net1)[:-5]
    res["a_ex5"] = alpha_only(net1[o], bench[o])
    res["med"], res["hit"], res["mdd"], res["mdd_b"] = np.median(net1), (net1 > 0).mean(), maxdd(net1), maxdd(bench)
    res["exp"] = np.nanmean(pos_exp)
    res["dsr"] = dsr(net1, N_TRIALS)
    res["ann"] = (np.prod(1 + net1) ** (252 / len(net1)) - 1)
    if placebo_alphas is not None:
        res["pct"] = (placebo_alphas < a).mean() * 100
        res["pl_p95"] = np.percentile(placebo_alphas, 95)
    g = [a > 0 and t >= 2, res["a_h1"] > 0 and res["a_h2"] > 0, res["sr"] - res["sr_b"] >= 0.20,
         a3 > 0 and t3 >= 2, (res["pct"] >= 95) if placebo_alphas is not None else None, res["a_ex5"] > 0]
    res["gates"] = g
    say(f"  {name}: judge alpha vs {label_bench} {a*1e4:+.2f}bp/day NW t {t:+.2f} (beta {b:.2f}); halves 2011-15 {res['a_h1']*1e4:+.2f} / "
        f"2016-20 {res['a_h2']*1e4:+.2f}bp")
    say(f"    net Sharpe {res['sr']:.2f} vs {label_bench} {res['sr_b']:.2f} (diff {res['sr']-res['sr_b']:+.2f}); CAGR {res['ann']*100:+.1f}%; "
        f"3bp/side alpha {a3*1e4:+.2f}bp t {t3:+.2f}; ex-top-5 alpha {res['a_ex5']*1e4:+.2f}bp")
    pl = f"placebo pct {res['pct']:.1f} (p95 {res['pl_p95']*1e4:+.2f}bp, n {len(placebo_alphas)})" if placebo_alphas is not None else "placebo n/a"
    say(f"    median day {res['med']*1e4:+.2f}bp, hit {res['hit']*100:.1f}%, maxDD {res['mdd']*100:.1f}% ({label_bench} {res['mdd_b']*100:.1f}%), "
        f"mean exposure {res['exp']:.2f}, DSR(N {N_TRIALS}) {res['dsr']:.3f}; {pl}")
    names = ["G1 alpha>0 & t>=2", "G2 both halves>0", "G3 dSharpe>=+0.20", "G4 3bp/side (alpha>0 & t>=2)", "G5 placebo>=95th", "G6 ex-top-5>0"]
    say("    gates: " + "; ".join(f"{n} {'n/a' if v is None else ('PASS' if v else 'FAIL')}" for n, v in zip(names, g)))
    return res


def main():
    T0 = time.time()
    say("EXP round A1 RFF-TIME (N 1212) / A2 RFF-ROT (N 1213) -- pre-reg round1_prose.md 'Amendment - EXP round'; program N 1218")
    say(f"P_base {P_BASE}, RFF {2*N_RFF} (gamma {GAMMA}), lambda grid {', '.join(f'{l:g}' for l in LAMS)}, refit every {REFIT}, "
        f"cost {C1*1e4:.0f}bp/side (shock {C3*1e4:.0f}), placebo {N_PLACEBO} circular shifts U{{250..2000}}, NW lags {NW_LAGS}")
    C, H, L = load_panel()
    dates = C.index.to_numpy()
    say(f"panel {len(C)} sessions {C.index[0].date()}..{C.index[-1].date()} (Sharadar TR to {SPLICE.date()}, Alpaca after)")
    lr = np.log(C).diff().shift(-1).to_numpy()              # lr[t] = log ret t->t+1
    sr_ = C.pct_change().shift(-1).to_numpy()               # simple
    dnext = np.append(dates[1:], np.datetime64("NaT"))
    end_row_judge = int(np.sum(dnext <= np.datetime64(JUDGE_END)))   # rows [0,end) have target realised <= 2020-12-31
    prng = np.random.default_rng(12345)
    shifts = prng.integers(250, 2001, N_PLACEBO)

    results = {}
    seeds_out = {}
    for seed in range(5):
        out = run_seed(seed, C, H, L, dates, lr, sr_, want_placebo=(seed == 0), want_a2=(seed == 0),
                       end_row_judge=end_row_judge, placebo_shifts=shifts)
        seeds_out[seed] = out
        say(f"    lambda chosen (true labels): {', '.join(f'{ETFS[j]} {out['lam_cols'][j]:g}' for j in range(out['m']))}")

    # ---- evaluation
    def judge_slice(out):
        first, dts = out["first"], out["dts"]
        rows = np.arange(len(dts))
        realised = np.append(dts[1:], np.datetime64("NaT"))
        jm = (realised > np.datetime64(FIT_END)) & (realised <= np.datetime64(JUDGE_END))
        rm = (realised > np.datetime64(JUDGE_END))
        return first, dts, realised, jm, rm

    say("\n=== A1 RFF-TIME (position = clip(1 + f/sd(f_fit), 0, 1.5), SPY; judged vs SPY) ===")
    a1_res = {}
    rep = {}
    for seed in range(5):
        out = seeds_out[seed]
        first, dts, realised, jm, rm = judge_slice(out)
        Rn = sr_[first:, 0]
        F = out["F"]
        pos, sdf = a1_positions(F[:, 0], dts, out["r0"])
        net1, _ = pnl_series(pos, Rn, C1); net3, _ = pnl_series(pos, Rn, C3)
        pl_alphas = None
        if seed == 0:
            pl_alphas = []
            m = out["m"]
            for p in range(N_PLACEBO):
                col = m * (p + 1) + 0
                pp, _ = a1_positions(F[:, col], dts, out["r0"])
                nn, _ = pnl_series(pp, Rn, C1)
                pl_alphas.append(alpha_only(nn[jm], Rn[jm]))
            pl_alphas = np.array(pl_alphas)
        say(f" seed {seed} (sd(f_fit) {sdf:.2e}, lambda {out['lam_cols'][0]:g})")
        a1_res[seed] = evaluate(f"A1 seed {seed}", net1[jm], net3[jm], Rn[jm], realised[jm], pos[np.where(jm)[0]], pl_alphas)
        ok = rm & np.isfinite(Rn)
        rep[seed] = (net1[ok], net3[ok], Rn[ok], pos[ok], realised[ok])

    say("\n=== A2 RFF-ROT (top-2 of 8 by ridge forecast, EW, 1.0x; judged vs EW 8-ETF basket) ===")
    out = seeds_out[0]
    first, dts, realised, jm, rm = judge_slice(out)
    Rn8 = sr_[first:, :]
    ew = Rn8.mean(1)
    F = out["F"]
    T = len(dts)
    ylog = out["ylog"]

    def ybar_for(Ylab):
        # intercept = mean of training labels [0, tau) for each walk-forward block
        yb = np.full((T, Ylab.shape[1]), np.nan)
        tau = out["r0"]
        cs = np.nancumsum(np.nan_to_num(Ylab), axis=0)
        while tau < T:
            blk = slice(tau, min(tau + REFIT, T))
            yb[blk] = cs[tau - 1] / tau
            tau += REFIT
        return yb

    Ytrue = ylog[:, :8]
    w = a2_weights(F[:, :8], ybar_for(Ytrue))
    net1, turn = pnl_series(w, Rn8, C1); net3, _ = pnl_series(w, Rn8, C3)
    pl_alphas = []
    seg = out["seg"]
    for p in range(N_PLACEBO):
        Yp = Ytrue.copy(); Yp[:seg] = np.roll(Ytrue[:seg], shifts[p], axis=0)
        wp = a2_weights(F[:, 8 * (p + 1): 8 * (p + 2)], ybar_for(Yp))
        nn, _ = pnl_series(wp, Rn8, C1)
        pl_alphas.append(alpha_only(nn[jm], ew[jm]))
    pl_alphas = np.array(pl_alphas)
    a2 = evaluate("A2 seed 0", net1[jm], net3[jm], ew[jm], realised[jm], w[jm].sum(1), pl_alphas, label_bench="EW8")
    jr = np.where(jm)[0]
    say(f"    mean daily turnover {np.nanmean(turn[jr]):.2f}; share of days holding each ETF: " +
        ", ".join(f"{ETFS[j]} {(w[jr, j] > 0).mean()*100:.0f}%" for j in range(8)))
    say("    (A2 seeds 1-4 not run: spec states the seed rule for A1 only; A2 is gated on seed 0)")

    # ---- verdicts
    say("\n=== VERDICTS ===")
    g0 = a1_res[0]["gates"]
    n13 = sum(all(a1_res[s]["gates"][:3]) for s in range(5))
    a1_pass = all(g0) and n13 >= 3
    say(f"A1 RFF-TIME (N 1212): seed 0 gates 1-6 {'all PASS' if all(g0) else 'not all pass'}; seeds passing gates 1-3: {n13}/5 "
        f"({', '.join(str(s) for s in range(5) if all(a1_res[s]['gates'][:3])) or 'none'}) -> {'PASS' if a1_pass else 'FAIL'}")
    a2_pass = all(a2["gates"])
    say(f"A2 RFF-ROT (N 1213): gates 1-6 {'all PASS' if a2_pass else 'not all pass'} -> {'PASS' if a2_pass else 'FAIL'}")

    # ---- report 2021-26
    say(f"\n=== REPORT 2021-01..{pd.Timestamp(rep[0][4][-1]).date()} (Alpaca, descriptive, not judged; walk-forward continues, hyperparameters frozen) ===")
    for seed in range(5):
        n1, n3, b, p, rd = rep[seed]
        a, t, be = ols_hac(n1, b)
        say(f"  A1 seed {seed}: alpha vs SPY {a*1e4:+.2f}bp/day t {t:+.2f}; Sharpe {sharpe(n1):.2f} vs SPY {sharpe(b):.2f}; "
            f"3bp alpha {alpha_only(n3, b)*1e4:+.2f}bp; maxDD {maxdd(n1)*100:.1f}% (SPY {maxdd(b)*100:.1f}%); exposure {p.mean():.2f}; n {len(n1)}")
    ok = rm & np.isfinite(Rn8).all(1)
    n1r, n3r, er = net1[ok], net3[ok], ew[ok]
    a, t, be = ols_hac(n1r, er)
    say(f"  A2 seed 0: alpha vs EW8 {a*1e4:+.2f}bp/day t {t:+.2f}; Sharpe {sharpe(n1r):.2f} vs EW8 {sharpe(er):.2f}; "
        f"3bp alpha {alpha_only(n3r, er)*1e4:+.2f}bp; maxDD {maxdd(n1r)*100:.1f}% (EW8 {maxdd(er)*100:.1f}%); n {len(n1r)}")

    say("\n=== Implementation choices (spec ambiguities, conservative / stated before reading any judge number) ===")
    for s in [
        "Data: Sharadar SFP 'close' here is split-adjusted but NOT dividend-adjusted (close == closeunadj after the last split);"
        " a total-return close was built by adding cache_ACTIONS dividends on the ex-date (dividend assumed split-adjusted), O/H/L"
        " scaled by the same factor. Alpaca etf_daily is split+dividend-adjusted; 2021+ is chained from its close-to-close returns.",
        "FIT nominally starts 2002-08; the first row with all 400 base features defined is ~140 sessions after TLT's 2002-07-30 listing.",
        "'max drawdown from window high' = log(close at window end / max close in window). 'mean IBS' = mean over the L+1 sessions"
        " [t-o-L, t-o]; realised vol = std (ddof 0) of the L daily log returns in the window.",
        "Ridge: unpenalised intercept (training-mean centering of features and labels), penalty lambda*||b||^2, kernel form. "
        "f = forecast minus the training-label mean (the timing signal around 1x); sd(f_fit) = sd of walk-forward out-of-sample f over"
        " 2009-01..2010-12 (refit every 21 sessions, inside the fit period). A2 ranks the full forecast (intercept + f).",
        "Lambda: one split, train = rows whose target is realised by 2008-12-31, validate = 2009-01..2010-12 rows (target realised by"
        " 2010-12-31), minimum validation MSE (ties -> larger lambda); A2 picks lambda per ETF model the same way.",
        "Walk-forward: refits at the first 2009 row and every 21 rows; a refit at row tau trains on rows < tau (last label realised at"
        " tau's close). Hyperparameters never change after the split.",
        "Placebo: the label vector (all 8 ETFs together for A2) is circularly shifted by k~U{250..2000} over the whole training segment"
        " (rows whose target is realised by 2020-12-31), and the entire pipeline (lambda, sd(f_fit), walk-forward) is rerun; P&L uses true"
        " returns. 200 draws, rng seed 12345; seed-0 features. Gate 5 compares judge alpha with the placebo alphas.",
        "Costs: c x |position change| per day (A2: sum of |weight changes|; intraday drift of weights ignored). P&L dated at t+1.",
        "Gate 4 read as gate 1 at 3bp/side (alpha > 0 AND NW t >= 2). NW lags 5 on the HAC OLS of strategy net on benchmark.",
        "Seeds: rng(seed) draws base features then the RFF matrix. A2 gated on seed 0 only (the 3-of-5 rule is stated for A1).",
        "REPORT ends at the last Alpaca session on disk, not 2026-10.",
    ]:
        say(" - " + s)
    say(f"\nruntime {time.time()-T0:.0f}s")
    OUT.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
