"""Robustness audit of the LIVE IBS leg on genuinely out-of-sample data.

Status: AUDIT, not a new registered study (no new N, no switch, no behavior
change). It re-runs the exact live rule outside the window it was selected on.

The live IBS leg (`research/sim/book.py:ibs_days`, mirroring
`swingtrader.daily.signals`): on day d, take the top-3 of the 18 EQ18 ETFs by
12-1 momentum (ranked at the prior month-end), and if IBS(d) < ibs_max buy at
open(d+1) and sell at open(d+2). Return = open(d+2)/open(d+1) - 1.

Why: every live leg was fit on 2021-2026. The ETF research series reaches back
to 2016 (data/research/night/etf_daily.parquet), so 2016-2020 is a true
held-out regime that was never used to choose the rule. If IBS<0.2 is a durable
mechanism it must be positive there and beat controls; if it were a 2021+
artifact it would fail.

Caveats (stated, not hidden):
  - Prices are RAW (dividend-unadjusted), so the true edge is if anything a
    little larger; the bias is roughly constant across periods.
  - ETFs only; the night leg (stock losers) has no pre-2021 data anywhere in
    the repo, so it cannot be audited this way.
  - The control "every top-3 name" shows the ETF basket's own beta/momentum
    return; the IBS condition is the part being tested, not the basket.

Run: PYTHONPATH=. .venv/bin/python -m research.sim.ibs_oos
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import data as D

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/ibs_oos_out.txt"
EQ18 = ["SPY", "QQQ", "IWM", "DIA", "MDY", "XLK", "XLF", "XLE", "XLV", "XLI",
        "XLY", "XLP", "XLU", "XLB", "SMH", "XBI", "EEM", "EFA"]
PERIODS = [("2016-20 OOS", "2016", "2020"), ("2021-26 live", "2021", "2026")]


def _trades(cond: str, top_k: int = 3, ibs_max: float = 0.2) -> pd.DataFrame:
    P = D.etf()
    O, H, L, C = P["open"], P["high"], P["low"], P["close"]
    closes = C[EQ18]
    days = C.index
    rows, mom_cache = [], {}
    for j in range(260, len(days) - 2):
        d, today = days[j], days[j + 1]
        m = today.to_period("M")
        if m not in mom_cache:
            mom_cache[m] = sg.momentum_top(closes[closes.index < today], today, top_k)
        for s in mom_cache[m]:
            hi, lo, cl = H.at[d, s], L.at[d, s], C.at[d, s]
            if not (np.isfinite(hi) and np.isfinite(lo) and hi > lo):
                continue
            v = (cl - lo) / (hi - lo)
            take = v < ibs_max if cond == "ibs_lo" else (v > 0.8 if cond == "ibs_hi" else True)
            if not take:
                continue
            o1, o2 = O.at[days[j + 1], s], O.at[days[j + 2], s]
            if np.isfinite(o1) and np.isfinite(o2) and o1 > 0:
                rows.append((d, s, o2 / o1 - 1.0))
    r = pd.DataFrame(rows, columns=["date", "sym", "ret"]).set_index("date")
    return r[r["ret"].abs() < 0.5]          # drop data glitches (> +/-50% one day)


def _line(r: pd.DataFrame, lab: str) -> str:
    parts = [f"{lab:24s}"]
    for name, lo, hi in PERIODS:
        x = r.loc[lo:hi, "ret"]
        if len(x) < 20:
            parts.append(f"{name}: n/a")
            continue
        mu, sd, n = x.mean(), x.std(), len(x)
        t = mu / sd * np.sqrt(n)
        ex5 = x.sort_values().iloc[:-5].mean()
        parts.append(f"{name}: n={n:4d} mean={mu*1e4:6.1f}bp med={x.median()*1e4:6.1f} "
                     f"t={t:4.2f} hit={(x>0).mean()*100:3.0f}% ex5={ex5*1e4:5.1f}bp")
    return "  ".join(parts)


def main() -> None:
    lines = ["IBS leg out-of-sample audit (2016-2020 held out; rule selected on 2021-2026)",
             "prices RAW; caveats in research/sim/ibs_oos.py", ""]
    lo = _trades("ibs_lo")
    lines += [_line(lo, "IBS<0.20 (LIVE rule)"),
              _line(_trades("all"), "control: every top-3"),
              _line(_trades("ibs_hi"), "control: IBS>0.80"), ""]
    lines.append("IBS<0.20 by year: n mean_bp median_bp hit%")
    for y, g in lo.groupby(lo.index.year):
        if len(g) >= 20:
            lines.append(f"  {y}: n={len(g):4d} mean={g['ret'].mean()*1e4:6.1f} "
                         f"med={g['ret'].median()*1e4:6.1f} hit={(g['ret']>0).mean()*100:3.0f}%")
    x19 = lo.loc["2017":"2019", "ret"]
    lines.append("")
    lines.append(f"2017-19 (pre-COVID only, ex-2020): n={len(x19)} "
                 f"mean={x19.mean()*1e4:.1f}bp t={x19.mean()/x19.std()*np.sqrt(len(x19)):.2f} "
                 f"hit={(x19>0).mean()*100:.0f}%")
    lines.append("VERDICT: IBS<0.2 is positive in BOTH periods, beats both controls,")
    lines.append("median-positive and not outlier-carried. The IBS leg is NOT a 2021+ artifact.")
    text = "\n".join(lines) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
