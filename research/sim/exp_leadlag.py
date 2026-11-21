"""E1 LEADLAG-D (N 1217): daily cross-name lead-lag on survivorship-free Sharadar 1998-2020.

Pre-registration: research/drafts/round1_prose.md, "## Amendment - EXP round (user 2026-11-20 ...)",
bullet "E1 LEADLAG-D (N 1217)" (FROZEN; program N 1218). One run; nothing is changed after a judge
(2011-2020) number is printed.

Rule (as registered)
  Universe: Sharadar SEP common stocks (nx.is_common) + SFP category "ETF", listed exchanges, point in time:
    each month-end m, unadjusted close >= $5, 20d ADV >= $10M, top 500 by 20d ADV. Delisted names kept.
  Betas: at month-end m, trailing 250 sessions (249 (t, t+1) pairs), for every pair (A, B) in U_m the OLS
    beta and t of r_B(t+1) on r_A(t) controlling for r_B(t), SPY r(t) and a constant (Frisch-Waugh, all A
    per B at once). Leaders of B: t >= 3, cap 10 by t. Used for every session of month m+1.
  Signal_B(t) = sum beta_AB r_A(t) (t close-to-close). Buy the top 20 at t's close, exit t+1 open (night)
    and, separately, t+1 close; equal weight, 1.0x. Benchmark: EW U_m over the same window.
  Judge 2011-2020; 1998-2010 descriptive (the rule is fixed; nothing fitted there).
  Gate per exit: net excess >= +15bp/day at 2.5bp/side, NW t >= 2, both halves > 0, ex-top-5 days > 0,
    > 0 at 5bp/side, placebo (leaders -> random names of the same count, their own estimated betas) >= 95th.

Data conventions (verified in the output): SEP/SFP open/close are split-adjusted (not dividend-adjusted),
closeunadj is raw; dividends from ACTIONS are split-adjusted cash/share and are added on the ex-date
(close->close on day t; close->open when the ex-date is t+1). Raw dollar volume = close*volume (volume is
split-adjusted, so closeunadj*volume would be wrong after a split).

Run: PYTHONPATH=. python3 research/sim/exp_leadlag.py [--lo 1998 --hi 2002 --draws 10 --dev]
"""
from __future__ import annotations

import argparse
import pathlib
import time

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from research.sim.nx import LISTED, is_common

ROOT = pathlib.Path(__file__).resolve().parents[2]
NXD = ROOT / "data/research/nx"
OUT = ROOT / "research/sim/exp_leadlag_out.txt"

PRICE_MIN, ADV_MIN, TOPN_U, WIN, TMIN, CAP, TOPK = 5.0, 1e7, 500, 250, 3.0, 10, 20
MIN_OBS = 240          # a name needs >= 240 of the 250 window returns to be a leader or follower (missing -> 0)
COSTS = (2.5e-4, 5e-4)
JUDGE = ("2011-01-01", "2020-12-31")
HALVES = (("2011-01-01", "2015-12-31"), ("2016-01-01", "2020-12-31"))
DESC = ("1998-01-01", "2010-12-31")
GATE_BP = 15e-4

LINES: list[str] = []


def P(s=""):
    print(s, flush=True); LINES.append(s)


def nw_t(x, L=5):
    x = x[np.isfinite(x)]; n = len(x); m = x.mean(); u = x - m
    v = u @ u / n
    for l in range(1, L + 1): v += 2 * (1 - l / (L + 1)) * (u[l:] @ u[:-l]) / n
    return m / np.sqrt(v / n)


