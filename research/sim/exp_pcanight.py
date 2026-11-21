"""PCA-NIGHT (N 1253, pre-registered in round1_prose.md "Amendment - DEEP round 3a").

    OMP_NUM_THREADS=3 PYTHONPATH=. python3 -m research.sim.exp_pcanight

AL s-score (N 1242 base: top-1000 ADV20, Marchenko-Pastur factors refit every 5 sessions, 60d OU) computed from closes
through T-1. At the close of T buy the 20 most negative s (s < -1.25), equal weight; sell at the open of T+1.
Outcomes, delistings and costs through research/sim/nx.py (night_outcome, cost_model tier_hi / 2x_tier_hi).
Benchmark: EW overnight (close T -> open T+1, + ex-div) of the same top-1000 universe. JUDGE 2003-2015; REPORT 2016-2026-10.
Data: ~/data/sharadar for both windows.
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
from .exp_rl import dsr
from .sel_night import load_actions
from .weekwin_short import tstat

OUT = pathlib.Path(__file__).resolve().parent / "exp_pcanight_out.txt"
N_PROGRAM = 1253
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


# ------------------------------------------------------------------ NX live-rule night leg (independence)
def live_leg(lo: str, hi: str, master, act) -> pd.DataFrame:
    """nx.collect_trades on the primary universe, 2-year chunks (memory), SEP bars from the store."""
    cols = ["ticker", "date", "open", "high", "low", "close", "volume", "closeunadj"]
    out = []
    edges = list(pd.date_range(lo, hi, freq="2YS")) + [pd.Timestamp(hi) + pd.Timedelta(days=1)]
    if edges[0] > pd.Timestamp(lo):
        edges = [pd.Timestamp(lo)] + edges
    for a, b in zip(edges[:-1], edges[1:]):
        b = b - pd.Timedelta(days=1)
        bars = pd.read_parquet(SRC["sep"], columns=cols, filters=[("date", ">=", (a - pd.Timedelta(days=60)).date()),
                                                                  ("date", "<=", (b + pd.Timedelta(days=10)).date())])
        bars["date"] = pd.to_datetime(bars["date"])
        bars["closeunadj"] = bars["closeunadj"].where(np.isfinite(bars["closeunadj"]), bars["close"])
        bars = bars.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
        pn = nx.build_panel(bars); del bars
        col = nx.collect_trades(pn, master, act, "primary", a, b)
        del pn; gc.collect()
        out.append(pd.DataFrame({m: nx.leg_series(col["trades"], col["nights"], m) for m in ("tier", "tier_hi")}))
    return pd.concat(out)


# ------------------------------------------------------------------ PCA-NIGHT
def night_table(sessions, R, info, sig, w0, w1, mt, dprice, divs, lag):
    """Per night T in [w0, w1]: tradable names of sig[T-lag] (bar at T), their s, net outcome at tier_hi and 2x, EW bench."""
    D = len(sessions)
    cl, op, cu, dv, adv, names = info["close"], info["open"], info["cu"], info["div"], info["adv"], info["names"]
    lastbar = np.where(np.isfinite(cl), np.arange(D)[:, None], -1).max(0)
    rows, kinds = [], {}
    ts = np.flatnonzero((sessions >= pd.Timestamp(w0)) & (sessions <= pd.Timestamp(w1)))
    for t in ts:
        if t + 1 >= D or t - lag < 0 or sig[t - lag] is None:
            rows.append(None); continue
        idx, s, _ = sig[t - lag]
        ok = np.isfinite(cl[t, idx]) & (cu[t, idx] > 0)
        idx, s = idx[ok], s[ok]
        c0, u0 = cl[t, idx].astype(np.float64), cu[t, idx].astype(np.float64)
        hn = np.isfinite(cl[t + 1, idx]) & np.isfinite(op[t + 1, idx])
        with np.errstate(invalid="ignore", divide="ignore"):
            ret = op[t + 1, idx] / c0 - 1.0
            dy = dv[t + 1, idx] / u0
        ret = np.where((dy > 0) & (dy < 0.25), ret + dy, ret)
        for k in np.flatnonzero(~hn):
            j = idx[k]
            ret[k], kind = nx.night_outcome(names[j], c0[k], u0[k], np.nan, False, sessions[t], sessions[t + 1], mt,
                                            dprice, divs, lambda j=j: sessions[lastbar[j]])
            kinds[kind] = kinds.get(kind, 0) + 1
        kinds["open"] = kinds.get("open", 0) + int(hn.sum())
        a_prev = adv[t - 1, idx]                                   # prior-20 $ volume (through T-1), as NX
        c_hi = nx.cost_model("tier_hi", u0, a_prev) / 1e4
        c_2x = nx.cost_model("2x_tier_hi", u0, a_prev) / 1e4
        ew = float(np.nanmean(ret[hn])) if hn.any() else 0.0
        rows.append(dict(s=s, gross=ret, net=ret - 2 * c_hi, net2=ret - 2 * c_2x, ew=ew, idx=idx))
    return sessions[ts], rows, kinds


def book(rows, rng=None):
    """Equal-weight the K most negative s < -1.25 each night. Returns gross, net, net2, ew (0 on cash nights), n."""
    out = np.zeros((len(rows), 5))
    for r, g in enumerate(rows):
        if g is None:
            continue
        s = rng.permutation(g["s"]) if rng is not None else g["s"]
        o = np.argsort(s, kind="stable")
        o = o[s[o] < -S_BO][:K]
        if len(o) == 0:
            continue
        out[r] = (g["gross"][o].mean(), g["net"][o].mean(), g["net2"][o].mean(), g["ew"], len(o))
    return pd.DataFrame(out, columns=["gross", "net", "net2", "ew", "n"])


def run_window(tag, d0, d1, w0, w1, split, judged, mt, dprice, divs, act, master):
    say(f"\n=== {tag}: load {d0}..{d1}, nights {w0}..{w1} (halves split {split})")
    live = live_leg(w0, w1, master, act)
    say(f"  NX live rule (primary, nx.collect_trades): {live.tier.mean() * 1e4:+.2f}bp/night at tier, {live.tier_hi.mean() * 1e4:+.2f} at tier_hi"
        f" over {len(live)} nights (NEXT.md NX RESULT 2003-15 primary tier: +3.07bp)")
    gc.collect()
    sessions, R, cu, adv, spy, info = load_panel(d0, d1, src=SRC, want_open=True, prefilter=True, adv_adj=True)
    info["cu"], info["adv"] = cu, adv
    dl = int((np.where(np.isfinite(cu), np.arange(len(sessions))[:, None], -1).max(0) < len(sessions) - 5).sum())
    say(f"  panel: {info['D']} sessions x {info['N']} common names (ever $10M/day, split-adjusted $ volume); duplicate rows {info['dup']}; "
        f"delisted inside the panel {dl}; |ret|>50% cells {int((np.abs(R) > 0.5).sum())}; open missing where close present "
        f"{int((np.isfinite(info['close']) & ~np.isfinite(info['open'])).sum())}")
    sig, dg = build_signals(R, cu, adv, spy)
    say(f"  signal: first {sessions[dg['t_first']].date()}; universe mean {dg['nu'].mean():.0f}; MP factors kept mean {dg['nf'].mean():.2f} "
        f"(min {dg['nf'].min()}, max {dg['nf'].max()}); valid s/day {dg['nval'].mean():.0f}")
    nights, rows, kinds = night_table(sessions, R, info, sig, w0, w1, mt, dprice, divs, lag=1)
    _, rows0, _ = night_table(sessions, R, info, sig, w0, w1, mt, dprice, divs, lag=0)
    del R, info, cu, adv; gc.collect()
    b = book(rows); b.index = nights
    on = b.n > 0
    x, x2, xg = (b.net - b.ew * on), (b.net2 - b.ew * on), (b.gross - b.ew * on)
    say(f"  outcomes (all tradable names, all nights): {kinds}")
    say(f"  book: {len(b)} nights, {int(on.sum())} with picks; names/night {b.n[on].mean():.1f} (nights < {K}: {np.mean(b.n[on] < K):.1%}); "
        f"turnover 2.0/night (fresh basket, buy close + sell open)")
    say(f"  absolute: gross {b.gross.mean() * 1e4:+.2f}bp/night, net tier_hi {b.net.mean() * 1e4:+.2f} (t {tstat(b.net.to_numpy()):+.2f}), "
        f"2x {b.net2.mean() * 1e4:+.2f}; EW universe overnight {b.ew[on].mean() * 1e4:+.2f}bp")
    hs = x.index <= split
    srt = np.sort(x.to_numpy())
    t_x = tstat(x.to_numpy())
    say(f"  EXCESS vs EW: gross {xg.mean() * 1e4:+.2f}bp/night | net tier_hi {x.mean() * 1e4:+.2f}bp (NW t {t_x:+.2f}, {x.mean() * 252:+.1%}/yr) | "
        f"halves {x[hs].mean() * 1e4:+.2f} / {x[~hs].mean() * 1e4:+.2f} | 2x tier_hi {x2.mean() * 1e4:+.2f} | ex-top5 {srt[:-5].mean() * 1e4:+.2f} | "
        f"median night {np.median(x) * 1e4:+.2f} hit {(x > 0).mean():.2f} | DSR(N {N_PROGRAM}) {dsr(x.to_numpy(), N_PROGRAM):.3f}")
    b0 = book(rows0); b0.index = nights
    on0 = b0.n > 0
    say(f"  diagnostic (UNTRADABLE, s through close T): gross excess {(b0.gross - b0.ew * on0).mean() * 1e4:+.2f}bp/night, "
        f"net tier_hi excess {(b0.net - b0.ew * on0).mean() * 1e4:+.2f}")
    j = pd.concat([b.net.rename("pca"), x.rename("x"), live.tier_hi.rename("live")], axis=1).dropna()
    say(f"  independence: daily corr with the NX live night leg (tier_hi) — book net {j.pca.corr(j.live):+.3f}, excess {j.x.corr(j.live):+.3f} "
        f"({len(j)} nights)")
    yr = x.groupby(x.index.year).mean() * 1e4
    say("  by year (net excess bp/night): " + " ".join(f"{y % 100:02d}:{v:+.1f}" for y, v in yr.items()))
    if not judged:
        return
    rng = np.random.default_rng(1253)
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
    say(f"  VERDICT N 1253 PCA-NIGHT: {'PASS' if ok else 'KILL'}")


def main():
    say("PCA-NIGHT (N 1253): AL s-score through T-1 (N 1242 base), buy the 20 most negative s < -1.25 at close T, sell open T+1;"
        f" nx tier_hi costs (2x shock), NX delisting rules; excess vs EW top-1000 overnight; DSR at N {N_PROGRAM}")
    master = nx.load_master(nx.Paths())
    mt = nx.master_by_ticker(master)
    dprice, divs = load_actions()
    act = pd.read_parquet(SRC["actions"], columns=["date", "action", "ticker", "value"])
    act["date"] = pd.to_datetime(act["date"])
    for w in WINDOWS:
        run_window(*w, mt, dprice, divs, act, master)
        gc.collect()


if __name__ == "__main__":
    main()
