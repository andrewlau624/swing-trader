"""EXP round 3, R1/R2 (N 1225-1228): linear / RL allocation between the book's two EXISTING legs (IBS, night).

Pre-registration: research/drafts/round1_prose.md, "## Amendment - EXP round 3: RL / linear models pointed at the book's
EXISTING edges" (Common data, gates, R1-LIN N 1225, R1-LINTS N 1226, R2-PPO N 1227, R2-PPO-DD N 1228). Frozen before any
outcome was read; nothing here is tuned on 2013-20. One run.

Data
  night  data/research/program/sel_night_nights_primary.parquet `leg_current` = GROSS sum(per * r) (r = close d -> open d+1
         incl. ex-div cash, delist price; per = frac*gs*tilt, sum(per) <= 1 = deployed share of the leg). Only nights with a
         pre-filter pick exist; every other session earns 0. Net = leg - 5bp * sum(per) (5bp RT per unit traded), sum(per)
         from sel_night_names_primary.parquet rule=='current'. Aligned to decision day d (the 15:40 decision of d).
  ibs    exact live rule: research/sim/ibs_oos.py `_trades("ibs_lo")` run on a Sharadar SFP panel (split-adjusted OHLC,
         EQ18; late listers join once momentum_top has 252 bars). Return open d+1 -> open d+2 plus ACTIONS cash dividend
         with ex-date d+2 (split-adjusted as exp_rl_universe._features). Day return = mean over fired names - 2bp (1bp/side);
         no fire -> 0 (idle cash earns 0). Aligned to decision day d (decided at d's close).
         REPORT 2021-26 uses ibs_oos._trades on Alpaca etf_daily. NOTE: etf_daily is dividend-ADJUSTED (Alpaca/SFP close
         ratio drifts 0.85 -> 0.92 SPY, 0.66 -> 0.80 XLE over 2016-20), not raw as ibs_oos's docstring says; so its 12-1
         momentum ranks high-yield ETFs higher than the SFP split-only close does (top-3 differs in 13/47 months 2017-20),
         which is the main source of the cross-check mismatch (IBS<0.2 flags agree 98-100%).
  book   r_d = w_ibs * ibs_d + w_night * night_d (both legs keyed by the decision day d; the IBS trade decided at d runs
         open d+1 -> open d+2 and overlaps night d+1: summed per decision day, not re-timed). Weight changes free.
  state  at d (close values stand in for 15:40): SPY 20d vol, SPY close/SMA50, close/SMA200, log1p(night pool size),
         night-leg net mean & sd over nights d-20..d-1, IBS-leg net mean over decisions d-21..d-2 (the last ones whose
         open->open return is known at d), IBS firing count at d, SPY 5d return. z-scored on FIT rows, clipped +-5.

    PYTHONPATH=. python3 research/sim/exp_legalloc.py --prep        # data checks only (no judge numbers)
    PYTHONPATH=. python3 research/sim/exp_legalloc.py --timing N    # time one PPO policy for N steps
    PYTHONPATH=. python3 research/sim/exp_legalloc.py               # full run -> research/sim/exp_legalloc_out.txt
"""
from __future__ import annotations

import math
import multiprocessing as mp
import os
import pathlib
import sys
import time

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from research.sim import ibs_oos  # noqa: E402
from research.sim.exp_rl import (build_nets, sharpe, maxdd, dsr, LR, GAMMA, LAM, CLIP, N_STEPS, N_EPOCHS, MB,  # noqa: E402
                                 VF_COEF, ENT_COEF, MAX_GN, EP_LEN)

NXD = ROOT / "data/research/nx"
PROG = ROOT / "data/research/program"
ALP = ROOT / "data/research/night/etf_daily.parquet"
OUT = pathlib.Path(os.environ.get("EXP_LA_OUT", ROOT / "research/sim/exp_legalloc_out.txt"))
EQ18 = ibs_oos.EQ18

FIT = ("2003-01-01", "2012-12-31")
JUDGE = ("2013-01-01", "2020-12-31")
REPORT = ("2021-01-01", "2026-09-30")
H1_END = "2016-12-31"
SMOKE = os.environ.get("EXP_LA_SMOKE") == "1"   # code check on FIT data only: windows moved inside 2003-12, df cut at 2012
if SMOKE:
    FIT, JUDGE, REPORT, H1_END = ("2003-01-01", "2006-12-31"), ("2007-01-01", "2010-12-31"), ("2011-01-01", "2012-12-31"), "2008-12-31"
IBS_COST, NIGHT_COST = 1e-4, 5e-4          # IBS per side, night round trip
W_HI = (1.0, 1.3)                          # action box (w_ibs, w_night)
BASE = np.array([0.5, 0.5])                # live base profile
N_TRIALS = 1231
WARM = 252                                 # walk-forward warm-up rows inside FIT
REFIT = 21
LAMBDAS = [0.1, 1.0, 10.0, 100.0, 1000.0, 1e4, 1e5, 1e6]
KS = [0.25, 0.5, 1.0]
N_PLACEBO = int(os.environ.get("EXP_LA_NPLAC", 50))
PPO_SEEDS = [0, 1, 2, 3, 4]
PPO_STEPS = int(os.environ.get("EXP_LA_STEPS", 1_000_000))
ZCLIP = 5.0
FEATS = ["spy_vol20", "spy_tr50", "spy_tr200", "npool", "nmean20", "nsd20", "imean20", "ifire", "spy_r5"]

