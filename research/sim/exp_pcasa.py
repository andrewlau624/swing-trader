"""PCA-SA (N 1242, pre-registered in round1_prose.md "Amendment - DEEP round 1", 2026-11-21).

Avellaneda-Lee (2010) residual mean reversion with a Marchenko-Pastur factor count.

    OMP_NUM_THREADS=3 PYTHONPATH=. python3 -m research.sim.exp_pcasa

Pass 1 = JUDGE 1998-2010 (gates, placebo, DSR). Pass 2 = REPORT 2011-20 (never judged).
2021-26 is not in the NX cache (SEP ends 2021-01-15): not run.

Timing: s is computed from closes through T; the position is entered at the close of T+1 and earns
close T+1 -> close T+2. A held name with no bar on the earning session earns 0 (repo convention: SEP has
no delisting return).
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS",
           "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "3")

import gc
import math
import pathlib
import sys

import numpy as np
import pandas as pd
import pyarrow.compute as pc
import pyarrow.parquet as pq

from .exp_rl_universe import NXD, PRICE_MIN, ADV_MIN
from .exp_rl import dsr
from .nx import is_common
from .weekwin_short import tstat

OUT = pathlib.Path(__file__).resolve().parent / "exp_pcasa_out.txt"
N_PROGRAM = 1245
NU, TW, RW, EIG_EVERY, KMAX = 1000, 252, 60, 5, 15
S_BO, S_SO, S_BC, S_SC = 1.25, 1.25, 0.75, 0.50     # open long s<-1.25, open short s>1.25, close short s<0.75, close long s>-0.50
KAPPA_MIN = 252 / 30
COST, COST_X, BORROW = 5e-4, 10e-4, 1e-2 / 252
N_PLACEBO = 50

L: list[str] = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    L.append(s)
    OUT.write_text("\n".join(L) + "\n")


# ------------------------------------------------------------------ data (dense, float32)
NX_SRC = dict(sep=NXD / "cache_SEP.parquet", sfp=NXD / "cache_SFP.parquet", actions=NXD / "cache_ACTIONS.parquet",
              tickers=NXD / "cache_TICKERS.parquet")


def _dfilt(path, d):
    """Filter value matching the file's date column type (timestamp in the NX caches, date32 in ~/data/sharadar)."""
    import pyarrow as pa
    typ = pq.read_schema(path).field("date").type
    return pd.Timestamp(d).date() if pa.types.is_date(typ) else pd.Timestamp(d)


