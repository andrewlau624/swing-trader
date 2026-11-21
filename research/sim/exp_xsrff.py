"""EXP round 4 N 1235 XS-RFF and N 1236 XS-LIN: cross-sectional monthly stock selection, RFF ridge vs linear ridge.

Pre-registration: research/drafts/round1_prose.md, "## Amendment - EXP round 4: linear/RFF siblings named in the A1/A2 kill"
(N 1233 -> 1236). Code frozen (sha256 printed in the header) before any judge number was printed.

Universe: Sharadar SEP common stocks (TICKERS category via nx.is_common), delisted names kept, unadjusted close >= $5 at t,
ADV20 (closeunadj x volume, 20 bars) >= $10M, >= 253 bars of history (all 19 features defined). Total return = split-adjusted
close + ACTIONS cash dividends (exp_rl_universe._features). Decision at each month-end close t (last session of the calendar month)
on bars <= t; label = total return t close -> t+21 sessions close; a name with no bar at t+21 runs to its last bar <= t+21
(delisted names: last bar; no delisting return exists in SEP, stated). Label for fitting = cross-sectional rank of that return,
scaled to [-1, 1].
Features (19, rank-normalised to [-1, 1] per month among eligible names): ret 1/5/21/63/126/252 bars, mom 252-21, vol20, vol63,
max5, IBS, close/252-bar max close - 1, close/252-bar min close - 1, log ADV20, turnover change = log(mean vol 21 / mean vol 252)
(SEP has no shares outstanding: volume ratio stands in for turnover), beta63 vs SPY, idio vol63, bars since the 20-bar high,
5-day volume ratio = log(mean vol 5 / mean vol 63).
Models: N 1235 RFF P = 4000 = 2000 x {sin, cos}(gamma w'z), gamma = 1, w ~ N(0, I) (seed 0); N 1236 linear ridge on the 19 ranks.
Ridge with intercept (centred); lambda = z * n_train grid z in 10^{-3..4} (half decades), chosen ONCE on train = labels realised
<= 2007-12-31 (rows from 2002-08) / validation = decision dates 2008-01..2010 with labels realised before the 2010-12 refit (MSE,
ties -> larger lambda); the absolute lambda is then frozen. Annual expanding refit at each December month-end close R from 2010-12:
training rows = month-end rows from 2002-08 with t + 21 sessions < R (labels fully realised before R; 21-session purge). Model R is
used for decisions R .. the next November month-end.
Portfolio: top min(50, floor(N/10)) forecasts EW, bought at t close, held 21 sessions; turnover = sum |w_t - w_{t-1}| (undrifted
weights, first month 1.0); cost 2.5bp/side x turnover, shock 10bp/side.
Periods: decision months 2010-12..2020-11 = JUDGE (labels realised 2011-01..2020-12, Sharadar NX cache); 2020-12.. = REPORT
(~/data/sharadar/stocks.parquet + funds.parquet SPY, descriptive).
Benchmarks: EW eligible universe (mean label return of all eligible names) and SPY (SFP total return t -> t+21).
Gates (all required, judge): G1 alpha > 0 & NW t >= 2 vs EW AND vs SPY; G2 alpha > 0 in 2011-15 and 2016-20 (both benchmarks);
G3 Sharpe >= benchmark Sharpe + 0.20 (both); G4 alpha > 0 at 10bp/side (both); G5 placebo: the whole pipeline (lambda selection +
refits) on labels circularly shifted per name by k ~ U{12..S-12} months within the label segment 2002-08..2020-11 (S months),
200 draws, real judge alpha vs EW >= 95th pct; G6 alpha with the 5 best hedged months removed > 0 (both).

    PYTHONPATH=. python3 research/sim/exp_xsrff.py            # -> research/sim/exp_xsrff_out.txt
    XSRFF_DRY=1 ...                                           # small P / ticker subset, prints no judge numbers
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "3")

import gc  # noqa: E402
import hashlib  # noqa: E402
import math  # noqa: E402
import pathlib  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
from scipy.linalg.blas import ssyrk  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from research.sim.exp_rl_universe import _features, load_etfs, PRICE_MIN, ADV_MIN, NXD  # noqa: E402
from research.sim.weekwin_short import tstat  # noqa: E402
from research.sim.exp_rl import ols_alpha, dsr  # noqa: E402
from research.sim.nx import is_common  # noqa: E402

DRY = os.environ.get("XSRFF_DRY") == "1"
OUT = ROOT / ("research/sim/exp_xsrff_dry.txt" if DRY else "research/sim/exp_xsrff_out.txt")
FULL = pathlib.Path(os.path.expanduser("~/data/sharadar"))
N_TRIALS = 1236
H = 21
P_HALF, GAMMA = (100 if DRY else 2000), 1.0
ZGRID = 10.0 ** np.arange(-3.0, 4.01, 0.5)
COST, SHOCK = 2.5e-4, 10e-4
MAXN = 50
N_PLACEBO = 20 if DRY else 200
MIN_SHIFT = 12
NW = 5
FEAT_START = pd.Timestamp("2002-08-01")
LAM_TRAIN_END = pd.Timestamp("2007-12-31")
VAL_START = pd.Timestamp("2008-01-01")
FIRST_REFIT = pd.Timestamp("2010-12-01")
JUDGE_LAST = pd.Timestamp("2020-11-30")       # last judge decision month-end (label realised by 2020-12-31)
H1_LAST = pd.Timestamp("2015-11-30")
FEATS = ["r1", "r5", "r21", "r63", "r126", "r252", "mom", "vol20", "vol63", "max5", "ibs", "dhi", "dlo", "ladv", "dturn",
         "beta", "ivol", "dsh", "vr5"]
COLS = ["ticker", "date", "high", "low", "close", "volume", "closeunadj"]

lines: list[str] = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    lines.append(s)


# ---------------------------------------------------------------- data (per ticker chunk, month-end rows only)
def _spy(source: str) -> pd.DataFrame:
    if source == "cache":
        s = load_etfs(["SPY"])
    else:
        t = pq.read_table(FULL / "funds.parquet", columns=COLS, filters=[("ticker", "=", "SPY")]).to_pandas()
        t["date"] = pd.to_datetime(t["date"]); t["ticker"] = t["ticker"].astype(str)
        for c in COLS[2:]:
            t[c] = t[c].astype(np.float64)
        s = _features(t.sort_values(["ticker", "date"], kind="mergesort"))
    return s[["date", "ret"]].reset_index(drop=True)


def _gather(a, idx, L):
    """a[idx - L + 1 .. idx] as rows (n x L); caller guarantees in-ticker."""
    return a[idx[:, None] - np.arange(L - 1, -1, -1)[None, :]]


def build_rows(source: str, me_from, me_to) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Month-end rows (features, label) for decisions in [me_from, me_to]; returns (rows, spy_me)."""
    if source == "cache":
        sep, tick, load_start = NXD / "cache_SEP.parquet", NXD / "cache_TICKERS.parquet", pd.Timestamp("1998-01-01")
    else:
        sep, tick, load_start = FULL / "stocks.parquet", FULL / "tickers.parquet", pd.Timestamp("2019-06-01")
    spy = _spy(source)
    spy = spy[spy.date >= load_start - pd.Timedelta(days=10)].reset_index(drop=True)
    sessions = spy.date.to_numpy("datetime64[ns]")
    spy_r = np.nan_to_num(spy.ret.to_numpy(float))
    lw_spy = np.cumsum(np.log1p(spy_r))
    last_s = len(sessions) - 1
    mon = pd.DatetimeIndex(sessions).to_period("M")
    me_mask = np.r_[mon[1:] != mon[:-1], False]                 # last session of a month whose next session is in a later month
    me_sidx = np.where(me_mask)[0]
    me_dates = pd.DatetimeIndex(sessions[me_sidx])
    keep = (me_dates >= me_from) & (me_dates <= me_to)
    me_sidx = me_sidx[keep]
    me_set = np.zeros(len(sessions), bool); me_set[me_sidx] = True

    t = pd.read_parquet(tick, columns=["table", "ticker", "category"])
    t = t[t.table == "SEP"]
    common = sorted(set(t.ticker[is_common(t.category.fillna("").astype(str))]))
    if DRY:
        common = common[::15]
    nchunk = 12
    out = []
    for ci in range(nchunk):
        tk = common[ci::nchunk]
        b = pq.read_table(sep, columns=COLS, filters=[("date", ">=", load_start), ("ticker", "in", tk)]).to_pandas()
        if len(b) == 0:
            continue
        b["date"] = pd.to_datetime(b["date"]); b["ticker"] = b["ticker"].astype(str)
        for c in COLS[2:]:
            b[c] = b[c].astype(np.float64)
        b = _features(b.sort_values(["ticker", "date"], kind="mergesort"))
        sidx = np.searchsorted(sessions, b.date.to_numpy("datetime64[ns]"))
        ok = (sidx < len(sessions)) & (sessions[np.minimum(sidx, last_s)] == b.date.to_numpy("datetime64[ns]"))
        b = b[ok].reset_index(drop=True); sidx = sidx[ok]
        code = pd.factorize(b.ticker)[0]
        n = len(b)
        newg = np.r_[True, code[1:] != code[:-1]]
        start = np.maximum.accumulate(np.where(newg, np.arange(n), 0))
        pos = np.arange(n) - start                               # recomputed after the calendar filter
        r = np.nan_to_num(b.ret.to_numpy(float)); r[pos == 0] = 0.0
        r = np.clip(r, -0.999, None)
        lw = np.cumsum(np.log1p(r))
        c = b.close.to_numpy(float); vol = b.volume.to_numpy(float)
        i = np.where(me_set[sidx] & (pos >= 252))[0]
        if len(i) == 0:
            continue
        f = {}
        for L in (1, 5, 21, 63, 126, 252):
            f[f"r{L}"] = np.expm1(lw[i] - lw[i - L])
        f["mom"] = np.expm1(lw[i - 21] - lw[i - 252])
        f["vol20"] = _gather(r, i, 20).std(1, ddof=1) * math.sqrt(252)
        R63 = _gather(r, i, 63)
        f["vol63"] = R63.std(1, ddof=1) * math.sqrt(252)
        f["max5"] = _gather(r, i, 5).max(1)
        f["ibs"] = b.ibs.to_numpy(float)[i]
        C252 = _gather(c, i, 252)
        f["dhi"] = c[i] / C252.max(1) - 1
        f["dlo"] = c[i] / C252.min(1) - 1
        del C252
        f["ladv"] = np.log(np.maximum(b.adv20.to_numpy(float)[i], 1.0))
        V252 = _gather(vol, i, 252)
        with np.errstate(divide="ignore", invalid="ignore"):
            f["dturn"] = np.log((V252[:, -21:].mean(1) + 1) / (V252.mean(1) + 1))
            f["vr5"] = np.log((V252[:, -5:].mean(1) + 1) / (V252[:, -63:].mean(1) + 1))
        del V252
        S63 = spy_r[_gather(sidx, i, 63)]
        sm = S63 - S63.mean(1, keepdims=True); rm = R63 - R63.mean(1, keepdims=True)
        var_s = (sm * sm).sum(1)
        beta = np.where(var_s > 0, (sm * rm).sum(1) / np.where(var_s > 0, var_s, 1), np.nan)
        f["beta"] = beta
        f["ivol"] = (R63 - beta[:, None] * S63).std(1, ddof=1) * math.sqrt(252)
        del R63, S63, sm, rm
        f["dsh"] = np.argmax(_gather(c, i, 20)[:, ::-1], axis=1).astype(float)     # 0 = today is the 20-bar high
        # label t close -> last bar <= t+21 of the same name
        key = code.astype(np.int64) * 10_000_000 + sidx
        tgt = code[i].astype(np.int64) * 10_000_000 + sidx[i] + H
        j = np.searchsorted(key, tgt, side="right") - 1
        assert (j >= i).all() and (code[j] == code[i]).all()
        y21 = np.expm1(lw[j] - lw[i])
        complete = sidx[i] + H <= last_s
        y21 = np.where(complete, y21, np.nan)
        lastbar = np.r_[code[1:] != code[:-1], True]
        delist = lastbar[j] & (sidx[j] < sidx[i] + H) & complete      # name stops before t+21 (delisted / leaves the file)
        d = pd.DataFrame(f)
        d["ticker"] = b.ticker.to_numpy()[i]; d["date"] = b.date.to_numpy()[i]; d["sidx"] = sidx[i]
        d["px"] = b.closeunadj.to_numpy(float)[i]; d["adv20"] = b.adv20.to_numpy(float)[i]
        d["y21"] = y21; d["delist"] = delist
        d = d[(d.px >= PRICE_MIN) & (d.adv20 >= ADV_MIN)]
        d = d[np.isfinite(d[FEATS].to_numpy(float)).all(1)]
        for col in FEATS + ["y21", "px"]:
            d[col] = d[col].astype(np.float32)
        out.append(d)
        del b, r, lw, c, vol, f
        gc.collect()
    rows = pd.concat(out, ignore_index=True)
    spy_me = pd.DataFrame({"sidx": me_sidx, "date": sessions[me_sidx],
                           "spy21": np.where(me_sidx + H <= last_s,
                                             np.expm1(lw_spy[np.minimum(me_sidx + H, last_s)] - lw_spy[me_sidx]), np.nan)})
    return rows, spy_me


