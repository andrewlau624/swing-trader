"""EXP round 3 R4-PICK (N 1229): night-pool RL picker (per-slot weights + cash) vs the live night leg.

Pre-registration: research/drafts/round1_prose.md, "## Amendment - EXP round 3: RL / linear models pointed at the book's
EXISTING edges", Common data + gates + bullet R4-PICK (N 1229). Frozen before any outcome was read; program N 1231.

Frame
  data    data/research/program/sel_night_names_primary.parquet rule=='current' (the live rule's kept names per night, in the
          live order = day_ret ascending; per = frac * gs * w is the live weight, r = close->open incl. delist handling).
          The live leg leg_current (sel_night_nights_primary.parquet) is reproduced from it first (sum per*r per night).
  slots   up to 20 per night in the live order; nights with more kept names use the first 20 (count reported). The live
          benchmark keeps ALL its names on those nights (it is the real leg).
  feats   per slot: log price, vol20, day_ret, log adv, slot rank/19, w (the pick's live tilt weight), frac (the live
          per-name fraction, which carries the pool count). z-scored on fit-period slots. IBS per pick is NOT in the file:
          left out (no new data fetched).
  action  Gaussian logits (21: 20 slots + cash, invalid slots masked) -> softmax s over valid slots + cash. Budget = gs
          (the live weekend scale, known at the decision); name i weight a_i = gs * min(s_i, 0.15 * w_i) (the live
          per-name ceiling NAME_CAP * tilt, so the live weights are inside the action set when <= 20 names and no crowd
          scaling); the clipped excess and s_cash go to cash (earns 0).
  reward  sum_i a_i r_i - 5bp * sum_i a_i (5bp round trip on gross deployed). Benchmark live net = leg_current - 5bp * sum per.
  net     permutation-equivariant: shared per-slot encoder (2x64 tanh) -> masked mean pool; slot logit from [h_i, pool],
          cash logit and value from pool; separate value encoder; one shared log_std.
  train   PPO with exp_rl.py's (SB3-default) hyperparameters, 5 seeds, episodes = 252 consecutive fit-period (2003-2012)
          slot-nights. exp_rl.py's agent is a fixed-width MLP (fixed obs dim, 5 outputs), which cannot take a variable
          slot set, so the PPO loop is re-implemented here with the same constants (imported).
  placebo same pipeline, fit-period slot returns shuffled across the valid slots within each night (labels only).
  judge   deterministic policy (softmax of mean logits), JUDGE 2013-01..2020-12; 2016-20 reported separately (touched by
          PATTERN-NIGHT); REPORT 2021-01..2026-09. Series are per session (0 on nights with no slot).

    PYTHONPATH=. python3 research/sim/exp_nightpick.py              # -> research/sim/exp_nightpick_out.txt
    PYTHONPATH=. python3 research/sim/exp_nightpick.py --timing N   # trains one policy for N steps, prints the time
"""
from __future__ import annotations

import math
import multiprocessing as mp
import pathlib
import sys
import time

import numpy as np
import pandas as pd

from research.sim.exp_rl import (CLIP, ENT_COEF, GAMMA, LAM, LR, MAX_GN, MB, N_EPOCHS, N_STEPS, VF_COEF, dsr, maxdd,
                                 sharpe)

ROOT = pathlib.Path(__file__).resolve().parents[2]
PROG = ROOT / "data/research/program"
SFP = ROOT / "data/research/nx/cache_SFP.parquet"
ALP = ROOT / "data/research/night/etf_daily.parquet"
OUT = ROOT / "research/sim/exp_nightpick_out.txt"

K = 20
NAME_CAP = 0.15
COST_RT = 5e-4
EP_LEN = 252
FIT = ("2003-01-01", "2012-12-31")
JUDGE = ("2013-01-01", "2020-12-31")
H1, H2 = ("2013-01-01", "2016-12-31"), ("2017-01-01", "2020-12-31")
TOUCH = ("2016-01-01", "2020-12-31")
REP = ("2021-01-01", "2026-09-30")
SEEDS = [0, 1, 2, 3, 4]
N_PLACEBO_DRAWS = 10          # x 5 seeds = 50 placebo policies (pre-reg common gate: 50 draws)
TOTAL_STEPS = 300_000         # cut uniformly from 1M (exp_rl default) to fit the ~2h runtime budget
N_TRIALS = 1231
NF = 7

lines: list[str] = []