def load_panel(d0: str, d1: str, src: dict | None = None, want_vol: bool = False, prefilter: bool = False):
    """Dense session x name panels of total return (div-adjusted, split-adjusted close) and ADV20 ($, unadjusted).
    src: file paths (default the NX caches). want_vol: also return dense share volume and its 20d mean.
    prefilter: drop names whose daily $ volume never reaches ADV_MIN in the window (result-neutral: they can never
    enter the top-ADV20 universe, and only universe names enter factors, regressions or books)."""
    src = src or NX_SRC
    t = pd.read_parquet(src["tickers"], columns=["table", "ticker", "category"])
    t = t[t.table == "SEP"]
    common = sorted(set(t.ticker[is_common(t.category.fillna("").astype(str))]))
    tb = pq.read_table(src["sep"], columns=["ticker", "date", "close", "volume", "closeunadj"],
                       filters=[("date", ">=", _dfilt(src["sep"], d0)), ("date", "<=", _dfilt(src["sep"], d1)),
                                ("ticker", "in", common)])
    if prefilter:
        dvol = pc.multiply(tb["closeunadj"], tb["volume"])
        mx = pa_table_groupmax(tb["ticker"], dvol)
        tb = tb.filter(pc.is_in(tb["ticker"], value_set=mx))
    tick = pc.dictionary_encode(tb["ticker"]).combine_chunks()
    names = np.asarray(tick.dictionary.to_pylist(), dtype=object)
    code = tick.indices.to_numpy()
    dt = tb["date"].to_numpy().astype("datetime64[ns]")
    sessions = np.unique(dt)
    si = np.searchsorted(sessions, dt)
    D, N = len(sessions), len(names)
    key = si.astype(np.int64) * N + code
    dup = len(key) - len(np.unique(key))
    close = np.full((D, N), np.nan); cu = np.full((D, N), np.nan); dv = np.full((D, N), np.nan, np.float32)
    c_ = tb["close"].to_numpy(); u_ = tb["closeunadj"].to_numpy(); v_ = tb["volume"].to_numpy()
    close[si, code] = c_; cu[si, code] = u_; dv[si, code] = (u_ * v_).astype(np.float32)
    if want_vol:
        vol = np.full((D, N), np.nan, np.float32); vol[si, code] = v_.astype(np.float32)
    del tb, c_, u_, v_, dt, si, code, tick, key
    # dividends (ex-date), converted to the split-adjusted close basis like exp_rl_universe._features
    a = pd.read_parquet(src["actions"], columns=["date", "action", "ticker", "value"])
    a = a[(a.action == "dividend")]
    a["date"] = pd.to_datetime(a["date"])
    nm = pd.Series(np.arange(N), index=names)
    a = a[a.ticker.isin(nm.index) & a.date.isin(pd.DatetimeIndex(sessions))]
    div = np.zeros((D, N))
    np.add.at(div, (np.searchsorted(sessions, a.date.to_numpy("datetime64[ns]")), nm[a.ticker].to_numpy()),
              a.value.to_numpy(float))
    with np.errstate(divide="ignore", invalid="ignore"):
        divadj = np.where(cu > 0, div * close / cu, 0.0)
        R = (close[1:] + divadj[1:]) / close[:-1] - 1
    R = np.vstack([np.full((1, N), np.nan), R])
    R[~np.isfinite(R)] = np.nan
    R = R.astype(np.float32)
    del close, div, divadj
    cu = cu.astype(np.float32)
    adv = pd.DataFrame(dv).rolling(20, min_periods=20).mean().to_numpy(np.float32)
    del dv
    # SPY total return on the same sessions
    sb = pq.read_table(src["sfp"], columns=["ticker", "date", "close", "closeunadj"],
                       filters=[("ticker", "=", "SPY"), ("date", ">=", _dfilt(src["sfp"], d0)),
                                ("date", "<=", _dfilt(src["sfp"], d1))]).to_pandas()
    sb["date"] = pd.to_datetime(sb["date"])
    a0 = pd.read_parquet(src["actions"], columns=["date", "action", "ticker", "value"])
    sd = a0[(a0.action == "dividend") & (a0.ticker == "SPY")].copy(); sd["date"] = pd.to_datetime(sd["date"])
    sb = sb.merge(sd.groupby("date")["value"].sum().rename("div").reset_index(), on="date", how="left").fillna({"div": 0})
    sb = sb.set_index("date").reindex(pd.DatetimeIndex(sessions))
    spy = ((sb.close + sb["div"] * sb.close / sb.closeunadj) / sb.close.shift(1) - 1).to_numpy(np.float32)
    lastbar = np.where(np.isfinite(cu), np.arange(D)[:, None], -1).max(0)
    info = dict(dup=dup, N=N, D=D, spy_nan=int(np.isnan(spy[1:]).sum()),
                delisted=int((lastbar < D - 5).sum()), names=names)
    if want_vol:
        info["vol"] = vol
        info["vol20"] = pd.DataFrame(vol).rolling(20, min_periods=20).mean().to_numpy(np.float32)
    return pd.DatetimeIndex(sessions), R, cu, adv, spy, info


def pa_table_groupmax(tick, val):
    """Tickers whose max daily $ volume reaches ADV_MIN."""
    import pyarrow as pa
    g = pa.table({"t": tick, "v": val}).group_by("t").aggregate([("v", "max")])
    return g.filter(pc.greater_equal(g["v_max"], ADV_MIN))["t"]


