"""Cross-asset scan of the LIVE IBS rule's core mechanism.

The one durable edge in this project is close-in-range reversal ("IBS<0.2"), proven
OOS on US-equity ETFs 2016-2020 (research/sim/ibs_oos.py). The live leg only ever trades
the 18 EQ18 US-equity ETFs. This scan asks the brief's question: is the mechanism a
general liquidity-provision/liquidity-shock effect, or is it US-equity-specific?

For every ETF in data/research/night/etf_daily.parquet (40 symbols, 2016-2026, incl.
bonds TLT/IEF/SHY/HYG, commodities GLD/SLV/USO, international EEM/EFA/FXI/KWEB,
leveraged SOXL/TQQQ/UPRO/... and inverse/vol SQQQ/UVXY) it computes the exact live
return: signal = IBS(close d) < 0.2, buy at open(d+1), sell at open(d+2); return =
open(d+2)/open(d+1) - 1.

It reports the CONDITIONAL mean minus the unconditional mean (the "IBS premium") so the
raw dividend/level bias of unadjusted prices cancels. Columns:
  n, cond_bp, uncond_bp, prem_bp, t(cond - uncond, paired by day), med_bp, hit%,
  2016-20 prem, 2021-26 prem, #years pos.
No pre-registration / no N: this is a mechanism-generalization scan (audit), not a new
strategy. Any survivor must be registered before it is traded.

Run: PYTHONPATH=. .venv/bin/python research/sim/ibs_xasset_scan.py
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from . import data as D

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/ibs_xasset_out.txt"

GROUPS = {
    "US equity": ["SPY", "QQQ", "IWM", "DIA", "MDY", "XLK", "XLF", "XLE", "XLV",
                  "XLI", "XLY", "XLP", "XLU", "XLB", "SMH", "XBI", "ARKK"],
    "intl equity": ["EEM", "EFA", "FXI", "KWEB"],
    "bonds": ["TLT", "IEF", "SHY", "HYG", "BIL"],
    "commodities": ["GLD", "SLV", "USO"],
    "leveraged long": ["SOXL", "TQQQ", "UPRO", "SPXL", "TECL", "LABU", "FAS", "TNA", "UDOW"],
    "inverse / vol": ["SQQQ", "UVXY"],
}


def _stats(sym, O, H, L, C, ibs_max=0.2):
    o1 = O.shift(-1)              # open d+1
    o2 = O.shift(-2)              # open d+2
    fwd = (o2 / o1 - 1.0)         # live open-to-open return
    rng = (H - L)
    ibs = (C - L) / rng.where(rng > 0)
    ok = np.isfinite(fwd) & np.isfinite(ibs) & fwd.abs().lt(0.5)
    sig = (ibs < ibs_max) & ok
    nonsig = (~(ibs < ibs_max)) & ok & np.isfinite(ibs)
    c, a = fwd[sig].dropna(), fwd[nonsig].dropna()
    if len(c) < 40 or len(a) < 40:
        return None
    # two-sample t of signal-day vs non-signal-day open-to-open returns
    se = np.sqrt(c.var() / len(c) + a.var() / len(a))
    t = (c.mean() - a.mean()) / se if se > 0 else 0.0
    allmean = fwd[ok].mean()
    halves = {}
    for lab, lo, hi in [("h1", "2016", "2020"), ("h2", "2021", "2026")]:
        cm = fwd[sig].loc[lo:hi].mean()
        am = fwd[nonsig].loc[lo:hi].mean()
        halves[lab] = cm - am
    yr = pd.DataFrame({"sig": fwd[sig], "non": fwd[nonsig]})
    yrprem = yr.groupby(lambda i: i.year).mean()
    yrprem["prem"] = yrprem["sig"] - yrprem["non"]
    npos = int((yrprem["prem"] > 0).sum()); ny = int(yrprem["prem"].notna().sum())
    return dict(sym=sym, n=len(c), cond=c.mean(), uncond=a.mean(),
                prem=c.mean() - a.mean(), t=t, med=c.median(),
                hit=(c > 0).mean(), h1=halves["h1"], h2=halves["h2"],
                ypos=f"{npos}/{ny}")


def main():
    P = D.etf()
    O, H, L, C = P["open"], P["high"], P["low"], P["close"]
    rows = []
    for g, syms in GROUPS.items():
        for s in syms:
            if s not in C.columns:
                continue
            st = _stats(s, O[s], H[s], L[s], C[s])
            if st:
                st["group"] = g
                rows.append(st)
    r = pd.DataFrame(rows)
    b = 1e4
    r = r.sort_values(["group", "prem"], ascending=[True, False])
    lines = ["Cross-asset scan of the IBS<0.2 close-in-range reversal mechanism (2016-2026)",
             "signal = IBS(close d)<0.2; buy open(d+1), sell open(d+2); RAW prices;",
             "prem = conditional - unconditional mean (bp). Positive & stable = effect generalizes.",
             ""]
    lines.append(f"{'sym':6s} {'group':15s} {'n':>4s} {'cond':>7s} {'uncond':>7s} "
                 f"{'prem':>6s} {'t':>5s} {'med':>6s} {'hit':>4s} {'16-20':>6s} "
                 f"{'21-26':>6s} {'yr+':>5s}")
    for _, x in r.iterrows():
        lines.append(f"{x['sym']:6s} {x['group']:15s} {x['n']:4d} {x['cond']*b:7.1f} "
                     f"{x['uncond']*b:7.1f} {x['prem']*b:6.1f} {x['t']:5.2f} {x['med']*b:6.1f} "
                     f"{x['hit']*100:3.0f}% {x['h1']*b:6.1f} {x['h2']*b:6.1f} {x['ypos']:>5s}")
    lines.append("")
    lines.append("pooled by group (equal-weight symbol average of prem, bp):")
    for g, gg in r.groupby("group"):
        lines.append(f"  {g:15s} n_syms={len(gg):2d} prem={gg['prem'].mean()*b:6.1f} "
                     f"h1={gg['h1'].mean()*b:6.1f} h2={gg['h2'].mean()*b:6.1f}")
    text = "\n".join(lines) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
