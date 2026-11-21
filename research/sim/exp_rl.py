"""EXP D1 RL-ALLOC (N 1216): does a PPO agent allocating SPY/QQQ/TLT/XLU/cash beat a 60/40 SPY/TLT book?

Pre-registration: research/drafts/round1_prose.md, "## Amendment - EXP round (user 2026-11-20 ...)", Common frame +
bullet D1 RL-ALLOC (N 1216). Frozen before any outcome was read; nothing here is tuned on 2011-20.

Frame
  data    Sharadar SFP (data/research/nx/cache_SFP.parquet), split-adjusted close + cash dividends from cache_ACTIONS
          -> total-return close-to-close. REPORT 2021-01..2026-09 on Alpaca etf_daily.parquet (split/div-adjusted).
  obs     last 20 daily returns of SPY QQQ IWM TLT XLK XLF XLE XLU (each / its fit-period sd) + current drifted weights (5).
  action  5 Gaussian logits -> softmax over {SPY, QQQ, TLT, XLU, cash}: long-only, sums to 1 (gross <= 1.0).
  timing  decide at t's close with data through t; earn t -> t+1 close-to-close; cost 1bp/side per unit turnover on the
          4 ETFs (cash free); shock 3bp/side (same frozen weights). Cash earns 0 (no T-bill credit: conservative).
  reward  log(1 + net return).
  train   FIT 2002-08..2010-12 only: random 252-session episodes, PPO (SB3-default hyperparameters, minimal torch
          implementation), 2x64 tanh MLPs, 5 seeds. Placebo: same pipeline with the fit-period earned returns circularly
          shifted by k ~ U{250..2000} sessions (observations unshifted), 5 draws x 5 seeds.
  judge   frozen deterministic policies (softmax of mean logits) run 2011-01..2020-12 vs 60/40 SPY/TLT rebalanced daily
          (benchmark charged no cost: conservative). Gates 1-6 of the Common frame with SPY -> 60/40.

    PYTHONPATH=. python3 research/sim/exp_rl.py            # -> research/sim/exp_rl_out.txt
    PYTHONPATH=. python3 research/sim/exp_rl.py --timing N # trains one policy for N steps, prints only the time
"""
from __future__ import annotations

import math
import multiprocessing as mp
import pathlib
import sys
import time

import numpy as np
import pandas as pd
import scipy.stats as SS

ROOT = pathlib.Path(__file__).resolve().parents[2]
SFP = ROOT / "data/research/nx/cache_SFP.parquet"
ACT = ROOT / "data/research/nx/cache_ACTIONS.parquet"
ALP = ROOT / "data/research/night/etf_daily.parquet"
OUT = ROOT / "research/sim/exp_rl_out.txt"

OBS_ETF = ["SPY", "QQQ", "IWM", "TLT", "XLK", "XLF", "XLE", "XLU"]
TRADE = ["SPY", "QQQ", "TLT", "XLU"]          # + cash
LOOK = 20
EP_LEN = 252
FIT_START, FIT_END = "2002-08-01", "2010-12-31"
JUDGE_START, JUDGE_END = "2011-01-01", "2020-12-31"
REP_START, REP_END = "2021-01-01", "2026-10-31"
COST, SHOCK = 1e-4, 3e-4
N_TRIALS = 1218
SEEDS = [0, 1, 2, 3, 4]
N_PLACEBO_DRAWS = 5
TOTAL_STEPS = 1_000_000
NW_LAGS = 5
# PPO (stable-baselines3 defaults)
LR, GAMMA, LAM, CLIP, N_STEPS, N_EPOCHS, MB = 3e-4, 0.99, 0.95, 0.2, 2048, 10, 64
VF_COEF, ENT_COEF, MAX_GN = 0.5, 0.0, 0.5

lines: list[str] = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    lines.append(s)