def rank_norm(rows: pd.DataFrame) -> pd.DataFrame:
    g = rows.groupby("date")
    nm = g["ticker"].transform("size").to_numpy(float)
    for col in FEATS:
        rk = g[col].rank(method="average").to_numpy(float)
        rows[col] = (2 * (rk - 1) / np.maximum(nm - 1, 1) - 1).astype(np.float32)
    rk = g["y21"].rank(method="average").to_numpy(float)
    ny = g["y21"].transform("count").to_numpy(float)
    rows["ylab"] = (2 * (rk - 1) / np.maximum(ny - 1, 1) - 1).astype(np.float32)
    return rows


# ---------------------------------------------------------------- ridge pipeline on sufficient statistics
class Acc:
    def __init__(self, P, m):
        self.xx = np.zeros((P, P)); self.x = np.zeros(P); self.xy = np.zeros((P, m)); self.y = np.zeros(m)
        self.yy = np.zeros(m); self.n = 0

    def add(self, X, Y):
        G = ssyrk(1.0, X, trans=1)                                 # upper triangle of X'X (float32)
        G = G + np.triu(G, 1).T
        self.xx += G; self.x += X.sum(0, dtype=np.float64)
        m = self.xy.shape[1]
        self.xy[:, :Y.shape[1]] += (X.T @ Y).astype(np.float64)
        self.y[:Y.shape[1]] += Y.sum(0, dtype=np.float64); self.yy[:Y.shape[1]] += (Y.astype(np.float64) ** 2).sum(0)
        self.n += len(X)
        assert Y.shape[1] in (1, m)

    def copy(self):
        o = Acc.__new__(Acc)
        o.xx, o.x, o.xy, o.y, o.yy, o.n = self.xx.copy(), self.x.copy(), self.xy.copy(), self.y.copy(), self.yy.copy(), self.n
        return o

    def centred(self, cols):
        mu = self.x / self.n; yb = self.y[cols] / self.n
        G = self.xx - self.n * np.outer(mu, mu)
        c = self.xy[:, cols] - self.n * np.outer(mu, yb)
        return mu, yb, G, c


