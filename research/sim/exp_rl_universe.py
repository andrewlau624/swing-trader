"""EXP round 2 D2a-D2d RL-UNIVERSE (N 1219-1222): can a PPO agent beat the equal-weight basket of a daily 10-slot universe?

Pre-registration: research/drafts/round1_prose.md, "## Amendment - EXP round (user 2026-11-20 ...)" (Common frame, D1 RL-ALLOC
N 1216) and "## Amendment - EXP round 2: the RL agent on other markets" (D2a-D2d, N 1219-1222). Frozen before any outcome.

  D2a RL-WEEKTOP (N 1219)  10 common stocks with the highest trailing 5-session total return
  D2b RL-VOLTOP  (N 1220)  10 highest 20d realised vol among the top 500 by 20d ADV
  D2c RL-LOSERS  (N 1221)  10 biggest day-t losers (close/prev close) among the top 1000 by 20d ADV
  D2d RL-SECTORS (N 1222)  XLB XLE XLF XLI XLK XLP XLU XLV XLY + SPY, fixed slots
Stocks: Sharadar SEP common stocks (TICKERS category via nx.is_common), delisted names kept, unadjusted close >= $5 at t,
20d ADV (closeunadj x volume, sessions t-19..t) >= $10M. Total return = split-adjusted close + ACTIONS cash dividends.
Selection and observation at t use data through t's close; earn t close -> t+1 close. A name with no bar on t+1 (delisted or
gap) earns 0 that day (last available close) and is counted.
Agent: one shared 2x64 tanh scorer per slot (input: slot features, mean-pooled slot features, cash + out-of-slot weight) ->
logit; a cash head on the pooled features -> cash logit; Gaussian over the 11 logits (shared slot log-std, cash log-std) ->
softmax: long-only, gross <= 1. Value head on the pooled features. PPO = D1's settings (lr 3e-4, gamma .99, lambda .95,
clip .2, 2048-step rollouts, 10 epochs, minibatch 64, vf .5, ent 0, grad-norm .5), 252-session random episodes in FIT
2002-08..2010-12, reward log(1 + net). Frozen deterministic policies (softmax of mean logits) judged 2011-01..2020-12 vs the
EW 10-slot basket (costless: conservative), and vs SPY. Placebo: same pipeline on fit-period earned returns circularly shifted
by k ~ U{250..2000} sessions (observations unshifted), 3 draws x 5 seeds per universe. No REPORT period (SEP ends 2021-01).

    PYTHONPATH=. python3 research/sim/exp_rl_universe.py --prep          # build + cache slot tensors, data checks only
    PYTHONPATH=. python3 research/sim/exp_rl_universe.py --timing N      # time one D2a policy for N steps
    PYTHONPATH=. python3 research/sim/exp_rl_universe.py                 # full run -> research/sim/exp_rl_universe_out.txt
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
from research.sim.exp_rl import ols_alpha, sharpe, maxdd, dsr  # noqa: E402  (shared stats helpers of D1)
from research.sim.nx import is_common  # noqa: E402

NXD = ROOT / "data/research/nx"
OUT = pathlib.Path(os.environ.get("EXP_RLU_OUT", ROOT / "research/sim/exp_rl_universe_out.txt"))
CACHE = pathlib.Path(os.environ.get("EXP_RLU_CACHE", "/tmp/exp_rl_universe_cache"))

K = 10
SECTORS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY", "SPY"]
LOAD_START = "1998-01-01"
FIT_START, FIT_END = "2002-08-01", "2010-12-31"
JUDGE_START, JUDGE_END = "2011-01-01", "2020-12-31"
PRICE_MIN, ADV_MIN = 5.0, 1e7
UNIV = {  # name: (N, cost, shock)
    "D2a RL-WEEKTOP": (1219, 2.5e-4, 5e-4),
    "D2b RL-VOLTOP": (1220, 2.5e-4, 5e-4),
    "D2c RL-LOSERS": (1221, 5e-4, 10e-4),
    "D2d RL-SECTORS": (1222, 1e-4, 3e-4),
}
N_TRIALS = 1222
SEEDS = [0, 1, 2, 3, 4]
N_PLACEBO_DRAWS = 3
TOTAL_STEPS = int(os.environ.get("EXP_RLU_STEPS", 1_000_000))
EP_LEN = 252
LR, GAMMA, LAM, CLIP, N_STEPS, N_EPOCHS, MB = 3e-4, 0.99, 0.95, 0.2, 2048, 10, 64
VF_COEF, ENT_COEF, MAX_GN = 0.5, 0.0, 0.5
NF = 9          # per-slot market features: r(t-4..t) x5, vol20, ibs, day ret, rank
ZCLIP = 5.0

lines: list[str] = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    lines.append(s)


# ---------------------------------------------------------------- data
def _divs(tickers) -> pd.DataFrame:
    a = pd.read_parquet(NXD / "cache_ACTIONS.parquet", columns=["date", "action", "ticker", "value"])
    a = a[(a.action == "dividend") & a.ticker.isin(tickers)].copy()
    a["date"] = pd.to_datetime(a["date"])
    return a.groupby(["ticker", "date"])["value"].sum().rename("div").reset_index()


def _features(b: pd.DataFrame) -> pd.DataFrame:
    """b sorted by (ticker, date), one table. Adds ret, r0..r4, vol20, adv20, ibs, ret5, nxt, nmiss (all causal except nxt)."""
    b = b.reset_index(drop=True)
    dv = _divs(b.ticker.unique())
    b = b.merge(dv, on=["ticker", "date"], how="left")
    b["div"] = b["div"].fillna(0.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        b["divadj"] = np.where(b.closeunadj > 0, b["div"] * b["close"] / b["closeunadj"], 0.0)
    code = pd.factorize(b.ticker)[0]
    n = len(b)
    newg = np.r_[True, code[1:] != code[:-1]]
    start = np.maximum.accumulate(np.where(newg, np.arange(n), 0))
    pos = np.arange(n) - start
    c = b.close.to_numpy(float); da = b.divadj.to_numpy(float)
    cprev = np.r_[np.nan, c[:-1]]; cprev[pos == 0] = np.nan
    with np.errstate(divide="ignore", invalid="ignore"):
        ret = (c + da) / cprev - 1
    ret[~np.isfinite(ret)] = np.nan
    b["ret"] = ret; b["pos"] = pos; b["code"] = code
    g = b.groupby(code, sort=False)
    for L in range(5):
        b[f"r{L}"] = g["ret"].shift(L)                        # r0 = day t, r4 = day t-4
    b["vol20"] = g["ret"].rolling(20, min_periods=20).std().reset_index(level=0, drop=True) * math.sqrt(252)
    b["dvol"] = b.close * b.volume          # SEP volume is split-adjusted: closeunadj*volume was lookahead (fixed 2026-11-21)
    b["adv20"] = g["dvol"].rolling(20, min_periods=20).mean().reset_index(level=0, drop=True)
    hl = (b.high - b.low).to_numpy(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        b["ibs"] = np.where(hl > 0, (b.close - b.low) / hl, 0.5)
    b["ret5"] = np.prod([1 + b[f"r{L}"].to_numpy(float) for L in range(5)], axis=0) - 1
    return b


def _next_ret(b: pd.DataFrame, sessions: np.ndarray) -> pd.DataFrame:
    """Earned return t close -> next session close; 0 + flag when the name has no bar on the next session."""
    sidx = np.searchsorted(sessions, b.date.to_numpy("datetime64[ns]"))
    code = b.code.to_numpy()
    same = np.r_[code[1:] == code[:-1], False]
    nxt_sess = np.r_[sidx[1:] == sidx[:-1] + 1, False] & same
    rn = np.r_[b.ret.to_numpy()[1:], np.nan]
    b["sidx"] = sidx
    b["miss"] = np.where(nxt_sess & np.isfinite(rn), 0, np.where(same, 1, 2))   # 1 = gap (bar later), 2 = no later bar
    b["nxt"] = np.where(b.miss == 0, rn, 0.0)
    return b


def load_stocks() -> pd.DataFrame:
    import pyarrow.parquet as pq
    t = pd.read_parquet(NXD / "cache_TICKERS.parquet", columns=["table", "ticker", "category"])
    t = t[t.table == "SEP"]
    common = set(t.ticker[is_common(t.category.fillna("").astype(str))])
    cols = ["ticker", "date", "high", "low", "close", "volume", "closeunadj"]
    tb = pq.read_table(NXD / "cache_SEP.parquet", columns=cols,
                       filters=[("date", ">=", pd.Timestamp(LOAD_START)), ("ticker", "in", sorted(common))])
    b = tb.to_pandas()
    b["date"] = pd.to_datetime(b["date"])
    b["ticker"] = b["ticker"].astype(str)
    for c in ("high", "low", "close", "volume", "closeunadj"):
        b[c] = b[c].astype(np.float64)
    b = b.sort_values(["ticker", "date"], kind="mergesort")
    return _features(b)


def load_etfs(tickers) -> pd.DataFrame:
    import pyarrow.parquet as pq
    cols = ["ticker", "date", "high", "low", "close", "volume", "closeunadj"]
    tb = pq.read_table(NXD / "cache_SFP.parquet", columns=cols,
                       filters=[("date", ">=", pd.Timestamp(LOAD_START)), ("ticker", "in", list(tickers))])
    b = tb.to_pandas(); b["date"] = pd.to_datetime(b["date"]); b["ticker"] = b["ticker"].astype(str)
    for c in ("high", "low", "close", "volume", "closeunadj"):
        b[c] = b[c].astype(np.float64)
    return _features(b.sort_values(["ticker", "date"], kind="mergesort"))


def _tensorise(sel: pd.DataFrame, sessions: np.ndarray, rankcol: str, asc: bool) -> dict:
    """sel: exactly the K chosen rows per decision session. Returns X [D,K,NF], E [D,K], C [D,K] (codes), dates, miss."""
    sel = sel.sort_values(["sidx", rankcol, "ticker"], ascending=[True, asc, True], kind="mergesort")
    cnt = sel.groupby("sidx").size()
    sel = sel[sel.sidx.isin(cnt.index[cnt == K])]
    D = sel.sidx.nunique()
    rank = np.tile(np.arange(K) / (K - 1), D)
    X = np.column_stack([sel[f"r{L}"] for L in (4, 3, 2, 1, 0)] + [sel.vol20, sel.ibs, sel.r0, rank]).reshape(D, K, NF)
    return dict(X=X.astype(np.float64), E=sel.nxt.to_numpy(float).reshape(D, K), C=sel.code.to_numpy().reshape(D, K),
                miss=sel.miss.to_numpy().reshape(D, K), sidx=sel.sidx.to_numpy().reshape(D, K)[:, 0],
                dates=sessions[sel.sidx.to_numpy().reshape(D, K)[:, 0]],
                tick=sel.ticker.to_numpy().reshape(D, K), r0=sel.r0.to_numpy().reshape(D, K),
                ibs=sel.ibs.to_numpy().reshape(D, K), cu=sel.closeunadj.to_numpy().reshape(D, K),
                vol=sel.vol20.to_numpy().reshape(D, K))


def prep() -> dict:
    t0 = time.time()
    U = {}
    b = load_stocks()
    sessions = np.unique(b.date.to_numpy("datetime64[ns]"))
    b = _next_ret(b, sessions)
    feat = ["r0", "r1", "r2", "r3", "r4", "vol20", "adv20", "ibs", "ret5"]
    el = b[(b.pos >= 20) & (b.closeunadj >= PRICE_MIN) & (b.adv20 >= ADV_MIN)
           & np.isfinite(b[feat]).all(axis=1) & (b.date <= JUDGE_END)].copy()
    say(f"[prep] SEP common rows {len(b):,}, eligible rows {len(el):,}, sessions {len(sessions)}, load {time.time()-t0:.0f}s")
    del b
    g = el.groupby("sidx")
    el["advrk"] = g["adv20"].rank(ascending=False, method="first")
    a = el.copy(); a["rk"] = a.groupby("sidx")["ret5"].rank(ascending=False, method="first")
    U["D2a RL-WEEKTOP"] = _tensorise(a[a.rk <= K], sessions, "ret5", False)
    v = el[el.advrk <= 500].copy(); v["rk"] = v.groupby("sidx")["vol20"].rank(ascending=False, method="first")
    U["D2b RL-VOLTOP"] = _tensorise(v[v.rk <= K], sessions, "vol20", False)
    lz = el[el.advrk <= 1000].copy(); lz["rk"] = lz.groupby("sidx")["r0"].rank(ascending=True, method="first")
    U["D2c RL-LOSERS"] = _tensorise(lz[lz.rk <= K], sessions, "r0", True)
    # live night rule pool (for the D2c overlap): day ret <= -8%, IBS < .10, $5..$2000, ADV >= $10M, vol20 >= .60
    live = el[(el.r0 <= -0.08) & (el.ibs < 0.10) & (el.closeunadj <= 2000) & (el.vol20 >= 0.60)]
    U["_live"] = live.groupby("sidx").size()
    U["_live_codes"] = set(zip(live.sidx, live.code))
    U["_live_top1000"] = set(zip(live.sidx[live.advrk <= 1000], live.code[live.advrk <= 1000]))
    del el
    e = _next_ret(load_etfs(SECTORS), sessions)
    e = e[(e.pos >= 20) & np.isfinite(e[["r0", "r1", "r2", "r3", "r4", "vol20", "ibs"]]).all(axis=1) & (e.date <= JUDGE_END)].copy()
    e["slot"] = e.ticker.map({t: i for i, t in enumerate(SECTORS)})
    U["D2d RL-SECTORS"] = _tensorise(e, sessions, "slot", True)
    spy = e[e.ticker == "SPY"].set_index("sidx")["nxt"]
    U["_spy"] = spy
    U["_sessions"] = sessions
    say(f"[prep] done {time.time()-t0:.0f}s")
    return U


# ---------------------------------------------------------------- env helpers
def match_prev(C: np.ndarray) -> np.ndarray:
    """M[d, j] = slot index on day d-1 holding the same code as slot j on day d, or -1."""
    M = np.full(C.shape, -1, np.int64)
    for d in range(1, len(C)):
        prev = {c: k for k, c in enumerate(C[d - 1])}
        M[d] = [prev.get(c, -1) for c in C[d]]
    return M


def carry(w_prev: np.ndarray, m: np.ndarray):
    """Drifted weights from yesterday's slots (w_prev [K]) into today's slots via match m. Returns w_in [K], out_w."""
    w_in = np.where(m >= 0, w_prev[np.maximum(m, 0)], 0.0)
    return w_in, float(w_prev.sum() - w_in.sum())


def obs_np(Z: np.ndarray, w_in: np.ndarray, cash: float, out_w: float):
    """Z [K,NF] normalised. Returns slot inputs [K, 2*(NF+1)+2] and global inputs [NF+1+2]."""
    x = np.concatenate([Z, w_in[:, None]], 1)
    pool = x.mean(0)
    gl = np.concatenate([pool, [cash, out_w]])
    si = np.concatenate([x, np.broadcast_to(gl, (K, gl.size))], 1)
    return si.astype(np.float32), gl.astype(np.float32)


SI_DIM = 2 * (NF + 1) + 2
GL_DIM = NF + 1 + 2


def build_nets(torch):
    nn = torch.nn

    def mlp(inp, gain):
        m = nn.Sequential(nn.Linear(inp, 64), nn.Tanh(), nn.Linear(64, 64), nn.Tanh(), nn.Linear(64, 1))
        for j, layer in enumerate([m[0], m[2], m[4]]):
            nn.init.orthogonal_(layer.weight, gain=(math.sqrt(2) if j < 2 else gain))
            nn.init.zeros_(layer.bias)
        return m

    return mlp(SI_DIM, 0.01), mlp(GL_DIM, 0.01), mlp(GL_DIM, 1.0), nn.Parameter(torch.zeros(2))


def np_mlp(sd):
    a = lambda x: np.asarray(x.detach().numpy() if hasattr(x, "detach") else x, np.float64)
    W = [(a(sd[f"{j}.weight"]), a(sd[f"{j}.bias"])) for j in (0, 2, 4)]

    def f(x):
        h = np.tanh(x @ W[0][0].T + W[0][1]); h = np.tanh(h @ W[1][0].T + W[1][1])
        return h @ W[2][0].T + W[2][1]
    return f


def softmax(x):
    x = x - x.max(); e = np.exp(x); return e / e.sum()


def train(job: dict) -> dict:
    import torch
    torch.set_num_threads(1)
    seed, shift, steps, cost = job["seed"], job["shift"], job["steps"], job["cost"]
    Z, E, M, lo, hi = job["Z"], job["E"], job["M"], job["lo"], job["hi"]   # decisions lo..hi earn E[i]
    torch.manual_seed(seed)
    rng = np.random.default_rng(1000 * seed + 7 + shift + job["uid"])
    Ef = E[lo:hi + 1].copy()
    if shift:
        Ef = np.roll(Ef, -shift, axis=0)
    sc, ch, vf, log_std = build_nets(torch)
    params = list(sc.parameters()) + list(ch.parameters()) + list(vf.parameters()) + [log_std]
    opt = torch.optim.Adam(params, lr=LR, eps=1e-5)
    LOG2PI = math.log(2 * math.pi)

    def reset():
        return int(rng.integers(lo, hi - EP_LEN + 2)), 0, np.zeros(K), 1.0

    i, t_ep, w_prev, cash = reset()
    n_upd = math.ceil(steps / N_STEPS)
    for _ in range(n_upd):
        fs, fc, fv = np_mlp(sc.state_dict()), np_mlp(ch.state_dict()), np_mlp(vf.state_dict())
        ls = log_std.detach().numpy().astype(np.float64); std = np.exp(np.r_[np.full(K, ls[0]), ls[1]])
        lsv = np.r_[np.full(K, ls[0]), ls[1]]
        SI = np.zeros((N_STEPS, K, SI_DIM), np.float32); GL = np.zeros((N_STEPS, GL_DIM), np.float32)
        A = np.zeros((N_STEPS, K + 1), np.float32); LP = np.zeros(N_STEPS, np.float32)
        V = np.zeros(N_STEPS + 1, np.float32); Rw = np.zeros(N_STEPS, np.float32); Dn = np.zeros(N_STEPS, np.float32)
        for k in range(N_STEPS):
            w_in, out_w = carry(w_prev, M[i]) if t_ep > 0 else (np.zeros(K), 0.0)
            si, gl = obs_np(Z[i], w_in, cash, out_w)
            mu = np.r_[fs(si)[:, 0], fc(gl)[0]]
            v = fv(gl)[0]
            a = mu + std * rng.standard_normal(K + 1)
            lp = float((-((a - mu) ** 2) / (2 * std ** 2) - lsv - 0.5 * LOG2PI).sum())
            wn = softmax(a)
            r = Ef[i - lo]
            to = np.abs(wn[:K] - w_in).sum() + out_w
            net = float(wn[:K] @ r) - cost * to
            SI[k] = si; GL[k] = gl; A[k] = a; LP[k] = lp; V[k] = v; Rw[k] = math.log1p(max(net, -0.999))
            g = wn[:K] * (1 + r); tot = g.sum() + wn[K]
            w_prev, cash = g / tot, wn[K] / tot
            i += 1; t_ep += 1
            if t_ep >= EP_LEN:
                Dn[k] = 1.0
                i, t_ep, w_prev, cash = reset()
        w_in, out_w = carry(w_prev, M[i]) if t_ep > 0 else (np.zeros(K), 0.0)
        V[N_STEPS] = fv(obs_np(Z[i], w_in, cash, out_w)[1])[0]
        adv = np.zeros(N_STEPS, np.float32); last = 0.0
        for k in reversed(range(N_STEPS)):
            nt = 1.0 - Dn[k]
            delta = Rw[k] + GAMMA * V[k + 1] * nt - V[k]
            last = delta + GAMMA * LAM * nt * last
            adv[k] = last
        ret = adv + V[:N_STEPS]
        SIt, GLt, At, LPt = map(torch.from_numpy, (SI, GL, A, LP))
        ADt, RTt = torch.from_numpy(adv), torch.from_numpy(ret)
        for _ep in range(N_EPOCHS):
            perm = torch.from_numpy(rng.permutation(N_STEPS))
            for bb in range(0, N_STEPS, MB):
                idx = perm[bb:bb + MB]
                mu = torch.cat([sc(SIt[idx]).squeeze(-1), ch(GLt[idx])], 1)
                v = vf(GLt[idx]).squeeze(-1)
                lsf = torch.cat([log_std[:1].expand(K), log_std[1:]])
                lp = (-((At[idx] - mu) ** 2) / (2 * lsf.exp() ** 2) - lsf - 0.5 * LOG2PI).sum(-1)
                ad = ADt[idx]; ad = (ad - ad.mean()) / (ad.std() + 1e-8)
                ratio = (lp - LPt[idx]).exp()
                pl = -torch.min(ratio * ad, ratio.clamp(1 - CLIP, 1 + CLIP) * ad).mean()
                vl = ((RTt[idx] - v) ** 2).mean()
                ent = (lsf + 0.5 * math.log(2 * math.pi * math.e)).sum()
                loss = pl + VF_COEF * vl - ENT_COEF * ent
                opt.zero_grad(); loss.backward()
                torch.nn.utils.clip_grad_norm_(params, MAX_GN); opt.step()
    sd = lambda m: {k: v.detach().numpy().copy() for k, v in m.state_dict().items()}
    return {"uid": job["uid"], "seed": seed, "shift": shift, "sc": sd(sc), "ch": sd(ch)}


def run_policy(pol: dict, Z, E, M, idx):
    fs, fc = np_mlp(pol["sc"]), np_mlp(pol["ch"])
    w_prev, cash = np.zeros(K), 1.0
    G, T, CW = [], [], []
    for n, i in enumerate(idx):
        w_in, out_w = carry(w_prev, M[i]) if n > 0 else (np.zeros(K), 0.0)
        si, gl = obs_np(Z[i], w_in, cash, out_w)
        wn = softmax(np.r_[fs(si.astype(np.float64))[:, 0], fc(gl.astype(np.float64))[0]])
        r = E[i]
        T.append(np.abs(wn[:K] - w_in).sum() + out_w); G.append(float(wn[:K] @ r)); CW.append(wn[K])
        g = wn[:K] * (1 + r); tot = g.sum() + wn[K]
        w_prev, cash = g / tot, wn[K] / tot
    return np.array(G), np.array(T), np.array(CW)


def run_weights(pol, Z, E, M, idx):
    """Slot weights per decision (for the D2c overlap)."""
    fs, fc = np_mlp(pol["sc"]), np_mlp(pol["ch"])
    w_prev, cash = np.zeros(K), 1.0; W = []
    for n, i in enumerate(idx):
        w_in, out_w = carry(w_prev, M[i]) if n > 0 else (np.zeros(K), 0.0)
        si, gl = obs_np(Z[i], w_in, cash, out_w)
        wn = softmax(np.r_[fs(si.astype(np.float64))[:, 0], fc(gl.astype(np.float64))[0]]); W.append(wn[:K])
        g = wn[:K] * (1 + E[i]); tot = g.sum() + wn[K]; w_prev, cash = g / tot, wn[K] / tot
    return np.array(W)


def evaluate(G, T, CW, B, S, dates, cost):
    net = G - cost * T
    a, t, beta = ols_alpha(net, B)
    h1 = dates.year <= 2015
    a1 = ols_alpha(net[h1], B[h1])[0]; a2 = ols_alpha(net[~h1], B[~h1])[0]
    hedged = net - beta * B
    keep = np.ones(len(net), bool); keep[np.argsort(hedged)[-5:]] = False
    ax5 = ols_alpha(net[keep], B[keep])[0]
    aS, tS, bS = ols_alpha(net, S)
    return dict(a=a, t=t, beta=beta, a1=a1, a2=a2, sh=sharpe(net), shb=sharpe(B), ax5=ax5, mdd=maxdd(net),
                hit=(net > 0).mean(), med=np.median(net), to=T.mean(), cash=CW.mean(), mean=net.mean(),
                aS=aS, tS=tS, bS=bS, dsr=dsr(hedged, N_TRIALS))


def fmt(tag, e):
    return (f"{tag:<9} alpha {e['a']*1e4:+6.2f}bp/d t {e['t']:+5.2f} b {e['beta']:.2f} | 11-15 {e['a1']*1e4:+6.2f} "
            f"16-20 {e['a2']*1e4:+6.2f} | Sh {e['sh']:.2f} vs EW {e['shb']:.2f} (d {e['sh']-e['shb']:+.2f}) | "
            f"ex-top5 {e['ax5']*1e4:+6.2f} | mean {e['mean']*1e4:+5.1f} med {e['med']*1e4:+5.1f}bp hit {e['hit']*100:4.1f}% "
            f"maxDD {e['mdd']*100:5.1f}% | cash {e['cash']:.2f} TO {e['to']:.3f}/d | vs SPY a {e['aS']*1e4:+6.2f} "
            f"t {e['tS']:+5.2f} b {e['bS']:.2f}")


# ---------------------------------------------------------------- main
def get_universes():
    import pickle
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / "universes.pkl"
    if f.exists():
        return pickle.loads(f.read_bytes())
    U = prep()
    f.write_bytes(pickle.dumps(U))
    return U


def setup(U, name):
    u = U[name]
    dates = pd.DatetimeIndex(u["dates"])
    fit = (dates >= FIT_START) & (dates <= FIT_END)
    sess = U["_sessions"]
    nxt_date = pd.DatetimeIndex(sess[np.minimum(u["sidx"] + 1, len(sess) - 1)])
    lo = int(np.argmax(fit)); hi = int(np.where(fit & (nxt_date <= FIT_END))[0][-1])
    X = u["X"].copy()
    mu = X[lo:hi + 1].reshape(-1, NF).mean(0); sd = X[lo:hi + 1].reshape(-1, NF).std(0)
    mu[-1], sd[-1] = 0.0, 1.0                                           # rank stays in [0, 1]
    Z = np.clip((X - mu) / sd, -ZCLIP, ZCLIP)
    J = np.where((dates >= JUDGE_START) & (nxt_date <= JUDGE_END) & (u["sidx"] + 1 < len(sess)))[0]
    # consecutive-session check: slot day d must be the session after day d-1 for the carry match to be meaningful
    M = match_prev(u["C"])
    gapday = np.r_[True, np.diff(u["sidx"]) != 1]
    M[gapday] = -1
    return dict(Z=Z, E=u["E"], M=M, lo=lo, hi=hi, J=J, dates=dates, nxt=nxt_date, gapdays=int(gapday[1:].sum()))


def main():
    t0 = time.time()
    if "--prep" in sys.argv:
        U = get_universes()
        for name in UNIV:
            u = U[name]; s = setup(U, name)
            fitm = u["miss"][s["lo"]:s["hi"] + 1]
            say(f"[prep] {name}: decision days {len(u['dates'])} ({u['dates'][0]}..{u['dates'][-1]}), fit lo..hi "
                f"{s['dates'][s['lo']].date()}..{s['dates'][s['hi']].date()}, judge days {len(s['J'])}, non-consecutive days "
                f"{s['gapdays']}; FIT missing-next: gap {(fitm == 1).mean()*100:.3f}% no-later-bar {(fitm == 2).mean()*100:.3f}%; "
                f"FIT |earned|>50%: {(np.abs(u['E'][s['lo']:s['hi']+1]) > 0.5).sum()}")
        return
    U = get_universes()
    S_all = U["_spy"]
    if "--timing" in sys.argv:
        n = int(sys.argv[sys.argv.index("--timing") + 1]); s = setup(U, "D2a RL-WEEKTOP"); t1 = time.time()
        train(dict(uid=0, seed=0, shift=0, steps=n, cost=2.5e-4, **{k: s[k] for k in ("Z", "E", "M", "lo", "hi")}))
        print(f"timing: {n} steps in {time.time()-t1:.1f}s"); return

    say(f"EXP round 2 D2a-D2d RL-UNIVERSE (N 1219-1222), program N {N_TRIALS}. FIT {FIT_START}..{FIT_END}, "
        f"JUDGE {JUDGE_START}..{JUDGE_END}. No REPORT period: Sharadar SEP ends 2021-01 (no 2021+ stock panel on disk).")
    say(f"PPO {TOTAL_STEPS:,} steps/policy, 5 seeds + {N_PLACEBO_DRAWS} placebo draws x 5 seeds per universe; torch CPU "
        f"(MPS available but unused: 64-row minibatches are faster on CPU)")
    setups, jobs = {}, []
    for uid, (name, (N, cost, shock)) in enumerate(UNIV.items()):
        s = setup(U, name); setups[name] = s
        rng = np.random.default_rng(N)
        s["shifts"] = [int(k) for k in rng.integers(250, 2001, N_PLACEBO_DRAWS)]
        base = dict(uid=uid, steps=TOTAL_STEPS, cost=cost, **{k: s[k] for k in ("Z", "E", "M", "lo", "hi")})
        jobs += [dict(base, seed=sd, shift=0) for sd in SEEDS]
        jobs += [dict(base, seed=sd, shift=k) for k in s["shifts"] for sd in SEEDS]
    nproc = int(os.environ.get("EXP_RLU_PROCS", 9))
    import pickle
    rf = CACHE / f"policies_{TOTAL_STEPS}.pkl"
    if rf.exists():
        res = pickle.loads(rf.read_bytes())
    else:
        with mp.get_context("spawn").Pool(nproc) as pool:
            res = pool.map(train, jobs, chunksize=1)
        rf.write_bytes(pickle.dumps(res))
    t_train = time.time() - t0
    say(f"trained {len(res)} policies in {t_train/60:.1f} min on {nproc} processes")

    for uid, (name, (N, cost, shock)) in enumerate(UNIV.items()):
        s = setups[name]; u = U[name]; J = s["J"]; dts = s["nxt"][J]
        B = u["E"][J].mean(1)
        Sx = S_all.reindex(u["sidx"][J]).to_numpy(float)
        assert np.isfinite(Sx).all()
        # EW basket turnover (daily rebalanced to 1/K over the new slots), for the cost-charged reference only
        to_ew = []
        for n, i in enumerate(J):
            if n == 0:
                to_ew.append(1.0); continue
            wp = (1 + u["E"][J[n - 1]]) / K; wp = wp / wp.sum()
            w_in, out_w = carry(wp, s["M"][i]); to_ew.append(np.abs(1 / K - w_in).sum() + out_w)
        to_ew = np.array(to_ew)
        jm = u["miss"][J]
        say(f"\n=== {name} (N {N}) cost {cost*1e4:.1f}bp/side, shock {shock*1e4:.1f}bp/side; judge {dts[0].date()}..{dts[-1].date()} "
            f"n {len(J)}")
        say(f"  missing next-day bar in judge slots: gap {(jm == 1).sum()} ({(jm == 1).mean()*100:.3f}%), no later bar "
            f"(delisted) {(jm == 2).sum()} ({(jm == 2).mean()*100:.3f}%) -> earned 0; non-consecutive slot days {s['gapdays']}")
        aSB = ols_alpha(B, Sx)
        say(f"  EW basket (costless benchmark): mean {B.mean()*1e4:+.2f}bp/d Sh {sharpe(B):.2f} maxDD {maxdd(B)*100:.1f}% | "
            f"vs SPY a {aSB[0]*1e4:+.2f} t {aSB[1]:+.2f} b {aSB[2]:.2f} | EW TO {to_ew.mean():.3f}/d -> EW net at {cost*1e4:.1f}bp "
            f"mean {(B - cost*to_ew).mean()*1e4:+.2f}bp/d Sh {sharpe(B - cost*to_ew):.2f}; SPY Sh {sharpe(Sx):.2f}")
        real = {r["seed"]: r for r in res if r["uid"] == uid and r["shift"] == 0}
        ev, ev3 = {}, {}
        for sd in SEEDS:
            G, T, CW = run_policy(real[sd], s["Z"], u["E"], s["M"], J)
            ev[sd] = evaluate(G, T, CW, B, Sx, dts, cost); ev3[sd] = evaluate(G, T, CW, B, Sx, dts, shock)
        order = sorted(SEEDS, key=lambda q: ev[q]["a"]); med = order[2]
        for sd in SEEDS:
            say(("*" if sd == med else " ") + fmt(f"seed {sd}", ev[sd]))
            say(f"    shock {shock*1e4:.0f}bp: alpha {ev3[sd]['a']*1e4:+6.2f} t {ev3[sd]['t']:+5.2f} | DSR {ev[sd]['dsr']:.3f}")
        plac = []
        for r in res:
            if r["uid"] == uid and r["shift"]:
                G, T, CW = run_policy(r, s["Z"], u["E"], s["M"], J)
                plac.append(ols_alpha(G - cost * T, B)[0])
        plac = np.array(plac); p95 = np.percentile(plac, 95); em, em3 = ev[med], ev3[med]
        pct = (plac < em["a"]).mean() * 100
        say(f"  placebo ({len(plac)} policies, shifts {s['shifts']}): alpha median {np.median(plac)*1e4:+.2f}, 95th "
            f"{p95*1e4:+.2f}, max {plac.max()*1e4:+.2f}; seed-median {em['a']*1e4:+.2f} at pct {pct:.0f}")
        g123 = {sd: (ev[sd]["a"] > 0 and ev[sd]["t"] >= 2, ev[sd]["a1"] > 0 and ev[sd]["a2"] > 0,
                     ev[sd]["sh"] - ev[sd]["shb"] >= 0.20) for sd in SEEDS}
        n_pass = sum(all(g) for g in g123.values())
        gates = [
            ("1 a>0&t>=2", sum(g[0] for g in g123.values()) >= 4, sum(g[0] for g in g123.values())),
            ("2 both halves", sum(g[1] for g in g123.values()) >= 4, sum(g[1] for g in g123.values())),
            ("3 dSh>=.20", sum(g[2] for g in g123.values()) >= 4, sum(g[2] for g in g123.values())),
            (f"4 med {shock*1e4:.0f}bp a>0&t>=2", em3["a"] > 0 and em3["t"] >= 2, None),
            ("5 med >= placebo 95th", em["a"] >= p95, None),
            ("6 med ex-top5>0", em["ax5"] > 0, None),
        ]
        say("  GATES: " + " | ".join(f"{g}: {'PASS' if p else 'FAIL'}" + (f" ({c}/5)" if c is not None else "")
                                     for g, p, c in gates) + f" | seeds passing all 1-3: {n_pass}/5")
        verdict = "PASS" if (n_pass >= 4 and all(p for _, p, _ in gates[3:])) else "FAIL"
        say(f"  VERDICT {name} (N {N}): {verdict}  (seed-median DSR at N {N_TRIALS}: {em['dsr']:.3f})")
        if name.startswith("D2c"):
            live_c = U["_live_codes"]; live_t = U["_live_top1000"]
            ins = np.array([[(u["sidx"][i], c) in live_c for c in u["C"][i]] for i in J])
            dr = u["r0"][J] <= -0.08
            covered = np.array([sum((u["sidx"][i], c) in live_t for c in u["C"][i]) for i in J])
            n_live_top = pd.Series([sx for sx, _ in live_t]).value_counts().reindex(u["sidx"][J]).fillna(0).to_numpy()
            Wm = run_weights(real[med], s["Z"], u["E"], s["M"], J)
            say(f"  overlap with the live night rule: slots with day ret <= -8%: {dr.mean()*100:.1f}% of slot-days "
                f"(days with all 10 <= -8%: {(dr.all(1)).mean()*100:.1f}%); slots meeting the full live rule (<= -8%, IBS<.10, "
                f"$5-2000, ADV>=$10M, vol20>=.60): {ins.mean()*100:.1f}%; live-rule names in the top 1000 that are in a D2c "
                f"slot: {covered.sum() / max(n_live_top.sum(), 1)*100:.1f}% ({int(covered.sum())}/{int(n_live_top.sum())}); "
                f"seed-median agent weight on <= -8% slots {(Wm * dr).sum() / Wm.sum()*100:.1f}% of its stock weight")
    say("\nreadings/deviations: total return = SEP/SFP split-adj close + ACTIONS cash dividends; missing next bar -> earned 0 "
        "(no delisting return; biases the basket and agent alike, upward if delists are losers); cash earns 0; EW benchmark "
        "costless (gates); 'day return' = close/prev close (live night definition), so it duplicates r(t); fixed D2d slots get "
        "rank = slot position; features z-scored on fit-period slots, clipped +-5; ENT_COEF 0 = D1/SB3 default; seed-median = "
        "3rd of 5 by judge alpha; gate 4 = seed-median alpha > 0 with t >= 2 at the shock cost; placebo = 15 shifted-label "
        "policies per universe (pre-reg minimum), 95th pct of 15; held names that leave the slots are sold at t's close "
        "(turnover); first judge day starts from cash.")
    say(f"runtime: train {t_train/60:.1f} min, total {(time.time()-t0)/60:.1f} min")
    OUT.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