lines: list[str] = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    lines.append(s)


# ---------------------------------------------------------------- data
def sfp_panel() -> dict:
    d = pd.read_parquet(NXD / "cache_SFP.parquet", columns=["ticker", "date", "open", "high", "low", "close", "closeunadj"],
                        filters=[("ticker", "in", EQ18)])
    d["date"] = pd.to_datetime(d["date"])
    a = pd.read_parquet(NXD / "cache_ACTIONS.parquet", columns=["date", "action", "ticker", "value"])
    a = a[(a.action == "dividend") & a.ticker.isin(EQ18)].copy()
    a["date"] = pd.to_datetime(a["date"])
    a = a.groupby(["ticker", "date"])["value"].sum().rename("div").reset_index()
    d = d.merge(a, on=["ticker", "date"], how="left").fillna({"div": 0.0})
    d["divadj"] = np.where(d.closeunadj > 0, d["div"] * d["close"] / d["closeunadj"], 0.0)
    P = {f: d.pivot(index="date", columns="ticker", values=f).sort_index().astype(float)
         for f in ["open", "high", "low", "close", "divadj"]}
    P["divadj"] = P["divadj"].fillna(0.0)
    return P


def ibs_trades(P: dict) -> pd.DataFrame:
    """ibs_oos._trades on panel P (monkeypatched D.etf). Adds the ex-date-d+2 dividend to open d+1 -> open d+2."""
    old = ibs_oos.D.etf
    ibs_oos.D.etf = lambda: P
    try:
        t = ibs_oos._trades("ibs_lo").reset_index()
    finally:
        ibs_oos.D.etf = old
    if "divadj" in P:
        days = P["close"].index
        j = days.get_indexer(t["date"])
        O, DV = P["open"], P["divadj"]
        o1 = np.array([O.iat[k + 1, O.columns.get_loc(s)] for k, s in zip(j, t.sym)])
        dv = np.array([DV.iat[k + 2, DV.columns.get_loc(s)] for k, s in zip(j, t.sym)])
        t["ret"] = t["ret"] + dv / o1
    return t


def ibs_daily(t: pd.DataFrame, sessions: pd.DatetimeIndex) -> pd.DataFrame:
    g = t.groupby("date")["ret"].agg(["mean", "size"])
    out = pd.DataFrame(index=sessions)
    out["ibs"] = (g["mean"] - 2 * IBS_COST).reindex(sessions).fillna(0.0)
    out["ifire"] = g["size"].reindex(sessions).fillna(0).astype(float)
    return out


def alpaca_panel() -> dict:
    P = ibs_oos.D.etf()
    return {f: P[f] for f in ["open", "high", "low", "close"]}


def night_daily(sessions: pd.DatetimeIndex) -> tuple[pd.DataFrame, dict]:
    n = pd.read_parquet(PROG / "sel_night_nights_primary.parquet", columns=["date", "n_picks", "leg_current", "nk_current"])
    m = pd.read_parquet(PROG / "sel_night_names_primary.parquet", columns=["date", "rule", "r", "per"])
    m = m[m.rule == "current"]
    expo = m.groupby("date")["per"].sum()
    recon = (m["r"] * m["per"]).groupby(m["date"]).sum()
    n = n.set_index("date")
    chk = dict(rows=len(n), zero_kept=int((n.nk_current == 0).sum()),
               recon_maxerr=float((recon.reindex(n.index).fillna(0) - n.leg_current).abs().max()),
               not_in_cal=int((~n.index.isin(sessions)).sum()), expo_mean=float(expo.mean()), expo_max=float(expo.max()))
    out = pd.DataFrame(index=sessions)
    e = expo.reindex(sessions).fillna(0.0)
    out["night_gross"] = n["leg_current"].reindex(sessions).fillna(0.0)
    out["night"] = out["night_gross"] - NIGHT_COST * e
    out["nexpo"] = e
    out["npool"] = np.log1p(n["n_picks"].reindex(sessions).fillna(0.0))
    return out, chk


def spy_feats(close: pd.Series, div: pd.Series | None) -> pd.DataFrame:
    r = (close + (div if div is not None else 0.0)) / close.shift(1) - 1
    f = pd.DataFrame(index=close.index)
    f["spy_vol20"] = r.rolling(20).std() * math.sqrt(252)
    f["spy_tr50"] = close / close.rolling(50).mean()
    f["spy_tr200"] = close / close.rolling(200).mean()
    f["spy_r5"] = (1 + r).rolling(5).apply(np.prod, raw=True) - 1
    return f


