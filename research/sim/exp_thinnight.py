"""THIN-NIGHT (N 1256, pre-registered in round1_prose.md "Amendment - DEEP round 3c").

    OMP_NUM_THREADS=3 PYTHONPATH=. python3 -m research.sim.exp_thinnight

The exact NX live rule (nx.collect_trades, primary universe, all registered filters and caps) with the ADV20 band
changed to [$2M, $10M) (nx ADV = prior-20 split-adjusted close x volume). Cost tier_hi + 10bp/side (nx cost model
"tier_hi_thin"), shock 2x. JUDGE 2003-2015, REPORT 2016-2026-10. Data: ~/data/sharadar SEP (as sel_night).
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
from .exp_rl import dsr
from .weekwin_short import tstat

OUT = pathlib.Path(__file__).resolve().parent / "exp_thinnight_out.txt"
STORE = nx.store_dir()
N_PROGRAM = 1256
THIN = (2e6, 1e7)
LIVE = (nx.ADV_MIN, np.inf)
WINDOWS = [("JUDGE 2003-2015", "2003-01-02", "2015-12-31", True),
           ("REPORT 2016-2026-10 (never judged)", "2016-01-01", "2026-10-05", False)]
SUBS = {"2003-07": ("2003", "2007"), "2008-09": ("2008", "2009"), "2010-15": ("2010", "2015")}
SUBS_R = {"2016-20": ("2016", "2020"), "2021-26": ("2021", "2026")}

L: list[str] = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    L.append(s)
    OUT.write_text("\n".join(L) + "\n")


def collect(lo: str, hi: str, master, act):
    """nx.collect_trades for the thin and the live band, 2-year chunks of SEP bars (memory)."""
    cols = ["ticker", "date", "open", "high", "low", "close", "volume", "closeunadj"]
    lo, hi = pd.Timestamp(lo), pd.Timestamp(hi)
    edges = [lo] + [d for d in pd.date_range(lo, hi, freq="2YS") if d > lo] + [hi + pd.Timedelta(days=1)]
    tr = {"thin": [], "live": []}; nights = []
    for a, b in zip(edges[:-1], edges[1:]):
        b = b - pd.Timedelta(days=1)
        bars = pd.read_parquet(STORE / "stocks.parquet", columns=cols,
                               filters=[("date", ">=", (a - pd.Timedelta(days=60)).date()),
                                        ("date", "<=", (b + pd.Timedelta(days=10)).date())])
        bars["date"] = pd.to_datetime(bars["date"])
        bars["closeunadj"] = bars["closeunadj"].where(np.isfinite(bars["closeunadj"]), bars["close"])
        for c in ("open", "high", "low"):
            bars[c] = bars[c].astype(np.float32)
        bars = bars.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
        pn = nx.build_panel(bars); del bars
        for k, band in (("thin", THIN), ("live", LIVE)):
            col = nx.collect_trades(pn, master, act, "primary", a, b, adv_band=band)
            t = col["trades"]
            if len(t):
                t = t.assign(o_print=np.isfinite(pn["o_next"][t.row.astype(int)]) & (pn["o_next"][t.row.astype(int)] > 0))
            tr[k].append(t)
        nights.append(col["nights"])
        del pn; gc.collect()
    return {k: pd.concat(v, ignore_index=True) for k, v in tr.items()}, nights[0].append(nights[1:]) if len(nights) > 1 else nights[0]


def run_window(tag, lo, hi, judged, master, act):
    say(f"\n=== {tag}: nights {lo}..{hi}")
    tr, nights = collect(lo, hi, master, act)
    t, tl = tr["thin"], tr["live"]
    Lt = nx.leg_series(t, nights, "tier_hi_thin"); Lx = nx.leg_series(t, nights, "2x_tier_hi_thin")
    Lg = nx.leg_series(t, nights, 0.0)
    Ll = nx.leg_series(tl, nights, "tier_hi")
    kinds = t["kind"].value_counts().to_dict() if len(t) else {}
    say(f"  thin band [$2M, $10M): {len(t)} trades on {int((Lt != 0).sum())} of {len(nights)} nights; outcome kinds {kinds}; "
        f"open print on the exit session {t.o_print.mean():.1%} of picks; mean leg weight/name {t.per.mean():.3f}")
    say(f"  live band (check): {len(tl)} trades; tier_hi {Ll.mean() * 1e4:+.2f}bp/night, tier {nx.leg_series(tl, nights, 'tier').mean() * 1e4:+.2f}"
        " (NEXT.md NX RESULT 2003-15 primary tier: +3.07)")
    subs = SUBS if judged else SUBS_R
    sub = {k: Lt[(Lt.index >= f"{a}-01-01") & (Lt.index <= f"{b}-12-31")].mean() for k, (a, b) in subs.items()}
    srt = np.sort(Lt.to_numpy()); t_nw = tstat(Lt.to_numpy())
    net = t.ret.to_numpy() - 2 * nx.cost_model("tier_hi_thin", t.cu.to_numpy(), t.adv.to_numpy()) / 1e4
    say(f"  leg: gross {Lg.mean() * 1e4:+.2f}bp/night | net tier_hi+10 {Lt.mean() * 1e4:+.2f}bp (NW t {t_nw:+.2f}; iid t {nx.tstat(Lt):+.2f}) | "
        "subperiods " + " ".join(f"{k} {v * 1e4:+.2f}" for k, v in sub.items()) +
        f" | 2x cost {Lx.mean() * 1e4:+.2f} | ex-top5 {srt[:-5].mean() * 1e4:+.2f} | median night {Lt.median() * 1e4:+.2f} | "
        f"per-trade median net {np.median(net) * 1e4:+.1f}bp hit {(net > 0).mean():.1%} | DSR(N {N_PROGRAM}) {dsr(Lt.to_numpy(), N_PROGRAM):.3f}")
    say(f"  mean round-trip cost {2 * nx.cost_model('tier_hi_thin', t.cu.to_numpy(), t.adv.to_numpy()).mean():.1f}bp; per-trade gross mean "
        f"{t.ret.mean() * 1e4:+.1f}bp median {t.ret.median() * 1e4:+.1f}bp")
    say(f"  context (not gated): net at plain tier_hi {nx.leg_series(t, nights, 'tier_hi').mean() * 1e4:+.2f}bp/night, at tier "
        f"{nx.leg_series(t, nights, 'tier').mean() * 1e4:+.2f}; share of picks priced < $10 {(t.cu < 10).mean():.1%}")
    tt = t.assign(net=net)
    say("  per-trade net by ADV: " + " | ".join(
        f"${a / 1e6:.0f}-{b / 1e6:.0f}M n {len(g)} mean {g.net.mean() * 1e4:+.1f}bp median {g.net.median() * 1e4:+.1f}"
        for a, b in ((2e6, 4e6), (4e6, 7e6), (7e6, 1e7)) for g in [tt[(tt.adv >= a) & (tt.adv < b)]]))
    for eq in (1e4, 2.5e4):
        say(f"  participation at ${eq / 1e3:.0f}k (whole account in the leg, $ = per x equity): share of trades > 1% of ADV20 "
            f"{(t.per * eq > 0.01 * t.adv).mean():.1%}; median $ {np.median(t.per * eq):.0f} vs median ADV ${np.median(t.adv) / 1e6:.1f}M")
    j = pd.concat([Lt.rename("thin"), Ll.rename("live")], axis=1)
    say(f"  independence: daily corr with the live-band night leg (tier_hi) {j.thin.corr(j.live):+.3f}; "
        f"nights both trade {int(((j.thin != 0) & (j.live != 0)).sum())}")
    comb = 0.5 * (j.thin + j.live)
    say(f"  combined at $10k (50/50 of the night capital, live tier_hi + thin): {comb.mean() * 1e4:+.2f}bp/night (t {tstat(comb.to_numpy()):+.2f}) "
        f"vs live alone {Ll.mean() * 1e4:+.2f} (t {tstat(Ll.to_numpy()):+.2f})")
    yr = Lt.groupby(Lt.index.year).mean() * 1e4
    say("  by year (net bp/night): " + " ".join(f"{y % 100:02d}:{v:+.1f}" for y, v in yr.items()))
    if not judged:
        return
    g = [("net>=3bp", Lt.mean() >= 3e-4), ("NW t>=2.5", t_nw >= 2.5), ("3 subperiods>0", all(v > 0 for v in sub.values())),
         ("ex-top5>0", srt[:-5].mean() > 0), ("2x cost>0", Lx.mean() > 0)]
    ok = all(o for _, o in g)
    say("  GATES: " + " | ".join(f"{n} {'PASS' if o else 'FAIL'}" for n, o in g) + f" -> {'PASS' if ok else 'KILL'}")
    say(f"  VERDICT N 1256 THIN-NIGHT: {'PASS' if ok else 'KILL'}")


def main():
    say("THIN-NIGHT (N 1256): exact NX live rule (nx.collect_trades, primary) with ADV20 in [$2M, $10M); cost tier_hi + 10bp/side,"
        f" shock 2x; NX delisting rules; DSR at N {N_PROGRAM}")
    master = nx.load_master(nx.Paths())
    act = pd.read_parquet(STORE / "actions.parquet", columns=["date", "action", "ticker", "value"])
    act["date"] = pd.to_datetime(act["date"])
    for w in WINDOWS:
        run_window(*w, master, act)
        gc.collect()


if __name__ == "__main__":
    main()
