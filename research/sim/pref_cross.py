"""PREF-EX judged on official SIP crosses 2021-26: buy the T-1 closing cross, sell the ex-date (T) opening cross
(or closing cross), collect the dividend. Also reports cross sizes (capacity) and SPY-free placebo: same names'
T-1 close -> T open on their NON-ex nights is not fetched here; the Sharadar non-ex baseline (~+2bp) is quoted.

    PYTHONPATH=. .venv/bin/python -m research.sim.pref_cross
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
D = ROOT / "data/research/pref"
OUT = pathlib.Path(__file__).resolve().parent / "pref_cross_out.txt"


def main():
    e = pd.read_parquet(D / "events.parquet")
    rows = []
    for f in sorted(glob.glob(str(D / "x" / "*.json"))):
        d = pd.Timestamp(pathlib.Path(f).stem)
        j = json.load(open(f))
        for r in e[e.date == d].itertuples():
            if r.sym not in j:
                continue
            x = crosses(j[r.sym])
            d0 = pd.Timestamp(r.d0)
            if d0 not in x.index or d not in x.index:
                continue
            c0, o1, c1 = x.loc[d0, "cp"], x.loc[d, "op"], x.loc[d, "cp"]
            rows.append((r.ticker, d, r.dv, r.div / r.pc, (o1 + r.div) / c0 - 1, (c1 + r.div) / c0 - 1,
                         x.loc[d0, "cs"] * c0, x.loc[d, "os"] * o1, (c0 - o1) / r.div))
    df = pd.DataFrame(rows, columns=["t", "d", "dv", "yld", "co", "cc", "close_usd", "open_usd", "drop_open"])
    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=["co", "cc"])
    lines = [f"PREF-EX on official crosses: {len(df)} events / {df.d.nunique()} ex-dates / {df.t.nunique()} preferreds "
             f"({df.d.min().date()}..{df.d.max().date()}); fetched events {len(e)}", ""]
    for lab, x in [("all (dv>=$100k)", df), ("dv>=$200k", df[df.dv >= 2e5]), ("dv>=$1M", df[df.dv >= 1e6]),
                   ("open cross >= $5k", df[df.open_usd >= 5e3])]:
        for c in ["co", "cc"]:
            day = x.groupby("d")[c].mean()
            t = day.mean() / day.std() * np.sqrt(len(day))
            srt = np.sort(x[c].values)
            yrs = x.groupby(x.d.dt.year)[c].mean() * 1e4
            lines.append(f"{lab:18s} {c}: n {len(x):5d} mean {x[c].mean()*1e4:+6.1f} med {x[c].median()*1e4:+6.1f} "
                         f"hit {(x[c] > 0).mean():.2f} t(day) {t:+5.2f} ex-top5 {srt[:-5].mean()*1e4:+6.1f} | yrs "
                         + " ".join(f"{y}:{v:+.0f}" for y, v in yrs.items()))
        lines.append("")
    lines.append(f"drop at open / dividend: median {df.drop_open.median():.2f}")
    lines.append(f"closing-cross $ on T-1: median ${df.close_usd.median():,.0f} p25 ${df.close_usd.quantile(.25):,.0f}; "
                 f"opening-cross $ on T: median ${df.open_usd.median():,.0f} p25 ${df.open_usd.quantile(.25):,.0f}")
    lines.append(f"events/yr {len(df) / ((df.d.max() - df.d.min()).days / 365.25):.0f}, ex-dates/yr "
                 f"{df.d.nunique() / ((df.d.max() - df.d.min()).days / 365.25):.0f}")
    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    df.to_parquet(D / "cross_rows.parquet")


if __name__ == "__main__":
    main()
