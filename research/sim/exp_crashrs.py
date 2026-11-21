"""DEEP round 2c, N 1250 CRASH-RS: relative strength inside a market drawdown.

Pre-registration: research/drafts/round1_prose.md, "## Amendment - DEEP round 2c" (N 1249 -> 1250). Not tuned.

    PYTHONPATH=. python3 research/sim/exp_crashrs.py        # -> research/sim/exp_crashrs_out.txt

Data: loaders from exp_tail (Sharadar SEP common, delisted kept through their last bar, total return = close + ACTIONS dividends).
Stocks: NX caches for bars <= 2020-12-31, ~/data/sharadar/stocks.parquet (loaded from 2020-06 so returns/ADV are warm) for bars
>= 2021-01-01, joined by ticker. Session grid and the drawdown state = SPY total-return index from ~/data/sharadar/funds.parquet
(one continuous series 1997-12..2026-10-05).
Reading of the registration where it is silent:
  * "trailing-252-session max" is rolling: M_t = max of the SPY TR index over sessions t-251..t, P_t = argmax. D switches on
    when TR_t <= 0.93 M_t and off when TR_t >= 0.97 M_t (hysteresis; time-in-D 1999-2015 ~40%, the fixed-peak reading is ~67%
    and makes 2000-06 one episode). An episode = one contiguous D spell; P is the current P_t at each decision.
  * Decisions: the first D session with t - P_t >= 5, then every 5 sessions while D is on.
  * Eligible at t: bar at t, closeunadj >= $5, ADV20 finite, top 1,500 by ADV20 (no ADV floor beyond the rank). A name then
    needs a 252-session beta ending at P (>= 200 finite paired returns); names without one are dropped from that decision.
  * r_i(P..t) compounds the name's returns over sessions P+1..t (no bar = 0). Sector = Sharadar TICKERS sector ('' its own group).
  * Hold: close t+1 -> close t+6 = sessions t+2..t+6. Decisions 5 apart make the book continuous within an episode.
  * Costs: 5bp x (sum |w_t - w_prev| within the episode, 1.0 at the first decision) + 5bp x 1.0 exit at the episode's last
    decision; benchmark (EW eligible) gross. Shock 10bp.
  * MC: per decision, Spearman(score_t, resid_i) with resid_i = r_i(t..t+20) - beta_i r_SPY(t..t+20); averaged within episode;
    the gate is over episodes (mean >= +0.05, t >= 2, positive share >= 60%).
  * Placebo: per decision a fake P = t - U{20..120}, score/beta/excess recomputed at that P; 100 draws; statistic = mean GROSS
    excess per hold (real gross compared), so the draws are not charged their own turnover.
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

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from research.sim.exp_rl import dsr  # noqa: E402
from research.sim.exp_tail import _read, NXD, FULL, PRICE_MIN  # noqa: E402
from research.sim.nx import is_common  # noqa: E402
from scipy.stats import rankdata  # noqa: E402

OUT = ROOT / "research/sim/exp_crashrs_out.txt"
ALPACA = pathlib.Path("/private/tmp/claude-501/-Users-andrewlau-Documents-Code-Projects-swing-trader/"
                      "f8b1efd9-fa49-4233-8b45-d15823460ce9/scratchpad/recent_bars.parquet")
COST, COST_X = 5e-4, 10e-4
N_TRIALS = 1250
TOPN, L, MINOBS = 1500, 252, 200
J0, J1, H1_END = "1999-01-01", "2015-12-31", "2007-12-31"
N_PLACEBO = 100
CUT = np.datetime64("2021-01-01")

lines: list[str] = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    lines.append(s)


# ---------------------------------------------------------------- SPY state
def dstate(tr):
    n = len(tr); D = np.zeros(n, bool); P = np.full(n, -1); ep = np.full(n, -1)
    on = False; e = -1
    for t in range(n):
        lo = max(0, t - L + 1); w = tr[lo:t + 1]; M = w.max(); P[t] = lo + int(w.argmax())
        if not on and tr[t] <= 0.93 * M:
            on = True; e += 1
        elif on and tr[t] >= 0.97 * M:
            on = False
        D[t] = on
        if on:
            ep[t] = e
    return D, P, ep


def decisions(D, P, ep):
    out = []; last = None
    for t in range(len(D)):
        if not D[t]:
            continue
        if last is not None and ep[last] == ep[t]:
            if t - last == 5:
                out.append(t); last = t
            continue
        if t - P[t] >= 5:   # first decision of the episode
            out.append(t); last = t
    return np.array(out, int)


# ---------------------------------------------------------------- stocks
def load_wide(sessions, dec):
    tk_c = pd.read_parquet(NXD / "cache_TICKERS.parquet", columns=["table", "ticker", "category", "sector"])
    tk_f = pd.read_parquet(FULL / "tickers.parquet", columns=["table", "ticker", "category", "sector"])
    tk = pd.concat([tk_f, tk_c]); tk = tk[tk.table == "SEP"].drop_duplicates("ticker")
    common = sorted(set(tk.ticker[is_common(tk.category.fillna("").astype(str))]))
    sector = tk.set_index("ticker").sector.fillna("").to_dict()
    S = len(sessions)
    is_dec = np.zeros(S, bool); is_dec[dec] = True
    names, rets, cand = [], [], []   # per name: (sidx, ret); candidate rows (dec sidx, gid, adv)
    nch = 8
    for ci in range(nch):
        chunk = common[ci::nch]
        parts = []
        for path, start, act, keep in ((NXD / "cache_SEP.parquet", "1997-12-01", NXD / "cache_ACTIONS.parquet", "lt"),
                                       (FULL / "stocks.parquet", "2020-06-01", FULL / "actions.parquet", "ge")):
            d = _read(path, chunk, start, act, sessions)
            dates = sessions[d["sidx"]]
            m = dates < CUT if keep == "lt" else dates >= CUT
            parts.append(pd.DataFrame(dict(ticker=d["names"][d["code"][m]], sidx=d["sidx"][m], ret=d["ret"][m],
                                           cu=d["cu"][m], adv=d["adv"][m])))
            del d, dates, m
        b = pd.concat(parts, ignore_index=True); del parts
        b = b.sort_values(["ticker", "sidx"], kind="mergesort")
        for t, g in b.groupby("ticker", sort=False):
            si = g.sidx.to_numpy(); c = is_dec[si] & (g.cu.to_numpy() >= PRICE_MIN) & np.isfinite(g.adv.to_numpy())
            if not c.any():
                continue
            gid = len(names); names.append(t)
            rets.append((si.astype(np.int32), g.ret.to_numpy(np.float32)))
            cand.append(np.column_stack([si[c], np.full(c.sum(), gid), g.adv.to_numpy()[c]]))
        del b
        say(f"  chunk {ci + 1}/{nch}: names so far {len(names)}")
    C = pd.DataFrame(np.vstack(cand), columns=["sidx", "gid", "adv"]); del cand
    C["sidx"] = C.sidx.astype(int); C["gid"] = C.gid.astype(int)
    C["rk"] = C.groupby("sidx").adv.rank(ascending=False, method="first")
    C = C[C.rk <= TOPN]
    keep = np.unique(C.gid.to_numpy())
    col = np.full(len(names), -1); col[keep] = np.arange(len(keep))
    R = np.full((S, len(keep)), np.nan, np.float32)
    for g_ in keep:
        si, r = rets[g_]; R[si, col[g_]] = r
    del rets
    elig = {s: col[g.gid.to_numpy()] for s, g in C.groupby("sidx")}
    nm = np.array(names, dtype=object)[keep]
    sec = np.array([sector.get(x, "") for x in nm], dtype=object)
    return R, elig, nm, sec


def rolling_beta(R, m):
    """beta[t, i] over sessions t-251..t, pairs with a finite name return, >= MINOBS of them."""
    S, N = R.shape
    B = np.full((S, N), np.nan, np.float32)
    mm = m.astype(np.float64)
    for j0 in range(0, N, 400):
        X = R[:, j0:j0 + 400].astype(np.float64)
        f = np.isfinite(X); X0 = np.where(f, X, 0.0); Y = np.where(f, mm[:, None], 0.0)
        def cs(a):
            c = np.cumsum(a, axis=0); out = c.copy(); out[L:] -= c[:-L]; return out
        n = cs(f.astype(np.float64)); sx = cs(X0); sy = cs(Y); sxy = cs(X0 * Y); syy = cs(Y * Y)
        with np.errstate(invalid="ignore", divide="ignore"):
            b = (sxy - sx * sy / n) / (syy - sy * sy / n)
        b[n < MINOBS] = np.nan; b[:L - 1] = np.nan
        B[:, j0:j0 + 400] = b.astype(np.float32)
        del X, f, X0, Y, n, sx, sy, sxy, syy, b
    return B


# ---------------------------------------------------------------- one decision
def cumret(LR, a, b, cols):
    """compounded return over sessions a..b inclusive (no bar = 0); LR = cumulative log(1+r) by session."""
    if b < a:
        return np.zeros(len(cols))
    return np.expm1(LR[b, cols].astype(np.float64) - LR[a - 1, cols].astype(np.float64))


def score_at(R, B, mcum, sec_codes, cols, t, p):
    beta = B[p, cols].astype(np.float64)
    ok = np.isfinite(beta)
    c = cols[ok]; beta = beta[ok]
    ri = cumret(R, p + 1, t, c)
    rs = mcum[t] / mcum[p] - 1
    sc = ri - beta * rs
    sg = sec_codes[c]
    sm = np.bincount(sg, sc, minlength=sec_codes.max() + 1) / np.maximum(np.bincount(sg, minlength=sec_codes.max() + 1), 1)
    return c, beta, sc - sm[sg]


def top_decile(c, beta, sc):
    k = max(1, len(c) // 10)
    idx = np.argpartition(-sc, k - 1)[:k]
    return idx


def hold(R, m, mcum, c, beta, idx, t):
    S = R.shape[0]
    h = cumret(R, t + 2, t + 6, c)
    hs = mcum[t + 6] / mcum[t + 1] - 1
    port = h[idx].mean(); ew = h.mean()
    return port - ew - (beta[idx].mean() - beta.mean()) * hs, port, ew, hs


# ---------------------------------------------------------------- main
def tstat(x):
    x = np.asarray(x, float); return float(x.mean() / (x.std(ddof=1) / math.sqrt(len(x)))) if len(x) > 1 else float("nan")


def main():
    say("CRASH-RS (N 1250): drawdown state on SPY TR (rolling 252 max, on <= 0.93, off >= 0.97); score = r(P..t) - beta_P r_SPY(P..t),"
        " sector-demeaned; long top decile of top-1500 ADV $5+ SEP common (delisted kept), close t+1 -> t+6; excess beta-matched vs EW;"
        " 5bp/side, shock 10bp; DSR N 1250")
    sp = _read(FULL / "funds.parquet", ["SPY"], "1997-12-01", FULL / "actions.parquet")
    sessions = sp["sessions"]; m = np.nan_to_num(sp["ret"].astype(np.float64)); m[0] = 0.0
    mcum = np.cumprod(1 + m)
    S = len(sessions)
    D, P, ep = dstate(mcum)
    dec = decisions(D, P, ep)
    dec = dec[(dec + 20 < S)]  # MC needs t+20; holds need t+6
    dd = pd.DatetimeIndex(sessions)
    jmask = (dd[dec] >= J0) & (dd[dec] <= J1)
    say(f"SPY sessions {dd[0].date()}..{dd[-1].date()}; time in D 1999-2015 {D[(dd >= J0) & (dd <= J1)].mean():.1%}, 2016-26 {D[dd > J1].mean():.1%};"
        f" decisions judge {int(jmask.sum())}, report {int((dd[dec] > J1).sum())}")
    R, elig, nm, sec = load_wide(sessions, dec)
    say(f"  wide R {R.shape} {R.nbytes / 1e6:.0f}MB")
    B = rolling_beta(R, m)
    R = np.cumsum(np.log1p(np.nan_to_num(R)), axis=0, dtype=np.float32)   # R now holds cumulative log returns (float32)
    sec_codes = pd.factorize(sec)[0]
    rows = []
    rng = np.random.default_rng(0)
    PL = np.full((N_PLACEBO, len(dec)), np.nan)
    offs = rng.integers(20, 121, (N_PLACEBO, len(dec)))
    prev_set, prev_ep = None, None
    for j, t in enumerate(dec):
        cols = elig.get(t)
        if cols is None or len(cols) < 100:
            continue
        p = int(P[t])
        c, beta, sc = score_at(R, B, mcum, sec_codes, cols, t, p)
        if len(c) < 100:   # no 252-session beta at P (P in 1998: data start)
            continue
        idx = top_decile(c, beta, sc)
        ex, port, ew, hs = hold(R, m, mcum, c, beta, idx, t)
        # MC
        r20 = cumret(R, t + 1, t + 20, c); rs20 = mcum[t + 20] / mcum[t] - 1
        rc = np.corrcoef(rankdata(sc), rankdata(r20 - beta * rs20))[0, 1]
        held = set(c[idx].tolist())
        if prev_ep == ep[t] and prev_set is not None:
            w = 1.0 / len(held); wp = 1.0 / len(prev_set)
            turn = sum(abs((w if x in held else 0) - (wp if x in prev_set else 0)) for x in held | prev_set)
        else:
            turn = 1.0
        rows.append(dict(j=j, t=t, date=dd[t], ep=int(ep[t]), P=dd[p], n=len(c), k=len(idx), ex=ex, port=port, ew=ew, spy=hs,
                         turn=turn, rc=rc, bport=beta[idx].mean(), bew=beta.mean()))
        prev_set, prev_ep = held, ep[t]
        for d_ in range(N_PLACEBO):
            pf = t - int(offs[d_, j])
            cf, bf, sf = score_at(R, B, mcum, sec_codes, cols, t, pf)
            if len(cf) < 100:
                continue
            PL[d_, j] = hold(R, m, mcum, cf, bf, top_decile(cf, bf, sf), t)[0]
    H = pd.DataFrame(rows)
    H["last"] = H.ep != H.ep.shift(-1)
    H["net"] = H.ex - COST * (H.turn + H["last"])
    H["netx"] = H.ex - COST_X * (H.turn + H["last"])
    epi = H.groupby("ep").agg(start=("date", "first"), end=("date", "last"), P=("P", "first"), holds=("ex", "size"),
                              ex=("ex", "mean"), net=("net", "mean"), rc=("rc", "mean"))
    say("\nEpisodes (first decision, last decision, P at first decision, holds, mean gross/net excess per hold, mean MC rank corr):")
    for e, r in epi.iterrows():
        say(f"  ep {e:2d} {r.start.date()}..{r.end.date()} P {r.P.date()} holds {r.holds:3d} gross {r.ex * 1e4:+7.1f}bp net {r.net * 1e4:+7.1f}bp rc {r.rc:+.3f}")
    for tag, mk, judge in (("JUDGE 1999-2015 (halves 1999-2007 / 2008-15)", (H.date >= J0) & (H.date <= J1), True),
                           ("REPORT 2016-2026-10 (never judged)", H.date > J1, False)):
        h = H[mk]
        if len(h) == 0:
            say(f"\n=== {tag}: no decisions"); continue
        e = epi.loc[h.ep.unique()]
        e_rc = h.groupby("ep").rc.mean()
        say(f"\n=== {tag}: {len(h)} holds in {h.ep.nunique()} episodes, names/decision {h.n.mean():.0f}, decile {h.k.mean():.0f},"
            f" beta port {h.bport.mean():.2f} vs EW {h.bew.mean():.2f}, turnover {h.turn.mean():.2f}/hold")
        mc_t = tstat(e_rc)
        gMC = e_rc.mean() >= 0.05 and mc_t >= 2 and (e_rc > 0).mean() >= 0.60
        say(f"  MC: mean episode rank corr(score, next-20 residual) {e_rc.mean():+.4f}, t {mc_t:+.2f} over {len(e_rc)} episodes, positive {(e_rc > 0).mean():.0%};"
            f" pooled over decisions {h.rc.mean():+.4f} (t {tstat(h.rc):+.2f}) -> {'PASS' if gMC else 'FAIL'}")
        x = h.net.to_numpy(); srt = np.sort(x)
        h1 = (h.date <= H1_END).to_numpy() if judge else (h.date <= h.date.iloc[len(h) // 2]).to_numpy()
        epsum = h.groupby("ep").net.sum(); best = epsum.idxmax()
        exb = h[h.ep != best].net.mean()
        t_ = tstat(x); t_ep = tstat(epsum / h.groupby("ep").size())
        pl = PL[:, h.j.to_numpy()]; plm = np.nanmean(pl, axis=1); real_g = h.ex.mean()
        pct = (plm < real_g).mean() * 100
        ds = dsr(x, N_TRIALS)
        say(f"  net excess {x.mean() * 1e4:+.1f}bp/hold (gross {h.ex.mean() * 1e4:+.1f}, 2x cost {h.netx.mean() * 1e4:+.1f}) t {t_:+.2f}"
            f" | median {np.median(x) * 1e4:+.1f} hit {(x > 0).mean():.2f} | halves {x[h1].mean() * 1e4:+.1f} / {x[~h1].mean() * 1e4:+.1f}"
            f" | ex-top5 {srt[:-5].mean() * 1e4:+.1f} | ex-best episode (ep {best}) {exb * 1e4:+.1f} | episode-clustered t {t_ep:+.2f}")
        say(f"  raw legs: decile {h.port.mean() * 1e4:+.1f}bp/hold, EW {h.ew.mean() * 1e4:+.1f}, SPY {h.spy.mean() * 1e4:+.1f}"
            f" | placebo fake-P (100): gross mean {plm.mean() * 1e4:+.1f}bp, 95th {np.percentile(plm, 95) * 1e4:+.1f}; real gross {real_g * 1e4:+.1f} at pct {pct:.0f}"
            f" | DSR (N {N_TRIALS}, per hold) {ds:.3f}")
        yrs = (h.date.iloc[-1] - h.date.iloc[0]).days / 365.25 if judge else (dd[-1] - h.date.iloc[0]).days / 365.25
        say(f"  ceiling: {len(h) / max(yrs, 1e-9):.1f} holds/yr x {x.mean() * 1e4:+.1f}bp = {len(h) / max(yrs, 1e-9) * x.mean() * 100:+.1f}pp/yr excess (simple sum)")
        if judge:
            g = [("MC", gMC), ("net>=60bp", x.mean() >= 60e-4), ("t>=2.5", t_ >= 2.5), ("halves", x[h1].mean() > 0 and x[~h1].mean() > 0),
                 ("ex-top5", srt[:-5].mean() > 0), ("ex-best-ep", exb > 0), ("2xcost", h.netx.mean() > 0), ("placebo95", pct >= 95)]
            say("  GATES: " + " | ".join(f"{n} {'PASS' if ok else 'FAIL'}" for n, ok in g) + f" -> {'PASS' if all(o for _, o in g) else 'KILL'}")
    del R, B
    alpaca_episode(sec_map(nm, sec))
    OUT.write_text("\n".join(lines) + "\n")


def sec_map(nm, sec):
    return dict(zip(nm, sec))


def alpaca_episode(_unused):
    say("\n=== 2026-10 episode, descriptive (Alpaca adjusted daily bars 2026-01-02..2026-11-20, ~2,400 liquid names; not Sharadar)")
    if not ALPACA.exists():
        say("  file missing"); return
    a = pd.read_parquet(ALPACA, columns=["sym", "date", "c", "v"])
    tk = pd.read_parquet(FULL / "tickers.parquet", columns=["table", "ticker", "category", "sector"])
    tk = tk[tk.table == "SEP"].drop_duplicates("ticker")
    common = set(tk.ticker[is_common(tk.category.fillna("").astype(str))]); sector = tk.set_index("ticker").sector.fillna("").to_dict()
    C = a.pivot(index="date", columns="sym", values="c").sort_index()
    V = a.pivot(index="date", columns="sym", values="v").reindex(C.index)
    spy = C["SPY"].ffill()
    tr = spy.to_numpy(); n = len(tr)
    D, P, ep = dstate(tr)
    oct_ = np.where(C.index >= pd.Timestamp("2026-10-01"))[0][0]
    on = np.where(D & (np.arange(n) >= oct_))[0]   # earlier 2026 spells are covered by the Sharadar run (ep 31)
    if len(on) == 0:
        say("  D never on after 2026-10-01 in the file"); return
    say(f"  D on {C.index[on[0]].date()}..{C.index[on[-1]].date()} ({len(on)} sessions, still on at the last bar: {bool(D[-1])}); P {C.index[P[on[0]]].date()}"
        f" (SPY {tr[P[on[0]]]:.2f}); last close {C.index[-1].date()} SPY {tr[-1]:.2f} = {tr[-1] / tr[P[on[-1]]] - 1:+.1%} from P"
        " (bars start 2026-01; P checked against data/research/hmm_rebal/px_SPY.csv: 2026-10-06 is the 252-session max)")
    dec = [t for t in decisions(D, P, ep) if t >= on[0]]
    say(f"  decisions: {len(dec)} ({', '.join(str(C.index[t].date()) for t in dec)}); completed t+1 -> t+6 holds: {sum(t + 6 < n for t in dec)}")
    R = C.pct_change(fill_method=None)
    m = R["SPY"].to_numpy()
    cols = [c for c in C.columns if c in common]
    for t in dec:
        p = int(P[t])
        adv = (C[cols] * V[cols]).iloc[t - 19:t + 1].mean()
        okp = (C[cols].iloc[t] >= PRICE_MIN) & adv.notna()
        names = adv[okp].sort_values(ascending=False).index[:TOPN]
        X = R[names].iloc[max(1, p - L + 1):p + 1]; mm = m[max(1, p - L + 1):p + 1]
        f = X.notna()
        bet = {}
        for c in names:
            xx = X[c].to_numpy(); fm = f[c].to_numpy()
            if fm.sum() >= 100:
                bet[c] = np.cov(xx[fm], mm[fm])[0, 1] / np.var(mm[fm], ddof=1)
        names = [c for c in names if c in bet]
        b = np.array([bet[c] for c in names])
        ri = (C[names].iloc[t] / C[names].iloc[p] - 1).to_numpy()
        rs = tr[t] / tr[p] - 1
        sc = pd.Series(ri - b * rs, index=names)
        sg = pd.Series([sector.get(c, "") for c in names], index=names)
        sc = sc - sc.groupby(sg).transform("mean")
        top = sc.sort_values(ascending=False).index[:max(1, len(names) // 10)]
        say(f"  decision {C.index[t].date()}: P {C.index[p].date()}, scored {len(names)} names (beta from {len(X)} sessions ending at P, >= 100 obs),"
            f" top decile {len(top)}; beta top {np.mean([bet[c] for c in top]):.2f} vs all {b.mean():.2f}")
        mix = sg[top].value_counts(normalize=True).head(6)
        say("    top-decile sectors: " + ", ".join(f"{k or 'n/a'} {v:.0%}" for k, v in mix.items())
            + " | eligible: " + ", ".join(f"{k or 'n/a'} {v:.0%}" for k, v in sg.value_counts(normalize=True).head(6).items()))
        say(f"    top 10 by score: {', '.join(top[:10])}")
        if t + 1 < n:
            nx = (C[names].iloc[-1] / C[names].iloc[t] - 1)
            say(f"    t -> last bar ({C.index[-1].date()}, {n - 1 - t} sessions; before the registered t+1 entry): top {nx[top].mean():+.2%}, all {nx.mean():+.2%}, SPY {tr[-1] / tr[t] - 1:+.2%}")


if __name__ == "__main__":
    main()
