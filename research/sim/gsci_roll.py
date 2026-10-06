"""Probe GSCI-ROLL: commodity-index ("Goldman") roll window, business days 5-9 of each month.

Participant: S&P GSCI / BCOM index funds and swaps. Constraint: published roll schedule, must sell the nearby and buy
the next contract (20% per day on BD5-9). Flow: predictable nearby-sell / deferred-buy. Effect: F1-F2 spread (as % of F2)
should cheapen into/through BD5-9 (front-running) and recover after. Trade: short F1 / long F2 before BD5, cover BD9.

Data: cached Databento GLBX daily outrights CL/NG 2011-2025 (data/research/program/glbx_*_daily.parquet).
Exploratory probe, no N.
"""
from __future__ import annotations

import pathlib
import re

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).with_name("gsci_roll_out.txt")
MON = {c: i + 1 for i, c in enumerate("FGHJKMNQUVXZ")}


def spreads(root: str) -> pd.DataFrame:
    d = pd.read_parquet(ROOT / "data/research/program" / f"glbx_{root}_daily.parquet")
    d["date"] = pd.to_datetime(d["ts_event"], utc=True).dt.normalize().dt.tz_localize(None)   # UTC session date
    pat = re.compile(rf"^{root}([FGHJKMNQUVXZ])(\d)$")
    rows = []
    for sym, g in d.groupby("symbol"):
        m = pat.match(str(sym))
        if not m:
            continue
        y0 = g.date.min().year
        y = y0 + ((int(m.group(2)) - y0 % 10) % 10)          # first year >= listing year with this last digit
        rows.append(pd.DataFrame({"date": g.date.values, "close": g.close.values, "exp": y * 100 + MON[m.group(1)]}))
    x = pd.concat(rows)
    x = x[x.close > 0]
    # delivery month must be after the trade month (drop expiring/expired months)
    x = x[x.exp > x.date.dt.year * 100 + x.date.dt.month]
    x = x.sort_values(["date", "exp"])
    f = x.groupby("date").head(2).copy()
    f["k"] = f.groupby("date").cumcount()
    p = f.pivot(index="date", columns="k", values="close").dropna()
    e = f.pivot(index="date", columns="k", values="exp").reindex(p.index)
    s = pd.DataFrame({"sp": (p[0] - p[1]) / p[1], "e1": e[0]})
    s["bd"] = s.groupby([s.index.year, s.index.month]).cumcount() + 1
    s["ym"] = s.index.year * 100 + s.index.month
    return s


def main():
    lines = ["GSCI-ROLL probe: change in (F1-F2)/F2 over business-day windows of each month (bp); negative = F1 cheapens", ""]
    for root in ["CL", "NG"]:
        s = spreads(root)
        res = []
        for ym, g in s.groupby("ym"):
            g = g.set_index("bd")
            if not {1, 4, 9, 12}.issubset(g.index) or g.e1.loc[1:12].nunique() > 1:
                continue                                  # skip months where the front contract changes in BD1-12
            res.append((ym, g.sp[4] - g.sp[1], g.sp[9] - g.sp[4], g.sp[12] - g.sp[9]))
        r = pd.DataFrame(res, columns=["ym", "pre", "roll", "post"])
        r["yr"] = r.ym // 100
        lines.append(f"== {root}: {len(r)} months ==")
        for c in ["pre", "roll", "post"]:
            v = r[c] * 1e4
            lines.append(f"{c:5s} mean {v.mean():+6.1f} med {v.median():+6.1f} t {v.mean()/v.std()*np.sqrt(len(v)):+5.2f} "
                         f"hit<0 {(v < 0).mean():.2f} | 2011-17 {v[r.yr <= 2017].mean():+6.1f} 2018-25 {v[r.yr >= 2018].mean():+6.1f}")
        lines.append("")
    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