# ------------------------------------------------------------------ signal
def ou_score(E, Y, sp, cand):
    """AL s-score from 60d residuals E (RW x n): X = cumsum(E), AR(1) fit, kappa filter, centred s; plus 60d SPY beta."""
    Xc = np.cumsum(E, 0)
    x0, x1 = Xc[:-1], Xc[1:]
    m0, m1 = x0.mean(0), x1.mean(0)
    vx = ((x0 - m0) ** 2).mean(0)
    b = ((x0 - m0) * (x1 - m1)).mean(0) / vx
    a = m1 - b * m0
    z = x1 - a - b * x0
    with np.errstate(invalid="ignore", divide="ignore"):
        kappa = -np.log(b) * 252
        m = a / (1 - b)
        seq = np.sqrt(z.var(0) / (1 - b ** 2))
        good = (b > 0) & (b < 1) & (kappa > KAPPA_MIN) & np.isfinite(seq) & (seq > 0)
        ms = m / seq
        s_raw = (Xc[-1] - m) / seq
    if good.sum() < 2:
        return None
    s = s_raw[good] + ms[good].mean()                   # AL centring: -(m/s - <m/s>) when X_last = 0
    spc = sp - sp.mean()                                # 60d beta vs SPY for the hedge (holdings-based book beta)
    beta = (spc @ (Y[:, good] - Y[:, good].mean(0))) / (spc @ spc)
    return cand[good], s.astype(np.float32), beta.astype(np.float32)


def build_signals(R, cu, adv, spy, vscale=None):
    """Per session t (signal date): (idx, s, beta60) for names with a valid s; plus diagnostics.
    vscale=(vol, vol20): also return AL volume-time s (residuals x vol20/vol before cumulation) as a second list."""
    D, N = R.shape
    out_v = [None] * D
    fin = np.isfinite(R).astype(np.int32)
    cs = np.vstack([np.zeros((1, N), np.int32), np.cumsum(fin, 0)])
    out = [None] * D
    nf_hist, nu_hist, nval_hist, x_end = [], [], [], 0.0
    Q = None; qidx = None; last_eig = -10**9; t_first = None
    for t in range(TW, D):
        full = (cs[t + 1] - cs[t + 1 - TW]) == TW
        el = full & (cu[t] >= PRICE_MIN) & (adv[t] >= ADV_MIN)
        cand = np.flatnonzero(el)
        if len(cand) < 50:
            continue
        if len(cand) > NU:
            cand = cand[np.argpartition(-adv[t, cand], NU - 1)[:NU]]
        cand = np.sort(cand)
        if t_first is None:
            t_first = t
        if (t - t_first) % EIG_EVERY == 0 or Q is None:
            W = R[t - TW + 1:t + 1, cand].astype(np.float64)
            mu = W.mean(0); sd = W.std(0, ddof=1)
            ok = sd > 0
            cand_e = cand[ok]; Z = (W[:, ok] - mu[ok]) / sd[ok]
            n_, T_ = Z.shape[1], Z.shape[0]
            _, sv, vt = np.linalg.svd(Z / math.sqrt(T_ - 1), full_matrices=False)
            lam = sv ** 2                                   # eigenvalues of the correlation matrix (trace = n)
            edge = (1 + math.sqrt(n_ / T_)) ** 2
            k = int(min(KMAX, (lam > edge).sum()))
            k = max(k, 1)                                   # never observed 0 (market mode); guard only
            V = vt[:k].T                                    # n x k eigenvectors
            Q = V / sd[ok][:, None]                         # eigenportfolio weights v_i / sigma_i
            qidx = cand_e
            last_eig = t
        nf_hist.append(Q.shape[1]); nu_hist.append(len(cand))
        Rq = np.nan_to_num(R[t - RW + 1:t + 1, qidx].astype(np.float64))
        F = Rq @ Q                                          # 60 x k factor returns at the current weights
        X = np.column_stack([np.ones(RW), F])
        Y = R[t - RW + 1:t + 1, cand].astype(np.float64)    # finite by construction (252 full)
        B = np.linalg.lstsq(X, Y, rcond=None)[0]
        E = Y - X @ B
        x_end = max(x_end, float(np.abs(E.sum(0)).max()))  # X_60 = 0 by the intercept
        sp = spy[t - RW + 1:t + 1].astype(np.float64)
        r0 = ou_score(E, Y, sp, cand)
        if r0 is None:
            continue
        out[t] = r0
        nval_hist.append(len(r0[0]))
        if vscale is not None:
            vol, vol20 = vscale
            with np.errstate(invalid="ignore", divide="ignore"):
                ratio = vol20[t - RW + 1:t + 1, cand].astype(np.float64) / vol[t - RW + 1:t + 1, cand]
            ratio[~np.isfinite(ratio) | (ratio <= 0)] = 1.0     # zero / missing volume: no rescale
            out_v[t] = ou_score(E * ratio, Y, sp, cand)
    diag = dict(nf=np.array(nf_hist), nu=np.array(nu_hist), nval=np.array(nval_hist), x_end=x_end, t_first=t_first)
    return (out, out_v, diag) if vscale is not None else (out, diag)


