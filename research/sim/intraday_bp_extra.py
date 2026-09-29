"""intraday_bp follow-ups (POST-HOC, labelled; at most SHADOW):
  exact MC P(DD) for every row; deflated Sharpe of the increments (N = 546 + 5 = 551);
  P1: Kelly x1.5 at the multiplier the live code reads today (2.48) -- i.e. only the target vol changes;
  P2: Kelly x1.5 at mult 2 (no buying-power change at all).

    PYTHONPATH=. .venv/bin/python -m research.sim.intraday_bp_extra
"""
from __future__ import annotations

import pickle

import pandas as pd

from . import book as B
from . import growth as G
from . import intraday_bp as IB
from . import macro_events as ME
from . import program_books as PB
from . import rawprice as RP
from . import taxable_frontier as TF
from .validate import load_sim

N_ALL = 546 + IB.N_VARIANTS + 2


def main():
    o = pickle.load(open(IB.OUT, "rb"))
    res = o["res"]
    print("== exact MC (EH, after tax, $3k+$1k/mo, 5y): tier_hi P30 / P50 net (raw balance)")
    for bl in IB.BOOKS:
        for vl in IB.VARS:
            m = res[(bl, vl, "tier_hi")]["mc"]; m3 = res[(bl, vl, 3.0)]["mc"]
            print(f"  {bl:15s} {vl:18s} tier_hi P30 {m['dd30']*100:5.1f} ({m['dd30_acct']*100:5.1f}) P50 {m['dd50']*100:4.1f} "
                  f"({m['dd50_acct']*100:4.1f}) | 3bp P30 {m3['dd30']*100:5.1f} P50 {m3['dd50']*100:4.1f}")
    print(f"\n== deflated Sharpe of increments vs M2 base (N = {N_ALL})")
    for bl in IB.BOOKS:
        for vl in list(IB.VARS)[1:]:
            for cost in (3.0, "tier_hi"):
                d = (res[(bl, vl, cost)]["r"] - res[(bl, "M2 base", cost)]["r"]).dropna()
                a = PB.dsr(d, N_ALL)
                print(f"  {bl:15s} {vl:18s} {str(cost):>8s} SR {a['sr_ann']:5.2f} t {a['t']:5.2f} DSR {a['dsr']:.3f}")

    # post-hoc rows
    IB.S_NZ0 = None
    s = load_sim(raw_price=True)
    rp = pickle.load(open(RP.CACHE, "rb"))
    me = pickle.load(open(ME.CACHE, "rb"))
    IB.S_NZ0 = {k: s.NZ[k] for k in G.S2}
    IB.S_BO0 = me["legs"][4]
    print("\n== POST-HOC: Kelly x1.5 without the multiplier fix (P1 mult 2.48, P2 mult 2)")
    for bl, (g, cap, conv) in IB.BOOKS.items():
        for lab, mult in (("P1 m2.48 Kelly", 2.48), ("P2 m2 Kelly", 2.0)):
            for cost in (3.0, "tier_hi"):
                df, tr, kw = IB.replay(s, rp["raw"][cap], g, conv, mult, 1.5, cost)
                e = G.eh(df); eat, _ = TF.after_tax(e, 0.35, trades=tr)
                b = res[(bl, "M2 base", cost)]
                m = TF.mc_tax(e, 0.35, start=3000, monthly=1000)
                d = (df.r - b["r"]).dropna()
                dd = [B.stats(df.r[a:z])[0] - B.stats(b["r"][a:z])[0] for _, a, z in PB.PER]
                print(f"  {bl:15s} {lab:16s} cap {kw['noise_cap']:4.2f} {str(cost):>8s} {PB.halves(df.r)} | EH-AT "
                      f"{B.stats(eat)[0]*100:5.1f} (d {100*(B.stats(eat)[0]-B.stats(b['eh_at'])[0]):+5.2f}pp) | "
                      f"d halves {dd[0]*100:+5.1f}/{dd[1]*100:+5.1f} t {TF.nw_t(d):5.2f} | MC P30 {m['dd30']:.0%} "
                      f"({m['dd30_acct']:.0%}) P50 {m['dd50']:.1%} ({m['dd50_acct']:.1%})", flush=True)


if __name__ == "__main__":
    main()
