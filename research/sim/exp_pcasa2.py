"""PCA-SA siblings (N 1248 K30, N 1249 VOL), pre-registered in round1_prose.md "Amendment - DEEP round 2b".

    OMP_NUM_THREADS=3 PYTHONPATH=. python3 -m research.sim.exp_pcasa2

Both windows must pass: W1 1999-2010 and W2 2011-01..2026-10-05. Data: ~/data/sharadar (stocks/funds/actions/tickers,
SEP common, delisted kept) for both windows, so W1 also replicates N 1242 (which used the NX cache).
Benchmark for LO/K30 = the EW universe (names with a valid s) at the book's beta: excess = book - (beta_book/beta_EW) * EW,
both betas 60d vs SPY. Factors, s-score, signal close T / trade close T+1, 5bp/side (shock 10bp), borrow 100bp/yr as N 1242.
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS",
           "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "3")

import gc
import pathlib

import numpy as np
import pandas as pd

from .exp_pcasa import load_panel, build_signals, simulate, sharpe, COST, COST_X, BORROW, N_PLACEBO, S_BO, S_SC
from .exp_rl import dsr
from .weekwin_short import tstat

OUT = pathlib.Path(__file__).resolve().parent / "exp_pcasa2_out.txt"
SH = pathlib.Path.home() / "data/sharadar"
SRC = dict(sep=SH / "stocks.parquet", sfp=SH / "funds.parquet", actions=SH / "actions.parquet", tickers=SH / "tickers.parquet")
N_PROGRAM = 1249
K = 30
WINDOWS = [  # tag, load from, load to, eval from, eval to, halves split
    ("W1 1999-2010", "1997-12-31", "2010-12-31", "1999-01-01", "2010-12-31", "2004-12-31"),
    ("W2 2011-2026-10", "2009-10-01", "2026-10-05", "2011-01-01", "2026-10-05", "2018-12-31"),
]

L: list[str] = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    L.append(s)
    OUT.write_text("\n".join(L) + "\n")


def simulate_k(sig, R, spy, lag=2):
    """K30 long book: keep a held name while s <= -0.50 and it ranks within the K most negative s; fill open slots
    with the most negative s among s < -1.25. Same row layout as exp_pcasa.simulate (short columns 0)."""
    D, N = R.shape
    held = np.zeros(N, bool); w_prev = np.zeros(N, np.float32)
    rows = []
    for t in range(D - lag):
        g = sig[t]
        if g is None:
            if not held.any():
                continue
            held[:] = False; bv = np.zeros(N, np.float32)
        else:
            idx, s, beta = g
            bv = np.zeros(N, np.float32); bv[idx] = beta
            order = idx[np.argsort(s, kind="stable")]           # most negative first
            rank = np.full(N, N); rank[order] = np.arange(len(order))
            sv = np.full(N, np.nan, np.float32); sv[idx] = s
            with np.errstate(invalid="ignore"):
                held &= (rank < K) & (sv <= -S_SC)
                room = K - int(held.sum())
                if room > 0:
                    new = [j for j in order[:K] if not held[j] and sv[j] < -S_BO][:room]
                    held[new] = True
        n = int(held.sum())
        w = np.where(held, 1.0 / max(n, 1), 0.0).astype(np.float32)
        r = np.nan_to_num(R[t + lag])
        bl = float(w @ bv)
        rows.append((t + lag, n, 0, float(w @ r), 0.0, bl, 0.0, float(np.nan_to_num(spy[t + lag])),
                     float(np.abs(w - w_prev).sum()), 0.0, 0.0))
        w_prev = w
    return pd.DataFrame(np.array(rows, float), columns=["ti", "nl", "ns", "gl", "gs", "bl", "h", "spy", "tl", "ts", "th"])


def ew_bench(sig, R):
    """EW universe next return and its mean 60d SPY beta, indexed by the earning session (t + 2)."""
    D = len(R); ew = np.zeros(D); ewb = np.ones(D)
    for t, g in enumerate(sig):
        if g is not None and t + 2 < D:
            ew[t + 2] = np.nan_to_num(R[t + 2, g[0]]).mean(); ewb[t + 2] = g[2].mean()
    return ew, ewb


def stats(x, dates, split):
    x = pd.Series(np.asarray(x, float), index=dates)
    srt = np.sort(x.to_numpy())
    mon = x.groupby(x.index.to_period("M")).sum()
    eq = np.cumprod(1 + x.to_numpy()); dd = (eq / np.maximum.accumulate(eq) - 1).min()
    return dict(mean=x.mean(), ann=x.mean() * 252, sh=sharpe(x), t=tstat(x.to_numpy()),
                h1=x[x.index <= split].mean(), h2=x[x.index > split].mean(), x5=srt[:-5].mean(),
                med_m=mon.median(), hit_m=(mon > 0).mean(), dd=dd, dsr=dsr(x.to_numpy(), N_PROGRAM))


def fmt(tag, s, sx):
    return (f"  {tag}: net {s['mean'] * 1e4:+.2f}bp/day ({s['ann']:+.1%}/yr) Sharpe {s['sh']:+.2f} t {s['t']:+.2f} | "
            f"halves {s['h1'] * 1e4:+.2f} / {s['h2'] * 1e4:+.2f}bp | 2x cost {sx['mean'] * 1e4:+.2f}bp ({sx['ann']:+.1%}/yr) | "
            f"ex-top5 {s['x5'] * 1e4:+.2f}bp | median month {s['med_m'] * 100:+.2f}% (hit {s['hit_m']:.2f}) | maxDD {s['dd']:.0%} | "
            f"DSR(N {N_PROGRAM}) {s['dsr']:.3f}")


def series(d, ew, ewb, cost):
    ti = d.ti.astype(int).to_numpy()
    ls = (d.gl + d.gs + d.h * d.spy - cost * (d.tl + d.ts + d.th) - BORROW * (d.ns > 0)).to_numpy()
    lo = (d.gl - (d.bl / ewb[ti]) * ew[ti] - cost * d.tl).to_numpy()        # excess vs EW universe at the book's beta
    return ls, lo


def window_eval(d, sessions, w0, w1):
    d = d.copy(); d["date"] = sessions[d.ti.astype(int)]
    return d[(d.date >= w0) & (d.date <= w1)].reset_index(drop=True)


def book_line(tag, d):
    return (f"  {tag} book: {len(d)} days; positions/day long {d.nl.mean():.1f} short {d.ns.mean():.1f} (days with 0 longs "
            f"{np.mean(d.nl == 0):.1%}); turnover/day long {d.tl.mean():.2f} short {d.ts.mean():.2f} hedge {d.th.mean():.3f}; "
            f"long-book beta {d.bl.mean():.2f}")


def gates_line(name, g):
    ok = all(o for _, o in g)
    return ok, f"  GATES {name}: " + " | ".join(f"{n} {'PASS' if o else 'FAIL'}" for n, o in g) + f" -> {'PASS' if ok else 'FAIL'}"


def run_window(tag, d0, d1, w0, w1, split, res):
    say(f"\n=== {tag}: load {d0}..{d1}, evaluate {w0}..{w1} (halves split {split})")
    sessions, R, cu, adv, spy, info = load_panel(d0, d1, src=SRC, want_vol=True, prefilter=True)
    lastbar = np.where(np.isfinite(cu), np.arange(len(sessions))[:, None], -1).max(0)
    dl_win = int(((lastbar < len(sessions) - 5) & (sessions[np.maximum(lastbar, 0)] >= pd.Timestamp(w0))).sum())
    say(f"  panel: {info['D']} sessions x {info['N']} common names that ever trade $10M/day; duplicate rows {info['dup']}; "
        f"delisted inside the panel {info['delisted']} (last bar inside the eval window {dl_win}); SPY missing {info['spy_nan']}; "
        f"|ret|>50% cells {int((np.abs(R) > 0.5).sum())}; zero/missing volume cells among priced {int((~(info['vol'] > 0) & np.isfinite(cu)).sum())}")
    sig, sigv, dg = build_signals(R, cu, adv, spy, vscale=(info["vol"], info["vol20"]))
    del cu, adv, info["vol"], info["vol20"]; gc.collect()
    nvv = np.mean([len(g[0]) for g in sigv if g is not None])
    say(f"  signal: first {sessions[dg['t_first']].date()}; universe mean {dg['nu'].mean():.0f} (min {dg['nu'].min()}); "
        f"MP factors kept mean {dg['nf'].mean():.2f} (min {dg['nf'].min()}, max {dg['nf'].max()}); valid s/day base {dg['nval'].mean():.0f}, "
        f"vol-time {nvv:.0f}; max |X_60| base {dg['x_end']:.1e}")
    ew, ewb = ew_bench(sig, R)
    books = {
        "base LS/LO (N 1242 replication, context)": simulate(sig, R, spy),
        "K30 base (N 1248)": simulate_k(sig, R, spy),
        "VOL LS/LO (N 1249)": simulate(sigv, R, spy),
        "VOL K30 (N 1249)": simulate_k(sigv, R, spy),
    }
    ewd = window_eval(pd.DataFrame({"ti": np.arange(len(R)), "ew": ew, "ewb": ewb}), sessions, w0, w1)
    ewd = ewd[ewd.ewb != 1.0]
    say(f"  EW universe: {ewd.ew.mean() * 252:+.1%}/yr, mean beta {ewd.ewb.mean():.2f}")
    out = {}
    for name, d in books.items():
        d = window_eval(d, sessions, w0, w1)
        ls, lo = series(d, ew, ewb, COST); lsx, lox = series(d, ew, ewb, COST_X)
        ti = d.ti.astype(int).to_numpy()
        say(book_line(name, d))
        say(f"    gross: long {d.gl.mean() * 1e4:+.2f}bp/d, vs EW at beta {(d.gl - d.bl / ewb[ti] * ew[ti]).mean() * 1e4:+.2f}bp/d"
            + (f"; LS gross {(d.gl + d.gs + d.h * d.spy).mean() * 1e4:+.2f}bp/d" if d.ns.mean() > 0 else ""))
        if d.ns.mean() > 0:
            out[name + " LS"] = (d, stats(ls, d.date, split), stats(lsx, d.date, split), ls)
            say(fmt("LS (SPY-hedged)", out[name + " LS"][1], out[name + " LS"][2]))
        key = name + (" LO" if d.ns.mean() > 0 else "")
        out[key] = (d, stats(lo, d.date, split), stats(lox, d.date, split), lo)
        say(fmt("long excess vs EW at beta", out[key][1], out[key][2]))
        yr = pd.Series(lo, index=pd.DatetimeIndex(d.date)).groupby(lambda x: x.year).mean() * 1e4
        say("    by year (long excess bp/d): " + " ".join(f"{y % 100:02d}:{v:+.1f}" for y, v in yr.items()))
    # placebo for the VOL LS/LO arms (gross, as N 1242's run note: a within-date shuffle multiplies turnover)
    rng = np.random.default_rng(1249)
    dv_, s_lsv, _, _ = out["VOL LS/LO (N 1249) LS"]
    pl_ls, pl_lo = [], []
    for _ in range(N_PLACEBO):
        p = window_eval(simulate(sigv, R, spy, rng=rng), sessions, w0, w1)
        a_, b_ = series(p, ew, ewb, 0.0)
        pl_ls.append(sharpe(a_ + BORROW * (p.ns > 0).to_numpy())); pl_lo.append(b_.mean() * 252)
    g_ls, g_lo = series(dv_, ew, ewb, 0.0)
    g_ls = g_ls + BORROW * (dv_.ns > 0).to_numpy()
    pct_ls = (np.array(pl_ls) < sharpe(g_ls)).mean() * 100; pct_lo = (np.array(pl_lo) < g_lo.mean() * 252).mean() * 100
    say(f"  placebo VOL (within-date shuffle, {N_PLACEBO} draws, gross): LS Sharpe 95th {np.percentile(pl_ls, 95):+.2f} vs real {sharpe(g_ls):+.2f} "
        f"(pct {pct_ls:.0f}); LO-vs-EW 95th {np.percentile(pl_lo, 95):+.1%}/yr vs real {g_lo.mean() * 252:+.1%} (pct {pct_lo:.0f})")
    for arm in ("K30 base (N 1248)", "VOL K30 (N 1249)"):
        s, sx = out[arm][1], out[arm][2]
        ok, line = gates_line(f"{arm} [{tag}]", [("excess>=8%/yr", s["ann"] >= 0.08), ("t>=2", s["t"] >= 2),
                                                 ("halves>0", s["h1"] > 0 and s["h2"] > 0), ("2xcost>0", sx["mean"] > 0),
                                                 ("ex-top5>0", s["x5"] > 0)])
        say(line); res[(arm, tag)] = ok
    s, sx = out["VOL LS/LO (N 1249) LS"][1:3]
    ok, line = gates_line(f"VOL LS (N 1249) [{tag}]", [("Sharpe>=1.0", s["sh"] >= 1.0), ("t>=2.5", s["t"] >= 2.5),
                                                       ("halves>0", s["h1"] > 0 and s["h2"] > 0), ("2xcost>0", sx["mean"] > 0),
                                                       ("ex-top5>0", s["x5"] > 0), ("median-month>0", s["med_m"] > 0),
                                                       ("placebo95", pct_ls >= 95)])
    say(line); res[("VOL LS", tag)] = ok
    s, sx = out["VOL LS/LO (N 1249) LO"][1:3]
    ok, line = gates_line(f"VOL LO (N 1249) [{tag}]", [("excess>=8%/yr", s["ann"] >= 0.08), ("t>=2", s["t"] >= 2),
                                                       ("halves>0", s["h1"] > 0 and s["h2"] > 0), ("2xcost>0", sx["mean"] > 0),
                                                       ("placebo95", pct_lo >= 95)])
    say(line); res[("VOL LO", tag)] = ok
    del R, sig, sigv; gc.collect()


def main():
    say("PCA-SA siblings: N 1248 K30 (long the 30 most negative s < -1.25) and N 1249 VOL (AL volume-time s: residual x vol20/vol)."
        f" Sharadar ~/data/sharadar SEP common, delisted kept; benchmark EW universe at book beta; 5bp/side, shock 10bp; DSR at N {N_PROGRAM}."
        " A pass needs both windows.")
    res = {}
    for w in WINDOWS:
        run_window(*w, res)
    t1, t2 = WINDOWS[0][0], WINDOWS[1][0]
    k30 = res[("K30 base (N 1248)", t1)] and res[("K30 base (N 1248)", t2)]
    vol = {a: res[(a, t1)] and res[(a, t2)] for a in ("VOL LS", "VOL LO", "VOL K30 (N 1249)")}
    say(f"\nVERDICT N 1248 PCA-SA-K30: {'PASS' if k30 else 'KILL'} (W1 {res[('K30 base (N 1248)', t1)]}, W2 {res[('K30 base (N 1248)', t2)]})")
    say(f"VERDICT N 1249 PCA-SA-VOL: {'PASS' if any(vol.values()) else 'KILL'} ("
        + ", ".join(f"{a}: W1 {res[(a, t1)]} W2 {res[(a, t2)]}" for a in vol) + ")")


if __name__ == "__main__":
    main()