# ------------------------------------------------------------------ simulate
def simulate(sig, R, spy, rng=None, lag=2):
    """Returns per-earning-session arrays. Weights decided on t's signal earn R[t+lag] (lag 2 = trade at close T+1)."""
    D, N = R.shape
    pos = np.zeros(N, np.int8)
    wl_prev = np.zeros(N, np.float32); ws_prev = np.zeros(N, np.float32); h_prev = 0.0; hl_prev = 0.0
    rows = []
    for t in range(D - lag):
        g = sig[t]
        valid = np.zeros(N, bool); sv = np.full(N, np.nan, np.float32); bv = np.zeros(N, np.float32)
        if g is not None:
            idx, s, beta = g
            if rng is not None:
                s = rng.permutation(s)
            valid[idx] = True; sv[idx] = s; bv[idx] = beta
        elif not pos.any():
            continue
        with np.errstate(invalid="ignore"):
            pos[(pos == 1) & (~valid | (sv > -S_SC))] = 0
            pos[(pos == -1) & (~valid | (sv < S_BC))] = 0
            flat = (pos == 0) & valid
            pos[flat & (sv < -S_BO)] = 1
            pos[flat & (sv > S_SO)] = -1
        nl = int((pos == 1).sum()); ns = int((pos == -1).sum())
        wl = np.where(pos == 1, 1.0 / max(nl, 1), 0.0).astype(np.float32)
        ws = np.where(pos == -1, 1.0 / max(ns, 1), 0.0).astype(np.float32)
        bl = float(wl @ bv); bs = float(ws @ bv)
        h = -(bl - bs)                                       # SPY hedge for LS
        r = np.nan_to_num(R[t + lag])
        gl = float(wl @ r); gs = -float(ws @ r)
        tl = float(np.abs(wl - wl_prev).sum()); ts = float(np.abs(ws - ws_prev).sum()); th = abs(h - h_prev)
        rows.append((t + lag, nl, ns, gl, gs, bl, h, float(spy[t + lag]) if np.isfinite(spy[t + lag]) else 0.0, tl, ts, th))
        wl_prev, ws_prev, h_prev = wl, ws, h
    a = np.array(rows, float)
    c = ["ti", "nl", "ns", "gl", "gs", "bl", "h", "spy", "tl", "ts", "th"]
    return pd.DataFrame(a, columns=c)


def arms(d, cost):
    ls = d.gl + d.gs + d.h * d.spy - cost * (d.tl + d.ts + d.th) - BORROW * (d.ns > 0)
    lo = d.gl - d.bl * d.spy - cost * d.tl
    return ls, lo


def sharpe(x):
    x = np.asarray(x, float)
    return float(x.mean() / x.std(ddof=1) * math.sqrt(252)) if x.std() > 0 else 0.0