def say(*a):
    s = " ".join(str(x) for x in a)
    lines.append(s)
    print(s, flush=True)


# ---------------------------------------------------------------- data
def load():
    nm = pd.read_parquet(PROG / "sel_night_names_primary.parquet")
    nm = nm[nm.rule == "current"].copy()
    nd = pd.read_parquet(PROG / "sel_night_nights_primary.parquet")[["date", "n_picks", "gs", "leg_current", "nk_current"]]
    nm["pr"] = nm["per"] * nm["r"]
    rec = nm.groupby("date")["pr"].sum()
    j = pd.concat([nd.set_index("date")["leg_current"], rec.rename("rec")], axis=1).fillna(0.0)
    match = float((j["leg_current"] - j["rec"]).abs().max())
    gross = nm.groupby("date")["per"].sum()
    nd = nd.set_index("date")
    nd["gross_live"] = gross.reindex(nd.index).fillna(0.0)
    nd["live_net"] = nd["leg_current"] - COST_RT * nd["gross_live"]
    nm = nm.merge(nd[["gs"]], left_on="date", right_index=True)
    nm["slot"] = nm.groupby("date").cumcount()
    nm = nm[nm.slot < K]
    dates = np.array(sorted(nm.date.unique()))
    N = len(dates)
    di = {d: i for i, d in enumerate(dates)}
    ii = nm.date.map(di).to_numpy()
    ss = nm.slot.to_numpy()
    F = np.zeros((N, K, NF), np.float64)
    F[ii, ss] = np.column_stack([np.log(nm.price), nm.vol20, nm.day_ret, np.log(nm.adv.clip(lower=1.0)),
                                 nm.slot / (K - 1), nm.w, nm.frac])
    M = np.zeros((N, K), bool); M[ii, ss] = True
    R = np.zeros((N, K)); R[ii, ss] = nm.r
    W = np.zeros((N, K)); W[ii, ss] = nm.w
    PER = np.zeros((N, K)); PER[ii, ss] = nm.per
    GS = nd.loc[dates, "gs"].to_numpy(float)
    return dict(nm=nm, nd=nd, match=match, dates=pd.DatetimeIndex(dates), F=F, M=M, R=R, W=W, PER=PER, GS=GS)


def load_spy() -> pd.Series:
    t = pd.read_parquet(SFP, columns=["ticker", "date", "close"], filters=[("ticker", "==", "SPY")])
    a = t.set_index("date")["close"].sort_index()
    a = a[a.index <= "2020-12-31"]
    e = pd.read_parquet(ALP, columns=["symbol", "timestamp", "close"])
    e = e[e.symbol == "SPY"].copy()
    e["date"] = pd.to_datetime(e.timestamp.dt.tz_convert("America/New_York").dt.date)
    b = e.set_index("date")["close"].sort_index()
    ra = a / a.shift(1) - 1
    rb = b / b.shift(1) - 1
    r = pd.concat([ra, rb[rb.index > "2020-12-31"]]).dropna()
    return r


# ---------------------------------------------------------------- policy
def build_nets(torch):
    nn = torch.nn

    def lin(i, o, g):
        L = nn.Linear(i, o); nn.init.orthogonal_(L.weight, gain=g); nn.init.zeros_(L.bias); return L

    s2 = math.sqrt(2)

    class Net(nn.Module):
        def __init__(self):
            super().__init__()
            self.enc = nn.Sequential(lin(NF, 64, s2), nn.Tanh(), lin(64, 64, s2), nn.Tanh())
            self.slot = nn.Sequential(lin(128, 64, s2), nn.Tanh(), lin(64, 1, 0.01))
            self.cash = nn.Sequential(lin(64, 64, s2), nn.Tanh(), lin(64, 1, 0.01))

        def forward(self, x, m):                       # x (B,K,NF) m (B,K) float
            h = self.enc(x)
            pool = (h * m[..., None]).sum(1) / m.sum(1, keepdim=True).clamp(min=1.0)
            sl = self.slot(torch.cat([h, pool[:, None, :].expand_as(h)], -1)).squeeze(-1)
            return torch.cat([sl, self.cash(pool)], -1)  # (B, K+1)

    class VNet(nn.Module):
        def __init__(self):
            super().__init__()
            self.enc = nn.Sequential(lin(NF, 64, s2), nn.Tanh(), lin(64, 64, s2), nn.Tanh())
            self.head = nn.Sequential(lin(64, 64, s2), nn.Tanh(), lin(64, 1, 1.0))

        def forward(self, x, m):
            h = self.enc(x)
            pool = (h * m[..., None]).sum(1) / m.sum(1, keepdim=True).clamp(min=1.0)
            return self.head(pool).squeeze(-1)

    return Net(), VNet(), nn.Parameter(torch.zeros(1))