# ---------------------------------------------------------------- data
def load_sharadar() -> pd.DataFrame:
    d = pd.read_parquet(SFP, columns=["ticker", "date", "close", "closeunadj"])
    d = d[d.ticker.isin(OBS_ETF)].copy()
    d["date"] = pd.to_datetime(d["date"])
    a = pd.read_parquet(ACT, columns=["date", "action", "ticker", "value"])
    a = a[(a.action == "dividend") & a.ticker.isin(OBS_ETF)].copy()
    a["date"] = pd.to_datetime(a["date"])
    a = a.groupby(["ticker", "date"])["value"].sum().rename("div").reset_index()
    d = d.merge(a, on=["ticker", "date"], how="left").fillna({"div": 0.0})
    d["divadj"] = d["div"] * d["close"] / d["closeunadj"]          # raw cash -> split-adjusted units
    c = d.pivot(index="date", columns="ticker", values="close")[OBS_ETF].sort_index()
    dv = d.pivot(index="date", columns="ticker", values="divadj")[OBS_ETF].reindex(c.index).fillna(0.0)
    r = (c + dv) / c.shift(1) - 1
    r = r[r.index >= "2002-07-31"].dropna()                          # TLT listed 2002-07-30
    return r


def load_alpaca() -> pd.DataFrame:
    e = pd.read_parquet(ALP, columns=["symbol", "timestamp", "close"])
    e = e[e.symbol.isin(OBS_ETF)].copy()
    e["date"] = pd.to_datetime(e.timestamp.dt.tz_convert("America/New_York").dt.date)
    c = e.pivot(index="date", columns="symbol", values="close")[OBS_ETF].sort_index()
    return (c / c.shift(1) - 1).dropna()


# ---------------------------------------------------------------- env / policy
def make_obs(Z: np.ndarray, i: int, w: np.ndarray) -> np.ndarray:
    return np.concatenate([Z[i - LOOK + 1:i + 1].ravel(), w]).astype(np.float32)


def drift(w: np.ndarray, r4: np.ndarray) -> np.ndarray:
    g = np.append(1 + r4, 1.0) * w
    return g / g.sum()


def softmax(x: np.ndarray) -> np.ndarray:
    x = x - x.max()
    e = np.exp(x)
    return e / e.sum()


def build_nets(torch, obs_dim: int):
    nn = torch.nn

    def mlp(out, gain):
        m = nn.Sequential(nn.Linear(obs_dim, 64), nn.Tanh(), nn.Linear(64, 64), nn.Tanh(), nn.Linear(64, out))
        for j, layer in enumerate([m[0], m[2], m[4]]):
            nn.init.orthogonal_(layer.weight, gain=(math.sqrt(2) if j < 2 else gain))
            nn.init.zeros_(layer.bias)
        return m

    pi = mlp(5, 0.01)
    vf = mlp(1, 1.0)
    log_std = nn.Parameter(torch.zeros(5))
    return pi, vf, log_std


