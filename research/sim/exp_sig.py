"""DEEP round 1 N 1243 SIG: path-signature features of stock-vs-SPY paths, learned model, weekly long top decile.

Pre-registration: research/drafts/round1_prose.md, "## Amendment - DEEP round 1" (common block + N 1243 bullet; N 1241 -> 1245).

    PYTHONPATH=. python3 -m research.sim.exp_sig            # full run (judge pass, then report pass)
    PYTHONPATH=. python3 -m research.sim.exp_sig selftest   # signature unit tests only

Universe: SEP common stock (nx.is_common), delisted names kept through their last bar, unadjusted close >= $5 and ADV20
(closeunadj x volume, 20 bars) >= $10M at the decision close T, >= 60 bars of history. Total return = split-adjusted close +
ACTIONS cash dividends (exp_rl_universe._features convention). Calendar = SPY sessions. Decision every 5th session.
Features at close T use daily returns of sessions T-59..T only; target = total return close T -> close T+5 (a name with no
later bar earns 0 after its last bar: SEP has no delisting return, stated) minus the equal-weight mean of its Sharadar
sector among eligible names at T (blank sector = its own group).
Paths (scaled by each series' own 20d sd of daily log returns; the 60-session path uses the same 20d sd, as registered):
  p20 = (t in [0,1], cum log ret name, cum log ret SPY), 21 points, daily; p60 = same, 13 weekly-sampled points over 60 sessions.
  Level-3 signature of each (39 terms) by Chen's identity on the piecewise-linear path, plus the lead-lag (Z_2k = (X_k, X_k),
  Z_2k+1 = (X_k+1, X_k)) 4-channel path of (name, SPY) to level 2 (20 terms) for each window. 118 features, rank-normalized to
  [-1, 1] per decision (constant terms -> 0).
Models: ridge (alpha = z * n_train, z in 10^-4..10^3, chosen by inner expanding time-series CV on the last 3 training years,
score = mean per-decision IC) and HistGradientBoostingRegressor(max_iter=200, defaults otherwise, random_state 0).
Expanding window from 1998, refit yearly, first OOS year 2003. Long top decile EW close T -> T+5; LS = top - bottom decile.
Cost 5bp/side on actual turnover (sum |dw|, drift ignored), shock 10bp. Better model chosen on 2003-06 long excess only.
Judge pass = NX cache (decisions 1998..2010). Report pass = full Sharadar store (~/data/sharadar; the NX cache ends 2021-01-15),
same code, decisions 1998..2026, OOS 2011-20 and 2021-26 reported, never judged.
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_v] = "3"

import gc  # noqa: E402
import hashlib  # noqa: E402
import itertools  # noqa: E402
import pathlib  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from research.sim.exp_rl import dsr  # noqa: E402
from research.sim.exp_rl_universe import PRICE_MIN, ADV_MIN  # noqa: E402
from research.sim.nx import is_common  # noqa: E402
from research.sim.weekwin_short import tstat  # noqa: E402

OUT = ROOT / "research/sim/exp_sig_out.txt"
CACHE = pathlib.Path(os.environ.get("SIG_CACHE", "/tmp/exp_sig_cache"))
SRC = {"cache": dict(sep=ROOT / "data/research/nx/cache_SEP.parquet", tick=ROOT / "data/research/nx/cache_TICKERS.parquet",
                     act=ROOT / "data/research/nx/cache_ACTIONS.parquet", sfp=ROOT / "data/research/nx/cache_SFP.parquet"),
       "full": dict(sep=pathlib.Path.home() / "data/sharadar/stocks.parquet", tick=pathlib.Path.home() / "data/sharadar/tickers.parquet",
                    act=pathlib.Path.home() / "data/sharadar/actions.parquet", sfp=pathlib.Path.home() / "data/sharadar/funds.parquet")}
N_TRIALS = 1245
COST, SHOCK = 5e-4, 10e-4
H, STEP, LB = 5, 5, 60
FIRST_OOS, JUDGE_LAST_Y = 2003, 2010
ZGRID = 10.0 ** np.arange(-4.0, 3.01, 1.0)
N_PLACEBO = 20
NW = 4
GATE_EXC, GATE_T, GATE_SNAP = 15e-4, 2.5, 5e-4

lines: list[str] = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    lines.append(s)


# ---------------------------------------------------------------- signatures (Chen's identity, vectorized over names)
def signature(inc: np.ndarray, depth: int) -> list[np.ndarray]:
    """inc (K steps, n, D) increments of a piecewise-linear path -> [S1 (n,D), S2 (n,D,D)(, S3 (n,D,D,D))].
    Each linear segment has signature exp(d) = (1, d, d(x)d/2, d(x)d(x)d/6); S <- S (x) exp(d) (Chen)."""
    K, n, D = inc.shape
    S1 = np.zeros((n, D)); S2 = np.zeros((n, D, D)); S3 = np.zeros((n, D, D, D)) if depth >= 3 else None
    for k in range(K):
        d = inc[k].astype(np.float64)
        d2 = d[:, :, None] * d[:, None, :]
        if depth >= 3:
            S3 += (S2[:, :, :, None] * d[:, None, None, :] + S1[:, :, None, None] * d2[:, None, :, :] * 0.5
                   + d2[:, :, :, None] * d[:, None, None, :] / 6.0)
        S2 += S1[:, :, None] * d[:, None, :] + 0.5 * d2
        S1 += d
    return [S1, S2] + ([S3] if depth >= 3 else [])


def tensor_mult(a: list, b: list) -> list:
    """Truncated (level 3) tensor product of two signatures (no batch dim), for Chen tests."""
    a1, a2, a3 = a; b1, b2, b3 = b
    return [a1 + b1, a2 + b2 + np.outer(a1, b1),
            a3 + b3 + np.einsum("ij,k->ijk", a2, b1) + np.einsum("i,jk->ijk", a1, b2)]


def leadlag_inc(dX: np.ndarray) -> np.ndarray:
    """dX (K, n, C) increments -> lead-lag path increments (2K, n, 2C): lead step (dX, 0) then lag step (0, dX)."""
    K, n, C = dX.shape
    out = np.zeros((2 * K, n, 2 * C))
    out[0::2, :, :C] = dX
    out[1::2, :, C:] = dX
    return out


def selftest() -> list[str]:
    rng = np.random.default_rng(7)
    inc = rng.standard_normal((17, 5, 3))
    S1, S2, S3 = signature(inc, 3)
    tot = inc.sum(0)
    e1 = np.abs(S1 - tot).max()
    e2 = np.abs(0.5 * (S2 + S2.transpose(0, 2, 1)) - 0.5 * tot[:, :, None] * tot[:, None, :]).max()
    sym3 = sum(S3.transpose((0,) + tuple(1 + np.array(p))) for p in itertools.permutations(range(3))) / 6.0
    e3 = np.abs(sym3 - np.einsum("ni,nj,nk->nijk", tot, tot, tot) / 6.0).max()
    A = signature(inc[:9], 3); B = signature(inc[9:], 3)
    ch = tensor_mult([x[2] for x in A], [x[2] for x in B])
    e4 = max(np.abs(ch[i] - [S1, S2, S3][i][2]).max() for i in range(3))
    one = signature(inc[:1], 3)
    d = inc[0]
    e5 = max(np.abs(one[1] - 0.5 * np.einsum("ni,nj->nij", d, d)).max(),
             np.abs(one[2] - np.einsum("ni,nj,nk->nijk", d, d, d) / 6.0).max())
    dx = rng.standard_normal((11, 5, 1))
    L1, L2 = signature(leadlag_inc(dx), 2)
    e6 = np.abs((L2[:, 0, 1] - L2[:, 1, 0]) - (dx[:, :, 0] ** 2).sum(0)).max()   # lead-lag area = quadratic variation
    e7 = np.abs(L1[:, 0] - L1[:, 1]).max()
    errs = dict(level1_total_increment=e1, level2_sym_shuffle=e2, level3_sym_shuffle=e3, chen_concat=e4, segment_exp=e5,
                leadlag_area_eq_QV=e6, leadlag_level1=e7)
    bad = {k: v for k, v in errs.items() if not v < 1e-9}
    assert not bad, f"signature self-test failed: {bad}"
    return [f"selftest PASS: " + ", ".join(f"{k} err {v:.1e}" for k, v in errs.items())]


CH3 = ["t", "S", "M"]
CHLL = ["S+", "M+", "S-", "M-"]


def feat_names() -> list[str]:
    out = []
    for w in ("p20", "p60"):
        out += [f"{w}:{a}" for a in CH3]
        out += [f"{w}:{a},{b}" for a in CH3 for b in CH3]
        out += [f"{w}:{a},{b},{c}" for a in CH3 for b in CH3 for c in CH3]
    for w in ("ll20", "ll60"):
        out += [f"{w}:{a}" for a in CHLL]
        out += [f"{w}:{a},{b}" for a in CHLL for b in CHLL]
    return out


FEATS = feat_names()
SNAP = ["ret5", "ret20", "vol20", "beta60"]
WORD = {"t": "time", "S": "stock", "M": "SPY", "S+": "stock(lead)", "M+": "SPY(lead)", "S-": "stock(lag)", "M-": "SPY(lag)"}


def interpret(f: str) -> str:
    w, term = f.split(":"); ix = term.split(",")
    win = "20d daily" if w.endswith("20") else "60d weekly"
    if w.startswith("p"):
        if len(ix) == 1:
            return {"t": "constant", "S": f"stock's vol-scaled return over the {win} path",
                    "M": f"SPY's vol-scaled return over the {win} path"}[ix[0]]
        if len(ix) == 2:
            a, b = ix
            if a == b:
                return f"half the squared total {WORD[a]} move ({win}; redundant with level 1)"
            if a == "t":
                return f"int t d{WORD[b]}: recency-weighted {WORD[b]} move (late moves count more) ({win})"
            if b == "t":
                return f"int ({WORD[a]}-start) dt: time-averaged {WORD[a]} displacement (early moves count more) ({win})"
            return (f"int ({WORD[a]}-start) d{WORD[b]}: {WORD[a]} displacement accumulated while {WORD[b]} moves; high vs the "
                    f"reverse order = {WORD[a]} moved first, {WORD[b]} followed (Levy-area order term) ({win})")
        if len(set(ix)) == 1:
            return f"total {WORD[ix[0]]} move cubed / 6 ({win}; redundant)"
        return (f"3rd-order ordered term: increments of {' then '.join(WORD[i] for i in ix)} ({win}); "
                + ("time-shape of " + "/".join(sorted(set(WORD[i] for i in ix if i != 't'))) + " path" if "t" in ix
                   else "order-sensitive stock-SPY interaction"))
    if len(ix) == 1:
        return f"{WORD[ix[0]]} total move ({win} lead-lag; same as level 1)"
    a, b = ix
    if a[0] == b[0] and a != b:
        return f"{WORD[a]} x {WORD[b]} of the same series: area = realized quadratic variation of {WORD[a[0]]} (vol-of-path vs 20d sd) ({win})"
    if a == b:
        return f"half the squared {WORD[a]} move ({win}; redundant)"
    if a.endswith("+") and b.endswith("+") or a.endswith("-") and b.endswith("-"):
        return f"int {WORD[a]} d{WORD[b]} on synchronous channels (same as p-path cross term) ({win})"
    rel = "at or before" if a.endswith("+") else "strictly before"
    return (f"sum of d{WORD[a[0]]}_j d{WORD[b[0]]}_k over j {'<=' if a.endswith('+') else '<'} k: {WORD[a[0]]} moves {rel} "
            f"{WORD[b[0]]} (lead-lag cross-covariance; vs its reverse term = which series moved first) ({win})")


# ---------------------------------------------------------------- data
def load(source: str, end: str):
    p = SRC[source]
    t0 = time.time()
    tk = pd.read_parquet(p["tick"], columns=["table", "ticker", "category", "sector"])
    tk = tk[tk.table == "SEP"].drop_duplicates("ticker")
    common = sorted(set(tk.ticker[is_common(tk.category.fillna("").astype(str))]))
    spy = pq.read_table(p["sfp"], columns=["ticker", "date", "close", "closeunadj"],
                        filters=[("ticker", "=", "SPY"), ("date", "<=", pd.Timestamp(end))]).to_pandas()
    spy["date"] = pd.to_datetime(spy.date); spy = spy.sort_values("date").reset_index(drop=True)
    sessions = spy.date.to_numpy("datetime64[ns]")
    act = pd.read_parquet(p["act"], columns=["date", "action", "ticker", "value"])
    act = act[act.action == "dividend"].copy(); act["date"] = pd.to_datetime(act.date)
    dv = act.groupby(["ticker", "date"])["value"].sum().reset_index()

    def tr(code, day, c, cu, div):
        """bar-to-bar total return (close + split-adjusted cash dividend) / previous close - 1 (exp_rl_universe convention)."""
        with np.errstate(divide="ignore", invalid="ignore"):
            da = np.where(cu > 0, div * c / cu, 0.0)
            prev = np.r_[np.nan, c[:-1]]
            first = np.r_[True, code[1:] != code[:-1]]
            prev[first] = np.nan
            r = (c + da) / prev - 1
        r[~np.isfinite(r)] = np.nan
        return r, first

    def day_of(x):
        return pd.DatetimeIndex(x).to_numpy("datetime64[D]").astype(np.int64)

    sd_ = dv[dv.ticker == "SPY"].set_index("date")["value"].reindex(spy.date).fillna(0.0).to_numpy()
    spy_r, _ = tr(np.zeros(len(spy), int), None, spy.close.to_numpy(np.float64), spy.closeunadj.to_numpy(np.float64), sd_)
    tb = pq.read_table(p["sep"], columns=["ticker", "date", "close", "closeunadj", "volume"],
                       filters=[("date", "<=", pd.Timestamp(end)), ("ticker", "in", common)])
    b = tb.to_pandas(strings_to_categorical=True); del tb
    b["date"] = pd.to_datetime(b.date)
    code = b.ticker.cat.codes.to_numpy().astype(np.int64)
    names = np.asarray(b.ticker.cat.categories).astype(str)
    b = b.drop(columns="ticker")
    o = np.lexsort((b.date.to_numpy(), code)); b = b.iloc[o].reset_index(drop=True); code = code[o]
    dday = day_of(b.date)
    dvc = pd.Index(names).get_indexer(dv.ticker.to_numpy())
    dvk = dv[dvc >= 0]; dkey = dvc[dvc >= 0].astype(np.int64) * 100000 + day_of(dvk.date)
    gi = pd.Index(dkey).get_indexer(code * 100000 + dday)
    div = np.where(gi >= 0, dvk.value.to_numpy(np.float64)[np.maximum(gi, 0)], 0.0)
    r, first = tr(code, dday, b.close.to_numpy(np.float64), b.closeunadj.to_numpy(np.float64), div)
    del div, gi, dday
    n = len(b)
    start = np.maximum.accumulate(np.where(first, np.arange(n), 0)); pos = np.arange(n) - start
    dvol = b.closeunadj.to_numpy(np.float64) * b.volume.to_numpy(np.float64)
    cs = np.cumsum(np.nan_to_num(dvol)); cs20 = np.r_[np.zeros(20), cs[:-20]]
    adv20 = np.where(pos >= 19, (cs - cs20) / 20.0, np.nan)
    sidx = np.searchsorted(sessions, b.date.to_numpy("datetime64[ns]"))
    on_cal = (sidx < len(sessions)) & (sessions[np.minimum(sidx, len(sessions) - 1)] == b.date.to_numpy("datetime64[ns]"))
    say(f"[{source}] SEP common rows {n:,} names {len(names):,} sessions {len(sessions)} ({str(sessions[0])[:10]}..{str(sessions[-1])[:10]}); "
        f"rows off the SPY calendar dropped {int((~on_cal).sum())}; load {time.time()-t0:.0f}s")
    R = np.full((len(sessions), len(names)), np.nan, np.float32)
    R[sidx[on_cal], code[on_cal]] = r[on_cal]
    elig = on_cal & (b.closeunadj.to_numpy() >= PRICE_MIN) & (adv20 >= ADV_MIN) & (pos >= LB) & np.isfinite(r)
    el = pd.DataFrame({"s": sidx[elig], "c": code[elig]})
    secmap = tk.set_index("ticker").sector.fillna("").reindex(names).fillna("").to_numpy()
    sec = pd.factorize(secmap)[0].astype(np.int32)
    del b, r, dvol, cs, cs20, adv20, sidx, code, pos, first, start; gc.collect()
    return sessions, np.nan_to_num(spy_r).astype(np.float64), R, el, sec, names


def build(source: str, end: str, last_decision: str):
    f = CACHE / f"{source}_{last_decision}.npz"
    if f.exists():
        z = np.load(f, allow_pickle=False)
        return {k: z[k] for k in z.files}
    sessions, spy_r, R, el, sec, names = load(source, end)
    t0 = time.time()
    S = len(sessions)
    dates = pd.DatetimeIndex(sessions)
    dec = np.arange(LB, S - H, STEP)
    dec = dec[dates[dec] <= pd.Timestamp(last_decision)]
    groups = el.groupby("s")["c"].apply(np.sort)
    Xs, XSn, Y, FW, C, D, EW, SPYF, CAN, NN, TRUNC = [], [], [], [], [], [], [], [], [], [], []
    lspy = np.log1p(spy_r)
    for k, s in enumerate(dec):
        if s not in groups.index:
            continue
        c = groups.loc[s]
        if len(c) < 20:
            continue
        lo = s - LB + 1
        assert lo >= 1 and s + H < S
        W = np.nan_to_num(R[lo:s + 1][:, c].astype(np.float64))                 # sessions T-59..T (features)
        F = np.nan_to_num(R[s + 1:s + H + 1][:, c].astype(np.float64))         # sessions T+1..T+5 (target)
        lr = np.log1p(np.maximum(W, -0.99))
        m = lspy[lo:s + 1]
        sd = np.maximum(lr[-20:].std(0, ddof=1), 1e-4); sdm = max(m[-20:].std(ddof=1), 1e-4)
        n = len(c)
        inc20 = np.empty((20, n, 3)); inc20[:, :, 0] = 1 / 20; inc20[:, :, 1] = lr[-20:] / sd; inc20[:, :, 2] = (m[-20:] / sdm)[:, None]
        w5 = lr.reshape(12, 5, n).sum(1); m5 = m.reshape(12, 5).sum(1)
        inc60 = np.empty((12, n, 3)); inc60[:, :, 0] = 1 / 12; inc60[:, :, 1] = w5 / sd; inc60[:, :, 2] = (m5 / sdm)[:, None]
        parts = []
        for inc in (inc20, inc60):
            s1, s2, s3 = signature(inc, 3)
            parts += [s1, s2.reshape(n, -1), s3.reshape(n, -1)]
        for inc in (inc20, inc60):
            l1, l2 = signature(leadlag_inc(inc[:, :, 1:]), 2)
            parts += [l1, l2.reshape(n, -1)]
        X = np.hstack(parts)
        assert X.shape[1] == len(FEATS)
        Wm = spy_r[lo:s + 1]
        beta = ((W - W.mean(0)) * (Wm - Wm.mean())[:, None]).sum(0) / ((Wm - Wm.mean()) ** 2).sum()
        snap = np.column_stack([np.expm1(lr[-5:].sum(0)), np.expm1(lr[-20:].sum(0)), W[-20:].std(0, ddof=1), beta])
        fw = np.prod(1 + F, axis=0) - 1
        sc = sec[c]
        smean = pd.Series(fw).groupby(sc).transform("mean").to_numpy()
        y = fw - smean
        # lookahead canary: IC of the window's own return (through T) vs a leaky return that includes T+1
        leak = np.expm1(lr[-19:].sum(0) + np.log1p(np.maximum(F[0], -0.99)))
        CAN.append((np.corrcoef(snap[:, 1], fw)[0, 1], np.corrcoef(leak, fw)[0, 1]))
        TRUNC.append(int(np.isnan(R[s + H, c]).sum()))
        Xs.append(pd.DataFrame(X).rank().to_numpy()); XSn.append(pd.DataFrame(snap).rank().to_numpy())
        Y.append(y); FW.append(fw); C.append(c); D.append(np.full(n, k)); EW.append(fw.mean())
        SPYF.append(np.prod(1 + spy_r[s + 1:s + H + 1]) - 1); NN.append(n)
    nn = np.array(NN)

    def rn(blocks):
        out = np.empty((nn.sum(), blocks[0].shape[1]), np.float32); o = 0
        for a, n in zip(blocks, nn):
            out[o:o + n] = (2 * (a - 1) / (n - 1) - 1); o += n
        return out
    kept = np.array(sorted(set(np.concatenate(D).tolist())))
    res = dict(X=rn(Xs), XS=rn(XSn), y=np.concatenate(Y).astype(np.float32), fw=np.concatenate(FW).astype(np.float32),
               code=np.concatenate(C).astype(np.int32), nn=nn, ddate=sessions[dec[kept]].astype("datetime64[D]").astype(np.int64),
               dsidx=dec[kept], ew=np.array(EW), spy=np.array(SPYF), canary=np.array(CAN), trunc=np.array(TRUNC))
    say(f"[{source}] decisions {len(nn)} ({str(sessions[dec[kept[0]]])[:10]}..{str(sessions[dec[kept[-1]]])[:10]}), rows {nn.sum():,}, "
        f"names/decision median {int(np.median(nn))} min {nn.min()} max {nn.max()}; features {len(FEATS)}; build {time.time()-t0:.0f}s")
    del R; gc.collect()
    CACHE.mkdir(parents=True, exist_ok=True)
    np.savez(f, **res)
    return res


# ---------------------------------------------------------------- models
class Data:
    def __init__(self, d: dict, which: str):
        self.X = d["X"] if which == "sig" else d["XS"]
        self.y = d["y"].astype(np.float64); self.fw = d["fw"]; self.code = d["code"]; self.nn = d["nn"]
        self.off = np.r_[0, np.cumsum(self.nn)]
        self.dates = pd.to_datetime(d["ddate"], unit="D"); self.years = self.dates.year.to_numpy()
        self.ew = d["ew"]; self.dsidx = d["dsidx"]
        self.dec_of_row = np.repeat(np.arange(len(self.nn)), self.nn)

    def rows(self, mask_dec):
        k = np.where(mask_dec)[0]
        return np.concatenate([np.arange(self.off[i], self.off[i + 1]) for i in k]) if len(k) else np.zeros(0, int)

    def train_mask(self, Y):
        """decisions before year Y whose label (T+5) is realised by the first decision close of year Y (purge)."""
        first = self.dsidx[self.years >= Y].min() if (self.years >= Y).any() else np.inf
        m = (self.years < Y) & (self.dsidx + H <= first)
        assert (m == (self.years < Y)).all(), "purge binds: yearly sufficient stats would include a purged decision"
        return m


def mean_ic(pred, y, dec):
    out = []
    for g in np.unique(dec):
        i = dec == g
        if i.sum() > 2 and pred[i].std() > 0:
            out.append(np.corrcoef(pred[i], y[i])[0, 1])
    return float(np.mean(out)) if out else -1.0


def ridge_stats(X, y):
    n = len(X); Xd = X.astype(np.float64)
    return dict(n=n, sx=Xd.sum(0), sy=y.sum(), xx=Xd.T @ Xd, xy=Xd.T @ y)


def ridge_solve(st_list, z):
    n = sum(s["n"] for s in st_list); sx = sum(s["sx"] for s in st_list); sy = sum(s["sy"] for s in st_list)
    xx = sum(s["xx"] for s in st_list); xy = sum(s["xy"] for s in st_list)
    mu = sx / n; my = sy / n
    Cm = xx - n * np.outer(mu, mu); c = xy - n * mu * my
    beta = np.linalg.solve(Cm + z * n * np.eye(len(mu)), c)
    return beta, my - mu @ beta


def run_ridge(D: Data, years, y=None):
    """Expanding yearly refit; returns OOS predictions per row (nan outside) and chosen z per year."""
    y = D.y if y is None else y
    pred = np.full(len(D.y), np.nan); zs = {}; coefs = {}
    yrs_all = np.unique(D.years)
    st = {}
    for yr in yrs_all:
        r = D.rows(D.years == yr)
        st[yr] = ridge_stats(D.X[r], y[r])
    for Y in years:
        trm = D.train_mask(Y)
        tr_years = [yr for yr in yrs_all if yr < Y]
        vals = tr_years[-3:]
        score = []
        for z in ZGRID:
            sc = []
            for v in vals:
                fit_y = [yr for yr in tr_years if yr < v]
                if len(fit_y) < 1:
                    continue
                b, a = ridge_solve([st[yr] for yr in fit_y], z)
                r = D.rows(D.years == v)
                sc.append(mean_ic(D.X[r] @ b + a, y[r], D.dec_of_row[r]))
            score.append(np.mean(sc))
        z = ZGRID[int(np.argmax(score))]; zs[Y] = z
        assert trm.sum() == sum(1 for yr in tr_years for _ in range(int((D.years == yr).sum())))
        b, a = ridge_solve([st[yr] for yr in tr_years], z)
        r = D.rows(D.years == Y)
        pred[r] = D.X[r] @ b + a
        coefs[Y] = b
    return pred, zs, coefs


def run_hgb(D: Data, years, y=None, keep_last=False):
    from sklearn.ensemble import HistGradientBoostingRegressor
    y = D.y if y is None else y
    pred = np.full(len(D.y), np.nan); last = None; iters = {}
    for Y in years:
        tr = D.rows(D.train_mask(Y)); te = D.rows(D.years == Y)
        m = HistGradientBoostingRegressor(max_iter=200, random_state=0)
        m.fit(D.X[tr], y[tr])
        pred[te] = m.predict(D.X[te]); iters[Y] = m.n_iter_
        if keep_last:
            last = m
        del m; gc.collect()
    return pred, iters, last


# ---------------------------------------------------------------- portfolio
def portfolio(D: Data, pred, decs):
    """Long top decile / short bottom decile, EW; per decision gross, turnover (sum |dw|) and EW benchmark."""
    L, Sg, TL, TS, EW = [], [], [], [], []
    wl, ws = {}, {}
    for k in decs:
        i0, i1 = D.off[k], D.off[k + 1]
        p = pred[i0:i1]; c = D.code[i0:i1]; f = D.fw[i0:i1].astype(np.float64)
        n = len(p); m = max(1, n // 10)
        o = np.lexsort((c, -p))
        top, bot = o[:m], o[-m:]
        L.append(f[top].mean()); Sg.append(f[bot].mean()); EW.append(f.mean())
        nl = {int(x): 1.0 / m for x in c[top]}; ns = {int(x): 1.0 / m for x in c[bot]}
        TL.append(sum(abs(nl.get(x, 0) - wl.get(x, 0)) for x in set(nl) | set(wl)))
        TS.append(sum(abs(ns.get(x, 0) - ws.get(x, 0)) for x in set(ns) | set(ws)))
        wl, ws = nl, ns
    return {k: np.array(v) for k, v in dict(L=L, S=Sg, TL=TL, TS=TS, EW=EW).items()}


def excess(P, cost=COST):
    return P["L"] - cost * P["TL"] - P["EW"]


def ls(P, cost=COST):
    return P["L"] - P["S"] - cost * (P["TL"] + P["TS"])


def ex_top5(x):
    return np.sort(x)[:-5].mean()


def summ(tag, P, dates, h1_end):
    x = excess(P); x2 = excess(P, SHOCK)
    h1 = dates <= pd.Timestamp(h1_end)
    l = ls(P)
    say(f"  {tag}: long excess net {x.mean()*1e4:+.1f}bp/wk t {tstat(x, NW):+.2f} | halves {x[h1].mean()*1e4:+.1f} / {x[~h1].mean()*1e4:+.1f} "
        f"| ex-top5 {ex_top5(x)*1e4:+.1f} | 2x cost {x2.mean()*1e4:+.1f} | median {np.median(x)*1e4:+.1f} hit {(x>0).mean()*100:.0f}% "
        f"| gross long-EW {(P['L']-P['EW']).mean()*1e4:+.1f} | turnover {P['TL'].mean():.2f}/wk | LS net {l.mean()*1e4:+.1f}bp/wk "
        f"t {tstat(l, NW):+.2f} | weeks {len(x)}")
    return x


def decile_table(D: Data, pred, decs):
    M = np.zeros((len(decs), 10))
    for j, k in enumerate(decs):
        i0, i1 = D.off[k], D.off[k + 1]
        p = pred[i0:i1]; f = D.fw[i0:i1].astype(np.float64)
        q = np.minimum((pd.Series(p).rank(method="first").to_numpy() - 1) * 10 // len(p), 9).astype(int)
        M[j] = [f[q == d].mean() - f.mean() for d in range(10)]
    return "  ".join(f"D{d+1} {M[:, d].mean()*1e4:+.1f}" for d in range(10))


# ---------------------------------------------------------------- main
def main():
    t0 = time.time()
    sha = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]
    say(f"DEEP round 1 N 1243 SIG (program N {N_TRIALS}; code sha256 {sha}; threads 3)")
    say(f"universe: SEP common, px>=${PRICE_MIN:g}, ADV20>=${ADV_MIN/1e6:g}M, >={LB} bars; weekly decisions (every {STEP}th SPY session); "
        f"target close T->T+{H} minus sector EW; long top decile EW; cost {COST*1e4:g}bp/side (shock {SHOCK*1e4:g}); NW lags {NW}")
    for s in selftest():
        say(s)
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        return
    # ================= JUDGE PASS (NX cache, decisions through 2010)
    d = build("cache", "2011-01-31", "2010-12-31")
    can = d["canary"]
    say(f"lookahead: features from sessions T-{LB-1}..T, target T+1..T+{H} (disjoint, asserted); canary mean XS corr with target: "
        f"ret20 through T {np.nanmean(can[:,0]):+.4f} vs leaky ret incl. T+1 {np.nanmean(can[:,1]):+.4f}; names with no bar at T+5 "
        f"(delisted/gap, earn 0 after last bar) {d['trunc'].sum():,} of {d['nn'].sum():,}")
    res = {}
    judge_years = list(range(FIRST_OOS, JUDGE_LAST_Y + 1))
    for which in ("sig", "snap"):
        D = Data(d, which)
        decs = np.where((D.years >= FIRST_OOS) & (D.years <= JUDGE_LAST_Y))[0]
        pr, zs, coefs = run_ridge(D, judge_years)
        res[("ridge", which)] = dict(pred=pr, P=portfolio(D, pr, decs), zs=zs, coefs=coefs)
        say(f"  ridge/{which} z by year: " + " ".join(f"{y}:{z:g}" for y, z in zs.items()) + f" ({time.time()-t0:.0f}s)")
        ph, it, last = run_hgb(D, judge_years, keep_last=(which == "sig"))
        res[("hgb", which)] = dict(pred=ph, P=portfolio(D, ph, decs), iters=it, last=last)
        say(f"  hgb/{which} n_iter by year: " + " ".join(f"{y}:{v}" for y, v in it.items()) + f" ({time.time()-t0:.0f}s)")
    D = Data(d, "sig")
    decs = np.where((D.years >= FIRST_OOS) & (D.years <= JUDGE_LAST_Y))[0]
    jd = D.dates[decs]
    say(f"\n=== JUDGE OOS 2003-2010 ({len(decs)} weeks; halves 2003-06 / 2007-10); excess = long top decile net - universe EW")
    X = {}
    for key in res:
        X[key] = summ(f"{key[0]}/{key[1]}", res[key]["P"], jd, "2006-12-31")
    h1 = jd <= pd.Timestamp("2006-12-31")
    sel = {m: X[(m, "sig")][h1].mean() for m in ("ridge", "hgb")}
    best = max(sel, key=sel.get)
    say(f"model choice on 2003-06 only: ridge {sel['ridge']*1e4:+.1f} vs hgb {sel['hgb']*1e4:+.1f}bp/wk -> {best}")
    x = X[(best, "sig")]; xs_ = X[(best, "snap")]
    x2 = excess(res[(best, "sig")]["P"], SHOCK)
    say(f"  {best}/sig deciles (mean 5d return minus EW, bp; D10 = highest forecast): {decile_table(D, res[(best,'sig')]['pred'], decs)}")
    # placebo: within-decision shuffled training targets, retrain (chosen model only)
    pl = []
    rng = np.random.default_rng(12345)
    for j in range(N_PLACEBO):
        order = np.lexsort((rng.random(len(D.y)), D.dec_of_row))
        ysh = D.y[order]
        pp = run_ridge(D, judge_years, ysh)[0] if best == "ridge" else run_hgb(D, judge_years, ysh)[0]
        pl.append(excess(portfolio(D, pp, decs)).mean())
        say(f"    placebo {j+1}/{N_PLACEBO}: {pl[-1]*1e4:+.1f}bp/wk ({time.time()-t0:.0f}s)")
    pl = np.array(pl); pct = (pl < x.mean()).mean() * 100
    say(f"  placebo (20 shuffled-target retrains of {best}): mean {pl.mean()*1e4:+.1f}, p95 {np.percentile(pl,95)*1e4:+.1f}bp/wk; real at pct {pct:.0f}")
    ds = dsr(x, N_TRIALS)
    say(f"  DSR(N {N_TRIALS}) of weekly excess {ds:.3f}; weekly Sharpe {x.mean()/x.std(ddof=1):.3f} (ann {x.mean()/x.std(ddof=1)*np.sqrt(52):.2f})")
    # importance
    if best == "ridge":
        b = res[("ridge", "sig")]["coefs"][JUDGE_LAST_Y]
        imp = np.abs(b); sign = np.sign(b); how = "|coef| on rank features, fit through 2009"
    else:
        m = res[("hgb", "sig")]["last"]
        r = D.rows(D.years == JUDGE_LAST_Y)
        base = mean_ic(m.predict(D.X[r]), D.y[r], D.dec_of_row[r])
        prng = np.random.default_rng(1); imp = np.zeros(len(FEATS)); sign = np.zeros(len(FEATS))
        Xr = D.X[r].copy(); pr0 = m.predict(Xr)
        for j in range(len(FEATS)):
            keep = Xr[:, j].copy(); Xr[:, j] = prng.permutation(keep)
            imp[j] = base - mean_ic(m.predict(Xr), D.y[r], D.dec_of_row[r]); Xr[:, j] = keep
            sign[j] = np.sign(np.corrcoef(keep, pr0)[0, 1])
        how = f"permutation drop in mean IC on 2010 OOS (fit through 2009; base IC {base:+.4f})"
    say(f"  top-10 signature terms ({how}; sign = direction of the forecast):")
    for j in np.argsort(-imp)[:10]:
        say(f"    {FEATS[j]:<14} imp {imp[j]:.5f} sign {'+' if sign[j] > 0 else '-'}  {interpret(FEATS[j])}")
    gates = [("G1 excess>=+15bp/wk", x.mean() >= GATE_EXC), ("G1b t>=2.5", tstat(x, NW) >= GATE_T),
             ("G2 halves>0", x[h1].mean() > 0 and x[~h1].mean() > 0), ("G3 ex-top-5>0", ex_top5(x) > 0),
             ("G4 2x cost>0", x2.mean() > 0), ("G5 beats snapshot by>=5bp", (x - xs_).mean() >= GATE_SNAP),
             ("G6 placebo>=95th", pct >= 95)]
    say(f"\nGATES ({best}/sig, judge 2003-10): excess {x.mean()*1e4:+.1f}bp/wk; t {tstat(x, NW):+.2f}; halves {x[h1].mean()*1e4:+.1f} / "
        f"{x[~h1].mean()*1e4:+.1f}; ex-top-5 {ex_top5(x)*1e4:+.1f}; 2x cost {x2.mean()*1e4:+.1f}; sig - snapshot "
        f"{(x-xs_).mean()*1e4:+.1f}bp/wk (snapshot {xs_.mean()*1e4:+.1f}); placebo pct {pct:.0f}; DSR(N {N_TRIALS}) {ds:.3f}")
    say("  " + "; ".join(f"{n} {'PASS' if v else 'FAIL'}" for n, v in gates))
    verdict = "PASS" if all(v for _, v in gates) else "KILL"
    say(f"{verdict}: N 1243 SIG ({best} chosen on 2003-06)" + ("" if verdict == "PASS" else
        " - failed: " + ", ".join(n for n, v in gates if not v)))
    OUT.write_text("\n".join(lines) + "\n")
    chosen_snap_mean = xs_.mean()
    del res, d, D, X; gc.collect()
    # ================= REPORT PASS (full store, OOS 2011-26, chosen model + its snapshot twin), never judged
    say(f"\n=== REPORT (full Sharadar store; descriptive, never judged) chosen model {best}")
    try:
        d = build("full", "2026-12-31", "2026-12-31")
    except Exception as e:  # noqa: BLE001
        say(f"full store unavailable ({e!r}); REPORT skipped")
        OUT.write_text("\n".join(lines) + "\n")
        return
    for which in ("sig", "snap"):
        D = Data(d, which)
        yrs = list(range(JUDGE_LAST_Y + 1, int(D.years.max()) + 1))
        pr = run_ridge(D, yrs)[0] if best == "ridge" else run_hgb(D, yrs)[0]
        for lo, hi, h1e in ((2011, 2020, "2015-12-31"), (2021, 2026, "2023-12-31")):
            decs = np.where((D.years >= lo) & (D.years <= hi))[0]
            if len(decs) == 0:
                continue
            P = portfolio(D, pr, decs)
            summ(f"{best}/{which} {lo}-{min(hi, int(D.years.max()))} (halves split {h1e[:4]})", P, D.dates[decs], h1e)
            if which == "sig":
                say(f"    deciles: {decile_table(D, pr, decs)}")
        say(f"  ({time.time()-t0:.0f}s)")
    say(f"total {time.time()-t0:.0f}s")
    OUT.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