def build() -> tuple[pd.DataFrame, dict]:
    P = sfp_panel()
    sess_s = P["close"]["SPY"].dropna().index
    sess_s = sess_s[sess_s <= "2020-12-31"]          # SFP decisions end with the judge period
    tS = ibs_trades(P)
    A = alpaca_panel()
    tA = ibs_trades(A)
    sess_a = A["close"]["SPY"].dropna().index
    sess_a = sess_a[(sess_a >= REPORT[0]) & (sess_a <= REPORT[1])]
    # last Alpaca decision with an open d+2
    last_ok = A["open"].index[-3]
    sess_a = sess_a[sess_a <= last_ok]
    sessions = sess_s.append(sess_a)
    I = pd.concat([ibs_daily(tS, sess_s), ibs_daily(tA, sess_a)])
    N, nchk = night_daily(sessions)
    fs = spy_feats(P["close"]["SPY"], P["divadj"]["SPY"]).reindex(sess_s)
    fa = spy_feats(A["close"]["SPY"], None).reindex(sess_a)
    F = pd.concat([fs, fa])
    df = pd.concat([I, N, F], axis=1)
    df["nmean20"] = df["night"].shift(1).rolling(20).mean()
    df["nsd20"] = df["night"].shift(1).rolling(20).std()
    df["imean20"] = df["ibs"].shift(2).rolling(20).mean()
    # cross-check 2016-20: Sharadar rebuild vs ibs_oos on Alpaca
    x0 = tA.date.min()                      # ibs_oos needs 260 Alpaca bars first: trades start ~2017-01
    a = tS[(tS.date >= x0) & (tS.date <= "2020-12-31")].set_index(["date", "sym"])["ret"]
    b = tA[(tA.date >= x0) & (tA.date <= "2020-12-31")].set_index(["date", "sym"])["ret"]
    both = a.index.intersection(b.index)
    xchk = dict(n_sharadar=len(a), n_alpaca=len(b), n_both=len(both), share_union=len(both) / len(a.index.union(b.index)),
                gap_matched_bp=float((a.loc[both] - b.loc[both]).mean() * 1e4),
                gap_all_bp=float((a.mean() - b.mean()) * 1e4),
                gap_matched_med_bp=float((a.loc[both] - b.loc[both]).median() * 1e4),
                first_sharadar=str(tS.date.min().date()), x0=str(x0.date()))
    # names in the momentum top-3 by year (joins of late listers)
    return df, dict(night=nchk, ibs=xchk)


# ---------------------------------------------------------------- stats
def cagr(x):
    x = np.asarray(x, float)
    return float(np.prod(1 + x) ** (252 / len(x)) - 1)


def scale_to_dd(x, target):
    """leverage s with maxdd(s*x) == target (target < 0); bisection (maxdd monotone in s)."""
    lo, hi = 1e-3, 50.0
    if maxdd(hi * x) > target:
        return hi
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if maxdd(mid * x) > target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def stats(r, dates, W=None, S=None):
    r = np.asarray(r, float)
    h1 = np.asarray(dates <= pd.Timestamp(H1_END))
    hs = (sharpe(r[h1]), sharpe(r[~h1])) if 1 < h1.sum() < len(r) - 1 else (float("nan"), float("nan"))
    e = dict(sh=sharpe(r), cagr=cagr(r), mdd=maxdd(r), sh1=hs[0], sh2=hs[1], mean=r.mean(),
             med=float(np.median(r)), hit=float((r > 0).mean()))
    if W is not None:
        e["w"] = W.mean(0); e["wsd"] = W.std(0)
        e["corr"] = {k: [float(np.corrcoef(W[:, j], S[k])[0, 1]) if W[:, j].std() > 0 else float("nan")
                         for j in range(2)] for k in ["spy_vol20", "spy_tr200", "spy_tr50", "npool"]}
    return e


def vs(e, r, base_r, eb, dates):
    """gate pieces vs one baseline."""
    r = np.asarray(r, float); base_r = np.asarray(base_r, float)
    s = scale_to_dd(r, eb["mdd"])
    c_m = cagr(s * r)
    d = r - base_r
    keep = np.ones(len(r), bool); keep[np.argsort(d)[-5:]] = False
    gx5 = sharpe(r[keep]) - sharpe(base_r[keep])
    return dict(dsh=e["sh"] - eb["sh"], cagr_m=c_m, scale=s, dcagr_m=c_m - eb["cagr"],
                halves=(e["sh1"] > eb["sh1"]) and (e["sh2"] > eb["sh2"]), gx5=gx5)


def fmt_e(tag, e):
    s = (f"{tag:<22} Sh {e['sh']:5.2f} CAGR {e['cagr']*100:6.2f}% maxDD {e['mdd']*100:6.1f}% | 13-16 Sh {e['sh1']:5.2f} "
         f"17-20 Sh {e['sh2']:5.2f} | mean {e['mean']*1e4:+6.2f}bp med {e['med']*1e4:+5.2f} hit {e['hit']*100:3.0f}%")
    if "w" in e:
        s += f" | w_ibs {e['w'][0]:.2f}+-{e['wsd'][0]:.2f} w_night {e['w'][1]:.2f}+-{e['wsd'][1]:.2f}"
    return s