def train(job: dict) -> dict:
    """Train one PPO policy on the fit period. job: seed, shift (0 = real), steps, Z, R4, lo, hi."""
    import torch
    torch.set_num_threads(1)
    seed, shift, steps = job["seed"], job["shift"], job["steps"]
    Z, R4, lo, hi = job["Z"], job["R4"], job["lo"], job["hi"]   # decision indices lo..hi (earn R4[i+1])
    torch.manual_seed(seed)
    rng = np.random.default_rng(1000 * seed + 7 + shift)
    # earned-return array per decision index in the fit range, optionally circularly shifted (placebo)
    E = R4[lo + 1:hi + 2].copy()
    if shift:
        E = np.roll(E, -shift, axis=0)

    pi, vf, log_std = build_nets(torch, LOOK * 8 + 5)
    params = list(pi.parameters()) + list(vf.parameters()) + [log_std]
    opt = torch.optim.Adam(params, lr=LR, eps=1e-5)

    def reset():
        s = int(rng.integers(lo, hi - EP_LEN + 2))
        return s, 0, np.array([0, 0, 0, 0, 1.0])

    i, t_ep, w = reset()
    od = LOOK * 8 + 5
    n_upd = math.ceil(steps / N_STEPS)
    for _ in range(n_upd):
        O = np.zeros((N_STEPS, od), np.float32); A = np.zeros((N_STEPS, 5), np.float32)
        LP = np.zeros(N_STEPS, np.float32); V = np.zeros(N_STEPS + 1, np.float32)
        Rw = np.zeros(N_STEPS, np.float32); D = np.zeros(N_STEPS, np.float32)
        for k in range(N_STEPS):
            o = make_obs(Z, i, w)
            with torch.no_grad():
                ot = torch.from_numpy(o)
                mu = pi(ot); v = vf(ot)[0]
                std = log_std.exp()
                a = mu + std * torch.randn(5)
                lp = (-((a - mu) ** 2) / (2 * std ** 2) - log_std - 0.5 * math.log(2 * math.pi)).sum()
            an = a.numpy()
            wn = softmax(an.astype(np.float64))
            r4 = E[i - lo]
            to = np.abs(wn[:4] - w[:4]).sum()
            net = float(wn[:4] @ r4) - COST * to
            O[k] = o; A[k] = an; LP[k] = lp.item(); V[k] = v.item(); Rw[k] = math.log1p(net)
            w = drift(wn, r4); i += 1; t_ep += 1
            if t_ep >= EP_LEN:
                D[k] = 1.0
                i, t_ep, w = reset()
        with torch.no_grad():
            V[N_STEPS] = vf(torch.from_numpy(make_obs(Z, i, w)))[0].item()
        adv = np.zeros(N_STEPS, np.float32); last = 0.0
        for k in reversed(range(N_STEPS)):
            nonterm = 1.0 - D[k]
            delta = Rw[k] + GAMMA * V[k + 1] * nonterm - V[k]
            last = delta + GAMMA * LAM * nonterm * last
            adv[k] = last
        ret = adv + V[:N_STEPS]
        Ot, At, LPt = torch.from_numpy(O), torch.from_numpy(A), torch.from_numpy(LP)
        ADt, RTt = torch.from_numpy(adv), torch.from_numpy(ret)
        for _ep in range(N_EPOCHS):
            perm = torch.from_numpy(rng.permutation(N_STEPS))
            for b in range(0, N_STEPS, MB):
                idx = perm[b:b + MB]
                mu = pi(Ot[idx]); v = vf(Ot[idx]).squeeze(-1)
                lp = (-((At[idx] - mu) ** 2) / (2 * log_std.exp() ** 2) - log_std - 0.5 * math.log(2 * math.pi)).sum(-1)
                ad = ADt[idx]; ad = (ad - ad.mean()) / (ad.std() + 1e-8)
                ratio = (lp - LPt[idx]).exp()
                pl = -torch.min(ratio * ad, ratio.clamp(1 - CLIP, 1 + CLIP) * ad).mean()
                vl = ((RTt[idx] - v) ** 2).mean()
                ent = (log_std + 0.5 * math.log(2 * math.pi * math.e)).sum()
                loss = pl + VF_COEF * vl - ENT_COEF * ent
                opt.zero_grad(); loss.backward()
                torch.nn.utils.clip_grad_norm_(params, MAX_GN); opt.step()
    sd = {k: v.detach().numpy().copy() for k, v in pi.state_dict().items()}
    return {"seed": seed, "shift": shift, "pi": sd, "log_std": log_std.detach().numpy().copy()}


def run_policy(pi_sd: dict, Z: np.ndarray, R4: np.ndarray, idx: np.ndarray):
    """Deterministic frozen policy over decision indices idx. Returns gross ret, turnover, weights (per decision)."""
    Ws = [(pi_sd["0.weight"], pi_sd["0.bias"]), (pi_sd["2.weight"], pi_sd["2.bias"]), (pi_sd["4.weight"], pi_sd["4.bias"])]

    def fwd(o):
        h = np.tanh(Ws[0][0] @ o + Ws[0][1]); h = np.tanh(Ws[1][0] @ h + Ws[1][1])
        return Ws[2][0] @ h + Ws[2][1]

    w = np.array([0, 0, 0, 0, 1.0]); G, T, W = [], [], []
    for i in idx:
        wn = softmax(fwd(make_obs(Z, i, w).astype(np.float64)))
        r4 = R4[i + 1]
        T.append(np.abs(wn[:4] - w[:4]).sum()); G.append(float(wn[:4] @ r4)); W.append(wn)
        w = drift(wn, r4)
    return np.array(G), np.array(T), np.array(W)