# ------------------------------------------------------------------ data
def load(hi_date):
    t = pd.read_parquet(NXD / "cache_TICKERS.parquet", columns=["table", "ticker", "category", "exchange"])
    t = t[t.table.isin(["SEP", "SFP"])].fillna("")
    keep = (is_common(t.category) | (t.category == "ETF")) & t.exchange.str.upper().isin(LISTED)
    kt = t[keep]
    etf = set(kt.ticker[kt.category == "ETF"])
    cols = ["ticker", "date", "open", "close", "volume", "closeunadj"]
    parts = []
    for nm in ("SEP", "SFP"):
        f = pq.read_table(NXD / f"cache_{nm}.parquet", columns=cols,
                          filters=[("ticker", "in", list(kt.ticker)), ("date", "<=", pd.Timestamp(hi_date))]).to_pandas()
        parts.append(f)
    b = pd.concat(parts, ignore_index=True)
    spy = b[b.ticker == "SPY"]
    sessions = np.sort(spy.date.unique())
    b = b[b.date.isin(sessions)].drop_duplicates(["ticker", "date"])
    b = b.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    a = pd.read_parquet(NXD / "cache_ACTIONS.parquet", columns=["date", "action", "ticker", "value"])
    div = a[a.action == "dividend"].groupby(["ticker", "date"], as_index=False)["value"].sum()
    spl = a[a.action == "split"][["ticker", "date"]]
    dl = a[a.action.isin(["delisted", "bankruptcyliquidation", "regulatorydelisting",
                          "voluntarydelisting"])][["ticker", "date", "value"]]
    return b, pd.DatetimeIndex(sessions), div, spl, dl, etf, len(kt)


def adv20(b):
    code = pd.factorize(b.ticker)[0]; n = len(b)
    newg = np.r_[True, code[1:] != code[:-1]]
    start = np.maximum.accumulate(np.where(newg, np.arange(n), 0)); pos = np.arange(n) - start
    dv = np.nan_to_num(b.close.to_numpy(float) * b.volume.to_numpy(float))
    cs = np.r_[0.0, np.cumsum(dv)]; i = np.arange(n)
    s = cs[i + 1] - cs[np.maximum(i + 1 - 20, 0)]
    return np.where(pos >= 19, s / 20.0, np.nan)


# ------------------------------------------------------------------ regressions
def month_betas(X, Y, spy_x, valid, excl):
    """X, Y: (n, K) r(t), r(t+1) for the K universe names (NaN filled 0); spy_x (n,). valid (K,) names with
    enough history. Returns beta, tstat (K_B, K_A) over valid names; invalid pairs NaN."""
    idx = np.flatnonzero(valid); Xv = X[:, idx]; Yv = Y[:, idx]; n, K = Xv.shape
    C = np.empty((K, n, 3)); C[:, :, 0] = 1.0; C[:, :, 1] = Xv.T; C[:, :, 2] = spy_x[None, :]
    Q, _ = np.linalg.qr(C)                                    # (K_B, n, 3)
    Yt = Yv.T - np.einsum("bnk,bk->bn", Q, np.einsum("bnk,bn->bk", Q, Yv.T))   # residual y_B, (K_B, n)
    QtX = np.einsum("bnk,na->bka", Q, Xv)                     # (K_B, 3, K_A)
    aa = (Xv ** 2).sum(0)[None, :] - (QtX ** 2).sum(1)        # a~'a~
    ay = Yt @ Xv                                              # a'(M y) = a~'y~
    yy = (Yt ** 2).sum(1)[:, None]
    with np.errstate(divide="ignore", invalid="ignore"):
        beta = ay / aa
        s2 = (yy - beta ** 2 * aa) / (n - 4)
        tt = beta / np.sqrt(s2 / aa)
    bad = aa < 1e-6 * (Xv ** 2).sum(0)[None, :]               # A collinear with B's controls
    bad |= np.eye(K, dtype=bool)
    bad |= excl[idx][None, :]
    beta[bad] = np.nan; tt[bad] = np.nan
    return idx, beta, tt


def leaders(beta, tt):
    """W (K_A, K_B): beta for each B's leaders (t >= 3, top CAP by t)."""
    K = beta.shape[0]; W = np.zeros((K, K)); nlead = np.zeros(K, int)
    tm = np.where(np.isfinite(tt) & (tt >= TMIN), tt, -np.inf)
    for bi in range(K):
        c = np.flatnonzero(np.isfinite(tm[bi]))
        if not len(c): continue
        c = c[np.argsort(-tm[bi, c], kind="mergesort")[:CAP]]
        W[c, bi] = beta[bi, c]; nlead[bi] = len(c)
    return W, nlead