def fmt_corr(e):
    return "    corr(w, state): " + "  ".join(f"{k}: ibs {v[0]:+.2f} night {v[1]:+.2f}" for k, v in e["corr"].items())


# ---------------------------------------------------------------- R1: ridge walk-forward
def ridge_fit(X, y, lam):
    xm, ym = X.mean(0), y.mean()
    Xc = X - xm
    A = Xc.T @ Xc + lam * np.eye(X.shape[1])
    Ainv = np.linalg.inv(A)
    b = Ainv @ (Xc.T @ (y - ym))
    res = y - ym - Xc @ b
    s2 = float(res @ res / max(len(y) - X.shape[1] - 1, 1))
    sdf = float((Xc @ b).std())
    return dict(xm=xm, ym=ym, b=b, Ainv=Ainv, s2=s2, n=len(y), sdf=sdf)


def wf(X, Y, lam, lo_train, start, end, rng=None):
    """Walk-forward standardized forecasts z[i, leg] for rows start..end-1; refit every REFIT rows on rows
    [lo_train, r-2]. rng -> Thompson sample of (b, intercept) each row. Also returns raw forecast (posterior mean)."""
    Z = np.zeros((end - start, 2)); Fm = np.zeros((end - start, 2))
    mods = [None, None]
    for i in range(start, end):
        if (i - start) % REFIT == 0:
            mods = [ridge_fit(X[lo_train:i - 1], Y[lo_train:i - 1, j], lam[j]) for j in range(2)]
        for j in range(2):
            m = mods[j]
            xc = X[i] - m["xm"]
            Fm[i - start, j] = m["ym"] + xc @ m["b"]
            if m["sdf"] <= 0:
                continue
            if rng is None:
                Z[i - start, j] = (xc @ m["b"]) / m["sdf"]
            else:
                bs = rng.multivariate_normal(m["b"], m["s2"] * m["Ainv"])
                i0 = rng.normal(0.0, math.sqrt(m["s2"] / m["n"]))
                Z[i - start, j] = (xc @ bs + i0) / m["sdf"]
    return Z, Fm


def act(Z, k):
    W = np.clip(BASE + k * Z, 0.0, None)
    return np.minimum(W, np.array([1.3, 1.3]))


def book(W, R):
    return (W * R).sum(1)


def r1_pipeline(X, Y, R, ix, ts_seed=None, verbose=False):
    """Choose lambda (WF MSE per leg) and k (WF Sharpe) on FIT, then walk forward through judge+report with frozen
    lambda,k (expanding refit). X is the (possibly placebo-shuffled) state matrix. Returns dict."""
    f0, f1, j1, rend = ix["fit0"], ix["fit1"], ix["j1"], ix["end"]
    ws = f0 + WARM
    lam = []
    mse_tab = {}
    for j in range(2):
        best = None
        for L in LAMBDAS:
            _, Fm = wf(X, Y, [L, L], f0, ws, f1)
            mse = float(((Y[ws:f1, j] - Fm[:, j]) ** 2).mean())
            mse_tab[(j, L)] = mse
            if best is None or mse < best[0] - 1e-15:
                best = (mse, L)
        lam.append(best[1])
    rng = None if ts_seed is None else np.random.default_rng(ts_seed)
    Zf, _ = wf(X, Y, lam, f0, ws, f1, rng)
    ksh = {k: sharpe(book(act(Zf, k), R[ws:f1])) for k in KS}
    k = max(KS, key=lambda kk: (round(ksh[kk], 9), -kk))
    rng = None if ts_seed is None else np.random.default_rng(ts_seed + 1)
    Zj, _ = wf(X, Y, lam, f0, f1, rend, rng)
    W = act(Zj, k)
    return dict(lam=lam, k=k, ksh=ksh, mse=mse_tab, W=W, r=book(W, R[f1:rend]))


# ---------------------------------------------------------------- R2: PPO
def _sig(x):
    return 1.0 / (1.0 + np.exp(-x))


CACHE = pathlib.Path(os.environ.get("EXP_LA_CACHE", "/tmp/exp_legalloc_cache"))


def ppo_train_cached(job: dict) -> dict:
    """ppo_train with a per-policy pickle (resume after an interrupted run; same job -> same file)."""
    import pickle
    f = CACHE / f"{job['kind']}_{'p' if job['perm'] is not None else 's'}{job.get('pid', job['seed'])}_{job['steps']}.pkl"
    if f.exists():
        return pickle.loads(f.read_bytes())
    out = ppo_train(job)
    CACHE.mkdir(parents=True, exist_ok=True)
    f.write_bytes(pickle.dumps(out))
    return out


