"""Runner: backtest the Systematic Intraday Day Book and print the full report.

Run: PYTHONPATH=. .venv/bin/python -m research.sim.daybook_run
"""
from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from swingtrader.daybook import DaybookConfig
from swingtrader.daybook.engine import simulate
from swingtrader.daybook import metrics as M

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "research" / "program" / "daytrade_scan_cache.pkl"
OUT = ROOT / "data" / "research" / "program" / "daybook_out.txt"


def load(syms):
    P = pickle.load(open(CACHE, "rb"))
    common = None
    for s in syms:
        idx = P[s]["dates"]
        common = idx if common is None else common.intersection(idx)
    out = {}
    for s in syms:
        pos = P[s]["dates"].get_indexer(common)
        out[s] = dict(dates=common, A=P[s]["A"][pos])
    return out


def periods():
    return [("2016", "2020", "16-20"), ("2021", "2023", "21-23"),
            ("2024", "2026", "24-26"), ("2016", "2026", "full")]


def slice_(daily, lo, hi):
    return daily[(daily.index >= f"{lo}-01-01") & (daily.index <= f"{hi}-12-31")]


def run(name, cfg, syms, out=None):
    out = out or sys.stdout
    panel = load(syms)
    total, per, nfill = simulate(panel, cfg)
    print(f"\n########## {name} ##########", file=out)
    print(f"instruments {syms}  core {cfg.core} conv {cfg.conviction}  "
          f"target_vol {cfg.target_vol} max_lev {cfg.max_lev} "
          f"conv_strength {cfg.conviction_strength} mult {cfg.conviction_mult} "
          f"cost {cfg.cost_bps}bp/fill", file=out)
    for lo, hi, lbl in periods():
        d = slice_(total, lo, hi).dropna()
        print(M.line(lbl, M._ann(d)), file=out)
    print(M.robustness(total.dropna()), file=out)
    print(f"fills {nfill}  total {sum(nfill.values())}  "
          f"(~{sum(nfill.values())/max(len(total),1):.2f}/day)", file=out)
    print("worst week %.2f%%  worst day %.2f%%" % (M.worst_week(total) * 100, total.min() * 100), file=out)
    yb = M.year_by_year(total)
    print(yb.to_string(index=False, float_format=lambda v: f"{v:.2f}"), file=out)
    for lo, hi, lbl in [("2016", "2020", "16-20"), ("2021", "2026", "21-26")]:
        d = slice_(total, lo, hi).dropna()
        a = M._ann(d)
        print(f"  annual $ {lbl}: {M.annual_dollars(a['cagr'])}", file=out)
    return total, per, nfill


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w") as fh:
        class T:
            def __init__(s, *fs): s.fs = fs
            def write(s, x):
                for f in s.fs: f.write(x)
            def flush(s):
                for f in s.fs: f.flush()
        old = sys.stdout
        sys.stdout = T(old, fh)
        try:
            print("SYSTEMATIC INTRADAY DAY BOOK — backtest report")
            print("Mechanism: intraday noise-area breakout, vol-targeted, flat nightly.")
            # sanity: QQQ-only should resemble the documented ~13% CAGR / Sharpe 0.98
            run("SANITY QQQ-only", DaybookConfig(core={"QQQ": 1.0}, conviction={},
                target_vol=0.02, max_lev=3.5, cost_bps=1.0), ["QQQ"])
            run("A core QQQ+SMH", DaybookConfig(core={"QQQ": 0.5, "SMH": 0.5}, conviction={},
                target_vol=0.02, max_lev=3.5, cost_bps=1.0), ["QQQ", "SMH"])
            run("B core + conviction TQQQ/SOXL",
                DaybookConfig(core={"QQQ": 0.4, "SMH": 0.4}, conviction={"TQQQ": 0.25, "SOXL": 0.25},
                              target_vol=0.02, max_lev=3.5, conviction_strength=0.341,
                              conviction_mult=2.0, cost_bps=1.0),
                ["QQQ", "SMH", "TQQQ", "SOXL"])
            run("C core + conviction, 2x risk target",
                DaybookConfig(core={"QQQ": 0.4, "SMH": 0.4}, conviction={"TQQQ": 0.25, "SOXL": 0.25},
                              target_vol=0.04, max_lev=7.0, conviction_strength=0.341,
                              conviction_mult=2.0, cost_bps=1.0),
                ["QQQ", "SMH", "TQQQ", "SOXL"])
            # cost sensitivity on B
            for c in (0.5, 2.0, 4.0):
                run(f"D cost stress {c}bp", DaybookConfig(core={"QQQ": 0.4, "SMH": 0.4},
                    conviction={"TQQQ": 0.25, "SOXL": 0.25}, target_vol=0.02, max_lev=3.5,
                    conviction_strength=0.341, conviction_mult=2.0, cost_bps=c),
                    ["QQQ", "SMH", "TQQQ", "SOXL"])
        finally:
            sys.stdout = old
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