def weights_np(logits, M, W, GS):
    """logits (B,K+1), mask (B,K) -> deployed per-name weights (B,K) and cash fraction of budget (B,)."""
    full = np.concatenate([M, np.ones((len(M), 1), bool)], 1)
    z = np.where(full, logits, -np.inf)
    z = z - z.max(1, keepdims=True)
    e = np.exp(z); s = e / e.sum(1, keepdims=True)
    a = np.minimum(s[:, :K], NAME_CAP * W) * M
    return a * GS[:, None], 1.0 - a.sum(1)


def train(job: dict) -> dict:
    import torch
    torch.set_num_threads(1)
    seed, draw, steps = job["seed"], job["draw"], job["steps"]
    X, M, R, W, GS = job["X"], job["M"], job["R"].copy(), job["W"], job["GS"]
    torch.manual_seed(seed + 100 * draw)
    rng = np.random.default_rng(1000 * seed + 7 + 31 * draw)
    if draw:                                            # placebo: shuffle slot returns across valid slots per night
        prng = np.random.default_rng(777 + draw)
        for n in range(len(R)):
            k = int(M[n].sum())
            if k > 1:
                R[n, :k] = R[n, :k][prng.permutation(k)]
    N = len(X)
    pi, vf, log_std = build_nets(torch)
    params = list(pi.parameters()) + list(vf.parameters()) + [log_std]
    opt = torch.optim.Adam(params, lr=LR, eps=1e-5)
    Xt = torch.from_numpy(X.astype(np.float32)); Mt = torch.from_numpy(M.astype(np.float32))
    fullm = torch.cat([Mt, torch.ones(N, 1)], 1)
    ep_len = min(EP_LEN, N)

    def reset():
        return int(rng.integers(0, N - ep_len + 1)), 0

    i, t_ep = reset()
    n_upd = math.ceil(steps / N_STEPS)
    for _ in range(n_upd):
        idx = np.zeros(N_STEPS, int); D = np.zeros(N_STEPS, np.float32)
        for k in range(N_STEPS):
            idx[k] = i; i += 1; t_ep += 1
            if t_ep >= ep_len:
                D[k] = 1.0; i, t_ep = reset()
        nxt = i
        it = torch.from_numpy(idx)
        with torch.no_grad():
            mu = pi(Xt[it], Mt[it]); V = vf(Xt[it], Mt[it]).numpy()
            Vn = vf(Xt[nxt:nxt + 1], Mt[nxt:nxt + 1]).item()
            std = log_std.exp()
            A = mu + std * torch.randn_like(mu)
            fm = fullm[it]
            LP = ((-((A - mu) ** 2) / (2 * std ** 2) - log_std - 0.5 * math.log(2 * math.pi)) * fm).sum(-1)
        a, _ = weights_np(A.numpy().astype(np.float64), M[idx], W[idx], GS[idx])
        Rw = ((a * R[idx]).sum(1) - COST_RT * a.sum(1)).astype(np.float32)
        Vb = np.append(V, Vn).astype(np.float32)
        adv = np.zeros(N_STEPS, np.float32); last = 0.0
        for k in reversed(range(N_STEPS)):
            nt = 1.0 - D[k]
            delta = Rw[k] + GAMMA * Vb[k + 1] * nt - Vb[k]
            last = delta + GAMMA * LAM * nt * last
            adv[k] = last
        ret = adv + Vb[:N_STEPS]
        ADt, RTt = torch.from_numpy(adv), torch.from_numpy(ret)
        for _ep in range(N_EPOCHS):
            perm = rng.permutation(N_STEPS)
            for b in range(0, N_STEPS, MB):
                bi = torch.from_numpy(perm[b:b + MB]); gi = it[bi]
                mu = pi(Xt[gi], Mt[gi]); v = vf(Xt[gi], Mt[gi])
                fmb = fullm[gi]
                lp = ((-((A[bi] - mu) ** 2) / (2 * log_std.exp() ** 2) - log_std - 0.5 * math.log(2 * math.pi))
                      * fmb).sum(-1)
                ad = ADt[bi]; ad = (ad - ad.mean()) / (ad.std() + 1e-8)
                ratio = (lp - LP[bi]).exp()
                pl = -torch.min(ratio * ad, ratio.clamp(1 - CLIP, 1 + CLIP) * ad).mean()
                vl = ((RTt[bi] - v) ** 2).mean()
                ent = (log_std + 0.5 * math.log(2 * math.pi * math.e)).sum()
                loss = pl + VF_COEF * vl - ENT_COEF * ent
                opt.zero_grad(); loss.backward()
                torch.nn.utils.clip_grad_norm_(params, MAX_GN); opt.step()
    sd = {k: v.detach().numpy().copy() for k, v in pi.state_dict().items()}
    return {"seed": seed, "draw": draw, "pi": sd, "log_std": float(log_std.item())}