def stats(x, dates, h_split):
    x = pd.Series(np.asarray(x, float), index=dates)
    srt = np.sort(x.to_numpy())
    mon = x.groupby(x.index.to_period("M")).sum()
    eq = np.cumprod(1 + x.to_numpy()); dd = (eq / np.maximum.accumulate(eq) - 1).min()
    return dict(mean=x.mean(), ann=x.mean() * 252, sh=sharpe(x), t=tstat(x.to_numpy()),
                h1=x[x.index <= h_split].mean(), h2=x[x.index > h_split].mean(),
                x5=srt[:-5].mean(), med_m=mon.median(), hit_m=(mon > 0).mean(), hit=(x > 0).mean(),
                dd=dd, dsr=dsr(x.to_numpy(), N_PROGRAM))


def fmt(tag, s, sx):
    return (f"  {tag}: net {s['mean'] * 1e4:+.2f}bp/day ({s['ann']:+.1%}/yr) Sharpe {s['sh']:+.2f} t {s['t']:+.2f} | "
            f"halves {s['h1'] * 1e4:+.2f} / {s['h2'] * 1e4:+.2f}bp | 2x cost {sx['mean'] * 1e4:+.2f}bp ({sx['ann']:+.1%}/yr, Sh {sx['sh']:+.2f}) | "
            f"ex-top5 {s['x5'] * 1e4:+.2f}bp | median month {s['med_m'] * 100:+.2f}% (hit {s['hit_m']:.2f}) | day hit {s['hit']:.2f} | "
            f"maxDD {s['dd']:.0%} | DSR(N {N_PROGRAM}) {s['dsr']:.3f}")


