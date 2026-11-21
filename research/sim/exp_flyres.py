"""EXP round B: fly-brain connectome reservoir (FLY-RES, N 1214) and dopamine-gated readout (FLY-DA, N 1215).

Pre-registration: research/drafts/round1_prose.md, "## Amendment - EXP round (user 2026-11-20 ...)", Common frame + B1/B2.
One run; no rule or hyperparameter changes after a judge-period number is printed.

Connectome: FlyWire adult whole-brain v783 (public, no login)
  edges  : Zenodo record 10676866, proofread_connections_783.feather
  classes: github.com/flyconnectome/flywire_annotations supplemental_files/Supplemental_file1_neuron_annotations.tsv
Raw downloads live in data/research/exp_flyres/raw/ and are read with pandas only (untrusted data).

Choices the pre-reg leaves open (fixed here before any judge number; recorded in the output):
  - edge = (pre, post) synapse count summed over neuropils, kept if >= 5 synapses (FlyWire standard threshold); autapses dropped
  - sign from the presynaptic neuron's top_nt (Dale): gaba/glutamate -1, acetylcholine +1, other/unknown +1
  - degree for the 3,000 cap = binary in+out degree inside the MB subgraph (KC + ALPN + MBON + DAN)
  - input matrix W_in: rows = ALPN units only, each entry nonzero w.p. 0.1, U(-1,1), seed 0, identical for every graph
  - washout: first 100 sessions of reservoir state never used for training/eval
  - lambda grid {1e-1,...,1e5}, chosen by validation MSE (train 2002-08..2008, val 2009-10)
  - walk-forward ridge refit every 21 sessions; at decision date d trains on rows t <= d-2 (label known by d-1)
  - sd(f_fit) = sd of the in-sample forecasts of the end-of-fit model over the fit rows
  - B2: w0 ~ N(0,1) scaled so sd(w0'x) = 0.1 on fit rows (w = 0 would never learn: a - abar = 0);
        rbar/abar = EMA with tau 20 sessions; eta chosen by fit-period net Sharpe
  - NW lags 8; alpha = intercept of OLS(strategy net on SPY close-to-close); ex-top-5 drops the 5 largest alpha days
  - gate 4 = gate 1 (alpha > 0 and NW t >= 2) repriced at 3bp/side; no margin financing charge (not in the pre-reg)
  - placebo: fit-period labels circularly shifted by k ~ U{250..2000}; judge-period refits see real labels (literal reading)
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.linalg as sla
import scipy.sparse as sp
import scipy.sparse.linalg as spla
import scipy.stats as SS

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/research/exp_flyres/raw"
CACHE = ROOT / "data/research/exp_flyres"
OUT = ROOT / "research/sim/exp_flyres_out.txt"
ETFS = ["SPY", "QQQ", "IWM", "TLT", "XLK", "XLF", "XLE", "XLU"]
MB_CLASSES = ["Kenyon_Cell", "ALPN", "MBON", "DAN"]
NCAP, SYN_MIN = 3000, 5
RHO, LEAK, IN_P = 0.9, 0.3, 0.1
WASHOUT, REFIT = 100, 21
LAMS = [10.0 ** k for k in range(-1, 6)]
ETAS = [1e-4, 1e-3, 1e-2]
TAU = 20.0
C1, C3 = 1e-4, 3e-4
N_CTRL, N_PLAC = 20, 200
N_PROGRAM = 1218
NW_LAGS = 8
FIT_END, JUDGE = "2010-12-31", ("2011-01-01", "2020-12-31")
T0 = time.time()
LINES: list[str] = []


def log(*a):
    print(f"[{time.time() - T0:7.0f}s]", *a, file=sys.stderr, flush=True)


def out(s=""):
    LINES.append(s)
    print(s, flush=True)


# ----------------------------------------------------------------------------- connectome
def build_mb():
    f = CACHE / "mb_edges.parquet"
    fn = CACHE / "mb_nodes.parquet"
    if f.exists() and fn.exists():
        return pd.read_parquet(fn), pd.read_parquet(f)
    a = pd.read_csv(RAW / "Supplemental_file1_neuron_annotations.tsv", sep="\t", low_memory=False,
                    usecols=["root_id", "cell_class", "cell_type", "top_nt", "known_nt"])
    mb = a[a.cell_class.isin(MB_CLASSES)].drop_duplicates("root_id")
    ids = mb.root_id.to_numpy()
    c = pd.read_feather(RAW / "proofread_connections_783.feather", columns=["pre_pt_root_id", "post_pt_root_id", "syn_count"])
    c = c[c.pre_pt_root_id.isin(ids) & c.post_pt_root_id.isin(ids)]
    e = c.groupby(["pre_pt_root_id", "post_pt_root_id"], as_index=False).syn_count.sum()
    e = e[(e.syn_count >= SYN_MIN) & (e.pre_pt_root_id != e.post_pt_root_id)]
    deg = pd.concat([e.pre_pt_root_id, e.post_pt_root_id]).value_counts()
    keep = deg.sort_values(ascending=False, kind="mergesort").index[:NCAP]
    e = e[e.pre_pt_root_id.isin(keep) & e.post_pt_root_id.isin(keep)].reset_index(drop=True)
    nodes = mb.set_index("root_id").loc[np.asarray(keep)].rename_axis("root_id").reset_index()
    nodes["idx"] = np.arange(len(nodes))
    nodes["mb_total_in_class"] = nodes.cell_class.map(mb.cell_class.value_counts())
    nodes["sign"] = np.where(nodes.top_nt.isin(["gaba", "glutamate"]), -1, 1)
    ix = pd.Series(nodes.idx.values, index=nodes.root_id)
    e["src"] = ix.loc[e.pre_pt_root_id].values
    e["dst"] = ix.loc[e.post_pt_root_id].values
    e["w"] = e.syn_count * nodes.sign.values[e.src.values]
    nodes.to_parquet(fn)
    e[["src", "dst", "syn_count", "w"]].to_parquet(f)
    return nodes, e[["src", "dst", "syn_count", "w"]]


def rewire(src, dst, n, rng):
    """Permute edge targets (keeps every out-degree, in-degree, edge weight/sign on its source), then repair
    self-loops and duplicate edges by re-permuting the offending targets with random partners."""
    d = dst[rng.permutation(len(dst))].copy()
    for it in range(1000):
        key = src.astype(np.int64) * n + d
        _, first = np.unique(key, return_index=True)
        bad = np.ones(len(d), bool); bad[first] = False
        bad |= src == d
        nb = int(bad.sum())
        if nb == 0:
            return d
        bi = np.flatnonzero(bad)
        oi = rng.choice(len(d), size=min(len(d), 2 * nb), replace=False)
        pool = np.unique(np.concatenate([bi, oi]))
        d[pool] = d[pool[rng.permutation(len(pool))]]
    raise RuntimeError("rewire did not converge")


def erdos(n, m, rng):
    keys = np.unique(rng.integers(0, n * n, size=int(m * 1.2)))
    keys = keys[(keys // n) != (keys % n)]
    while len(keys) < m:
        keys = np.unique(np.concatenate([keys, rng.integers(0, n * n, size=m)]))
        keys = keys[(keys // n) != (keys % n)]
    keys = rng.permutation(keys)[:m]
    return keys // n, keys % n


def to_W(src, dst, w, n):
    W = sp.csr_matrix((w.astype(np.float64), (dst, src)), shape=(n, n))
    try:
        ev = spla.eigs(W, k=1, which="LM", return_eigenvectors=False, maxiter=20000, tol=1e-6)
        r = float(np.abs(ev[0]))
    except Exception:
        r = float(np.abs(np.linalg.eigvals(W.toarray())).max())
    return (W * (RHO / r)).tocsr(), r


# ----------------------------------------------------------------------------- market data
def load_panel():
    s = pd.read_parquet(ROOT / "data/research/nx/cache_SFP.parquet", columns=["ticker", "date", "close"])
    s = s[s.ticker.isin(ETFS)]
    s["date"] = pd.to_datetime(s.date)
    s = s.pivot(index="date", columns="ticker", values="close")[ETFS]
    a = pd.read_parquet(ROOT / "data/research/night/etf_daily.parquet", columns=["symbol", "timestamp", "close"])
    a = a[a.symbol.isin(ETFS)]
    a["date"] = pd.to_datetime(a.timestamp.dt.tz_convert("America/New_York").dt.date)
    a = a.pivot(index="date", columns="symbol", values="close")[ETFS]
    ls = np.log(s).diff().loc["2002-07-30":"2020-12-31"]
    la = np.log(a).diff().loc["2021-01-01":"2026-10-31"]
    r = pd.concat([ls, la]).dropna()
    vol = r.rolling(20).std()
    df = pd.concat([r.add_suffix("_r"), vol.add_suffix("_v")], axis=1).dropna()
    return df, r.loc[df.index]


# ----------------------------------------------------------------------------- reservoir
def run_reservoir(W, Win, U):
    T, n = U.shape[0], W.shape[0]
    X = np.zeros((T, n), np.float32)
    x = np.zeros(n)
    WinU = U @ Win.T
    Wt = W
    for t in range(T):
        x = (1 - LEAK) * x + LEAK * np.tanh(Wt @ x + WinU[t])
        X[t] = x
    return X


# ----------------------------------------------------------------------------- B1 ridge readout
class Gram:
    def __init__(self, n, k):
        self.G = np.zeros((n, n)); self.sx = np.zeros(n); self.XY = np.zeros((n, k)); self.sy = np.zeros(k); self.m = 0

    def add(self, X, Y):
        X = X.astype(np.float64)
        self.G += X.T @ X; self.sx += X.sum(0); self.XY += X.T @ Y; self.sy += Y.sum(0); self.m += len(X)

    def solve(self, lam, cols=None):
        mu = self.sx / self.m
        Gc = self.G - self.m * np.outer(mu, mu)
        XY = self.XY if cols is None else self.XY[:, cols]
        sy = self.sy if cols is None else self.sy[cols]
        ybar = sy / self.m
        XYc = XY - np.outer(mu, sy)
        Gc[np.diag_indices_from(Gc)] += lam
        b = sla.cho_solve(sla.cho_factor(Gc, lower=False, check_finite=False), XYc, check_finite=False)
        return ybar - mu @ b, b


def b1_positions(X, Y, ix):
    """Y: (T, k) label matrix (col 0 real, others placebo). Returns positions (T, k), chosen lambdas."""
    w0, d_tr_end, d_val0, d0, T = ix["w0"], ix["tr_end"], ix["val0"], ix["d0"], X.shape[0]
    k = Y.shape[1]
    # lambda selection: train rows w0..tr_end (label inside 2008), val rows val0..d0-2
    g = Gram(X.shape[1], k); g.add(X[w0:d_tr_end + 1], Y[w0:d_tr_end + 1])
    Xv, Yv = X[d_val0:d0 - 1].astype(np.float64), Y[d_val0:d0 - 1]
    mse = np.zeros((len(LAMS), k))
    for i, lam in enumerate(LAMS):
        a0, b = g.solve(lam)
        mse[i] = ((Xv @ b + a0 - Yv) ** 2).mean(0)
    lam_ix = mse.argmin(0)
    # expanding Gram up to rows <= d-2 at each refit date d = d0 + 21j
    g = Gram(X.shape[1], k)
    pos = np.full((T, k), np.nan)
    sdf = None
    last = w0
    refits = list(range(d0, T - 1, REFIT))
    for j, d in enumerate(refits):
        g.add(X[last:d - 1], Y[last:d - 1]); last = d - 1
        nxt = refits[j + 1] if j + 1 < len(refits) else T
        Xs = X[d:nxt].astype(np.float64)
        F = np.zeros((nxt - d, k))
        if sdf is None:
            sdf = np.zeros(k)
            Xf = X[w0:d0 - 1].astype(np.float64)
        for li in np.unique(lam_ix):
            cols = np.flatnonzero(lam_ix == li)
            a0, b = g.solve(LAMS[li], cols)
            F[:, cols] = Xs @ b + a0
            if j == 0:
                sdf[cols] = (Xf @ b + a0).std(0)
        pos[d:nxt] = np.clip(1 + F / sdf, 0, 1.5)
    return pos, lam_ix


# ----------------------------------------------------------------------------- B2 dopamine-gated readout
def b2_positions(X, Rlab, ix, seed=0):
    """Rlab: (T, k) next-day SPY simple return used as reward (placebo cols shifted in fit). Runs all ETAS for all k.
    Returns positions (T, k) using the eta picked per column by fit-period net Sharpe, and the chosen eta index."""
    w0, d0, T = ix["w0"], ix["d0"], X.shape[0]
    k = Rlab.shape[1]
    n = X.shape[1]
    rng = np.random.default_rng(seed)
    z = rng.standard_normal(n)
    sc = (X[w0:d0] @ z).std()
    winit = z * (0.1 / sc)
    eta = np.repeat(np.array(ETAS), k)          # columns: eta-major blocks
    R = np.tile(Rlab, (1, len(ETAS)))
    Wm = np.tile(winit[:, None], (1, k * len(ETAS)))
    rbar = np.zeros(k * len(ETAS)); abar = np.ones(k * len(ETAS))
    A = np.full((T, k * len(ETAS)), np.nan)
    a_prev = None
    for t in range(w0, T - 1):
        xt = X[t].astype(np.float64)
        a = np.clip(1 + xt @ Wm, 0, 1.5)
        A[t] = a
        if a_prev is None:
            a_prev = a
        # R[t] = return t->t+1 (label of row t); reward is realised at t+1's close, before a_{t+1} is computed
        r = a * R[t] - C1 * np.abs(a - a_prev)
        Wm += np.outer(xt, eta * (r - rbar) * (a - abar))
        rbar += (r - rbar) / TAU; abar += (a - abar) / TAU
        a_prev = a
    # eta selection on fit rows w0..d0-1 (P&L dates <= d0), with the same (possibly shifted) reward series
    pnl = A[w0:d0] * R[w0:d0]
    turn = np.abs(np.diff(A[w0:d0], axis=0, prepend=A[w0:w0 + 1]))
    net = pnl - C1 * turn
    sh = net.mean(0) / net.std(0)
    sh = sh.reshape(len(ETAS), k)
    e_ix = sh.argmax(0)
    pos = np.stack([A[:, e_ix[c] * k + c] for c in range(k)], axis=1)
    return pos, e_ix


# ----------------------------------------------------------------------------- evaluation
def nw_t(x, lags=NW_LAGS):
    x = np.asarray(x, float); n = len(x)
    e = x - x.mean(); s = (e * e).sum()
    for L in range(1, lags + 1):
        s += 2 * (1 - L / (lags + 1)) * (e[L:] * e[:-L]).sum()
    se = math.sqrt(s) / n
    return x.mean() / se if se > 0 else float("nan")


def alpha(s, m):
    b = np.cov(s, m, ddof=1)[0, 1] / m.var(ddof=1)
    res = s - b * m
    return res.mean(), nw_t(res), b, res


def dsr(x, n_trials):
    x = np.asarray(x, float); T = len(x)
    sr = x.mean() / x.std(ddof=1)
    sk = SS.skew(x); ku = SS.kurtosis(x, fisher=False); g = 0.5772156649
    sr0 = math.sqrt(1.0 / T) * ((1 - g) * SS.norm.ppf(1 - 1 / n_trials) + g * SS.norm.ppf(1 - 1 / (n_trials * math.e)))
    z = (sr - sr0) * math.sqrt(T - 1) / math.sqrt(max(1e-12, 1 - sk * sr + (ku - 1) / 4 * sr ** 2))
    return float(SS.norm.cdf(z))


def strat_returns(pos, Rs, cost):
    """pos[t] decided at close t, earns Rs[t] (t->t+1). Returns net return indexed by t (P&L lands on t+1)."""
    turn = np.abs(np.diff(pos, prepend=pos[:1]))
    return pos * Rs - cost * turn


def judge_alpha(pos, Rs, mask, cost=C1):
    s = strat_returns(pos, Rs, cost)
    return alpha(s[mask], Rs[mask])[0]


def full_stats(pos, Rs, pdates, mask):
    s1 = strat_returns(pos, Rs, C1)
    s3 = strat_returns(pos, Rs, C3)
    m = Rs
    a1, t1, b1, res = alpha(s1[mask], m[mask])
    h1 = mask & (pdates < pd.Timestamp("2016-01-01")); h2 = mask & (pdates >= pd.Timestamp("2016-01-01"))
    nan4 = (float("nan"),) * 4
    ah1, th1, _, _ = alpha(s1[h1], m[h1]) if h1.sum() > 10 else nan4
    ah2, th2, _, _ = alpha(s1[h2], m[h2]) if h2.sum() > 10 else nan4
    sh = s1[mask].mean() / s1[mask].std() * math.sqrt(252); shm = m[mask].mean() / m[mask].std() * math.sqrt(252)
    a3, t3, _, _ = alpha(s3[mask], m[mask])
    top = np.argsort(res)[-5:]
    keep = np.ones(mask.sum(), bool); keep[top] = False
    ax5, tx5, _, _ = alpha(s1[mask][keep], m[mask][keep])
    eq = np.cumprod(1 + s1[mask]); dd = (eq / np.maximum.accumulate(eq) - 1).min()
    return dict(a1=a1, t1=t1, beta=b1, ah1=ah1, th1=th1, ah2=ah2, th2=th2, sh=sh, shm=shm, dsh=sh - shm, a3=a3, t3=t3,
                ax5=ax5, tx5=tx5, med=np.median(s1[mask]), hit=(s1[mask] > 0).mean(), mdd=dd, expo=pos[mask].mean(),
                turn=np.abs(np.diff(pos[mask])).mean(), dsr=dsr(res, N_PROGRAM), n=int(mask.sum()),
                ann=(np.prod(1 + s1[mask]) ** (252 / mask.sum()) - 1), annm=(np.prod(1 + m[mask]) ** (252 / mask.sum()) - 1))


def fmt(st, tag):
    bp = 1e4
    return [f"  [{tag}] n={st['n']}  alpha {st['a1']*bp:+.2f}bp/day NW t {st['t1']:+.2f} (beta {st['beta']:.2f})",
            f"     halves: 2011-15 {st['ah1']*bp:+.2f}bp t {st['th1']:+.2f} | 2016-20 {st['ah2']*bp:+.2f}bp t {st['th2']:+.2f}",
            f"     Sharpe {st['sh']:.2f} vs SPY B&H {st['shm']:.2f} -> diff {st['dsh']:+.2f};  CAGR {st['ann']*100:.1f}% vs SPY {st['annm']*100:.1f}%",
            f"     3bp/side: alpha {st['a3']*bp:+.2f}bp t {st['t3']:+.2f};  ex-top-5 alpha {st['ax5']*bp:+.2f}bp t {st['tx5']:+.2f}",
            f"     median day {st['med']*bp:+.2f}bp, hit {st['hit']*100:.1f}%, maxDD {st['mdd']*100:.1f}%, mean exposure {st['expo']:.3f}, "
            f"turnover {st['turn']:.3f}/day, DSR(N {N_PROGRAM}) {st['dsr']:.3f}"]


def pct(x, ref):
    ref = np.asarray(ref)
    return 100.0 * (ref < x).mean()


# ----------------------------------------------------------------------------- main
def main():
    nodes, e = build_mb()
    n = len(nodes)
    src, dst, w = e.src.to_numpy(), e.dst.to_numpy(), e.w.to_numpy().astype(float)
    m = len(e)
    log("graph", n, m)
    pn = np.flatnonzero(nodes.cell_class.values == "ALPN")

    df, r = load_panel()
    dates = df.index
    T = len(dates)
    U_raw = df.to_numpy()
    fit_rows = dates <= pd.Timestamp(FIT_END)
    mu, sd = U_raw[fit_rows].mean(0), U_raw[fit_rows].std(0)
    U = (U_raw - mu) / sd
    spy_log = r["SPY"].to_numpy()
    y = np.append(spy_log[1:], np.nan)                       # label of row t = log ret t->t+1
    Rs = np.append(np.expm1(spy_log[1:]), np.nan)            # simple ret t->t+1
    pdates = pd.DatetimeIndex(np.append(dates[1:], pd.NaT))  # P&L date of row t
    d0 = int(np.flatnonzero(fit_rows)[-1])
    w0 = WASHOUT
    tr_end = int(np.flatnonzero(dates <= pd.Timestamp("2008-12-31"))[-1]) - 1
    val0 = tr_end + 1
    ix = dict(w0=w0, tr_end=tr_end, val0=val0, d0=d0)
    jmask = np.zeros(T, bool)
    jmask[d0:T - 1] = (pdates[d0:T - 1] >= pd.Timestamp(JUDGE[0])) & (pdates[d0:T - 1] <= pd.Timestamp(JUDGE[1]))
    rmask = np.zeros(T, bool); rmask[d0:T - 1] = pdates[d0:T - 1] > pd.Timestamp(JUDGE[1])

    rng_in = np.random.default_rng(0)
    Win = np.zeros((n, U.shape[1]))
    Win[pn] = (rng_in.random((len(pn), U.shape[1])) < IN_P) * rng_in.uniform(-1, 1, (len(pn), U.shape[1]))

    # placebo label matrix: col 0 real, cols 1..N_PLAC circularly shifted within fit rows w0..d0-1
    rng_p = np.random.default_rng(12345)
    shifts = rng_p.integers(250, 2001, size=N_PLAC)
    Fr = np.arange(w0, d0)
    Y = np.repeat(y[:, None], N_PLAC + 1, axis=1)
    RL = np.repeat(Rs[:, None], N_PLAC + 1, axis=1)
    for j, kk in enumerate(shifts, start=1):
        Y[Fr, j] = np.roll(y[Fr], kk); RL[Fr, j] = np.roll(Rs[Fr], kk)
    Y[np.isnan(Y)] = 0.0; RL[np.isnan(RL)] = 0.0
    Rs0 = np.nan_to_num(Rs)

    # ---- header
    cc = nodes.cell_class.value_counts()
    out("EXP round B: FLY-RES (N 1214) and FLY-DA (N 1215) -- research/sim/exp_flyres.py")
    out("pre-reg: research/drafts/round1_prose.md, '## Amendment - EXP round (user 2026-11-20 ...)'; program N 1218")
    out("")
    out("CONNECTOME: FlyWire adult whole-brain, materialization v783 (public, no login)")
    out("  edges  : https://zenodo.org/records/10676866  proofread_connections_783.feather (16.85M pre/post/neuropil rows)")
    out("  classes: https://github.com/flyconnectome/flywire_annotations  supplemental_files/Supplemental_file1_neuron_annotations.tsv")
    out(f"  MB subgraph: classes {MB_CLASSES}; pair synapses summed over neuropils, kept if >= {SYN_MIN}; autapses dropped;")
    out(f"  capped at {NCAP} by binary in+out degree inside the MB subgraph")
    out("  kept / total in class: " + ", ".join(f"{k} {cc.get(k,0)}/{int(nodes.loc[nodes.cell_class==k,'mb_total_in_class'].iloc[0]) if cc.get(k,0) else '?'}" for k in MB_CLASSES))
    nt = nodes.top_nt.fillna("unknown").value_counts()
    out("  presyn top_nt of kept neurons: " + ", ".join(f"{k} {v}" for k, v in nt.items()))
    other = int((~nodes.top_nt.isin(["gaba", "glutamate", "acetylcholine"])).sum())
    out(f"  sign rule: gaba/glutamate -1, acetylcholine +1, other/unknown +1 -> {other} neurons signed + as other/unknown"
        f" (KCs are predicted 'dopamine' by the FlyWire NT classifier; known_nt says ACh; both give +)")
    kc_known = nodes.loc[nodes.cell_class == "Kenyon_Cell", "known_nt"].fillna("na").value_counts().to_dict()
    out(f"  KC known_nt: {kc_known}")
    neg = (w < 0).sum()
    out(f"  edges {m:,}, density {m/(n*(n-1)):.4f}, negative edges {neg:,} ({100*neg/m:.2f}%), synapses {e.syn_count.sum():,}")
    out(f"  input units (ALPN) {len(pn)}; W_in nonzeros {int((Win!=0).sum())} (p {IN_P}, U(-1,1), seed 0)")
    out(f"  reservoir: spectral radius {RHO}, leak {LEAK}, tanh; inputs = 8 ETF day-t log return + 20d vol, z-scored on fit")
    out(f"  sessions {T} ({dates[0].date()}..{dates[-1].date()}); washout {WASHOUT} (training from {dates[w0].date()});"
        f" fit decisions end {dates[d0].date()}; Sharadar <= 2020-12-31, Alpaca etf_daily after")
    out("")

    # ---- real graph
    Wr, rad = to_W(src, dst, w, n)
    log("real radius", rad)
    X = run_reservoir(Wr, Win, U)
    log("reservoir done")
    posB1, lamB1 = b1_positions(X, Y, ix)
    log("B1 done", LAMS[lamB1[0]])
    posB2, etaB2 = b2_positions(X, RL, ix)
    log("B2 done", ETAS[etaB2[0]])
    plac1 = np.array([judge_alpha(np.nan_to_num(posB1[:, j], nan=1.0), Rs0, jmask) for j in range(1, N_PLAC + 1)])
    plac2 = np.array([judge_alpha(np.nan_to_num(posB2[:, j], nan=1.0), Rs0, jmask) for j in range(1, N_PLAC + 1)])
    p1, p2 = np.nan_to_num(posB1[:, 0], nan=1.0), np.nan_to_num(posB2[:, 0], nan=1.0)
    del X

    # ---- controls
    ctrl = {"rewire": ([], []), "ER": ([], [])}
    for fam in ["rewire", "ER"]:
        for c in range(N_CTRL):
            rg = np.random.default_rng(1000 + (0 if fam == "rewire" else 500) + c)
            if fam == "rewire":
                s_, d_, w_ = src, rewire(src, dst, n, rg), w
            else:
                s_, d_ = erdos(n, m, rg); w_ = w[rg.permutation(m)]
            Wc, _ = to_W(s_, d_, w_, n)
            Xc = run_reservoir(Wc, Win, U)
            pc1, _ = b1_positions(Xc, Y[:, :1], ix)
            pc2, _ = b2_positions(Xc, RL[:, :1], ix)
            ctrl[fam][0].append(judge_alpha(np.nan_to_num(pc1[:, 0], nan=1.0), Rs0, jmask))
            ctrl[fam][1].append(judge_alpha(np.nan_to_num(pc2[:, 0], nan=1.0), Rs0, jmask))
            log(fam, c, ctrl[fam][0][-1] * 1e4, ctrl[fam][1][-1] * 1e4)

    np.savez(CACHE / "flyres_results.npz", p1=p1, p2=p2, plac1=plac1, plac2=plac2, rw1=ctrl["rewire"][0], rw2=ctrl["rewire"][1],
             er1=ctrl["ER"][0], er2=ctrl["ER"][1], lam=lamB1, eta=etaB2)
    # ---- report
    spy_j = Rs0[jmask]
    out(f"SPY B&H judge 2011-20: mean {spy_j.mean()*1e4:+.2f}bp/day, Sharpe {spy_j.mean()/spy_j.std()*math.sqrt(252):.2f}")
    out("")
    for tag, pos, plac, ci, extra in [("B1 FLY-RES ridge", p1, plac1, 0, f"lambda chosen {LAMS[lamB1[0]]:g}"),
                                      ("B2 FLY-DA three-factor", p2, plac2, 1, f"eta chosen {ETAS[etaB2[0]]:g}")]:
        st = full_stats(pos, Rs0, pdates, jmask)
        out(f"== {tag} ({extra}) JUDGE 2011-01..2020-12 (P&L dates), 1bp/side ==")
        for L in fmt(st, "judge"):
            out(L)
        pp = pct(st["a1"], plac)
        rw, er = np.array(ctrl["rewire"][ci]), np.array(ctrl["ER"][ci])
        out(f"  placebo ({N_PLAC} circular label shifts 250-2000 in fit): real alpha percentile {pp:.1f} "
            f"(placebo median {np.median(plac)*1e4:+.2f}bp, 95th {np.percentile(plac,95)*1e4:+.2f}bp)")
        out(f"  controls: rewire (n {len(rw)}) median {np.median(rw)*1e4:+.2f}bp, 95th {np.percentile(rw,95)*1e4:+.2f}bp -> real percentile {pct(st['a1'], rw):.1f}")
        out(f"            ER     (n {len(er)}) median {np.median(er)*1e4:+.2f}bp, 95th {np.percentile(er,95)*1e4:+.2f}bp -> real percentile {pct(st['a1'], er):.1f}")
        g = [("1 alpha>0 & NW t>=2", st["a1"] > 0 and st["t1"] >= 2),
             ("2 both halves alpha>0", st["ah1"] > 0 and st["ah2"] > 0),
             ("3 Sharpe - SPY >= +0.20", st["dsh"] >= 0.20),
             ("4 3bp/side alpha>0 & t>=2", st["a3"] > 0 and st["t3"] >= 2),
             ("5 placebo >= 95th", pp >= 95),
             ("6 ex-top-5 alpha>0", st["ax5"] > 0),
             ("C rewire > 95th", st["a1"] > np.percentile(rw, 95)),
             ("C ER > 95th", st["a1"] > np.percentile(er, 95))]
        out("  GATES: " + " | ".join(f"{k}: {'PASS' if v else 'FAIL'}" for k, v in g))
        ok = all(v for _, v in g)
        out(f"  VERDICT {tag.split()[0]} {tag.split()[1]}: {'PASS' if ok else 'FAIL'}"
            + ("" if ok else " -- " + ("the fly's wiring adds nothing over a random reservoir" if not (g[6][1] and g[7][1]) else "fails the market gates")))
        if rmask.any():
            sr = full_stats(pos, Rs0, pdates, rmask)
            out(f"  REPORT 2021-01..{pdates[rmask][-1].date()} (Alpaca, descriptive, not judged):")
            for L in fmt(sr, "report")[:1] + fmt(sr, "report")[2:3] + fmt(sr, "report")[4:]:
                out(L)
        out("")
    out(f"runtime {time.time()-T0:.0f}s")
    OUT.write_text("\n".join(LINES) + "\n")


if __name__ == "__main__":
    main()