def policy_logits(sd: dict, X: np.ndarray, M: np.ndarray) -> np.ndarray:
    import torch
    torch.set_num_threads(1)
    pi, _, _ = build_nets(torch)
    pi.load_state_dict({k: torch.from_numpy(v) for k, v in sd.items()})
    with torch.no_grad():
        return pi(torch.from_numpy(X.astype(np.float32)), torch.from_numpy(M.astype(np.float32))).numpy().astype(np.float64)


# ---------------------------------------------------------------- stats
def cagr(x):
    x = np.asarray(x, float)
    return float(np.prod(1 + x) ** (252 / len(x)) - 1)


def cagr_matched(x, target_dd):
    """Scale x so its maxDD equals target_dd (<0); return the CAGR of the scaled series."""
    dd1 = maxdd(x)
    if dd1 >= 0:
        return float("nan")
    lo, hi = 0.0, 20.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if maxdd(mid * x) > target_dd:
            lo = mid
        else:
            hi = mid
    return cagr(lo * np.asarray(x))


def block(tag, sess, ag, lv, slotn, cash, logn, spyv):
    """ag/lv: per-session net series (pd.Series on sess). slotn: bool per session (night with >=1 slot)."""
    a, l = ag.to_numpy(), lv.to_numpy()
    d = (a - l)[slotn]
    t = d.mean() / (d.std(ddof=1) / math.sqrt(len(d)))
    sa, sl = sharpe(a), sharpe(l)
    o = np.argsort(a - l)[::-1][:5]
    keep = np.ones(len(a), bool); keep[o] = False
    ex_gain = sharpe(a[keep]) - sharpe(l[keep])
    dm = d.mean() * 1e4
    dex = (a - l)[keep & slotn].mean() * 1e4
    c = cash[slotn]
    rc_n = np.corrcoef(c, logn[slotn])[0, 1]
    ok = np.isfinite(spyv[slotn])
    rc_v = np.corrcoef(c[ok], spyv[slotn][ok])[0, 1]
    cm = cagr_matched(a, maxdd(l))
    return dict(tag=tag, n=int(slotn.sum()), am=a[slotn].mean() * 1e4, lm=l[slotn].mean() * 1e4, dm=dm, t=t, sa=sa, sl=sl,
                gain=sa - sl, ex_gain=ex_gain, dex=dex, cash=float(c.mean()), rc_n=rc_n, rc_v=rc_v,
                cagr_l=cagr(l), cagr_m=cm, dd_l=maxdd(l), dd_a=maxdd(a))


def fmt(e):
    return (f"  {e['tag']:<11s} nights {e['n']:5d} agent {e['am']:7.2f} live {e['lm']:7.2f} bp/night | diff {e['dm']:+7.2f} "
            f"t {e['t']:+5.2f} | Sh {e['sa']:5.2f} vs {e['sl']:5.2f} gain {e['gain']:+5.2f} ex5 {e['ex_gain']:+5.2f} "
            f"(diff ex5 {e['dex']:+6.2f}) | cash {e['cash']:.3f} r(cash,log n) {e['rc_n']:+.2f} r(cash,SPYvol) "
            f"{e['rc_v']:+.2f} | CAGR@liveDD {e['cagr_m']:+.1%} vs live {e['cagr_l']:+.1%} (DD live {e['dd_l']:.1%})")