# ---------------------------------------------------------------- stats
def ols_alpha(y, x, lags=NW_LAGS):
    y = np.asarray(y, float); X = np.column_stack([np.ones(len(y)), np.asarray(x, float)])
    XtX_inv = np.linalg.inv(X.T @ X); b = XtX_inv @ X.T @ y; u = y - X @ b
    Xu = X * u[:, None]; S = Xu.T @ Xu
    for L in range(1, lags + 1):
        G = Xu[L:].T @ Xu[:-L]; S += (1 - L / (lags + 1)) * (G + G.T)
    V = XtX_inv @ S @ XtX_inv
    return b[0], b[0] / math.sqrt(V[0, 0]), b[1]


def sharpe(x):
    x = np.asarray(x, float)
    return x.mean() / x.std(ddof=1) * math.sqrt(252)


def maxdd(x):
    eq = np.cumprod(1 + np.asarray(x, float)); return float((eq / np.maximum.accumulate(eq) - 1).min())


def dsr(x, n_trials):
    x = np.asarray(x, float); T = len(x)
    sr = x.mean() / x.std(ddof=1); sk = SS.skew(x); ku = SS.kurtosis(x, fisher=False); g = 0.5772156649
    sr0 = math.sqrt(1.0 / T) * ((1 - g) * SS.norm.ppf(1 - 1 / n_trials) + g * SS.norm.ppf(1 - 1 / (n_trials * math.e)))
    z = (sr - sr0) * math.sqrt(T - 1) / math.sqrt(max(1e-12, 1 - sk * sr + (ku - 1) / 4 * sr ** 2))
    return float(SS.norm.cdf(z))


def evaluate(G, T, W, B, dates, cost=COST):
    net = G - cost * T
    a, t, beta = ols_alpha(net, B)
    h1 = dates.year <= 2015
    a1 = ols_alpha(net[h1], B[h1])[0]; a2 = ols_alpha(net[~h1], B[~h1])[0]
    hedged = net - beta * B
    top5 = np.argsort(hedged)[-5:]; keep = np.ones(len(net), bool); keep[top5] = False
    ax5 = ols_alpha(net[keep], B[keep])[0]
    return dict(a=a, t=t, beta=beta, a1=a1, a2=a2, sh=sharpe(net), shb=sharpe(B), ax5=ax5, mdd=maxdd(net),
                hit=(net > 0).mean(), med=np.median(net), to=T.mean(), w=W.mean(0), dsr=dsr(hedged, N_TRIALS))


def fmt(tag, e):
    w = " ".join(f"{n}{v:.2f}" for n, v in zip(["SPY", "QQQ", "TLT", "XLU", "cash"], e["w"]))
    return (f"{tag:<12} alpha {e['a']*1e4:+6.2f}bp/d t {e['t']:+5.2f} beta {e['beta']:.2f} | 11-15 {e['a1']*1e4:+6.2f} "
            f"16-20 {e['a2']*1e4:+6.2f} | Sh {e['sh']:.2f} vs 60/40 {e['shb']:.2f} (d {e['sh']-e['shb']:+.2f}) | "
            f"ex-top5 {e['ax5']*1e4:+6.2f} | maxDD {e['mdd']*100:5.1f}% hit {e['hit']*100:4.1f}% med {e['med']*1e4:+5.1f}bp "
            f"TO {e['to']:.3f}/d | w {w}")


