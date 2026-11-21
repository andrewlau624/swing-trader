"""DEEP round 1, N 1244 TAIL: downside beta / coskewness / empirical lower-tail dependence vs SPY.

Pre-registration: research/drafts/round1_prose.md, "## Amendment - DEEP round 1" (common block + N 1244 bullet). Not tuned.

    PYTHONPATH=. python3 research/sim/exp_tail.py         # -> research/sim/exp_tail_out.txt

Data: Sharadar SEP common stocks (nx.is_common), delisted kept through their last bar. JUDGE + 2011-20 from the NX caches
(data/research/nx, 1998-2021-01); 2021-26 REPORT from ~/data/sharadar/stocks.parquet (loaded from 2019-06, same code path, the
xsrff "full" precedent). Total return = split-adjusted close + ACTIONS cash dividends (exp_rl_universe._features convention).
Session grid = SPY's sessions; a stock bar off the grid is dropped.
Month-end features (last session of a month, trailing 252 sessions, name must have a finite return on all 252):
  beta; downside / upside beta (days SPY ret < / >= its 252d mean, conditional cov/var, Ang-Chen-Xing);
  coskewness (Harvey-Siddique standardized: E[e (m-mbar)^2] / (sqrt(E[e^2]) E[(m-mbar)^2]), e = CAPM residual);
  LTD = P(name <= its 10% quantile | SPY <= its 10% quantile) / 0.10; UTD the same at the 90% quantiles.
Eligible at the formation close: closeunadj >= $5, ADV20 (closeunadj x volume, last 20 bars) >= $10M.
Holding month = sessions after the formation close through the next month-end close, compounded; a name with no bar on a
session earns 0 that session (a gap's return lands on the next bar; after the last bar = cash). No delisting return beyond the
last SEP close (SEP carries none).
Gate M: formation months whose 12-month (252-session) forward window ends inside the window. Forward LTD needs 252 finite
forward returns (survivor-conditional); crash return = mean return on SPY's worst 5% of the forward 252 sessions (>= 5 of them
traded). Pooled cross-sectional rank corr = Pearson corr of within-month percentile ranks, pooled. The crash-return relation is
expected negative (high LTD -> worse crash return); it is gated as -corr >= 0.20.
Resilient arm: within monthly beta terciles, the lowest-LTD quintile (ties broken by a seeded random draw), equal weight across
the three tercile quintiles; benchmark = mean of the three tercile EW returns (gross). Cost 5bp/side on drifted turnover; 2x shock.
CAPM alpha vs SPY on excess returns over DTB3 (monthly); NW(5) t. Placebo: 200 random-within-tercile draws of the same counts,
gross alpha vs real gross alpha. ACX: quintiles on (beta_down - beta) across all eligible, Q5 - Q1 EW, 5bp/side both legs.
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "3")

import math  # noqa: E402
import pathlib  # noqa: E402
import sys  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from research.sim.exp_rl import ols_alpha, dsr  # noqa: E402
from research.sim.nx import is_common  # noqa: E402

NXD = ROOT / "data/research/nx"
FULL = pathlib.Path(os.path.expanduser("~/data/sharadar"))
OUT = ROOT / "research/sim/exp_tail_out.txt"
PRICE_MIN, ADV_MIN = 5.0, 1e7
COST, COST_X = 5e-4, 10e-4
N_TRIALS = 1245
L = 252
J0, J1 = "1999-01-01", "2010-12-31"
H1_END = "2004-12-31"
N_PLACEBO = 200

lines: list[str] = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    lines.append(s)


# ---------------------------------------------------------------- data
def _src(source):
    if source == "cache":
        return NXD / "cache_SEP.parquet", NXD / "cache_SFP.parquet", NXD / "cache_TICKERS.parquet", NXD / "cache_ACTIONS.parquet", "1997-12-01"
    return FULL / "stocks.parquet", FULL / "funds.parquet", FULL / "tickers.parquet", FULL / "actions.parquet", "2019-06-01"


def _read(path, tickers, start, act_path, sessions=None):
    """Long arrays sorted by (code, date) on the session grid: names, code, sidx, ret (f32), cu (f32), adv20 (f32), pos."""
    tb = pq.read_table(path, columns=["ticker", "date", "close", "volume", "closeunadj"],
                       filters=[("date", ">=", pd.Timestamp(start)), ("ticker", "in", list(tickers))])
    tk = tb.column("ticker").combine_chunks().dictionary_encode()
    names = np.array(tk.dictionary.to_pylist(), dtype=object)
    code = tk.indices.to_numpy().astype(np.int32)
    date = tb.column("date").to_numpy().astype("datetime64[ns]")
    close = tb.column("close").to_numpy().astype(np.float32)
    cu = tb.column("closeunadj").to_numpy().astype(np.float32)
    vol = tb.column("volume").to_numpy().astype(np.float32)
    del tb, tk
    o = np.lexsort((date, code))
    code, date, close, cu, vol = code[o], date[o], close[o], cu[o], vol[o]
    del o
    if sessions is None:
        sessions = np.unique(date)
    sidx = np.searchsorted(sessions, date)
    ok = (sidx < len(sessions)) & (sessions[np.minimum(sidx, len(sessions) - 1)] == date)
    code, close, cu, vol, sidx = code[ok], close[ok], cu[ok], vol[ok], sidx[ok].astype(np.int32)
    del date, ok
    S = len(sessions)
    # dividends
    a = pd.read_parquet(act_path, columns=["date", "action", "ticker", "value"])
    a = a[(a.action == "dividend") & a.ticker.isin(set(names))]
    cmap = {t: i for i, t in enumerate(names)}
    ac = a.ticker.map(cmap).to_numpy(np.int64)
    asx = np.searchsorted(sessions, pd.to_datetime(a.date).to_numpy("datetime64[ns]"))
    okd = asx < S
    dv = pd.Series(a.value.to_numpy(float)[okd]).groupby(ac[okd] * S + asx[okd]).sum()
    key = code.astype(np.int64) * S + sidx
    j = np.searchsorted(dv.index.to_numpy(), key)
    j = np.minimum(j, len(dv) - 1)
    hit = dv.index.to_numpy()[j] == key
    div = np.where(hit, dv.to_numpy()[j], 0.0)
    c64 = close.astype(np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        divadj = np.where(cu > 0, div * c64 / cu, 0.0)
    n = len(code)
    newg = np.r_[True, code[1:] != code[:-1]]
    start_i = np.maximum.accumulate(np.where(newg, np.arange(n), 0))
    pos = (np.arange(n) - start_i).astype(np.int32)
    cprev = np.r_[np.nan, c64[:-1]]; cprev[newg] = np.nan
    with np.errstate(divide="ignore", invalid="ignore"):
        ret = (c64 + divadj) / cprev - 1
    ret[~np.isfinite(ret)] = np.nan
    ret = np.clip(ret, -0.999, None).astype(np.float32)
    del c64, cprev, divadj, div
    dvol = cu.astype(np.float64) * vol.astype(np.float64)
    cs = np.cumsum(np.nan_to_num(dvol))
    adv = np.full(n, np.nan)
    i = np.where(pos >= 19)[0]
    adv[i] = (cs[i] - np.where(i - 20 >= 0, cs[np.maximum(i - 20, 0)], 0.0)) / 20
    # i-20 may cross into the previous code only when pos < 20 for row i-19; pos>=19 means rows i-19..i are this code; cs[i-20] is
    # the row before the window, which is correct regardless of its code.
    return dict(names=names, code=code, sidx=sidx, ret=ret, cu=cu, adv=adv.astype(np.float32), pos=pos, sessions=sessions)


def _rf(sessions):
    t = pd.read_csv(ROOT / "data/research/regime_x/DTB3.csv", parse_dates=["observation_date"])
    s = pd.to_numeric(t.DTB3, errors="coerce"); s.index = t.observation_date
    s = s.ffill().reindex(pd.DatetimeIndex(sessions), method="ffill").to_numpy() / 100.0
    gap = np.r_[1, np.diff(sessions).astype("timedelta64[D]").astype(int)]
    return s * gap / 360.0  # daily accrual for the session (calendar days since previous session)


def build_panel(source, f_from, f_to):
    sep, sfp, tick, act, start = _src(source)
    spy = _read(sfp, ["SPY"], start, act)
    sessions = spy["sessions"]
    m_all = spy["ret"].astype(np.float64)
    m_all[~np.isfinite(m_all)] = 0.0
    rf = _rf(sessions)
    t = pd.read_parquet(tick, columns=["table", "ticker", "category", "sector"])
    t = t[t.table == "SEP"].drop_duplicates("ticker")
    common = sorted(set(t.ticker[is_common(t.category.fillna("").astype(str))]))
    sector = t.set_index("ticker").sector.fillna("").to_dict()
    d = _read(sep, common, start, act, sessions)
    S = len(sessions)
    mon = pd.DatetimeIndex(sessions).to_period("M")
    me_sidx = np.where(np.r_[mon[1:] != mon[:-1], False])[0]
    me_dates = pd.DatetimeIndex(sessions[me_sidx])
    keep = (me_dates >= f_from) & (me_dates <= f_to) & (me_sidx >= L)
    me_sidx = me_sidx[keep]
    is_me = np.zeros(S, bool); is_me[me_sidx] = True
    rows = is_me[d["sidx"]] & (d["cu"] >= PRICE_MIN) & (d["adv"] >= ADV_MIN) & (d["pos"] >= 19)
    E = np.unique(d["code"][rows])
    col = np.full(len(d["names"]), -1, np.int32); col[E] = np.arange(len(E))
    nE = len(E)
    R = np.full((S, nE), np.nan, np.float32)
    inE = col[d["code"]] >= 0
    R[d["sidx"][inE], col[d["code"][inE]]] = d["ret"][inE]
    me_pos = {s: k for k, s in enumerate(me_sidx)}
    EL = np.zeros((len(me_sidx), nE), bool)
    ri = np.where(rows)[0]
    EL[[me_pos[s] for s in d["sidx"][ri]], col[d["code"][ri]]] = True
    tick_of = d["names"][E]
    del d, rows, ri, inE
    say(f"[{source}] sessions {pd.Timestamp(sessions[0]).date()}..{pd.Timestamp(sessions[-1]).date()}, ever-eligible names {nE}, "
        f"formations {len(me_sidx)} ({me_dates[keep][0].date()}..{me_dates[keep][-1].date()}), R {R.nbytes / 1e6:.0f}MB")
    out, mrow = [], []
    rng = np.random.default_rng(0)
    for k, s in enumerate(me_sidx):
        W = R[s - L + 1:s + 1]
        cand = EL[k] & np.isfinite(W).all(0)
        if cand.sum() < 50:
            continue
        X = W[:, cand].astype(np.float64)
        m = m_all[s - L + 1:s + 1]
        mm = m - m.mean(); vm = mm @ mm / L
        Xc = X - X.mean(0)
        beta = (mm @ Xc) / L / vm
        dn = m < m.mean(); up = ~dn
        def cbeta(mask):
            md = m[mask] - m[mask].mean(); Xd = X[mask] - X[mask].mean(0)
            return (md @ Xd) / (md @ md)
        bd, bu = cbeta(dn), cbeta(up)
        e = Xc - np.outer(mm, beta)
        cosk = ((mm ** 2) @ e / L) / (np.sqrt((e ** 2).mean(0)) * vm)
        ql_m, qh_m = np.quantile(m, 0.10), np.quantile(m, 0.90)
        ql, qh = np.quantile(X, 0.10, axis=0), np.quantile(X, 0.90, axis=0)
        lo_m, hi_m = m <= ql_m, m >= qh_m
        ltd = (X[lo_m] <= ql).mean(0) / 0.10
        utd = (X[hi_m] >= qh).mean(0) / 0.10
        vol = X.std(0, ddof=1) * math.sqrt(252)
        # holding month
        e_s = me_sidx[k + 1] if k + 1 < len(me_sidx) else min(S - 1, s + 23)
        if k + 1 == len(me_sidx):  # last formation: run to the next month-end in the data, if any
            nxt = np.where(np.r_[mon[1:] != mon[:-1], False])[0]
            nxt = nxt[nxt > s]
            e_s = nxt[0] if len(nxt) else S - 1
        H = R[s + 1:e_s + 1][:, cand].astype(np.float64)
        h = np.prod(1 + np.nan_to_num(H), axis=0) - 1
        hspy = np.prod(1 + m_all[s + 1:e_s + 1]) - 1
        hrf = np.prod(1 + rf[s + 1:e_s + 1]) - 1
        # forward 12 months (gate M)
        fl = np.full(cand.sum(), np.nan); fc = np.full(cand.sum(), np.nan)
        if s + L < S:
            F = R[s + 1:s + L + 1][:, cand].astype(np.float64)
            fm = m_all[s + 1:s + L + 1]
            full = np.isfinite(F).all(0)
            if full.any():
                Ff = F[:, full]
                fql = np.quantile(Ff, 0.10, axis=0)
                fl[full] = (Ff[fm <= np.quantile(fm, 0.10)] <= fql).mean(0) / 0.10
            cr = fm <= np.quantile(fm, 0.05)
            Fc = F[cr]
            cnt = np.isfinite(Fc).sum(0)
            with np.errstate(invalid="ignore"):
                fc = np.where(cnt >= 5, np.nanmean(np.where(np.isfinite(Fc), Fc, np.nan), axis=0), np.nan)
        cc = np.where(cand)[0]
        out.append(pd.DataFrame(dict(k=k, col=cc.astype(np.int32), beta=beta, bd=bd, bu=bu, cosk=cosk, ltd=ltd, utd=utd, vol=vol,
                                     h=h, fltd=fl, fcrash=fc, u=rng.random(len(cc)))))
        mrow.append(dict(k=k, me=pd.Timestamp(sessions[s]), hold_end=pd.Timestamp(sessions[e_s]), spy=hspy, rf=hrf,
                         fwd_end=pd.Timestamp(sessions[min(s + L, S - 1)]), fwd_ok=s + L < S, n=int(cand.sum())))
    P = pd.concat(out, ignore_index=True)
    for c in ("beta", "bd", "bu", "cosk", "ltd", "utd", "vol", "h", "fltd", "fcrash", "u"):
        P[c] = P[c].astype(np.float32)
    M = pd.DataFrame(mrow).set_index("k")
    P["ticker"] = pd.Categorical(tick_of[P.col.to_numpy()])
    P["sector"] = pd.Categorical([sector.get(x, "") for x in tick_of[P.col.to_numpy()]])
    del R, EL
    # daily SPY / rf for the windows (crisis drawdowns use monthly series; daily kept for reference)
    return P, M


# ---------------------------------------------------------------- portfolios
def assign(P):
    g = P.groupby("k")
    P["terc"] = np.minimum(np.ceil(g.beta.rank(pct=True, method="first") * 3), 3).astype(np.int8)
    P["lkey"] = P.ltd + P.u * 1e-4  # LTD is discrete (steps of ~0.38); seeded random tie-break
    P["lq"] = P.groupby(["k", "terc"]).lkey.rank(pct=True, method="first")
    P["res"] = P.lq <= 0.2
    P["rel"] = P.bd - P.beta
    rq = P.groupby("k").rel.rank(pct=True, method="first")
    P["acx"] = np.where(rq <= 0.2, 1, np.where(rq > 0.8, 5, 0)).astype(np.int8)
    return P


def weights_turnover(P, M, wcol):
    """wcol: per-row weight (0 = not held). Returns monthly gross return and drifted turnover."""
    gross, turn = [], []
    prev = None
    for k, g in P[P[wcol] != 0].groupby("k", sort=True):
        w = pd.Series(g[wcol].to_numpy(float), index=g.col.to_numpy())
        hh = pd.Series(g.h.to_numpy(float), index=g.col.to_numpy())
        r = float((w * hh).sum())
        if prev is None:
            tv = float(w.abs().sum())
        else:
            pw, ph, pr = prev
            drift = pw * (1 + ph) / (1 + pr)
            tv = float(w.sub(drift, fill_value=0.0).abs().sum())
        gross.append((k, r)); turn.append((k, tv))
        prev = (w, hh, r)
    return pd.Series(dict(gross)), pd.Series(dict(turn))


def series(P, M):
    P = assign(P)
    n_t = P[P.res].groupby(["k", "terc"]).size().rename("nq")
    P = P.join(n_t, on=["k", "terc"])
    P["w_res"] = np.where(P.res, 1.0 / (3 * P.nq), 0.0)
    nT = P.groupby(["k", "terc"]).size().rename("nt")
    P = P.join(nT, on=["k", "terc"])
    P["w_bench"] = 1.0 / (3 * P.nt)
    nq5 = P[P.acx == 5].groupby("k").size(); nq1 = P[P.acx == 1].groupby("k").size()
    P["w_q5"] = np.where(P.acx == 5, 1.0 / P.k.map(nq5), 0.0)
    P["w_q1"] = np.where(P.acx == 1, 1.0 / P.k.map(nq1), 0.0)
    out = pd.DataFrame(index=M.index)
    for nm in ("res", "bench", "q5", "q1"):
        gr, tv = weights_turnover(P, M, f"w_{nm}")
        out[nm] = gr; out[f"t_{nm}"] = tv
    for t in (1, 2, 3):
        q = P[P.res & (P.terc == t)].groupby("k").h.mean(); b = P[P.terc == t].groupby("k").h.mean()
        out[f"res{t}"] = q; out[f"bench{t}"] = b
    out["me"] = M.me; out["hold_end"] = M.hold_end; out["spy"] = M.spy; out["rf"] = M.rf; out["n"] = M.n
    return P, out


# ---------------------------------------------------------------- stats
def nwt(x, lags=5):
    x = np.asarray(x, float); mu = x.mean(); d = x - mu; n = len(x)
    v = d @ d / n
    for l_ in range(1, lags + 1):
        v += 2 * (1 - l_ / (lags + 1)) * (d[l_:] @ d[:-l_]) / n
    return float(mu / math.sqrt(v / n))


def mdd(r):
    eq = np.cumprod(1 + np.asarray(r, float)); return float((eq / np.maximum.accumulate(eq) - 1).min())


def pooled_rc(P, xcol, ycol, within=None):
    d = P[["k", xcol, ycol] + ([within] if within else [])].dropna()
    keys = ["k"] + ([within] if within else [])
    rx = d.groupby(keys)[xcol].rank(pct=True); ry = d.groupby(keys)[ycol].rank(pct=True)
    per = d.assign(rx=rx, ry=ry).groupby("k").apply(lambda g: g.rx.corr(g.ry), include_groups=False)
    return float(np.corrcoef(rx, ry)[0, 1]), float(per.mean()), int(len(d)), int(d.k.nunique())


def analyse(P, S, M, w0, w1, judge: bool, tag: str):
    ks = M.index[(M.hold_end >= pd.Timestamp(w0)) & (M.hold_end <= pd.Timestamp(w1) + pd.Timedelta(days=10))
                 & (M.me < pd.Timestamp(w1))]
    D = S.loc[ks].copy()
    say(f"\n=== {tag}: holding months {D.hold_end.iloc[0].date()}..{D.hold_end.iloc[-1].date()} ({len(D)}), "
        f"mean eligible names {D.n.mean():.0f}, resilient names/month {(P[P.res & P.k.isin(ks)].groupby('k').size()).mean():.0f}")
    # gate M
    kM = M.index[M.index.isin(ks) & M.fwd_ok & (M.fwd_end <= pd.Timestamp(w1) + pd.Timedelta(days=10))]
    PM = P[P.k.isin(kM)]
    rcL, rcLm, nL, mL = pooled_rc(PM, "ltd", "fltd")
    rcC, rcCm, nC, mC = pooled_rc(PM, "ltd", "fcrash")
    rcLb, _, _, _ = pooled_rc(PM, "ltd", "fltd", within="terc")
    rcCb, _, _, _ = pooled_rc(PM, "ltd", "fcrash", within="terc")
    rcBC, _, _, _ = pooled_rc(PM, "beta", "fcrash")
    say(f"  gate M ({len(kM)} formation months with 12m forward inside window): rankcorr(LTD, fwd-12m LTD) pooled {rcL:+.3f} "
        f"(mean monthly {rcLm:+.3f}, n {nL}); rankcorr(LTD, fwd crash-day ret) pooled {rcC:+.3f} (monthly {rcCm:+.3f}, n {nC})")
    say(f"    within beta tercile: LTD->fwdLTD {rcLb:+.3f}, LTD->crash ret {rcCb:+.3f} | reference beta->crash ret {rcBC:+.3f}")
    gM = rcL >= 0.20 and -rcC >= 0.20
    # resilient arm
    ex = lambda r: r - D.rf  # noqa: E731
    net = D.res - COST * D.t_res; netx = D.res - COST_X * D.t_res
    a, t, b = ols_alpha(ex(net).to_numpy(), ex(D.spy).to_numpy())
    ax = ols_alpha(ex(netx).to_numpy(), ex(D.spy).to_numpy())[0]
    ag, _, _ = ols_alpha(ex(D.res).to_numpy(), ex(D.spy).to_numpy())
    ab, tb, bb = ols_alpha(ex(D.bench).to_numpy(), ex(D.spy).to_numpy())
    h1 = (D.hold_end <= pd.Timestamp(H1_END)).to_numpy() if judge else (D.hold_end <= D.hold_end.iloc[len(D) // 2]).to_numpy()
    a1 = ols_alpha(ex(net)[h1].to_numpy(), ex(D.spy)[h1].to_numpy())[0]
    a2 = ols_alpha(ex(net)[~h1].to_numpy(), ex(D.spy)[~h1].to_numpy())[0]
    xs = (net - D.bench).to_numpy()
    srt = np.sort(xs)
    wd = D.spy <= D.spy.quantile(0.10)
    wdx = xs[wd.to_numpy()].mean()
    hedged = (ex(net) - b * ex(D.spy)).to_numpy()
    ds = dsr(hedged, N_TRIALS)
    say(f"  RESILIENT (lowest-LTD quintile within beta terciles): net {net.mean() * 100:+.2f}%/mo, turnover {D.t_res.mean():.2f}/mo, "
        f"beta {b:.2f} (bench beta {bb:.2f})")
    say(f"    CAPM alpha net {a * 1200:+.2f}%/yr t {t:+.2f} | gross {ag * 1200:+.2f} | 2x cost {ax * 1200:+.2f} | halves {a1 * 1200:+.2f} / {a2 * 1200:+.2f}"
        f" | bench (tercile EW) alpha {ab * 1200:+.2f} t {tb:+.2f}")
    say(f"    excess vs tercile bench: mean {xs.mean() * 100:+.3f}%/mo t {nwt(xs):+.2f} median {np.median(xs) * 100:+.3f} hit {(xs > 0).mean():.2f}"
        f" ex-top5 {srt[:-5].mean() * 100:+.3f} | SPY worst-decile months ({int(wd.sum())}): excess {wdx * 100:+.2f}%/mo, arm {net[wd].mean() * 100:+.2f}"
        f" bench {D.bench[wd].mean() * 100:+.2f} SPY {D.spy[wd].mean() * 100:+.2f}")
    for tt in (1, 2, 3):
        e_t = (D[f"res{tt}"] - D[f"bench{tt}"]).to_numpy()
        at, ttt, bt = ols_alpha(ex(D[f"res{tt}"]).to_numpy(), ex(D.spy).to_numpy())
        say(f"    beta tercile {tt}: gross alpha {at * 1200:+.2f}%/yr t {ttt:+.2f} beta {bt:.2f} | excess vs tercile {e_t.mean() * 100:+.3f}%/mo t {nwt(e_t):+.2f}")
    # placebo
    rng = np.random.default_rng(1)
    PP = P[P.k.isin(ks)]
    pl = np.zeros((N_PLACEBO, len(ks)))
    kpos = {k: i for i, k in enumerate(ks)}
    for (k, tt), g in PP.groupby(["k", "terc"], sort=False):
        hh = g.h.to_numpy(float); nq = int(g.res.sum())
        idx = np.argpartition(rng.random((N_PLACEBO, len(hh))), nq - 1, axis=1)[:, :nq]
        pl[:, kpos[k]] += hh[idx].mean(1) / 3
    Xd = np.column_stack([np.ones(len(ks)), ex(D.spy).to_numpy()])
    coef = np.linalg.lstsq(Xd, (pl - D.rf.to_numpy()[None, :]).T, rcond=None)[0]
    pa = coef[0]
    pct = (pa < ag).mean() * 100
    say(f"    placebo random-within-tercile (200): gross alpha mean {pa.mean() * 1200:+.2f}%/yr, 95th {np.percentile(pa, 95) * 1200:+.2f}; real gross {ag * 1200:+.2f} at pct {pct:.1f}")
    say(f"    DSR (N {N_TRIALS}, monthly beta-hedged net) {ds:.3f}")
    # ACX
    acx = (D.q5 - D.q1) - COST * (D.t_q5 + D.t_q1); acxx = (D.q5 - D.q1) - COST_X * (D.t_q5 + D.t_q1)
    ta = nwt(acx.to_numpy())
    c1, c2 = acx[h1].mean(), acx[~h1].mean()
    aa, at_, ab_ = ols_alpha(acx.to_numpy(), ex(D.spy).to_numpy())
    dsa = dsr(acx.to_numpy(), N_TRIALS)
    say(f"  ACX Q5-Q1 on (beta_down - beta): net {acx.mean() * 100:+.3f}%/mo t {ta:+.2f} | gross {(D.q5 - D.q1).mean() * 100:+.3f} | 2x cost {acxx.mean() * 100:+.3f}"
        f" | halves {c1 * 100:+.3f} / {c2 * 100:+.3f} | median {acx.median() * 100:+.3f} | CAPM alpha {aa * 1200:+.2f}%/yr t {at_:+.2f} beta {ab_:+.2f}"
        f" | Q5 {D.q5.mean() * 100:+.2f} Q1 {D.q1.mean() * 100:+.2f} | turnover {D.t_q5.mean():.2f}+{D.t_q1.mean():.2f} | DSR {dsa:.3f}")
    # crisis windows and sector mix
    def win(a0, a1_):
        mk = (D.hold_end >= pd.Timestamp(a0)) & (D.hold_end <= pd.Timestamp(a1_))
        if mk.sum() == 0:
            return None
        return tuple(f(D.loc[mk, c]) for c in ("res", "bench", "spy") for f in (lambda r: np.prod(1 + r) - 1, mdd))
    for nm, a0, a1_ in (("2000-02", "2000-01-01", "2002-12-31"), ("2008", "2008-01-01", "2008-12-31"), ("2022", "2022-01-01", "2022-12-31")):
        w = win(a0, a1_)
        if w:
            say(f"    {nm} (monthly): arm cum {w[0]:+.1%} maxDD {w[1]:.1%} | tercile bench cum {w[2]:+.1%} maxDD {w[3]:.1%} | SPY cum {w[4]:+.1%} maxDD {w[5]:.1%}")
    sm = PP[PP.res].groupby("sector", observed=True).size() / PP.res.sum()
    sb = PP.groupby("sector", observed=True).size() / len(PP)
    mix = pd.DataFrame({"arm": sm, "univ": sb}).fillna(0).sort_values("arm", ascending=False)
    say("    sector mix (name-months, arm vs eligible): " + ", ".join(f"{s or 'n/a'} {r.arm:.0%}/{r.univ:.0%}" for s, r in mix.iterrows()))
    say(f"    arm features vs eligible (means): LTD {PP[PP.res].ltd.mean():.2f}/{PP.ltd.mean():.2f}, beta {PP[PP.res].beta.mean():.2f}/{PP.beta.mean():.2f},"
        f" vol {PP[PP.res].vol.mean():.0%}/{PP.vol.mean():.0%}, coskew {PP[PP.res].cosk.mean():+.3f}/{PP.cosk.mean():+.3f}, UTD {PP[PP.res].utd.mean():.2f}/{PP.utd.mean():.2f}")
    if judge:
        gR = [("M", gM), ("alpha>=6%&t>=2", a * 12 >= 0.06 and t >= 2), ("halves", a1 > 0 and a2 > 0), ("median-excess", np.median(xs) > 0),
              ("worst-decile", wdx > 0), ("placebo95", pct >= 95), ("2xcost", ax > 0)]
        gA = [("Q5-Q1>=0.5%&t>=2", acx.mean() >= 0.005 and ta >= 2), ("halves", c1 > 0 and c2 > 0), ("2xcost", acxx.mean() > 0)]
        say("  GATES resilient: " + " | ".join(f"{n} {'PASS' if ok else 'FAIL'}" for n, ok in gR) + f" -> {'PASS' if all(o for _, o in gR) else 'KILL'}")
        say("  GATES ACX: " + " | ".join(f"{n} {'PASS' if ok else 'FAIL'}" for n, ok in gA) + f" -> {'PASS' if all(o for _, o in gA) else 'KILL'}")
    return D


def selloff_2026(P, S, M):
    say("\n=== 2026-10/11 selloff pattern (descriptive only; stock bars on disk end 2026-10-05)")
    last = M.index[-1]
    g = P[P.k == last]
    say(f"  last formation {M.me.loc[last].date()} (holding to {M.hold_end.loc[last].date()}): {int(g.res.sum())} resilient of {len(g)} eligible")
    tech = g.sector == "Technology"
    say(f"    arm: Technology {tech[g.res].mean():.0%} vs eligible {tech.mean():.0%}; beta {g[g.res].beta.mean():.2f} vs {g.beta.mean():.2f};"
        f" vol {g[g.res].vol.mean():.0%} vs {g.vol.mean():.0%}; partial-month return arm {g[g.res].h.mean():+.2%} bench {g.h.mean():+.2%} SPY {M.spy.loc[last]:+.2%}")
    # monthly relation of the arm's excess to the low-vol-minus-high-vol and tech-minus-rest spreads, 2021-26 panel
    vt = np.minimum(np.ceil(P.groupby("k").vol.rank(pct=True, method="first") * 3), 3)
    lv = P[vt == 1].groupby("k").h.mean() - P[vt == 3].groupby("k").h.mean()
    tk = P[P.sector == "Technology"].groupby("k").h.mean() - P[P.sector != "Technology"].groupby("k").h.mean()
    xs = (S.res - COST * S.t_res - S.bench)
    say(f"    2021-26 monthly corr of arm excess (vs tercile bench) with low-vol-minus-high-vol tercile {xs.corr(lv):+.2f}, with tech-minus-rest {xs.corr(tk):+.2f}")
    pat = (lv > 0) & (tk < 0) & (S.spy < 0)
    say(f"    months matching the pattern (SPY down, low-vol beat high-vol, tech lagged): {int(pat.sum())}; arm excess in them {xs[pat].mean() * 100:+.2f}%/mo"
        f" (hit {(xs[pat] > 0).mean():.2f}); other months {xs[~pat].mean() * 100:+.2f}%/mo")
    try:
        sp = pd.read_csv(ROOT / "data/research/hmm_rebal/px_SPY.csv", parse_dates=["date"]).set_index("date").adjclose
        a0 = sp[:"2026-09-30"].iloc[-1]
        say(f"    SPY from 2026-09-30: to 2026-10-05 {sp[:'2026-10-05'].iloc[-1] / a0 - 1:+.1%}, to {sp.index[-1].date()} {sp.iloc[-1] / a0 - 1:+.1%}"
            f" (px_SPY.csv); no stock-level bars after 2026-10-05 on disk, so the arm's Oct-Nov return is not measurable")
    except Exception as e:  # noqa: BLE001
        say(f"    SPY px read failed: {e}")


def main():
    say("TAIL (N 1244): month-end beta / downside beta / HS coskew / empirical LTD-UTD vs SPY (trailing 252), $5+ ADV20 $10M+ SEP common, "
        "delisted kept; cost 5bp/side, shock 10bp; alpha on DTB3 excess; DSR N 1245")
    P, M = build_panel("cache", pd.Timestamp("1998-12-01"), pd.Timestamp("2020-12-31"))
    P, S = series(P, M)
    say("\n##### PASS 1: JUDGE 1999-2010 (halves 1999-2004 / 2005-10)")
    analyse(P, S, M, J0, J1, True, "JUDGE 1999-2010")
    say("\n##### PASS 2: REPORT, never judged")
    analyse(P, S, M, "2011-01-01", "2020-12-31", False, "REPORT 2011-20 (NX cache)")
    del P, S, M
    P, M = build_panel("full", pd.Timestamp("2020-12-01"), pd.Timestamp("2026-12-31"))
    P, S = series(P, M)
    analyse(P, S, M, "2021-01-01", "2026-12-31", False, "REPORT 2021-26 (~/data/sharadar full; last month partial)")
    selloff_2026(P, S, M)
    OUT.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