def main():
    t0 = time.time()
    timing = "--timing" in sys.argv
    D = load()
    dates, F, M = D["dates"], D["F"], D["M"]
    fit = (dates >= FIT[0]) & (dates <= FIT[1])
    mu = F[fit][M[fit]].mean(0); sd = F[fit][M[fit]].std(0)
    X = np.where(M[..., None], (F - mu) / sd, 0.0)
    base = dict(X=X[fit], M=M[fit], R=D["R"][fit], W=D["W"][fit], GS=D["GS"][fit])
    if timing:
        n = int(sys.argv[sys.argv.index("--timing") + 1])
        t1 = time.time(); train(dict(base, seed=0, draw=0, steps=n))
        print(f"{n} steps: {time.time() - t1:.1f}s"); return 0

    nd = D["nd"]
    say("EXP round 3 R4-PICK (N 1229) night-pool RL picker. Pre-reg: research/drafts/round1_prose.md 'Amendment - EXP round 3'.")
    say(f"Program N {N_TRIALS}. Run {time.strftime('%Y-%m-%d %H:%M')}.")
    say(f"leg_current reproduced from names file (sum per*r per night): max |diff| {D['match']:.2e} over {len(nd)} nights")
    trunc = nd["nk_current"] > K
    say(f"nights with >{K} kept names (truncated to first {K} in live order): all {int(trunc.sum())}; "
        + ", ".join(f"{a[:4]}-{b[:4]} {int(trunc[(nd.index >= a) & (nd.index <= b)].sum())}" for a, b in (FIT, JUDGE, REP)))
    say("IBS per pick: not in the names file -> left out (no new data). Features: log price, vol20, day_ret, log adv, "
        "rank/19, w, frac (z on fit slots).")
    say(f"PPO: lr {LR} gamma {GAMMA} gae {LAM} clip {CLIP} n_steps {N_STEPS} epochs {N_EPOCHS} mb {MB} vf {VF_COEF} "
        f"ent {ENT_COEF} maxgn {MAX_GN}; {TOTAL_STEPS} steps/policy; episodes {EP_LEN} fit slot-nights; seeds {SEEDS}; "
        f"placebo {N_PLACEBO_DRAWS} draws x {len(SEEDS)} seeds")
    say(f"fit slot-nights {int(fit.sum())}")

    jobs = [dict(base, seed=s, draw=0, steps=TOTAL_STEPS) for s in SEEDS]
    jobs += [dict(base, seed=s, draw=d, steps=TOTAL_STEPS) for d in range(1, N_PLACEBO_DRAWS + 1) for s in SEEDS]
    ctx = mp.get_context("spawn")
    with ctx.Pool(min(9, len(jobs))) as pool:
        res = pool.map(train, jobs, chunksize=1)
    say(f"training done {(time.time() - t0) / 60:.1f} min")

    # session calendar + per-session series
    spy = load_spy()
    sess = spy.index[(spy.index >= FIT[0]) & (spy.index <= REP[1])]
    spyv = (spy.rolling(20).std() * math.sqrt(252)).shift(1).reindex(sess).to_numpy()   # through t-1 close
    lv = nd["live_net"].reindex(sess).fillna(0.0)
    missing = int((~nd.index[(nd.index >= FIT[0]) & (nd.index <= REP[1])].isin(sess)).sum())
    say(f"sessions {len(sess)} (SPY SFP to 2020, Alpaca 2021+); pick-nights not in calendar: {missing}")
    pos = pd.Series(np.arange(len(dates)), index=dates)
    sidx = pos.reindex(sess)
    slotn = sidx.notna().to_numpy()
    si = sidx.dropna().astype(int).to_numpy()
    logn = np.zeros(len(sess)); logn[slotn] = np.log(nd["n_picks"].reindex(dates[si]).to_numpy(float))
    # truncation diagnostic: live weights on first 20 slots only
    tr = np.zeros(len(sess)); P = D["PER"]
    tr[slotn] = (P[si] * D["R"][si]).sum(1) - COST_RT * P[si].sum(1)
    live_cash = np.ones(len(sess)); live_cash[slotn] = 1 - P[si].sum(1) / D["GS"][si]
    per_ = lambda a, b: (sess >= a) & (sess <= b)
    for nmn, (a, b) in (("judge", JUDGE), ("2016-20", TOUCH), ("report", REP)):
        m = per_(a, b)
        say(f"live leg net {nmn}: {lv[m][slotn[m]].mean() * 1e4:.2f} bp/slot-night, Sharpe {sharpe(lv[m]):.2f}; "
            f"first-20-only live {tr[m][slotn[m]].mean() * 1e4:.2f} bp; live cash frac {live_cash[m][slotn[m]].mean():.3f}")

    def series(r):
        lg = policy_logits(r["pi"], X, M)
        a, cash = weights_np(lg, M, D["W"], D["GS"])
        net = (a * D["R"]).sum(1) - COST_RT * a.sum(1)
        ag = np.zeros(len(sess)); ag[slotn] = net[si]
        cs = np.ones(len(sess)); cs[slotn] = cash[si]
        return pd.Series(ag, index=sess), cs

    def evalr(r, a, b, tag):
        ag, cs = series(r)
        m = per_(a, b)
        return block(tag, sess[m], ag[m], lv[m], slotn[m], cs[m], logn[m], spyv[m])

    real = [r for r in res if r["draw"] == 0]
    plac = [r for r in res if r["draw"] > 0]
    say("")
    say("Per seed (JUDGE 2013-20, halves, 2016-20 touched, REPORT 2021-26; fit 2003-12 for reference):")
    J, H1s, H2s, gates_seed = [], [], [], []
    for r in real:
        say(f" seed {r['seed']} (log_std {r['log_std']:+.2f})")
        ef = evalr(r, *FIT, "fit03-12"); ej = evalr(r, *JUDGE, "judge13-20")
        e1 = evalr(r, *H1, "h13-16"); e2 = evalr(r, *H2, "h17-20")
        et = evalr(r, *TOUCH, "touch16-20"); er = evalr(r, *REP, "rep21-26")
        for e in (ef, ej, e1, e2, et, er):
            say(fmt(e))
        J.append(ej); H1s.append(e1); H2s.append(e2)
        gates_seed.append(ej["gain"] >= 0.15 and ej["cagr_m"] >= ej["cagr_l"] + 0.02 and e1["gain"] > 0 and e2["gain"] > 0
                          and ej["ex_gain"] > 0)
    pg = np.array([evalr(r, *JUDGE, "p")["gain"] for r in plac])
    med = lambda k, L=J: float(np.median([e[k] for e in L]))
    g_med = med("gain")
    pct = float((pg < g_med).mean() * 100)
    say("")
    say(f"Seed-median JUDGE: agent {med('am'):.2f} vs live {med('lm'):.2f} bp/night, diff {med('dm'):+.2f} (t med "
        f"{med('t'):+.2f}); Sharpe gain {g_med:+.3f}; ex-top-5 gain {med('ex_gain'):+.3f}; CAGR@liveDD "
        f"{med('cagr_m'):+.1%} vs live {med('cagr_l'):+.1%}; halves gain {med('gain', H1s):+.3f} / {med('gain', H2s):+.3f}; "
        f"cash {med('cash'):.3f}")
    say(f"Placebo ({len(pg)} policies, slot returns shuffled within night): judge Sharpe gain median {np.median(pg):+.3f}, "
        f"95th {np.percentile(pg, 95):+.3f}; real seed-median at {pct:.0f}th pct")
    # DSR of the seed-median-gain seed's judge series
    js = sorted(range(len(real)), key=lambda k: J[k]["gain"])[len(real) // 2]
    ag, _ = series(real[js]); m = per_(*JUDGE)
    say(f"DSR (N {N_TRIALS}) judge, median seed {real[js]['seed']}: agent {dsr(ag[m].to_numpy(), N_TRIALS):.3f}, "
        f"live leg {dsr(lv[m].to_numpy(), N_TRIALS):.3f}")
    G = {
        "Sharpe gain >= +0.15 (seed-median)": g_med >= 0.15,
        "CAGR at live maxDD >= live + 2pp": med("cagr_m") >= med("cagr_l") + 0.02,
        "both halves beat live on Sharpe": med("gain", H1s) > 0 and med("gain", H2s) > 0,
        "placebo >= 95th pct": pct >= 95,
        "ex-top-5 gain > 0": med("ex_gain") > 0,
        ">= 4/5 seeds pass all per-seed gates": sum(gates_seed) >= 4,
    }
    say("Gates:")
    for k, v in G.items():
        say(f"  {'PASS' if v else 'FAIL'}  {k}")
    verdict = "PASS" if all(G.values()) else "FAIL"
    say(f"VERDICT R4-PICK (N 1229): {verdict}  (seeds passing all per-seed gates: {sum(gates_seed)}/5)")
    say(f"runtime {(time.time() - t0) / 60:.1f} min")
    OUT.write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