def ppo_train(job: dict) -> dict:
    """exp_rl.train's PPO (same nets via exp_rl.build_nets, same SB3-default update) on this env: obs = 9 z-state,
    action = first 2 of the 5 Gaussian outputs -> (w_ibs, w_night) = (1.0, 1.3) * sigmoid(a)."""
    import torch
    torch.set_num_threads(1)
    seed, perm, steps, kind = job["seed"], job["perm"], job["steps"], job["kind"]
    S, R, lo, hi = job["S"], job["R"], job["lo"], job["hi"]      # decision rows lo..hi-1 (fit)
    torch.manual_seed(seed)
    rng = np.random.default_rng(1000 * seed + 11 + (0 if perm is None else 7))
    Sx = S.copy()
    if perm is not None:
        Sx[lo:hi] = S[lo:hi][perm]
    od = S.shape[1]
    pi, vf, log_std = build_nets(torch, od)
    params = list(pi.parameters()) + list(vf.parameters()) + [log_std]
    opt = torch.optim.Adam(params, lr=LR, eps=1e-5)
    whi = np.array(W_HI)

    def reset():
        return int(rng.integers(lo, hi - EP_LEN + 1)), 0, 1.0, 1.0

    i, t_ep, eq, pk = reset()
    for _ in range(math.ceil(steps / N_STEPS)):
        O = np.zeros((N_STEPS, od), np.float32); A = np.zeros((N_STEPS, 2), np.float32)
        LP = np.zeros(N_STEPS, np.float32); V = np.zeros(N_STEPS + 1, np.float32)
        Rw = np.zeros(N_STEPS, np.float32); D = np.zeros(N_STEPS, np.float32)
        for k in range(N_STEPS):
            o = Sx[i]
            with torch.no_grad():
                ot = torch.from_numpy(o)
                mu = pi(ot)[:2]; v = vf(ot)[0]
                ls = log_std[:2]; std = ls.exp()
                a = mu + std * torch.randn(2)
                lp = (-((a - mu) ** 2) / (2 * std ** 2) - ls - 0.5 * math.log(2 * math.pi)).sum()
            an = a.numpy().astype(np.float64)
            w = whi * _sig(an)
            net = float(w @ R[i])
            if kind == "var":
                rew = math.log1p(net) - 0.5 * net * net
            else:
                dd0 = 1 - eq / pk
                eq *= 1 + net; pk = max(pk, eq)
                rew = math.log1p(net) - 2.0 * max(0.0, (1 - eq / pk) - dd0)
            O[k] = o; A[k] = an; LP[k] = lp.item(); V[k] = v.item(); Rw[k] = rew
            i += 1; t_ep += 1
            if t_ep >= EP_LEN:
                D[k] = 1.0
                i, t_ep, eq, pk = reset()
        with torch.no_grad():
            V[N_STEPS] = vf(torch.from_numpy(Sx[i]))[0].item()
        adv = np.zeros(N_STEPS, np.float32); last = 0.0
        for k in reversed(range(N_STEPS)):
            nt = 1.0 - D[k]
            delta = Rw[k] + GAMMA * V[k + 1] * nt - V[k]
            last = delta + GAMMA * LAM * nt * last
            adv[k] = last
        ret = adv + V[:N_STEPS]
        Ot, At, LPt = torch.from_numpy(O), torch.from_numpy(A), torch.from_numpy(LP)
        ADt, RTt = torch.from_numpy(adv), torch.from_numpy(ret)
        for _e in range(N_EPOCHS):
            pm = torch.from_numpy(rng.permutation(N_STEPS))
            for b in range(0, N_STEPS, MB):
                idx = pm[b:b + MB]
                mu = pi(Ot[idx])[:, :2]; v = vf(Ot[idx]).squeeze(-1)
                ls = log_std[:2]
                lp = (-((At[idx] - mu) ** 2) / (2 * ls.exp() ** 2) - ls - 0.5 * math.log(2 * math.pi)).sum(-1)
                ad = ADt[idx]; ad = (ad - ad.mean()) / (ad.std() + 1e-8)
                ratio = (lp - LPt[idx]).exp()
                pl = -torch.min(ratio * ad, ratio.clamp(1 - CLIP, 1 + CLIP) * ad).mean()
                vl = ((RTt[idx] - v) ** 2).mean()
                ent = (ls + 0.5 * math.log(2 * math.pi * math.e)).sum()
                loss = pl + VF_COEF * vl - ENT_COEF * ent
                opt.zero_grad(); loss.backward()
                torch.nn.utils.clip_grad_norm_(params, MAX_GN); opt.step()
    sd = {k: v.detach().numpy().copy() for k, v in pi.state_dict().items()}
    return {"seed": seed, "kind": kind, "placebo": perm is not None, "pid": job.get("pid"), "pi": sd}


def ppo_weights(sd, S):
    h = np.tanh(S @ sd["0.weight"].T + sd["0.bias"]); h = np.tanh(h @ sd["2.weight"].T + sd["2.bias"])
    a = (h @ sd["4.weight"].T + sd["4.bias"])[:, :2]
    return np.array(W_HI) * _sig(a)


# ---------------------------------------------------------------- main
def zstate(df, fit_mask):
    X = df[FEATS].to_numpy(float)
    mu = np.nanmean(X[fit_mask], 0); sd = np.nanstd(X[fit_mask], 0)
    return np.clip((X - mu) / sd, -ZCLIP, ZCLIP)