def run_pass(tag, d0, d1, w0, w1, h_split, judge):
    say(f"\n=== {tag}: load {d0}..{d1}, evaluate {w0}..{w1} (halves split {h_split})")
    sessions, R, cu, adv, spy, info = load_panel(d0, d1)
    big = int((np.abs(R) > 0.5).sum())
    say(f"  panel: {info['D']} sessions x {info['N']} common names (SEP, delisted kept: {info['delisted']} names end >5 sessions before the panel end); "
        f"duplicate (ticker,date) rows {info['dup']}; SPY missing returns {info['spy_nan']}; |daily ret|>50% cells {big}")
    sig, dg = build_signals(R, cu, adv, spy)
    del cu, adv; gc.collect()
    say(f"  signal: first signal {sessions[dg['t_first']].date()}; universe mean {dg['nu'].mean():.0f} (min {dg['nu'].min()}); "
        f"MP factors kept mean {dg['nf'].mean():.2f} (min {dg['nf'].min()}, max {dg['nf'].max()}, at cap 15 {np.mean(dg['nf'] == KMAX):.0%}); "
        f"names passing 0<b<1 & kappa>252/30 mean {dg['nval'].mean():.0f}; max |X_60| {dg['x_end']:.1e} (should be ~0)")
    d = simulate(sig, R, spy)
    d["date"] = sessions[d.ti.astype(int)]
    win = (d.date >= w0) & (d.date <= w1)
    d = d[win].reset_index(drop=True)
    ls, lo = arms(d, COST); lsx, lox = arms(d, COST_X)
    s_ls, s_lsx = stats(ls, d.date, h_split), stats(lsx, d.date, h_split)
    s_lo, s_lox = stats(lo, d.date, h_split), stats(lox, d.date, h_split)
    say(f"  book: {len(d)} earning days ({d.date.iloc[0].date()}..{d.date.iloc[-1].date()}); positions/day long {d.nl.mean():.1f} short {d.ns.mean():.1f} "
        f"(days with 0 longs {np.mean(d.nl == 0):.1%}, 0 shorts {np.mean(d.ns == 0):.1%}); turnover/day (sum|dw|, each side 1x) long {d.tl.mean():.2f} "
        f"short {d.ts.mean():.2f} hedge {d.th.mean():.3f}; mean hedge {d.h.mean():+.2f}x SPY; long-book beta {d.bl.mean():.2f}")
    say(f"  gross LS {(d.gl + d.gs + d.h * d.spy).mean() * 1e4:+.2f}bp/day (long {d.gl.mean() * 1e4:+.2f}, short {d.gs.mean() * 1e4:+.2f}); "
        f"gross LO excess {(d.gl - d.bl * d.spy).mean() * 1e4:+.2f}bp/day; cost drag at 5bp LS {COST * (d.tl + d.ts + d.th).mean() * 1e4:.2f}bp/day")
    # untradable diagnostic: same signal earning close T -> T+1 (would need to trade at the close T that made it)
    d0g = simulate(sig, R, spy, lag=1); d0g["date"] = sessions[d0g.ti.astype(int)]
    d0g = d0g[(d0g.date >= w0) & (d0g.date <= w1)]
    say(f"  diagnostic (UNTRADABLE, trade at close T): gross LS {(d0g.gl + d0g.gs + d0g.h * d0g.spy).mean() * 1e4:+.2f}bp/day, "
        f"LO excess {(d0g.gl - d0g.bl * d0g.spy).mean() * 1e4:+.2f}bp/day -> the one-day lag costs this much")
    # control (not a gate): the equal-weight universe (names with a valid s) at the same lag, vs SPY at its mean 60d beta
    ew = np.zeros(len(R)); ewb = np.zeros(len(R))
    for t, g in enumerate(sig):
        if g is not None and t + 2 < len(R):
            ew[t + 2] = np.nan_to_num(R[t + 2, g[0]]).mean(); ewb[t + 2] = g[2].mean()
    ti = d.ti.astype(int).to_numpy()
    ewx = ew[ti] - ewb[ti] * d.spy.to_numpy()
    lo_vs_ew = d.gl.to_numpy() - ew[ti]
    say(f"  control: universe-EW excess vs SPY at its beta {ewx.mean() * 1e4:+.2f}bp/day ({ewx.mean() * 252:+.1%}/yr, halves "
        f"{ewx[(d.date <= h_split).to_numpy()].mean() * 1e4:+.2f} / {ewx[(d.date > h_split).to_numpy()].mean() * 1e4:+.2f}); "
        f"LO gross minus universe EW {lo_vs_ew.mean() * 1e4:+.2f}bp/day ({lo_vs_ew.mean() * 252:+.1%}/yr, t {tstat(lo_vs_ew):+.2f}, halves "
        f"{lo_vs_ew[(d.date <= h_split).to_numpy()].mean() * 1e4:+.2f} / {lo_vs_ew[(d.date > h_split).to_numpy()].mean() * 1e4:+.2f}); "
        f"LO net of 5bp minus universe EW {(lo_vs_ew - COST * d.tl.to_numpy()).mean() * 252:+.1%}/yr")
    say(fmt("LS (hedged, 5bp/side, borrow 100bp/yr)", s_ls, s_lsx))
    say(fmt("LO excess vs SPY at long-book beta (5bp/side)", s_lo, s_lox))
    for y, g in d.assign(ls=ls, lo=lo).groupby(d.date.dt.year):
        L_ = f"    {y}: LS {g.ls.mean() * 1e4:+6.2f}bp/d Sh {sharpe(g.ls):+5.2f} | LO-x {g.lo.mean() * 1e4:+6.2f}bp/d | nL {g.nl.mean():5.1f} nS {g.ns.mean():5.1f}"
        say(L_)
    if not judge:
        return
    rng = np.random.default_rng(1242)
    # Placebo is compared GROSS (0 cost): a within-date shuffle destroys s persistence, so the shuffled book turns over
    # ~5x more and a net comparison only measures turnover (run note). Net placebo printed for reference.
    pl_ls, pl_lo, pn_ls, pn_lo, pt = [], [], [], [], []
    for k in range(N_PLACEBO):
        p = simulate(sig, R, spy, rng=rng); p["date"] = sessions[p.ti.astype(int)]
        p = p[(p.date >= w0) & (p.date <= w1)]
        a_, b_ = arms(p, 0.0); an, bn = arms(p, COST)
        pl_ls.append(sharpe(a_ + BORROW * (p.ns > 0))); pl_lo.append(b_.mean() * 252)
        pn_ls.append(sharpe(an)); pn_lo.append(bn.mean() * 252); pt.append(p.tl.mean())
    pl_ls, pl_lo = np.array(pl_ls), np.array(pl_lo)
    g_ls0 = (d.gl + d.gs + d.h * d.spy).to_numpy(); g_lo0 = (d.gl - d.bl * d.spy).to_numpy()
    sh_g, lo_g = sharpe(g_ls0), g_lo0.mean() * 252
    pct_ls = (pl_ls < sh_g).mean() * 100; pct_lo = (pl_lo < lo_g).mean() * 100
    say(f"  placebo (within-date shuffle of s, {N_PLACEBO} draws, GROSS): LS Sharpe mean {pl_ls.mean():+.2f} 95th {np.percentile(pl_ls, 95):+.2f} "
        f"-> real gross {sh_g:+.2f} at pct {pct_ls:.0f}; LO excess mean {pl_lo.mean():+.1%}/yr 95th {np.percentile(pl_lo, 95):+.1%} -> real gross {lo_g:+.1%} at pct {pct_lo:.0f}")
    say(f"    (net placebo for reference: LS Sharpe mean {np.mean(pn_ls):+.2f}, LO {np.mean(pn_lo):+.1%}/yr; placebo long turnover {np.mean(pt):.2f}/day vs real {d.tl.mean():.2f})")
    g_ls = [("Sharpe>=1.0", s_ls["sh"] >= 1.0), ("t>=2.5", s_ls["t"] >= 2.5), ("halves>0", s_ls["h1"] > 0 and s_ls["h2"] > 0),
            ("2xcost>0", s_lsx["mean"] > 0), ("ex-top5>0", s_ls["x5"] > 0), ("median-month>0", s_ls["med_m"] > 0),
            ("placebo95", pct_ls >= 95)]
    g_lo = [("excess>=8%/yr", s_lo["ann"] >= 0.08), ("t>=2", s_lo["t"] >= 2), ("halves>0", s_lo["h1"] > 0 and s_lo["h2"] > 0),
            ("2xcost>0", s_lox["mean"] > 0), ("placebo95", pct_lo >= 95)]
    ok_ls, ok_lo = all(o for _, o in g_ls), all(o for _, o in g_lo)
    say("  GATES LS: " + " | ".join(f"{n} {'PASS' if o else 'FAIL'}" for n, o in g_ls) + f" -> {'PASS' if ok_ls else 'FAIL'}")
    say("  GATES LO: " + " | ".join(f"{n} {'PASS' if o else 'FAIL'}" for n, o in g_lo) + f" -> {'PASS' if ok_lo else 'FAIL'}")
    say(f"  VERDICT N 1242 PCA-SA: {'PASS (' + ('LS' if ok_ls else '') + (' LO' if ok_lo else '') + ')' if (ok_ls or ok_lo) else 'KILL (both arms fail)'}")
    del R, sig; gc.collect()


def main():
    say("PCA-SA (N 1242): Avellaneda-Lee residual reversion, top-1000 ADV20 common SEP ($5+, ADV20 $10M+, 252 full returns; delisted kept),"
        f" MP-edge factors (cap {KMAX}) refit every {EIG_EVERY} sessions, {RW}d OLS residual -> AR(1) s-score; signal close T, trade close T+1;"
        f" cost {COST * 1e4:.0f}bp/side (shock {COST_X * 1e4:.0f}), borrow 100bp/yr; DSR at N {N_PROGRAM}")
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    if which in ("both", "judge"):
        run_pass("JUDGE 1998-2010", "1997-12-31", "2010-12-31", "1998-01-01", "2010-12-31", "2004-12-31", True)
    if which in ("both", "report"):
        run_pass("REPORT 2011-20 (never judged)", "2009-10-01", "2021-01-15", "2011-01-01", "2020-12-31", "2015-12-31", False)
        say("  REPORT 2021-26: not run (NX SEP cache ends 2021-01-15; no survivorship-clean 2021+ panel in the same format)")


if __name__ == "__main__":
    main()