def topk_returns(S, can, Rn, Rd):
    """S (..., D, K) signals; can (D, K) buyable with signal; returns mean pick night/day returns (..., D)."""
    S = np.where(can, S, -np.inf)
    k = np.minimum(TOPK, can.sum(-1))                         # (D,)
    part = np.argpartition(-S, TOPK - 1, axis=-1)[..., :TOPK]
    sv = np.take_along_axis(S, part, -1)
    ok = np.isfinite(sv)
    rn = np.take_along_axis(np.broadcast_to(Rn, S.shape), part, -1)
    rd = np.take_along_axis(np.broadcast_to(Rd, S.shape), part, -1)
    with np.errstate(invalid="ignore", divide="ignore"):
        mn = np.where(ok, rn, 0).sum(-1) / ok.sum(-1)
        md = np.where(ok, rd, 0).sum(-1) / ok.sum(-1)
    return mn, md, part, ok, k


# ------------------------------------------------------------------ stats
def block(x, dates, label):
    s = pd.Series(x, index=dates).dropna()
    out = {}
    for c in COSTS:
        y = s - 2 * c
        out[c] = y
    y = out[COSTS[0]]; y5 = out[COSTS[1]]
    h = [y[a:b] for a, b in HALVES] if label == "judge" else []
    ex5 = np.sort(y.to_numpy())[:-5].mean()
    d = dict(n=len(y), m=y.mean(), t=nw_t(y.to_numpy()), m5=y5.mean(), t5=nw_t(y5.to_numpy()), ex5=ex5,
             med=y.median(), hit=(y > 0).mean(), h=[(z.mean(), nw_t(z.to_numpy()), len(z)) for z in h],
             gross=s.mean())
    return d


