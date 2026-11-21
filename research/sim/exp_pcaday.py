"""PCA-DAY (N 1257, pre-registered in round1_prose.md "Amendment - DEEP round 3c").

    OMP_NUM_THREADS=3 PYTHONPATH=. python3 -m research.sim.exp_pcaday

AL s-score (N 1242 base via exp_pcasa.build_signals: top-1000 by split-adjusted ADV20 (adv_adj=True), Marchenko-Pastur
factors refit every 5 sessions, 60d OU) computed through close T. Buy the 20 most negative s (s < -1.25) at the open of T+1,
sell at the close of T+1; fresh basket each day, equal weight (1/n of the picks).
Outcome = close T+1 / open T+1 - 1 (split-adjusted, same bar; an ex-date dividend is struck before the open, so none accrues).
A pick with no T+1 bar (halt / delisted after T) cannot be bought at the open: its slot stays cash (0, no cost) and still counts
in the 1/n weight. Costs: nx.cost_model tier_hi per side on closeunadj_T and ADV20 through T; shock 2x_tier_hi.
Benchmark: EW open -> close T+1 of the same top-1000 universe (names with a T+1 bar). JUDGE 2003-2015 (halves 2003-09 /
2010-15); REPORT 2016-2026-10. Structure, windows and the NX live-night independence series copied from exp_pcanight (N 1253).
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

from research.sim import nx
from .exp_pcasa import load_panel, build_signals, S_BO
from .exp_pcasa2 import SRC
from .exp_pcanight import live_leg
from .exp_rl import dsr
from .weekwin_short import tstat

OUT = pathlib.Path(__file__).resolve().parent / "exp_pcaday_out.txt"
N_PROGRAM = 1257
K = 20
N_PLACEBO = 50
WINDOWS = [  # tag, load from, load to, eval from, eval to, halves split, judged
    ("JUDGE 2003-2015", "2001-09-01", "2016-01-15", "2003-01-02", "2015-12-31", "2009-12-31", True),
    ("REPORT 2016-2026-10 (never judged)", "2014-09-01", "2026-10-05", "2016-01-01", "2026-10-05", "2020-12-31", False),
]

L: list[str] = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    L.append(s)
    OUT.write_text("\n".join(L) + "\n")


def day_table(sessions, info, sig, w0, w1):
    """Per decision close T in [w0, w1]: s of sig[T] (through close T), open->close T+1 outcomes, costs, EW bench.
    Rows are indexed by the traded day T+1."""
    D = len(sessions)
    cl, op, cu, adv = info["close"], info["open"], info["cu"], info["adv"]
    rows, days = [], []
    miss = 0; tot = 0
    ts = np.flatnonzero((sessions >= pd.Timestamp(w0)) & (sessions <= pd.Timestamp(w1)))
    for t in ts:
        if t + 1 >= D:
            continue
        days.append(sessions[t + 1])
        if sig[t] is None:
            rows.append(None); continue
        idx, s, _ = sig[t]
        ok = np.isfinite(cl[t, idx]) & (cu[t, idx] > 0)
        idx, s = idx[ok], s[ok]
        u0 = cu[t, idx].astype(np.float64)
        o1, c1 = op[t + 1, idx].astype(np.float64), cl[t + 1, idx].astype(np.float64)
        hn = np.isfinite(o1) & np.isfinite(c1) & (o1 > 0)
        with np.errstate(invalid="ignore", divide="ignore"):
            ret = np.where(hn, c1 / o1 - 1.0, 0.0)
        c_hi = nx.cost_model("tier_hi", u0, adv[t, idx]) / 1e4
        c_2x = nx.cost_model("2x_tier_hi", u0, adv[t, idx]) / 1e4
        tot += len(idx); miss += int((~hn).sum())
        ew = float(ret[hn].mean()) if hn.any() else 0.0
        rows.append(dict(s=s, gross=ret, net=np.where(hn, ret - 2 * c_hi, 0.0), net2=np.where(hn, ret - 2 * c_2x, 0.0), ew=ew,
                         hn=hn, cost=np.where(hn, 2 * c_hi, 0.0)))
    return pd.DatetimeIndex(days), rows, (miss, tot)


def book(rows, rng=None):
    """EW the K most negative s < -1.25 each day. Returns gross, net, net2, ew (0 on cash days), n, cost, untradable picks."""
    out = np.zeros((len(rows), 7))
    for r, g in enumerate(rows):
        if g is None:
            continue
        s = rng.permutation(g["s"]) if rng is not None else g["s"]
        o = np.argsort(s, kind="stable")
        o = o[s[o] < -S_BO][:K]
        if len(o) == 0:
            continue
        out[r] = (g["gross"][o].mean(), g["net"][o].mean(), g["net2"][o].mean(), g["ew"], len(o), g["cost"][o].mean(),
                  int((~g["hn"][o]).sum()))
    return pd.DataFrame(out, columns=["gross", "net", "net2", "ew", "n", "cost", "nmiss"])


def run_window(tag, d0, d1, w0, w1, split, judged, act, master):
    say(f"\n=== {tag}: load {d0}..{d1}, decision closes {w0}..{w1} (halves split {split}, by traded day)")
    live = live_leg(w0, w1, master, act)
    say(f"  NX live night rule (primary, nx.collect_trades): {live.tier_hi.mean() * 1e4:+.2f}bp/night at tier_hi over {len(live)} nights")
    gc.collect()
    sessions, R, cu, adv, spy, info = load_panel(d0, d1, src=SRC, want_open=True, prefilter=True, adv_adj=True)
    info["cu"], info["adv"] = cu, adv
    say(f"  panel: {info['D']} sessions x {info['N']} common names (ever $10M/day, split-adjusted $ volume); duplicate rows {info['dup']}; "
        f"open missing where close present {int((np.isfinite(info['close']) & ~np.isfinite(info['open'])).sum())}")
    sig, dg = build_signals(R, cu, adv, spy)
    say(f"  signal: first {sessions[dg['t_first']].date()}; universe mean {dg['nu'].mean():.0f}; MP factors kept mean {dg['nf'].mean():.2f}; "
        f"valid s/day {dg['nval'].mean():.0f}")
    del R; gc.collect()
    days, rows, (miss, tot) = day_table(sessions, info, sig, w0, w1)
    del info, cu, adv, sig; gc.collect()
    b = book(rows); b.index = days
    on = b.n > 0
    x, x2, xg = (b.net - b.ew * on), (b.net2 - b.ew * on), (b.gross - b.ew * on)
    say(f"  universe names with no T+1 bar (cash slot): {miss} of {tot:,} name-days; picks without a T+1 bar {int(b.nmiss.sum())}")
    say(f"  book: {len(b)} days, {int(on.sum())} with picks; names/day {b.n[on].mean():.1f} (days < {K}: {np.mean(b.n[on] < K):.1%}); "
        f"round-trip tier_hi cost {b.cost[on].mean() * 1e4:.1f}bp/name; turnover 2.0/day (buy open + sell close)")
    say(f"  absolute: gross {b.gross.mean() * 1e4:+.2f}bp/day, net tier_hi {b.net.mean() * 1e4:+.2f} (t {tstat(b.net.to_numpy()):+.2f}, "
        f"{b.net.mean() * 252:+.1%}/yr simple), 2x {b.net2.mean() * 1e4:+.2f}; EW universe open->close {b.ew[on].mean() * 1e4:+.2f}bp")
    hs = x.index <= split
    srt = np.sort(x.to_numpy())
    t_x = tstat(x.to_numpy())
    say(f"  EXCESS vs EW: gross {xg.mean() * 1e4:+.2f}bp/day | net tier_hi {x.mean() * 1e4:+.2f}bp (NW t {t_x:+.2f}, {x.mean() * 252:+.1%}/yr) | "
        f"halves {x[hs].mean() * 1e4:+.2f} / {x[~hs].mean() * 1e4:+.2f} | 2x tier_hi {x2.mean() * 1e4:+.2f} | ex-top5 {srt[:-5].mean() * 1e4:+.2f} | "
        f"median day {np.median(x) * 1e4:+.2f} hit {(x > 0).mean():.2f} | DSR(N {N_PROGRAM}) {dsr(x.to_numpy(), N_PROGRAM):.3f}")
    j = pd.concat([b.net.rename("pca"), x.rename("x"), live.tier_hi.rename("live")], axis=1).dropna()
    say(f"  corr with the NX live night series (tier_hi, same calendar date: the night ending at that open) — book net {j.pca.corr(j.live):+.3f}, "
        f"excess {j.x.corr(j.live):+.3f} ({len(j)} days)")
    yr = x.groupby(x.index.year).mean() * 1e4
    say("  by year (net excess bp/day): " + " ".join(f"{y % 100:02d}:{v:+.1f}" for y, v in yr.items()))
    if not judged:
        return
    rng = np.random.default_rng(1257)
    pl = []
    for _ in range(N_PLACEBO):
        p = book(rows, rng)
        pl.append(float((p.net - p.ew * (p.n > 0)).mean()))
    pl = np.array(pl); pct = (pl < x.mean()).mean() * 100
    say(f"  placebo (within-date shuffle of s, {N_PLACEBO} draws, net excess): mean {pl.mean() * 1e4:+.2f}bp 95th {np.percentile(pl, 95) * 1e4:+.2f} "
        f"-> real {x.mean() * 1e4:+.2f} at pct {pct:.0f}")
    g = [("net>=5bp", x.mean() >= 5e-4), ("t>=2.5", t_x >= 2.5), ("halves>0", x[hs].mean() > 0 and x[~hs].mean() > 0),
         ("2x tier_hi>0", x2.mean() > 0), ("ex-top5>0", srt[:-5].mean() > 0), ("placebo95", pct >= 95)]
    ok = all(o for _, o in g)
    say("  GATES: " + " | ".join(f"{n} {'PASS' if o else 'FAIL'}" for n, o in g) + f" -> {'PASS' if ok else 'KILL'}")
    say(f"  VERDICT N 1257 PCA-DAY: {'PASS' if ok else 'KILL'}")


def main():
    say("PCA-DAY (N 1257): AL s-score through close T (N 1242 base, adv_adj), buy the 20 most negative s < -1.25 at open T+1, sell close T+1;"
        f" nx tier_hi costs (2x shock); excess vs EW top-1000 open->close; DSR at N {N_PROGRAM}")
    master = nx.load_master(nx.Paths())
    act = pd.read_parquet(SRC["actions"], columns=["date", "action", "ticker", "value"])
    act["date"] = pd.to_datetime(act["date"])
    for w in WINDOWS:
        run_window(*w, act, master)
        gc.collect()


if __name__ == "__main__":
    main()