def main():
    t0 = time.time()
    prep = "--prep" in sys.argv
    if "--timing" in sys.argv:
        df, _ = build()
        fm = (df.index >= FIT[0]) & (df.index <= FIT[1])
        S = zstate(df, fm).astype(np.float32); R = df[["ibs", "night"]].to_numpy(float)
        lo, hi = int(np.argmax(fm)), int(len(fm) - np.argmax(fm[::-1]))
        n = int(sys.argv[sys.argv.index("--timing") + 1])
        t1 = time.time()
        ppo_train(dict(seed=0, perm=None, steps=n, kind="var", S=S, R=R, lo=lo, hi=hi))
        print(f"{n} steps: {time.time()-t1:.1f}s")
        return

    df, chk = build()
    if SMOKE:
        df = df[df.index <= "2012-12-31"]
    nc, xc = chk["night"], chk["ibs"]
    say("EXP round 3 R1/R2 (N 1225-1228): leg allocation IBS x night. Pre-reg round1_prose.md 'EXP round 3'.")
    say(f"FIT {FIT[0]}..{FIT[1]}  JUDGE {JUDGE[0]}..{JUDGE[1]}  REPORT {REPORT[0]}..{df.index[-1].date()}")
    say(f"night file: {nc['rows']} nights with a pre-filter pick (others earn 0), {nc['zero_kept']} with none kept; leg_current"
        f" is GROSS (recon sum(per*r) max err {nc['recon_maxerr']:.1e}); deployed sum(per) mean {nc['expo_mean']:.2f} max "
        f"{nc['expo_max']:.2f}; net = gross - 5bp x sum(per); nights not in the session calendar: {nc['not_in_cal']}")
    say(f"IBS rebuild: Sharadar SFP first trade {xc['first_sharadar']}; cross-check {xc['x0']}..2020-12 vs ibs_oos on Alpaca: trades "
        f"Sharadar {xc['n_sharadar']} / Alpaca {xc['n_alpaca']} / both {xc['n_both']} (overlap {xc['share_union']*100:.1f}% of"
        f" union); mean gap Sharadar-Alpaca matched {xc['gap_matched_bp']:+.2f}bp (median {xc['gap_matched_med_bp']:+.2f}),"
        f" all-trade means {xc['gap_all_bp']:+.2f}bp (Sharadar split-adj + ACTIONS dividends, Alpaca div-adjusted bars)")
    fm = np.asarray((df.index >= FIT[0]) & (df.index <= FIT[1]))
    jm = np.asarray((df.index >= JUDGE[0]) & (df.index <= JUDGE[1]))
    rm = np.asarray(df.index >= REPORT[0])
    assert df.loc[fm | jm | rm, FEATS].notna().all().all(), df.loc[fm | jm | rm, FEATS].isna().sum()
    X = zstate(df, fm)
    R = df[["ibs", "night"]].to_numpy(float)
    f0, f1 = int(np.argmax(fm)), int(np.argmax(jm))
    j1, end = int(np.argmax(rm)), len(df)
    ix = dict(fit0=f0, fit1=f1, j1=j1, end=end)
    dates = df.index
    say(f"rows: fit {fm.sum()} judge {jm.sum()} report {rm.sum()}; fit leg means: IBS {R[fm,0].mean()*1e4:+.2f}bp/d "
        f"night {R[fm,1].mean()*1e4:+.2f}bp/d, corr {np.corrcoef(R[fm,0], R[fm,1])[0,1]:+.2f}")
    if prep:
        say("prep only: no judge numbers printed")
        return

    # ---------------- baselines
    grid = [(a / 10, b / 10) for a in range(0, 11) for b in range(0, 14) if a + b > 0]
    fsh = {g: round(sharpe(book(np.array(g)[None, :], R[fm])), 6) for g in grid}
    best = max(grid, key=lambda g: (fsh[g], -abs(g[0] + g[1] - 1.0), -g[0]))
    say(f"best fixed on FIT (0.1 grid, w_ibs 0..1, w_night 0..1.3; ties -> gross nearest 1.0): w_ibs {best[0]:.1f} "
        f"w_night {best[1]:.1f} (fit Sh {fsh[best]:.2f}; live 0.5/0.5 fit Sh {fsh[(0.5, 0.5)]:.2f})")
    Sj = {k: df[k].to_numpy(float)[jm] for k in ["spy_vol20", "spy_tr200", "spy_tr50", "npool"]}
    Sr = {k: df[k].to_numpy(float)[rm] for k in ["spy_vol20", "spy_tr200", "spy_tr50", "npool"]}
    dj, dr = dates[jm], dates[rm]
    base = {"live 0.5/0.5": np.array([0.5, 0.5]), f"best fixed {best[0]:.1f}/{best[1]:.1f}": np.array(best)}
    say("\nBASELINES (JUDGE 2013-20, net)")
    bj, be = {}, {}
    for n, w in base.items():
        bj[n] = book(w[None, :], R[jm]); be[n] = stats(bj[n], dj)
        say(fmt_e(n, be[n]))
    better = max(be, key=lambda n: be[n]["sh"])
    say(f"better baseline (higher judge Sharpe): {better}")

    def judge_block(tag, r, W, plac_sh=None):
        e = stats(r, dj, W, Sj)
        say(fmt_e(tag, e)); say(fmt_corr(e))
        res = {}
        for n in base:
            v = vs(e, r, bj[n], be[n], dj)
            res[n] = v
            say(f"    vs {n:<16} dSh {v['dsh']:+.3f} | CAGR@maxDD {be[n]['mdd']*100:.1f}% = {v['cagr_m']*100:6.2f}% (x{v['scale']:.2f})"
                f" vs {be[n]['cagr']*100:6.2f}% (d {v['dcagr_m']*100:+.2f}pp) | halves beat {v['halves']} | ex-top-5 dSh "
                f"{v['gx5']:+.3f}")
        g = dict(
            sh=all(res[n]["dsh"] >= 0.15 for n in base),
            cagr=all(res[n]["dcagr_m"] >= 0.02 for n in base),
            halves=all(res[n]["halves"] for n in base),
            x5=all(res[n]["gx5"] > 0 for n in base))
        if plac_sh is not None:
            p95 = float(np.percentile(plac_sh, 95))
            pct = float((np.asarray(plac_sh) < e["sh"]).mean() * 100)
            g["plac"] = e["sh"] >= p95
            say(f"    placebo ({len(plac_sh)}): judge Sh median {np.median(plac_sh):.2f} 95th {p95:.2f} max {np.max(plac_sh):.2f};"
                f" real {e['sh']:.2f} at pct {pct:.0f} (gain vs better {e['sh']-be[better]['sh']:+.3f} vs placebo-95th gain "
                f"{p95-be[better]['sh']:+.3f})")
        say(f"    DSR (N {N_TRIALS}): {dsr(r, N_TRIALS):.3f}")
        return e, g

    def gate_line(g):
        names = [("sh", "dSh>=+0.15"), ("cagr", "CAGR@DD>=+2pp"), ("halves", "both halves"), ("plac", "placebo>=95th"),
                 ("x5", "ex-top-5 gain>0")]
        return " | ".join(f"{lab}: {'PASS' if g.get(k) else 'FAIL'}" for k, lab in names if k in g)

    verdicts = {}
    report_rows = []
    # ---------------- R1-LIN, R1-LINTS
    for name, N, ts in [("R1-LIN", 1225, None), ("R1-LINTS", 1226, 0)]:
        t1 = time.time()
        real = r1_pipeline(X, R, R, ix, ts_seed=ts)
        nj = jm.sum()
        rj, Wj = real["r"][:nj], real["W"][:nj]
        rng = np.random.default_rng(12345 + N)
        plac = []
        for p in range(N_PLACEBO):
            Xp = X.copy()
            Xp[f0:f1] = X[f0:f1][rng.permutation(f1 - f0)]
            pr = r1_pipeline(Xp, R, R, ix, ts_seed=None if ts is None else 1000 + 2 * p)
            plac.append(sharpe(pr["r"][:nj]))
        say(f"\n{name} (N {N}): lambda ibs {real['lam'][0]:g} night {real['lam'][1]:g}; k {real['k']} (fit WF Sh "
            + " ".join(f"k{k}:{v:.2f}" for k, v in real["ksh"].items()) + f"){' ; TS seed 0' if ts is not None else ''}"
            f"  [{(time.time()-t1)/60:.1f} min]")
        e, g = judge_block(name, rj, Wj, plac)
        say(f"  GATES {name}: {gate_line(g)}")
        verdicts[name] = all(g.values())
        say(f"  VERDICT {name} (N {N}): {'PASS' if verdicts[name] else 'FAIL'}")
        report_rows.append((name, real["r"][nj:], real["W"][nj:]))

    # ---------------- R2 PPO
    S32 = X.astype(np.float32)
    jobs = []
    rngp = np.random.default_rng(777)
    perms = [rngp.permutation(f1 - f0) for _ in range(N_PLACEBO)]
    for kind in ["var", "dd"]:
        for s in PPO_SEEDS:
            jobs.append(dict(seed=s, perm=None, steps=PPO_STEPS, kind=kind, S=S32, R=R, lo=f0, hi=f1))
        for p in range(N_PLACEBO):
            jobs.append(dict(seed=100 + p, perm=perms[p], steps=PPO_STEPS, kind=kind, S=S32, R=R, lo=f0, hi=f1, pid=p))
    t1 = time.time()
    with mp.get_context("spawn").Pool(int(os.environ.get("EXP_LA_PROCS", 9))) as pool:
        out = pool.map(ppo_train_cached, jobs, chunksize=1)
    t_ppo = time.time() - t1
    say(f"\nPPO: {PPO_STEPS:,} steps/policy, {len(jobs)} policies (2 rewards x (5 seeds + {N_PLACEBO} placebo)); exp_rl"
        f" SB3-default hyperparameters; obs = 9 z-state; action (1.0, 1.3) x sigmoid(first 2 Gaussian outputs); train "
        f"{t_ppo/60:.1f} min")
    for name, N, kind in [("R2-PPO", 1227, "var"), ("R2-PPO-DD", 1228, "dd")]:
        reals = [o for o in out if o["kind"] == kind and not o["placebo"]]
        placs = [o for o in out if o["kind"] == kind and o["placebo"]]
        plac_sh = [sharpe(book(ppo_weights(o["pi"], X[f1:j1]), R[f1:j1])) for o in placs]
        say(f"\n{name} (N {N}): reward {'log(1+r) - 0.5 r^2' if kind == 'var' else 'log(1+r) - 2 x dDD+'}")
        npass = 0
        for o in sorted(reals, key=lambda o: o["seed"]):
            W = ppo_weights(o["pi"], X[f1:end])
            r = book(W, R[f1:end])
            e, g = judge_block(f"{name} seed {o['seed']}", r[:jm.sum()], W[:jm.sum()], plac_sh)
            ok = all(g.values()); npass += ok
            say(f"  GATES seed {o['seed']}: {gate_line(g)} -> {'PASS' if ok else 'FAIL'}")
            report_rows.append((f"{name} s{o['seed']}", r[jm.sum():], W[jm.sum():]))
        verdicts[name] = npass >= 4
        say(f"  VERDICT {name} (N {N}): {'PASS' if verdicts[name] else 'FAIL'} ({npass}/5 seeds pass all gates; need >= 4)")

    # ---------------- REPORT
    say(f"\nREPORT {dr[0].date()}..{dr[-1].date()} (descriptive, not judged; IBS from Alpaca etf_daily via ibs_oos._trades,"
        f" div-adjusted bars; night from the same nights file; R1 keeps its expanding monthly refit, PPO frozen)")
    for n, w in base.items():
        e = stats(book(w[None, :], R[rm]), dr)
        say(f"{n:<22} Sh {e['sh']:5.2f} CAGR {e['cagr']*100:6.2f}% maxDD {e['mdd']*100:6.1f}%")
    for tag, r, W in report_rows:
        e = stats(r, dr, W, Sr)
        say(f"{tag:<22} Sh {e['sh']:5.2f} CAGR {e['cagr']*100:6.2f}% maxDD {e['mdd']*100:6.1f}% | w_ibs {e['w'][0]:.2f} "
            f"w_night {e['w'][1]:.2f} | dSh vs live {e['sh']-sharpe(book(BASE[None, :], R[rm])):+.2f}")

    say("\nVERDICTS: " + " | ".join(f"{k}: {'PASS' if v else 'FAIL'}" for k, v in verdicts.items()))
    say("\nreadings/deviations: " + " ; ".join([
        "night leg_current is gross; net = gross - 5bp x deployed sum(per); sessions without a nights row earn 0",
        "IBS no-fire days earn 0 (no BIL credit); IBS day = mean of fired names - 2bp",
        "both legs keyed by decision day d and summed (IBS d = open d+1 -> d+2, night d = close d -> open d+1)",
        "state at d's close stands in for 15:40; IBS rolling mean uses decisions <= d-2 (known at d), night <= d-1",
        "night pool size enters as log1p(n_picks); state z clipped +-5 (fit mean/sd)",
        "ridge/LINTS refits every 21 sessions on rows [2003-01, r-2]; WF warm-up 252 rows; lambda per leg by WF MSE on FIT,"
        " k by WF Sharpe on FIT 2004-12; forecast/sd = centred forecast (x - xbar).b / sd of training forecasts (intercept"
        " excluded, the signals.night_tilt convention); base = live 0.5/0.5; weights clipped to [0, 1.3] both legs as the"
        " pre-reg says (so w_ibs may exceed the PPO box of 1.0)",
        "LINTS: posterior N(b, s2 (X'X+lam I)^-1) plus intercept N(ybar, s2/n), one draw per day; primary = TS seed 0",
        "placebo R1: FIT rows of the state shuffled (judge rows unshuffled, expanding refit as real); lambda and k re-chosen",
        "lambda grid 0.1..1e6 (decades); forecast/sd makes the action scale-free in lambda, so lambda only sets the"
        " forecast direction",
        "placebo PPO: 50 policies per reward on fit-shuffled states (seeds 100-149); each real seed compared with the"
        " same 50",
        "gates applied vs BOTH baselines (live and best fixed); placebo vs the higher judge Sharpe; ex-top-5 drops the 5"
        " judge days with the largest strategy - baseline difference",
        "PPO PASS = >= 4/5 seeds passing every gate; deterministic policy (mean action)",
        "REPORT IBS from Alpaca etf_daily (dividend-adjusted bars, so dividends are inside the open->open return) and SPY"
        " state from Alpaca closes",
        "cross-check mismatch: etf_daily is dividend-adjusted, SFP momentum uses split-only close as the pre-reg says;"
        " 12-1 top-3 differs in 13/47 months 2017-20 (IBS<0.2 flags agree 98-100%); the overlap window starts at the"
        " first ibs_oos trade (needs 260 Alpaca bars)",
        "REPORT ends 2026-09-17 (last etf_daily decision with an open d+2); 9 later night rows dropped",
    ]))
    say(f"runtime: total {(time.time()-t0)/60:.1f} min")
    OUT.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
