"""Study V: night-leg capacity at the auctions (report).

    PYTHONPATH=. .venv/bin/python -m research.sim.night_capacity

Stamp: research/drafts/round1_prose.md, "Round 9" (commit 9673e20). Entry = the 16:00 bar on d
(lm1), exit = the 09:30 bar on d+1 (am1); both include that minute's continuous trading, so the
auction depth is overstated and capacity is a best case. Impact per side = Y sigma sqrt(p).
"""
from __future__ import annotations

import glob
import os
import time

import numpy as np
import pandas as pd

from . import book as B
from .night_filings import FULL, PER, ROOT

OUT = ROOT / "data/research/program/night_capacity_out.txt"
LM1 = ROOT / "data/research/night/lm1"
AM1 = ROOT / "data/research/night/am1"
SIZES = (2_300, 25_000, 100_000, 250_000, 500_000, 1_000_000, 2_500_000, 5_000_000)
LIVE_COST = 1.0


def bar_dollars(folder, hm: int) -> dict:
    """session -> {sym: dollar volume of the hh:mm bar}."""
    out = {}
    for f in sorted(glob.glob(str(folder / "*.parquet"))):
        df = pd.read_parquet(f, columns=["symbol", "timestamp", "volume", "vwap", "close"])
        t = df.timestamp.dt.tz_convert("America/New_York")
        df = df[t.dt.hour * 100 + t.dt.minute == hm]
        px = df.vwap.fillna(df.close)
        out[pd.Timestamp(os.path.basename(f)[:10])] = dict(zip(df.symbol, df.volume * px))
    return out


def main():
    t0 = time.time()
    fs = open(OUT, "w")

    def log(*a):
        s_ = " ".join(str(x) for x in a)
        print(s_, flush=True)
        fs.write(s_ + "\n")
        fs.flush()

    log("== Study V: night-leg capacity at the auctions, started", pd.Timestamp.now(), "\n")
    N = B.night_days(raw_price=True, max_corr=0.7)
    close_bar = bar_dollars(LM1, 1600)
    open_bar = bar_dollars(AM1, 930)
    sess = B.D.returns20().index
    nxt = {d: sess[i + 1] for i, d in enumerate(sess[:-1])}
    rows = []
    for d, nd in N.items():
        d = pd.Timestamp(d)
        if not (pd.Timestamp(FULL[0]) <= d <= pd.Timestamp(FULL[1])):
            continue
        for j, s in enumerate(nd.syms):
            rows.append(dict(d=d, sym=s, ret=nd.ret[j], vol=nd.vol20[j], adv=nd.adv[j],
                             w=min(nd.frac, 0.10),
                             cbar=close_bar.get(d, {}).get(s, np.nan),
                             obar=open_bar.get(nxt.get(d), {}).get(s, np.nan)))
    T = pd.DataFrame(rows)
    ok = T.cbar.notna() & T.obar.notna() & (T.cbar > 0) & (T.obar > 0)
    log(f"picks {len(T)}; with both auction bars {ok.sum()} ({ok.mean():.0%})")
    S = T[ok].copy()
    log(f"  closing bar $ median {S.cbar.median() / 1e3:,.0f}k (= {np.median(S.cbar / S.adv):.1%} of ADV); "
        f"opening bar $ median {S.obar.median() / 1e3:,.0f}k (= {np.median(S.obar / S.adv):.1%} of ADV)")
    g0 = (S.ret * S.w).sum() / S.w.sum() * 1e4
    log(f"  weighted gross {g0:+.1f}bp/trade on this subset (all picks: "
        f"{(T.ret * T.w).sum() / T.w.sum() * 1e4:+.1f})\n")
    sig = S.vol / np.sqrt(252) * 1e4        # daily sd, bp
    days = sess[(sess >= FULL[0]) & (sess <= FULL[1])]
    yrs = len(days) / 252

    for Y in (0.5, 1.0):
        log(f"## Y = {Y}  (impact per side = Y x sigma_daily x sqrt(participation))")
        log(f"{'equity':>11s} {'net bp/trade':>12s} {'impact bp rt':>12s} {'p>10%':>6s} {'p>25%':>6s}"
            f" {'leg pp/yr':>9s} {'21-23':>7s} {'24-26':>7s} {'$/yr':>11s}")
        base_net = None
        halves = {}
        for E in SIZES:
            q = 0.5 * E * S.w
            pc, po = q / S.cbar, q / S.obar
            imp = Y * sig * (np.sqrt(pc) + np.sqrt(po))
            net = S.ret * 1e4 - 2 * LIVE_COST - imp
            nbp = (net * S.w).sum() / S.w.sum()
            base_net = nbp if base_net is None else base_net
            inc = (0.5 * S.w * net / 1e4).groupby(S.d).sum().reindex(days).fillna(0)
            pp = inc.sum() / yrs * 100
            hv = [inc[a:b].sum() / (len(inc[a:b]) / 252) * 100 for _, a, b in PER]
            halves[E] = (nbp, pp)
            big = np.maximum(pc, po)
            log(f"${E:>10,} {nbp:+12.1f} {(imp * S.w).sum() / S.w.sum():12.1f} {(big > .10).mean():6.1%}"
                f" {(big > .25).mean():6.1%} {pp:+9.1f} {hv[0]:+7.1f} {hv[1]:+7.1f} {pp / 100 * E:>11,.0f}")
        half_at = next((E for E, (n, _) in halves.items() if n <= base_net / 2), None)
        zero_at = next((E for E, (n, _) in halves.items() if n <= 0), None)
        peak = max(halves, key=lambda E: halves[E][1] / 100 * E)
        log(f"  edge halves by: {'>' if half_at is None else ''}${half_at or SIZES[-1]:,}; "
            f"reaches 0 by: {'>' if zero_at is None else ''}${zero_at or SIZES[-1]:,}; "
            f"$/yr peaks on this grid at ${peak:,}\n")
    log("(the leg's pp/yr is on the leg's 0.5 share of equity, subset with auction bars only;\n"
        " bars overstate auction depth, so real capacity is LOWER than shown)")
    log(f"\ndone in {time.time() - t0:4.0f} s")


if __name__ == "__main__":
    main()