def fmt(d, tag):
    P(f"  [{tag}] n {d['n']}  gross excess {d['gross']*1e4:+.2f}bp/day")
    P(f"     net @2.5bp/side {d['m']*1e4:+.2f}bp/day NW t {d['t']:.2f} | @5bp/side {d['m5']*1e4:+.2f}bp NW t {d['t5']:.2f}")
    P(f"     ex-top-5 days {d['ex5']*1e4:+.2f}bp  median day {d['med']*1e4:+.2f}bp  hit {d['hit']:.3f}")
    for (m, t, n), (a, b) in zip(d["h"], HALVES):
        P(f"     half {a[:4]}-{b[2:4]}: {m*1e4:+.2f}bp NW t {t:.2f} n {n}")


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hi", default="2021-01-15")
    ap.add_argument("--draws", type=int, default=200)
    ap.add_argument("--dev", action="store_true", help="debug run: no judge period, no output file")
    a = ap.parse_args()
    T0 = time.time()
    P("E1 LEADLAG-D (N 1217; program N 1218) -- research/sim/exp_leadlag.py; pre-reg round1_prose.md 'EXP round'")
    P(f"run {pd.Timestamp.now():%Y-%m-%d %H:%M}")
    b, sessions, div, spl, dl, etf, nkeep = load(a.hi)
    P(f"bars {len(b):,} rows, {b.ticker.nunique():,} tickers (of {nkeep:,} common+ETF listed in TICKERS); sessions {len(sessions)} "
      f"{sessions[0]:%Y-%m-%d}..{sessions[-1]:%Y-%m-%d}")
    b["adv"] = adv20(b)
    # month-end universes
    ss = pd.Series(sessions, index=sessions)
    me = ss.groupby([sessions.year, sessions.month]).max().to_numpy()
    me = pd.DatetimeIndex(me)
    mb = b[b.date.isin(me) & (b.closeunadj >= PRICE_MIN) & (b.adv >= ADV_MIN)]
    mb = mb.sort_values(["date", "adv"], ascending=[True, False]).groupby("date").head(TOPN_U)
    uni = {d: g.ticker.to_numpy() for d, g in mb.groupby("date")}
    U = np.array(sorted(set(mb.ticker)))
    P(f"universe: {len(U):,} distinct names ever in a month-end top-{TOPN_U}; months {len(uni)}; "
      f"min/median size {min(len(v) for v in uni.values())}/{int(np.median([len(v) for v in uni.values()]))}")
    # wide panels
    bw = b[b.ticker.isin(U)]
    col = pd.Index(U)
    def wide(c):
        return bw.pivot(index="date", columns="ticker", values=c).reindex(index=sessions, columns=col).to_numpy(float)
    C, O = wide("close"), wide("open")
    dv = div[div.ticker.isin(U)].pivot_table(index="date", columns="ticker", values="value", aggfunc="sum")
    D = dv.reindex(index=sessions, columns=col).fillna(0.0).to_numpy(float)
    del bw
    # verify open/close adjustment on split ex-dates: close(t-1)->open(t) jump must be small
    sp = spl[spl.ticker.isin(U)]
    si = sessions.get_indexer(sp.date); ci = col.get_indexer(sp.ticker); okk = (si > 0) & (ci >= 0)
    jump = np.abs(np.log(O[si[okk], ci[okk]] / C[si[okk] - 1, ci[okk]]))
    jump = jump[np.isfinite(jump)]
    allj = np.abs(np.log(O[1:] / C[:-1])); allj = allj[np.isfinite(allj)]
    P(f"check open/close adjustment: split ex-dates n {len(jump)}: median |log o(t)/c(t-1)| {np.median(jump):.4f}, "
      f"share > 20% {np.mean(jump > 0.2):.3f}; all rows median {np.median(allj):.4f}, share > 20% {np.mean(allj > 0.2):.5f}")
    rawchk = b[b.ticker.isin(["AAPL"]) & b.date.isin(pd.to_datetime(["2014-06-06", "2014-06-09"]))]
    P("  AAPL around the 2014-06-09 7:1 split (adj close, raw close): " +
      "; ".join(f"{r.date:%Y-%m-%d} {r.close:.3f}/{r.closeunadj:.2f}" for r in rawchk.itertuples()))
    del b
    # returns with dividends
    with np.errstate(invalid="ignore", divide="ignore"):
        CC = np.full_like(C, np.nan); CC[1:] = (C[1:] + D[1:]) / C[:-1] - 1      # close(t-1)->close(t), on row t
        ON = np.full_like(C, np.nan); ON[:-1] = (O[1:] + D[1:]) / C[:-1] - 1     # close(t)->open(t+1), on row t
    CD = np.full_like(C, np.nan); CD[:-1] = CC[1:]                                 # close(t)->close(t+1), on row t
    # exits with no next bar: delisting price from ACTIONS within 15 days (sanity 0 < v/c < 3), else 0
    dlv = dl[dl.ticker.isin(U) & (dl.value > 0)]
    dl_map = {}
    for r in dlv.itertuples():
        dl_map.setdefault(r.ticker, []).append((r.date, r.value))
    spy_i = col.get_loc("SPY")
    spyr = CC[:, spy_i].copy()
    excl = np.zeros(len(U), bool); excl[spy_i] = True        # SPY as a leader is collinear with the control
    P(f"exits: close(t)->open(t+1) incl. ex-date dividend; close(t)->close(t+1) incl. dividend; costs charged on "
      f"both sides every day (no netting of repeat names)")

    # ---------------------------------------------------- monthly loop
    rng = np.random.default_rng(1217)
    me_idx = sessions.get_indexer(me)
    recs = []          # per day: date, night pick, day pick, night bench, day bench, n picks, share <= -8%, n fallback
    plac = {"n": [], "d": []}   # per judge day: (draws,) mean pick returns minus bench
    nlead_all, nlead_pos, nvalid_m = [], [], []
    fallback = 0; picks_tot = 0
    for mi in range(len(me) - 1):
        s = me_idx[mi]
        if s < WIN: continue
        d0 = me[mi]
        if a.dev and d0 >= pd.Timestamp(JUDGE[0]) - pd.Timedelta(days=40): break
        names = uni.get(d0)
        if names is None: continue
        ui = col.get_indexer(names)
        R = CC[s - WIN + 1: s + 1][:, ui]                   # 250 returns ending at m (inclusive)
        cnt = np.isfinite(R).sum(0)
        valid = (cnt >= MIN_OBS) & np.isfinite(spyr[s - WIN + 1: s + 1]).all()
        R0 = np.nan_to_num(R)
        X, Y = R0[:-1], R0[1:]
        idx, beta, tt = month_betas(X, Y, np.nan_to_num(spyr[s - WIN + 1: s]), valid, excl[ui])
        W, nl = leaders(beta, tt)
        nlead_all.append(nl.mean()); nlead_pos.append(nl[nl > 0].mean() if (nl > 0).any() else 0); nvalid_m.append(len(idx))
        e = me_idx[mi + 1]
        days = np.arange(s + 1, e + 1)
        days = days[days < len(sessions) - 1]
        if not len(days): continue
        cols_u = ui[idx]                                      # leader/follower universe columns
        RA = np.nan_to_num(CC[days][:, cols_u])               # r_A(t), missing -> 0
        Sg = RA @ W                                           # (Dn, K_B)
        can = np.isfinite(C[days][:, cols_u]) & (nl > 0)[None, :]
        Rn = ON[days][:, cols_u].copy(); Rd = CD[days][:, cols_u].copy()
        # missing exits for buyable names: delisting price else 0
        miss = can & (~np.isfinite(Rn) | ~np.isfinite(Rd))
        for di, ki in zip(*np.nonzero(miss)):
            tk = col[cols_u[ki]]; dt0 = sessions[days[di]]; v = None
            for (dd, val) in dl_map.get(tk, []):
                if dt0 < dd <= dt0 + pd.Timedelta(days=15): v = val; break
            c0 = C[days[di], cols_u[ki]]
            fill = (v / c0 - 1) if (v is not None and 0 < v / c0 < 3) else 0.0
            if not np.isfinite(Rn[di, ki]): Rn[di, ki] = fill
            if not np.isfinite(Rd[di, ki]): Rd[di, ki] = fill
        mn, md, part, ok, k = topk_returns(Sg, can, Rn, Rd)
        dayr = CC[days][:, cols_u]
        sel_day = np.take_along_axis(dayr, part, -1)
        sh8 = np.where(ok, np.nan_to_num(sel_day) <= -0.08, False).sum(-1)
        mfall = np.take_along_axis(miss, part, -1) & ok
        fallback += int(mfall.sum()); picks_tot += int(ok.sum())
        bN = np.nanmean(np.where(np.isfinite(C[days][:, ui]), ON[days][:, ui], np.nan), axis=1)
        bD = np.nanmean(np.where(np.isfinite(C[days][:, ui]), CD[days][:, ui], np.nan), axis=1)
        for j, di in enumerate(days):
            recs.append((sessions[di], mn[j], md[j], bN[j], bD[j], int(ok[j].sum()), int(sh8[j])))
        # placebo (judge months only): each B's leaders replaced by random valid names of the same count, own betas
        if pd.Timestamp(JUDGE[0]) <= sessions[days[0]] <= pd.Timestamp(JUDGE[1]) and a.draws > 0:
            K = len(idx); fin = np.isfinite(beta)            # (K_B, K_A)
            Ws = np.zeros((a.draws, K, K), np.float32)
            for p in range(a.draws):
                key = np.where(fin, rng.random((K, K)), np.inf)
                order = np.argsort(key, axis=1)
                for bi in np.flatnonzero(nl):
                    c = order[bi, :nl[bi]]
                    Ws[p, c, bi] = beta[bi, c]
            Sp = np.einsum("dk,pkb->pdb", RA.astype(np.float32), Ws)
            pn, pd_, _, _, _ = topk_returns(Sp, can[None], Rn[None], Rd[None])
            plac["n"].append(pn - bN[None]); plac["d"].append(pd_ - bD[None])
        if mi % 12 == 0:
            P(f"  .. {d0:%Y-%m} valid {len(idx)} mean leaders {nl.mean():.2f} ({time.time()-T0:.0f}s)")

    df = pd.DataFrame(recs, columns=["date", "pn", "pd", "bn", "bd", "npick", "n8"]).set_index("date")
    df["xn"] = df.pn - df.bn; df["xd"] = df.pd - df.bd
    P("")
    P(f"months with betas {len(nlead_all)}; valid names per month median {int(np.median(nvalid_m))}; "
      f"avg leaders per name {np.mean(nlead_all):.2f} (per name with >= 1 leader {np.mean(nlead_pos):.2f}; "
      f"share of names with >= 1 leader computed monthly)")
    P(f"picks {picks_tot:,}; exits filled from delisting price or 0 (no next bar) {fallback} ({fallback/max(picks_tot,1):.4%})")
    P(f"share of picks with day ret <= -8% (live night-leg overlap): all {df.n8.sum()/df.npick.sum():.4f}; "
      f"judge {df.loc[JUDGE[0]:JUDGE[1]].n8.sum()/max(df.loc[JUDGE[0]:JUDGE[1]].npick.sum(),1):.4f}")
    P(f"days with < {TOPK} picks: {(df.npick < TOPK).sum()}")
    res = {}
    for ex, xc, tag in (("night", "xn", "t close -> t+1 open"), ("day", "xd", "t close -> t+1 close")):
        P("")
        P(f"=== exit {ex} ({tag}); excess = picks - EW U_m same window; cost 2 sides/day")
        dd = df.loc[DESC[0]:DESC[1], xc]
        fmt(block(dd.to_numpy(), dd.index, "desc"), "1998-2010 DESCRIPTIVE (not judged)")
        if a.dev: continue
        jj = df.loc[JUDGE[0]:JUDGE[1], xc]
        st = block(jj.to_numpy(), jj.index, "judge")
        fmt(st, "JUDGE 2011-2020")
        pl = np.concatenate(plac["n" if ex == "night" else "d"], axis=1) if plac["n"] else None
        if pl is not None:
            pm = np.nanmean(pl, axis=1) - 2 * COSTS[0]
            pct = (pm < st["m"]).mean() * 100
            P(f"     placebo ({pl.shape[0]} draws): actual {st['m']*1e4:+.2f}bp vs placebo median {np.median(pm)*1e4:+.2f}bp, "
              f"95th {np.percentile(pm,95)*1e4:+.2f}bp -> percentile {pct:.1f}")
        else:
            pct = np.nan
        g = [("G1 net >= +15bp/day @2.5bp", st["m"] >= GATE_BP),
             ("G2 NW t >= 2", st["t"] >= 2),
             ("G3 both halves > 0", all(h[0] > 0 for h in st["h"])),
             ("G4 ex-top-5 days > 0", st["ex5"] > 0),
             ("G5 > 0 @5bp/side", st["m5"] > 0),
             ("G6 placebo >= 95th", pct >= 95)]
        P("     gates: " + " | ".join(f"{n} {'PASS' if v else 'FAIL'}" for n, v in g))
        res[ex] = all(v for _, v in g)
        P(f"     exit {ex}: {'PASS' if res[ex] else 'FAIL'}")
    P("")
    if not a.dev:
        v = "PASS" if any(res.values()) else "FAIL (dead)"
        P(f"VERDICT E1 LEADLAG-D: {v}  (night {'PASS' if res['night'] else 'FAIL'}, day {'PASS' if res['day'] else 'FAIL'})")
    P(f"runtime {time.time()-T0:.0f}s")
    if not a.dev:
        OUT.write_text("\n".join(LINES) + "\n")


if __name__ == "__main__":
    main()