def select_lambda(tr: Acc, va: Acc):
    """per label column: index into ZGRID minimising validation MSE (ties -> larger lambda); absolute lambdas returned."""
    m = tr.xy.shape[1]
    mu, yb, G, c = tr.centred(np.arange(m))
    s, Q = np.linalg.eigh(G); s = np.clip(s, 0, None)
    A = Q.T @ c
    Hc = va.xx - np.outer(va.x, mu) - np.outer(mu, va.x) + va.n * np.outer(mu, mu)
    hc = va.xy - np.outer(va.x, yb) - np.outer(mu, va.y) + va.n * np.outer(mu, yb)
    syy = va.yy - 2 * yb * va.y + va.n * yb ** 2
    QHQ = Q.T @ Hc @ Q; Qh = Q.T @ hc
    mse = np.empty((len(ZGRID), m))
    for k, z in enumerate(ZGRID):
        Bq = A / (s[:, None] + z * tr.n)
        mse[k] = (syy - 2 * (Bq * Qh).sum(0) + (Bq * (QHQ @ Bq)).sum(0)) / va.n
    best = len(ZGRID) - 1 - np.argmin(mse[::-1], axis=0)
    return ZGRID[best] * tr.n, best, mse


def fit(acc: Acc, lam_cols):
    cols = np.arange(len(lam_cols))
    mu, yb, G, c = acc.centred(cols)
    if len(np.unique(lam_cols)) == 1:
        B = np.linalg.solve(G + lam_cols[0] * np.eye(len(G)), c)
    else:
        s, Q = np.linalg.eigh(G); s = np.clip(s, 0, None)
        B = Q @ ((Q.T @ c) / (s[:, None] + lam_cols[None, :]))
    return mu.astype(np.float32), B.astype(np.float32)


