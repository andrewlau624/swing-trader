"""SSR lift-day short judged on official SIP crosses, 2021-2026 (data from ssr_fetch.py).

Trade per event (Rule 201 triggered on T, not re-triggered on T+1): sell short at the official opening cross on T+2,
cover at the official closing cross on T+2 (A), or at the T+2 open from the T+1 close (B: C1->C2, entry needs a short
into the T+1 closing cross while SSR is still in force: execution feasibility unverified). Raw and SPY-hedged
(beta 1.5 x SPY's same-window official return). Control = L in (-10%, -7%].

    PYTHONPATH=. .venv/bin/python -m research.sim.ssr_cross
"""
from __future__ import annotations

import glob
import json
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from exdiv_open import crosses  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data/research/ssr"
OUT = pathlib.Path(__file__).resolve().parent / "ssr_cross_out.txt"


def main():
    e = pd.read_parquet(D / "events.parquet")
    rows = []
    for f in sorted(glob.glob(str(D / "x" / "*.json"))):
        d1 = pd.Timestamp(pathlib.Path(f).stem)
        j = json.load(open(f))
        if "SPY" not in j:
            continue
        spy = crosses(j["SPY"])
        for r in e[e.d1 == d1].itertuples():
            if r.ticker not in j:
                continue
            x = crosses(j[r.ticker])
            d2 = pd.Timestamp(r.d2)
            if d1 not in x.index or d2 not in x.index or d2 not in spy.index or d1 not in spy.index:
                continue
            a = x.loc[d2, "cp"] / x.loc[d2, "op"] - 1
            bb = x.loc[d2, "cp"] / x.loc[d1, "cp"] - 1
            sa = spy.loc[d2, "cp"] / spy.loc[d2, "op"] - 1
            sb = spy.loc[d2, "cp"] / spy.loc[d1, "cp"] - 1
            rows.append((r.ticker, r.date, d2, r.L, r.adv, r.praw, -a, -bb, -a + 1.5 * sa, -bb + 1.5 * sb,
                         x.loc[d2, "os"] * x.loc[d2, "op"]))
    df = pd.DataFrame(rows, columns=["t", "d", "d2", "L", "adv", "praw", "A", "B", "Ah", "Bh", "open_cross_usd"])
    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=["A", "B"])
    for c in ["A", "B", "Ah", "Bh"]:
        df[c] = df[c].clip(-0.9, 0.9)
    lines = [f"SSR lift-day short on official crosses: {len(df)} event rows, {df.d2.nunique()} sessions "
             f"({df.d2.min().date()} .. {df.d2.max().date()})", ""]
    for lab, x in [("TREATED L<=-10%", df[df.L <= -0.10]), ("CONTROL L -10..-7", df[df.L > -0.10]),
                   ("TREATED ADV>=$20M", df[(df.L <= -0.10) & (df.adv >= 2e7)]),
                   ("TREATED L -13..-10", df[df.L.between(-0.13, -0.10)])]:
        for c in ["A", "Ah", "B", "Bh"]:
            day = x.groupby("d2")[c].mean()
            t = day.mean() / day.std() * np.sqrt(len(day))
            yrs = day.groupby(day.index.year).mean() * 1e4
            lines.append(f"{lab:20s} {c:3s} n {len(x):5d} mean {x[c].mean()*1e4:+6.1f} med {x[c].median()*1e4:+6.1f} "
                         f"hit {(x[c] > 0).mean():.2f} | EW day {day.mean()*1e4:+6.1f} t {t:+5.2f} | yrs "
                         + " ".join(f"{y}:{v:+.0f}" for y, v in yrs.items()))
        lines.append("")
    tr = df[df.L <= -0.10]
    lines.append(f"open-cross $ size on T+2 (treated): median ${tr.open_cross_usd.median():,.0f}, "
                 f"p10 ${tr.open_cross_usd.quantile(.1):,.0f}")
    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    df.to_parquet(D / "cross_rows.parquet")


if __name__ == "__main__":
    main()
