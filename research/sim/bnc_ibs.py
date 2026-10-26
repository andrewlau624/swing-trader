"""BNC-IBS (N 1056): does waiting for the bounce beat buying the dip, on the live IBS ETF universe?

Pre-registration: research/drafts/round1_prose.md "Study BNC-IBS". 18 ibs_symbols, IBS(d) < 0.2, arms DIP / WAIT / BNC-O / NOB /
BNC-C / BNC-H. Sharadar SFP split-adjusted OHLC, total-return scale via closeadj/close. 5bp/side, shock 15bp/side.
Run: .venv/bin/python -m research.sim.bnc_ibs  ->  data/research/program/bnc_ibs_out.txt
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd
import yaml

from sharadar import prices

from . import winsig as W

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "research" / "program" / "bnc_ibs_out.txt"
COST, SHOCK = 10e-4, 30e-4
PERIODS = {"2003-15 (PRIMARY)": ("2003-01-01", "2015-12-31"), "2016-26": ("2016-01-01", "2026-09-30")}


def panel() -> pd.DataFrame:
    syms = yaml.safe_load((ROOT / "config.yaml").read_text())["daily"]["ibs_symbols"]
    t = prices(syms, start="2002-06-01", end="2026-10-05", source="funds")
    t = t.sort_values(["ticker", "date"]).reset_index(drop=True)
    t["date"] = pd.to_datetime(t["date"])
    f = t.closeadj / t.close
    t["O"], t["C"] = t.open * f, t.closeadj
    rng = (t.high - t.low).replace(0, np.nan)
    t["ibs"] = (t.close - t.low) / rng
    g = t.groupby("ticker", sort=False)
    sh = lambda c, k: g[c].shift(-k)
    t["o1"], t["o2"], t["o3"], t["c1"] = sh("O", 1), sh("O", 2), sh("O", 3), sh("C", 1)
    t["close1"], t["high0"] = sh("close", 1), t["high"]
    t["r_dip"] = t.o2 / t.o1 - 1          # open d+1 -> open d+2
    t["r_wait"] = t.o3 / t.o2 - 1         # open d+2 -> open d+3
    t["r_night1"] = t.o2 / t.c1 - 1       # close d+1 -> open d+2
    t["up1"] = t.close1 > t.close
    t["reclaim"] = t.close1 > t.high0
    return t[t.ibs < 0.2].dropna(subset=["r_dip", "r_wait", "r_night1"]).copy()


def block(sel: pd.DataFrame, col: str, lo: str, hi: str) -> dict:
    s = sel[(sel.date >= lo) & (sel.date <= hi)]
    x = s[col]
    d = x.groupby(s.date).mean()
    mid = pd.Timestamp(lo) + (pd.Timestamp(hi) - pd.Timestamp(lo)) / 2
    return dict(n=len(x), mean=x.mean() * 1e4, net=(x.mean() - COST) * 1e4, med=x.median() * 1e4, hit=(x > 0).mean(),
                t=W.nw_t(d, 1), h1=d[d.index < mid].mean() * 1e4, h2=d[d.index >= mid].mean() * 1e4,
                ex5=d.sort_values().iloc[:-5].mean() * 1e4 if len(d) > 10 else np.nan, shock=(x.mean() - SHOCK) * 1e4)


def ok(r):
    return r["net"] >= 15 and r["t"] >= 2.5 and min(r["h1"], r["h2"]) > 0 and r["med"] > 0 and r["ex5"] > 0


def fmt(lab, r):
    return (f"{lab:40} n {r['n']:5} mean {r['mean']:+6.1f} net {r['net']:+6.1f} med {r['med']:+6.1f} hit {r['hit']:.0%} "
            f"t {r['t']:+5.2f} halves {r['h1']:+5.1f}/{r['h2']:+5.1f} ex5 {r['ex5']:+5.1f} shock {r['shock']:+6.1f} {'PASS' if ok(r) else 'fail'}")


def pair(sel, m1, c1, m2, c2, lo, hi):
    s = sel[(sel.date >= lo) & (sel.date <= hi)]
    a = s[m1.loc[s.index]].groupby("date")[c1].mean()
    b = s[m2.loc[s.index]].groupby("date")[c2].mean()
    d = (a - b).dropna()
    return d.mean() * 1e4, W.nw_t(d, 1), len(d)


def main():
    t = panel()
    lines = [f"BNC-IBS (N 1056) one look {pd.Timestamp.today():%Y-%m-%d}. 18 ibs_symbols, IBS<0.2 (all 18, no momentum rank), "
             f"{len(t)} signal name-days, cost {COST*1e4:.0f}bp RT, shock {SHOCK*1e4:.0f}bp. Total-return scale."]
    arms = [("DIP  open d+1 -> open d+2 (live form)", t.ibs.notna(), "r_dip"),
            ("WAIT open d+2 -> open d+3 (any d+1)", t.ibs.notna(), "r_wait"),
            ("BNC-O up-close d+1: open d+2 -> open d+3", t.up1, "r_wait"),
            ("NOB  down-close d+1: open d+2 -> open d+3", ~t.up1, "r_wait"),
            ("BNC-C up-close d+1: close d+1 -> open d+2", t.up1, "r_night1"),
            ("NOB-C down-close d+1: close d+1 -> open d+2", ~t.up1, "r_night1"),
            ("BNC-H reclaim high(d): close d+1 -> open d+2", t.reclaim, "r_night1"),
            ("BNC-H reclaim high(d): open d+2 -> open d+3", t.reclaim, "r_wait")]
    res = {}
    for pname, (lo, hi) in PERIODS.items():
        lines.append(f"\n-- {pname} --")
        for lab, m, col in arms:
            r = block(t[m], col, lo, hi)
            res[(pname, lab)] = r
            lines.append(fmt(lab, r))
        for a, b, lab in [((t.up1, "r_wait"), (t.ibs.notna(), "r_wait"), "BNC-O - WAIT"),
                          ((t.up1, "r_wait"), (~t.up1, "r_wait"), "BNC-O - NOB  [bar >= +10, t >= 2]"),
                          ((t.up1, "r_night1"), (~t.up1, "r_night1"), "BNC-C - NOB-C"),
                          ((t.up1, "r_wait"), (t.ibs.notna(), "r_dip"), "BNC-O - DIP (same signal days)")]:
            d, tt, n = pair(t, a[0], a[1], b[0], b[1], lo, hi)
            lines.append(f"   paired {lab:34} {d:+6.1f}bp (t {tt:+5.2f}, {n} dates)")
    yr = t.groupby(t.date.dt.year).agg(dip=("r_dip", "mean"), wait=("r_wait", "mean"))
    bo = t[t.up1].groupby(t[t.up1].date.dt.year)["r_wait"].mean()
    lines.append("\nby year (bp): year DIP / WAIT / BNC-O")
    lines.append(" ".join(f"{y}:{v.dip*1e4:+.0f}/{v.wait*1e4:+.0f}/{bo.get(y, np.nan)*1e4:+.0f}" for y, v in yr.iterrows()))
    thesis = []
    for pname, (lo, hi) in PERIODS.items():
        o = ok(res[(pname, arms[2][0])]) or ok(res[(pname, arms[4][0])])
        d, tt, _ = pair(t, t.up1, "r_wait", ~t.up1, "r_wait", lo, hi)
        thesis.append(o and d >= 10 and tt >= 2)
    lines.append("\nVERDICT (registered: BNC-O or BNC-C passes in both periods AND BNC-O - NOB >= +10bp t>=2): "
                 + ("PASS" if all(thesis) else "KILL"))
    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    sys.exit(main())