def run_model(name, fmap, P, months, Zs, Ylab, codes, me_dates, seg_S, shifts, Lmat):
    """Returns forecasts F[month] (n_m x (1+npl) for judge months, n_m x 1 for report) plus lambda info."""
    t0 = time.time()
    m_all = 1 + len(shifts)
    me_sidx = np.array([mo[1] for mo in months])

    def labels(mi, full):
        y = Ylab[mi][:, None]
        if not full:
            return y
        cols = [y[:, 0]]
        for k in shifts:
            src = (mi - k) % seg_S
            yp = Lmat[codes[mi], src]
            cols.append(np.where(np.isfinite(yp), yp, 0.0))
        return np.column_stack(cols).astype(np.float32)

    acc = Acc(P, m_all)
    added = 0
    nmon = len(months)

    def add_until(cut_sidx, va=None, va_from=None):
        nonlocal added
        while added < nmon and me_sidx[added] + H < cut_sidx:
            in_seg = added < seg_S
            X = fmap(Zs[added]); Y = labels(added, in_seg)
            acc.add(X, Y)
            if va is not None and me_dates[added] >= va_from:
                va.add(X, Y)
            added += 1

    # lambda split: train labels realised <= 2007-12-31; validation = 2008.. rows realised before the first refit
    sess_2007 = me_sidx[np.searchsorted(me_dates, LAM_TRAIN_END, side="right") - 1]      # Dec-2007 month-end session
    add_until(sess_2007 + 1)
    tr = acc.copy(); n_tr_rows = tr.n
    va = Acc(P, m_all)
    ref_idx = [k for k, d in enumerate(me_dates) if d.month == 12 and d >= FIRST_REFIT]
    add_until(me_sidx[ref_idx[0]], va=va, va_from=VAL_START)
    lam_cols, best, mse = select_lambda(tr, va)
    say(f"  {name}: P {P}; lambda split train rows {n_tr_rows} (labels <= 2007-12-31), validation rows {va.n}; "
        f"true-label z = {ZGRID[best[0]]:.3g} (lambda {lam_cols[0]:.3g}); placebo z median {np.median(ZGRID[best[1:]]) if m_all > 1 else float('nan'):.3g}; "
        f"val MSE by z (true) " + " ".join(f"{z:.0e}:{v:.5f}" for z, v in zip(ZGRID, mse[:, 0])))
    del tr, va
    F = {}
    for r_i, ri in enumerate(ref_idx):
        add_until(me_sidx[ri])
        last_pred = ref_idx[r_i + 1] if r_i + 1 < len(ref_idx) else nmon
        need_pl = ri < seg_S and me_dates[ri] <= JUDGE_LAST
        cols = m_all if need_pl else 1
        mu, B = fit(acc, lam_cols[:cols] if need_pl else lam_cols[:1])
        for mi in range(ri, last_pred):
            X = fmap(Zs[mi])
            F[mi] = (X - mu) @ B
        say(f"    refit {me_dates[ri].date()} train rows {acc.n} cols {cols} -> months {me_dates[ri].date()}..{me_dates[last_pred-1].date()} "
            f"({time.time()-t0:.0f}s)")
    return F, lam_cols


