"""DEEP round 3b, N 1255 VOLRATIO: weekly sd(60d) / sd(20d) of daily returns, long the top decile (calm recently vs the past).

Pre-registration: research/drafts/round1_prose.md, "## Amendment - DEEP round 3b" (N 1253 -> 1255). Not tuned.

    PYTHONPATH=. python3 research/sim/exp_volratio.py        # -> research/sim/exp_volratio_out.txt

Pipeline as N 1243 (research/sim/exp_sig.py): ~/data/sharadar SEP common (nx.is_common), delisted kept through their last bar;
calendar = ~/data/sharadar SPY sessions; decisions = sessions LB=60, 65, 70, ... (exp_sig `np.arange(LB, S - H, STEP)`), so the
weeks are exactly N 1243/N 1251's; eligible at T = bar at T with a finite return, closeunadj >= $5, ADV20 >= $10M, >= 60 bars
(bars counted from the 2010-01 load start; only 2011+ decisions are used). Features use sessions T-59..T with no-bar days = 0
(exp_sig convention). Ratio = sd(60 daily returns) / max(sd(last 20), 1e-4). Forward = compounded total return T+1..T+5 (no
later bar = 0). Long top decile EW (n // 10, ties by code), turnover sum |dw|, 5bp/side; excess vs the universe EW.
Gates as N 1251 (exp_sig2): net >= +15bp/wk, NW(4) t >= 2.5, halves 2011-18 / 2019-26 > 0, ex-top-5 > 0, 2x cost > 0,
beta-matched excess > 0 = long net - [EW + (beta_port - 1) x SPY 5d], beta_port = OLS slope of weekly long gross on SPY 5d over
the judge window. JUDGE 2011-01..2026-10. DSR at N 1255.
Report: the bottom decile, and the weekly corr of the top-decile excess with the ret5-reversal decile (lowest 5-day return).
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "3")

import pathlib  # noqa: E402
import sys  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from research.sim.exp_rl import dsr  # noqa: E402
from research.sim.exp_tail import _read, FULL  # noqa: E402
from research.sim.exp_rl_universe import PRICE_MIN, ADV_MIN  # noqa: E402
from research.sim.weekwin_short import tstat  # noqa: E402
from research.sim.nx import is_common  # noqa: E402

OUT = ROOT / "research/sim/exp_volratio_out.txt"
N_TRIALS = 1255
COST, SHOCK = 5e-4, 10e-4
H, STEP, LB, NW = 5, 5, 60, 4
J0, J_END, H1_END = pd.Timestamp("2011-01-01"), pd.Timestamp("2026-10-31"), pd.Timestamp("2018-12-31")
LOAD = "2010-01-01"

lines: list[str] = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    lines.append(s)


def load(sessions, dec):
    tk = pd.read_parquet(FULL / "tickers.parquet", columns=["table", "ticker", "category"])
    tk = tk[tk.table == "SEP"].drop_duplicates("ticker")
    common = sorted(set(tk.ticker[is_common(tk.category.fillna("").astype(str))]))
    S = len(sessions); is_dec = np.zeros(S, bool); is_dec[dec] = True
    keep, el = [], []
    nch = 6
    for ci in range(nch):
        d = _read(FULL / "stocks.parquet", common[ci::nch], LOAD, FULL / "actions.parquet", sessions)
        ok = is_dec[d["sidx"]] & (d["cu"] >= PRICE_MIN) & (d["adv"] >= ADV_MIN) & (d["pos"] >= LB) & np.isfinite(d["ret"])
        codes = np.unique(d["code"][ok])
        sel = np.isin(d["code"], codes)
        keep.append((d["names"][d["code"][sel]], d["sidx"][sel], d["ret"][sel]))
        el.append((d["names"][d["code"][ok]], d["sidx"][ok]))
        del d, ok, sel
    nm = np.unique(np.concatenate([k[0] for k in el]).astype(str))
    ix = {t: i for i, t in enumerate(nm)}
    R = np.full((S, len(nm)), np.nan, np.float32)
    for names, si, r in keep:
        R[si, np.array([ix[x] for x in names.astype(str)])] = r
    E = pd.DataFrame({"s": np.concatenate([e[1] for e in el]),
                      "c": np.concatenate([np.array([ix[x] for x in e[0].astype(str)]) for e in el])})
    groups = E.groupby("s")["c"].apply(np.sort)
    return R, groups, nm


def main():
    say("VOLRATIO (N 1255): weekly sd60/sd20 of daily returns, long top decile EW close T -> T+5, ~/data/sharadar SEP common $5+ ADV20 $10M+"
        " >= 60 bars (N 1243 eligible set, delisted kept); 5bp/side, shock 10bp; excess vs universe EW; JUDGE 2011-01..2026-10; DSR N 1255")
    sp = _read(FULL / "funds.parquet", ["SPY"], "1990-01-01", FULL / "actions.parquet")
    sessions = sp["sessions"]; spy_r = np.nan_to_num(sp["ret"].astype(np.float64))
    S = len(sessions); dates = pd.DatetimeIndex(sessions)
    dec = np.arange(LB, S - H, STEP)
    dec = dec[(dates[dec] >= J0) & (dates[dec] <= J_END)]
    R, groups, nm = load(sessions, dec)
    say(f"sessions {dates[0].date()}..{dates[-1].date()}, decisions {len(dec)} ({dates[dec[0]].date()}..{dates[dec[-1]].date()}), names {len(nm)}, R {R.nbytes / 1e6:.0f}MB")
    rec = {k: [] for k in ("date", "n", "EW", "SPY", "L", "B", "V", "TL", "TB", "TV")}
    wp = {"L": {}, "B": {}, "V": {}}
    corr_rv = []
    for s in dec:
        if s not in groups.index:
            continue
        c = groups.loc[s]
        if len(c) < 20:
            continue
        W = np.nan_to_num(R[s - LB + 1:s + 1][:, c].astype(np.float64))
        F = np.nan_to_num(R[s + 1:s + H + 1][:, c].astype(np.float64))
        ratio = W.std(0, ddof=1) / np.maximum(W[-20:].std(0, ddof=1), 1e-4)
        ret5 = np.expm1(np.log1p(np.maximum(W[-5:], -0.99)).sum(0))
        fw = np.prod(1 + F, axis=0) - 1
        n = len(c); m = max(1, n // 10)
        o = np.lexsort((c, -ratio)); top, bot = o[:m], o[-m:]
        rv = np.lexsort((c, ret5))[:m]          # ret5-reversal decile = the 5-day losers
        corr_rv.append(np.corrcoef(pd.Series(ratio).rank(), pd.Series(ret5).rank())[0, 1])
        rec["date"].append(dates[s]); rec["n"].append(n); rec["EW"].append(fw.mean())
        rec["SPY"].append(np.prod(1 + spy_r[s + 1:s + H + 1]) - 1)
        for key, ids, tk in (("L", top, "TL"), ("B", bot, "TB"), ("V", rv, "TV")):
            nw_ = {int(x): 1.0 / m for x in c[ids]}
            rec[key].append(fw[ids].mean())
            rec[tk].append(sum(abs(nw_.get(x, 0) - wp[key].get(x, 0)) for x in set(nw_) | set(wp[key])))
            wp[key] = nw_
    T = pd.DataFrame(rec)
    x = (T.L - COST * T.TL - T.EW).to_numpy(); x2 = (T.L - SHOCK * T.TL - T.EW).to_numpy()
    h1 = (T.date <= H1_END).to_numpy()
    srt = np.sort(x)
    bp = np.polyfit(T.SPY, T.L, 1)[0]; bew = np.polyfit(T.SPY, T.EW, 1)[0]
    bm = (T.L - COST * T.TL - (T.EW + (bp - 1) * T.SPY)).to_numpy()
    t_ = tstat(x, NW)
    ds = dsr(x, N_TRIALS)
    say(f"\n=== JUDGE 2011-01..2026-10 ({len(T)} weeks; halves 2011-18 / 2019-26); eligible names/week {T.n.mean():.0f}, decile {T.n.mean() / 10:.0f}")
    say(f"  TOP decile (high sd60/sd20): net excess {x.mean() * 1e4:+.1f}bp/wk t {t_:+.2f} | gross {(T.L - T.EW).mean() * 1e4:+.1f} | 2x cost {x2.mean() * 1e4:+.1f}"
        f" | halves {x[h1].mean() * 1e4:+.1f} / {x[~h1].mean() * 1e4:+.1f} | ex-top5 {srt[:-5].mean() * 1e4:+.1f} | median {np.median(x) * 1e4:+.1f}"
        f" hit {(x > 0).mean():.2f} | turnover {T.TL.mean():.2f}/wk")
    say(f"    beta_port {bp:.2f} (EW {bew:.2f}); beta-matched excess {bm.mean() * 1e4:+.1f}bp/wk t {tstat(bm, NW):+.2f} | raw long {T.L.mean() * 1e4:+.1f}"
        f" EW {T.EW.mean() * 1e4:+.1f} SPY {T.SPY.mean() * 1e4:+.1f} | DSR (N {N_TRIALS}) {ds:.3f} | ceiling {x.mean() * 52 * 100:+.1f}pp/yr")
    bx = (T.B - COST * T.TB - T.EW).to_numpy()
    say(f"  REPORT bottom decile (low ratio = vol rising): net excess {bx.mean() * 1e4:+.1f}bp/wk t {tstat(bx, NW):+.2f} (gross {(T.B - T.EW).mean() * 1e4:+.1f});"
        f" top-minus-bottom gross {(T.L - T.B).mean() * 1e4:+.1f}bp/wk t {tstat((T.L - T.B).to_numpy(), NW):+.2f}")
    vx = (T.V - COST * T.TV - T.EW).to_numpy(); gx = (T.L - T.EW).to_numpy(); gv = (T.V - T.EW).to_numpy()
    resid = gx - np.polyfit(gv, gx, 1)[0] * gv
    say(f"  REPORT ret5-reversal decile (5-day losers): net excess {vx.mean() * 1e4:+.1f}bp/wk t {tstat(vx, NW):+.2f} (gross {gv.mean() * 1e4:+.1f}, turnover {T.TV.mean():.2f});"
        f" weekly corr(top-decile excess, reversal excess) {np.corrcoef(gx, gv)[0, 1]:+.2f}; top excess net of its reversal loading"
        f" {resid.mean() * 1e4:+.1f}bp/wk gross (slope {np.polyfit(gv, gx, 1)[0]:+.2f}); mean cross-sectional rank corr(ratio, ret5) {np.mean(corr_rv):+.3f}")
    g = [("net>=15bp", x.mean() >= 15e-4), ("t>=2.5", t_ >= 2.5), ("halves", x[h1].mean() > 0 and x[~h1].mean() > 0),
         ("ex-top5", srt[:-5].mean() > 0), ("2xcost", x2.mean() > 0), ("beta-matched", bm.mean() > 0)]
    say("  GATES: " + " | ".join(f"{n} {'PASS' if ok else 'FAIL'}" for n, ok in g) + f" -> {'PASS' if all(o for _, o in g) else 'KILL'}")
    OUT.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