# ---------------------------------------------------------------- main
def main():
    t0 = time.time()
    r = load_sharadar()
    fit_r = r[(r.index >= FIT_START) & (r.index <= FIT_END)]
    scale = fit_r.std().values
    Z = (r.values / scale).astype(np.float32)
    R4 = r[TRADE].values
    dates = r.index
    # decision index i earns R4[i+1]; obs needs i-19 >= 0 and the window inside the fit period
    first_fit = max(LOOK - 1, int(np.searchsorted(dates, pd.Timestamp(FIT_START))) + LOOK - 1)
    last_fit = int(np.searchsorted(dates, pd.Timestamp(FIT_END), side="right")) - 2   # date[i+1] <= FIT_END

    if len(sys.argv) > 2 and sys.argv[1] == "--timing":
        n = int(sys.argv[2]); s = time.time()
        train(dict(seed=0, shift=0, steps=n, Z=Z, R4=R4, lo=first_fit, hi=last_fit))
        print(f"timing: {n} steps in {time.time()-s:.1f}s"); return

    rng = np.random.default_rng(1216)
    shifts = [int(k) for k in rng.integers(250, 2001, N_PLACEBO_DRAWS)]
    jobs = [dict(seed=s, shift=0) for s in SEEDS] + [dict(seed=s, shift=k) for k in shifts for s in SEEDS]
    for j in jobs:
        j.update(steps=TOTAL_STEPS, Z=Z, R4=R4, lo=first_fit, hi=last_fit)
    with mp.get_context("spawn").Pool(8) as pool:
        res = pool.map(train, jobs, chunksize=1)
    t_train = time.time() - t0

    say("EXP D1 RL-ALLOC (N 1216) -- PPO allocator over {SPY,QQQ,TLT,XLU,cash} vs 60/40 SPY/TLT daily-rebalanced")
    say("pre-reg: research/drafts/round1_prose.md 'Amendment - EXP round', Common frame + D1. Program N 1218.")
    say(f"fit decisions {dates[first_fit].date()}..{dates[last_fit].date()} ({last_fit-first_fit+1} sessions); "
        f"{TOTAL_STEPS:,} PPO steps x {len(jobs)} policies (5 real + {N_PLACEBO_DRAWS}x5 placebo); placebo shifts {shifts}")
    say(f"PPO: SB3 defaults lr {LR} gamma {GAMMA} gae {LAM} clip {CLIP} n_steps {N_STEPS} epochs {N_EPOCHS} mb {MB} "
        f"vf {VF_COEF} ent {ENT_COEF} maxgn {MAX_GN}; 2x64 tanh separate pi/vf; Gaussian logits -> softmax weights")

    # judge
    jidx = np.where((dates >= JUDGE_START) & (dates <= JUDGE_END))[0] - 1           # decisions whose earned day in judge
    jd = dates[jidx + 1]
    B = 0.6 * r["SPY"].values[jidx + 1] + 0.4 * r["TLT"].values[jidx + 1]
    say(f"\nJUDGE {jd[0].date()}..{jd[-1].date()} n {len(jd)}; 60/40: mean {B.mean()*1e4:.2f}bp/d Sharpe {sharpe(B):.2f} "
        f"maxDD {maxdd(B)*100:.1f}%; SPY Sharpe {sharpe(r['SPY'].values[jidx+1]):.2f}")
    real = {x["seed"]: x for x in res if x["shift"] == 0}
    ev, ev3, runs = {}, {}, {}
    say("\nper seed, 1bp/side (alpha = OLS intercept of net on 60/40, NW t lags 5):")
    for s in SEEDS:
        G, T, W = run_policy(real[s]["pi"], Z, R4, jidx); runs[s] = (G, T, W)
        ev[s] = evaluate(G, T, W, B, jd); ev3[s] = evaluate(G, T, W, B, jd, SHOCK)
        say(fmt(f"seed {s}", ev[s]) + f" | 3bp alpha {ev3[s]['a']*1e4:+6.2f} t {ev3[s]['t']:+5.2f} | DSR {ev[s]['dsr']:.3f}")
    plac = []
    for x in res:
        if x["shift"]:
            G, T, W = run_policy(x["pi"], Z, R4, jidx); plac.append(evaluate(G, T, W, B, jd)["a"])
    plac = np.array(plac)

    g123 = {s: (ev[s]["a"] > 0 and ev[s]["t"] >= 2, ev[s]["a1"] > 0 and ev[s]["a2"] > 0,
                ev[s]["sh"] - ev[s]["shb"] >= 0.20) for s in SEEDS}
    for s in SEEDS:
        say(f"  seed {s} gates 1-3: " + " ".join("PASS" if g else "FAIL" for g in g123[s]))
    n_pass = sum(all(g) for g in g123.values())
    order = sorted(SEEDS, key=lambda s: ev[s]["a"]); med = order[2]
    em, em3 = ev[med], ev3[med]
    say(f"\nseed-median policy = seed {med} (3rd of 5 by judge alpha)")
    say(fmt(f"median s{med}", em))
    pct = (plac < em["a"]).mean() * 100; p95 = np.percentile(plac, 95)
    say(f"placebo (25 shifted-label policies) judge alpha bp/d: median {np.median(plac)*1e4:+.2f}, 95th {p95*1e4:+.2f}, "
        f"min {plac.min()*1e4:+.2f}, max {plac.max()*1e4:+.2f}; real seed-median {em['a']*1e4:+.2f} at pct {pct:.0f}; "
        f"real seeds above placebo 95th: {sum(ev[s]['a'] >= p95 for s in SEEDS)}/5")
    gates = [
        ("1 alpha>0 & NW t>=2 (>=4/5 seeds)", sum(g[0] for g in g123.values()) >= 4),
        ("2 alpha>0 both halves (>=4/5 seeds)", sum(g[1] for g in g123.values()) >= 4),
        ("3 Sharpe - 60/40 >= +0.20 (>=4/5 seeds)", sum(g[2] for g in g123.values()) >= 4),
        ("4 seed-median survives 3bp/side (alpha>0, t>=2)", em3["a"] > 0 and em3["t"] >= 2),
        ("5 seed-median alpha >= placebo 95th", em["a"] >= p95),
        ("6 seed-median ex-top-5 alpha > 0", em["ax5"] > 0),
    ]
    say(f"\nseeds passing all of gates 1-3: {n_pass}/5 (need >= 4); seed-median 3bp alpha {em3['a']*1e4:+.2f} t {em3['t']:+.2f}")
    say("GATES: " + " | ".join(f"{n}: {'PASS' if p else 'FAIL'}" for n, p in gates))
    verdict = "PASS" if (n_pass >= 4 and all(p for _, p in gates[3:])) else "FAIL"
    say(f"VERDICT D1 RL-ALLOC (N 1216): {verdict}  (DSR seed-median at N {N_TRIALS}: {em['dsr']:.3f})")

    # report 2021-26 (Alpaca, descriptive)
    ra = load_alpaca()
    Za = (ra.values / scale).astype(np.float32); R4a = ra[TRADE].values; da = ra.index
    ridx = np.where((da >= REP_START) & (da <= REP_END))[0] - 1
    rd = da[ridx + 1]
    Ba = 0.6 * ra["SPY"].values[ridx + 1] + 0.4 * ra["TLT"].values[ridx + 1]
    say(f"\nREPORT {rd[0].date()}..{rd[-1].date()} (Alpaca, descriptive, not judged) n {len(rd)}; 60/40 Sharpe {sharpe(Ba):.2f} "
        f"maxDD {maxdd(Ba)*100:.1f}%")
    for s in SEEDS:
        G, T, W = run_policy(real[s]["pi"], Za, R4a, ridx)
        net = G - COST * T; a, t, beta = ols_alpha(net, Ba)
        wv = " ".join(f"{n}{v:.2f}" for n, v in zip(["SPY", "QQQ", "TLT", "XLU", "cash"], W.mean(0)))
        say(f"{'*' if s == med else ' '}seed {s} alpha {a*1e4:+6.2f}bp/d t {t:+5.2f} beta {beta:.2f} Sh {sharpe(net):.2f} "
            f"maxDD {maxdd(net)*100:5.1f}% TO {T.mean():.3f} | w {wv}")

    say("\nreadings/deviations: total return = SFP split-adj close + ACTIONS cash dividends; cash earns 0; benchmark costless;"
        " ENT_COEF 0 (SB3/PPO-paper continuous default); 'seed-median policy' = seed ranked 3rd of 5 on judge alpha;"
        " gate 4 = 3bp alpha > 0 with t >= 2; gate 6 drops the 5 largest hedged (net - beta*60/40) days;"
        " placebo = 25 policies (not 200 draws) as D1 specifies; episodes end at 252 sessions (treated as terminal);"
        " REPORT ends at Alpaca's last bar.")
    say(f"runtime: train {t_train/60:.1f} min, total {(time.time()-t0)/60:.1f} min")
    OUT.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