# ---------------------------------------------------------------- portfolio + stats
def portfolio(F_col, months_idx, Ylab_ret, codes, px):
    """F_col(mi) -> forecasts; returns gross, turnover, picks per month."""
    gross, turn, picks, prev = [], [], [], None
    for mi in months_idx:
        f = F_col(mi)
        N = len(f); n = min(MAXN, N // 10)
        o = np.lexsort((codes[mi], -f))[:n]                        # highest forecast first (ties by code)
        assert f[o].min() >= np.sort(f)[::-1][n - 1] - 1e-9
        cur = set(codes[mi][o].tolist())
        gross.append(float(Ylab_ret[mi][o].mean()))
        if prev is None:
            turn.append(1.0)
        else:
            w_new, w_old = 1.0 / len(cur), 1.0 / len(prev)
            both = cur & prev
            turn.append(len(both) * abs(w_new - w_old) + len(cur - both) * w_new + len(prev - both) * w_old)
        picks.append(o); prev = cur
    return np.array(gross), np.array(turn), picks


def stats(net, bench):
    a, t, beta = ols_alpha(net, bench, lags=NW)
    return a, t, beta


def sharpe_m(x):
    x = np.asarray(x, float); return x.mean() / x.std(ddof=1) * math.sqrt(12)


def maxdd(x):
    eq = np.cumprod(1 + np.asarray(x, float)); return float((eq / np.maximum.accumulate(eq) - 1).min())


def evaluate(tag, gross, turn, ew, spy, dates, placebo_alphas=None, gate=True):
    net = gross - COST * turn; net_s = gross - SHOCK * turn
    h1 = dates <= H1_LAST
    res = {}
    gl = []
    for bn, B in (("EW", ew), ("SPY", spy)):
        a, t, beta = stats(net, B)
        a1 = stats(net[h1], B[h1])[0] if h1.sum() > 12 else float("nan")
        a2 = stats(net[~h1], B[~h1])[0] if (~h1).sum() > 12 else float("nan")
        as_, ts_, _ = stats(net_s, B)
        hedged = net - beta * B
        keep = np.ones(len(net), bool); keep[np.argsort(hedged)[-5:]] = False
        ax5 = stats(net[keep], B[keep])[0]
        sh, shb = sharpe_m(net), sharpe_m(B)
        exc = net - B
        res[bn] = dict(a=a, t=t, beta=beta)
        say(f"  {tag} vs {bn:<3}: alpha {a*1e4:+7.1f}bp/mo NW t {t:+5.2f} beta {beta:.2f} | halves 11-15 {a1*1e4:+7.1f} 16-20 {a2*1e4:+7.1f} | "
            f"Sharpe {sh:.2f} vs {shb:.2f} (d {sh-shb:+.2f}) | 10bp/side alpha {as_*1e4:+7.1f} t {ts_:+5.2f} | ex-top5 {ax5*1e4:+7.1f} | "
            f"excess mean {exc.mean()*1e4:+6.1f}bp t {tstat(exc, NW):+5.2f} med {np.median(exc)*1e4:+6.1f} hit {(exc>0).mean()*100:4.1f}% | "
            f"DSR(N {N_TRIALS}) {dsr(hedged, N_TRIALS):.3f}")
        gl.append((a > 0 and t >= 2, a1 > 0 and a2 > 0, sh - shb >= 0.20, as_ > 0, ax5 > 0))
    say(f"  {tag} net: mean {net.mean()*1e4:+.1f}bp/mo, CAGR {(np.prod(1+net)**(12/len(net))-1)*100:+.1f}%, Sharpe {sharpe_m(net):.2f}, "
        f"maxDD {maxdd(net)*100:.1f}% (EW {maxdd(ew)*100:.1f}%, SPY {maxdd(spy)*100:.1f}%), median {np.median(net)*1e4:+.1f}bp, "
        f"hit {(net>0).mean()*100:.1f}%, months {len(net)}, turnover {turn.mean():.2f}/mo ({turn.mean()*12:.1f}x/yr), "
        f"cost drag {COST*turn.mean()*12*1e4:.0f}bp/yr")
    if not gate:
        return res
    pct = (placebo_alphas < res["EW"]["a"]).mean() * 100
    say(f"  {tag} placebo: real alpha vs EW {res['EW']['a']*1e4:+.1f}bp/mo at pct {pct:.1f} of {len(placebo_alphas)} "
        f"(placebo p50 {np.percentile(placebo_alphas,50)*1e4:+.1f}, p95 {np.percentile(placebo_alphas,95)*1e4:+.1f}bp/mo)")
    g = [gl[0][0] and gl[1][0], gl[0][1] and gl[1][1], gl[0][2] and gl[1][2], gl[0][3] and gl[1][3], pct >= 95, gl[0][4] and gl[1][4]]
    names = ["G1 alpha t>=2 (EW & SPY)", "G2 both halves>0", "G3 dSharpe>=+0.20", "G4 10bp/side>0", "G5 placebo>=95th", "G6 ex-top-5>0"]
    say("  " + tag + " gates: " + "; ".join(f"{n} {'PASS' if v else 'FAIL'}" for n, v in zip(names, g)) +
        f" => {'PASS' if all(g) else 'DEAD'}")
    res["gates"] = g
    return res


def deciles(tag, F_col, months_idx, Yret):
    D = np.full((len(months_idx), 10), np.nan); FM = np.full((len(months_idx), 10), np.nan)
    for k, mi in enumerate(months_idx):
        f = F_col(mi); y = Yret[mi]
        q = np.minimum((pd.Series(f).rank(method="first").to_numpy() - 1) * 10 // len(f), 9).astype(int)
        for d in range(10):
            D[k, d] = y[q == d].mean(); FM[k, d] = f[q == d].mean()
    fm = FM.mean(0)
    assert np.all(np.diff(fm) > 0), "sign convention: decile 10 must hold the highest mean forecast"
    sp = D[:, 9] - D[:, 0]
    say(f"  {tag} deciles (mean 21d return bp | mean forecast): " +
        " ".join(f"D{d+1}[f {fm[d]:+.4f}] {D[:, d].mean()*1e4:+.0f}" for d in range(10)))
    say(f"  {tag} D10-D1 {sp.mean()*1e4:+.1f}bp/mo NW t {tstat(sp, NW):+.2f}; D10-mean {np.mean(D[:,9]-D.mean(1))*1e4:+.1f}bp")


def dollars(tag, net, ew, spy, picks, months_idx, PX):
    say(f"  {tag} $/yr: " + " ".join(
        f"${cap/1e3:g}k net {net.mean()*12*cap:+,.0f} (alpha-EW {(net-ew).mean()*12*cap:+,.0f}, vs SPY {(net-spy).mean()*12*cap:+,.0f}; "
        f"whole-share deployed {np.mean([np.mean(np.floor(cap/len(o)/PX[mi][o]) * PX[mi][o] / (cap/len(o))) for o, mi in zip(picks, months_idx)])*100:.0f}%)"
        for cap in (2300, 10000, 25000)) + "; arithmetic mean x 12, before tax")


# ---------------------------------------------------------------- main
def main():
    t0 = time.time()
    sha = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]
    say(f"EXP round 4 N 1235 XS-RFF / N 1236 XS-LIN  (program N {N_TRIALS}; code sha256 {sha}; DRY {DRY}; threads 3)")
    say(f"universe: SEP common, px>=${PRICE_MIN:g}, ADV20>=${ADV_MIN/1e6:g}M, >=253 bars; decisions at month-end closes; label t->t+{H} "
        f"sessions; top min({MAXN}, N/10) EW; cost {COST*1e4:g}bp/side (shock {SHOCK*1e4:g}); placebo {N_PLACEBO} per-name circular "
        f"label shifts U{{{MIN_SHIFT}..S-{MIN_SHIFT}}} months seed 12345; NW lags {NW}")
    rows_c, spy_c = build_rows("cache", FEAT_START, JUDGE_LAST)
    assert rows_c.y21.notna().all(), "judge labels must be complete inside the cache"
    say(f"cache rows {len(rows_c)} months {rows_c.date.nunique()} names {rows_c.ticker.nunique()} "
        f"(labels truncated by delisting/leaving {int(rows_c.delist.sum())}); {time.time()-t0:.0f}s")
    try:
        rows_f, spy_f = build_rows("full", pd.Timestamp("2020-12-01"), pd.Timestamp("2030-01-01"))
        rows_f = rows_f[rows_f.y21.notna()]
        report_ok = True
        say(f"full-store rows {len(rows_f)} months {rows_f.date.nunique()} ({rows_f.date.min().date()}..{rows_f.date.max().date()}); "
            f"{time.time()-t0:.0f}s")
    except Exception as e:  # noqa: BLE001
        say(f"full store unavailable ({e!r}); REPORT 2021-26 skipped")
        rows_f, spy_f, report_ok = rows_c.iloc[:0], spy_c.iloc[:0], False
    # stitch month sessions: one global month index; sidx are source-specific so the purge uses dates mapped to a global calendar
    rows = pd.concat([rows_c, rows_f], ignore_index=True)
    del rows_c, rows_f; gc.collect()
    rows = rank_norm(rows)
    # global session calendar for the purge rule (cache SPY sessions through 2021-01-15, then full-store SPY sessions)
    cal_c = load_etfs(["SPY"]).date.to_numpy("datetime64[ns]")
    if report_ok:
        tt = pq.read_table(FULL / "funds.parquet", columns=["date"], filters=[("ticker", "=", "SPY")]).to_pandas()
        cal_f = pd.to_datetime(tt.date).to_numpy("datetime64[ns]")
        cal = np.unique(np.r_[cal_c, cal_f[cal_f > cal_c[-1]]])
    else:
        cal = cal_c
    rows["gs"] = np.searchsorted(cal, rows.date.to_numpy("datetime64[ns]"))
    rows = rows.sort_values(["date", "ticker"], kind="mergesort").reset_index(drop=True)
    tick_codes = pd.factorize(rows.ticker)[0]
    rows["code"] = tick_codes
    spym = pd.concat([spy_c, spy_f]).drop_duplicates("date", keep="first").set_index("date").spy21
    groups = rows.groupby("date", sort=True).indices
    me_dates = pd.DatetimeIndex(sorted(groups))
    months = [(d, int(rows.gs.iloc[groups[d][0]])) for d in me_dates]
    Z = [rows[FEATS].to_numpy(np.float32)[groups[d]] for d in me_dates]
    Ylab = [rows.ylab.to_numpy(np.float32)[groups[d]] for d in me_dates]
    Yret = [rows.y21.to_numpy(np.float32)[groups[d]] for d in me_dates]
    codes = [rows.code.to_numpy()[groups[d]] for d in me_dates]
    PX = [rows.px.to_numpy(np.float32)[groups[d]] for d in me_dates]
    ew = np.array([y.astype(float).mean() for y in Yret])
    spy21 = spym.reindex(me_dates).to_numpy(float)
    assert np.isfinite(spy21).all()
    # sign convention of the label: higher rank = higher realised return
    assert all(np.corrcoef(Ylab[k], Yret[k])[0, 1] > 0.5 for k in range(0, len(me_dates), 7))
    seg_S = int((me_dates <= JUDGE_LAST).sum())
    Lmat = np.full((tick_codes.max() + 1, seg_S), np.nan, np.float32)
    for k in range(seg_S):
        Lmat[codes[k], k] = Ylab[k]
    prng = np.random.default_rng(12345)
    shifts = prng.integers(MIN_SHIFT, seg_S - MIN_SHIFT + 1, N_PLACEBO)
    nm = np.array([len(z) for z in Z])
    say(f"months {len(me_dates)} ({me_dates[0].date()}..{me_dates[-1].date()}), label segment S {seg_S}, names/month median {int(np.median(nm))} "
        f"min {nm.min()} max {nm.max()}; delisted-truncated labels {int(rows.delist.sum())}; {time.time()-t0:.0f}s")
    del rows; gc.collect()

    rng = np.random.default_rng(0)
    W = (GAMMA * rng.standard_normal((len(FEATS), P_HALF))).astype(np.float32)

    def f_rff(z):
        S = z @ W
        return np.hstack([np.sin(S), np.cos(S)]).astype(np.float32)

    def f_lin(z):
        return np.ascontiguousarray(z, dtype=np.float32)

    judge_idx = [k for k, d in enumerate(me_dates) if FIRST_REFIT <= d <= JUDGE_LAST]
    rep_idx = [k for k, d in enumerate(me_dates) if d > JUDGE_LAST]
    jd = me_dates[judge_idx]
    results = {}
    say("\n# FROZEN: everything below is the first and only judge read of this code (sha above)")
    for name, fmap, P in (("N1236 XS-LIN", f_lin, len(FEATS)), ("N1235 XS-RFF", f_rff, 2 * P_HALF)):
        say(f"\n## {name}")
        F, lam = run_model(name, fmap, P, months, Z, Ylab, codes, me_dates, seg_S, shifts, Lmat)
        g, tu, pk = portfolio(lambda mi: F[mi][:, 0], judge_idx, Yret, codes, PX)
        pl = []
        for c in range(1, 1 + N_PLACEBO):
            gp, tp, _ = portfolio(lambda mi, c=c: F[mi][:, c], judge_idx, Yret, codes, PX)
            pl.append(stats(gp - COST * tp, ew[judge_idx])[0])
        pl = np.array(pl)
        if DRY:
            say(f"  DRY: judge months {len(judge_idx)}, placebo cols {len(pl)}, picks/month {np.mean([len(o) for o in pk]):.0f}; "
                f"judge numbers suppressed ({time.time()-t0:.0f}s)")
            continue
        say(f"JUDGE decisions {jd[0].date()}..{jd[-1].date()} ({len(judge_idx)} months), picks/month {np.mean([len(o) for o in pk]):.0f}")
        r = evaluate(name, g, tu, ew[judge_idx], spy21[judge_idx], jd, pl)
        deciles(name, lambda mi: F[mi][:, 0], judge_idx, Yret)
        dollars(name + " judge", g - COST * tu, ew[judge_idx], spy21[judge_idx], pk, judge_idx, PX)
        results[name] = r
        if rep_idx:
            gr, tr_, pkr = portfolio(lambda mi: F[mi][:, 0], rep_idx, Yret, codes, PX)
            rd = me_dates[rep_idx]
            say(f"REPORT (descriptive, full store) decisions {rd[0].date()}..{rd[-1].date()} ({len(rep_idx)} months)")
            evaluate(name + " REPORT", gr, tr_, ew[rep_idx], spy21[rep_idx], rd, gate=False)
            deciles(name + " REPORT", lambda mi: F[mi][:, 0], rep_idx, Yret)
            dollars(name + " REPORT", gr - COST * tr_, ew[rep_idx], spy21[rep_idx], pkr, rep_idx, PX)
        del F; gc.collect()
    if not DRY:
        a = results.get("N1235 XS-RFF", {}).get("gates"); b = results.get("N1236 XS-LIN", {}).get("gates")
        say(f"\nVERDICT: N1235 XS-RFF {'PASS' if a and all(a) else 'DEAD'}; N1236 XS-LIN {'PASS' if b and all(b) else 'DEAD'}"
            f"{'; nonlinearity is the result (1235 passes, 1236 does not)' if a and all(a) and not (b and all(b)) else ''}")
    say(f"total {time.time()-t0:.0f}s")
    OUT.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
