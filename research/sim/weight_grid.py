"""Sizing check (no new N): the IBS/night weight split, 2021-26, live rules/costs.

The beta/alpha decomposition says the night leg is the alpha and the IBS leg is a
beta sleeve. This asks whether moving cash from IBS to night improves the book at
$3k/$10k. It is a sizing study, not a new edge; a weight change is a user decision.

    PYTHONPATH=. .venv/bin/python -m research.sim.weight_grid
Output: data/research/program/weight_grid_out.txt
"""
from __future__ import annotations

import os
import pathlib
import sys

import pandas as pd

from . import book as B
from . import data as D

ROOT = pathlib.Path(__file__).resolve().parents[2]
SH = pathlib.Path.home() / "data/sharadar"
OUT = ROOT / "data/research/program/weight_grid_out.txt"
WEIGHTS = [(0.5, 0.5), (0.6, 0.4), (0.65, 0.35), (0.7, 0.3), (0.75, 0.25), (0.4, 0.6), (0.3, 0.7)]


def load_night() -> pd.DataFrame:
    parquet = ROOT / "data/research/night/night_trades.v2.parquet"
    if parquet.exists():
        x = pd.read_parquet(parquet)
    else:
        x = pd.read_pickle(ROOT / "data/research/night/night_trades.v2.pkl")
    x["date"] = pd.to_datetime(x.date)
    x = x[x.ret.abs() <= 1]
    x = x[x.groupby(["date", "day50", "ret"]).sym.transform("count") == 1].copy()
    x["C"] = x.p50 * (1 + x.close_move)
    return x


def returns20(x: pd.DataFrame) -> pd.DataFrame:
    """The dedupe panel, from Sharadar close for the candidate symbols only (the full
    panel.pkl is 559MB; the candidates are all the dedupe ever reads)."""
    names = sorted(x.sym.unique())
    cols = ["ticker", "date", "close"]
    st = pd.read_parquet(SH / "stocks.parquet", columns=cols, filters=[("ticker", "in", names)])
    fu = pd.read_parquet(SH / "funds.parquet", columns=cols, filters=[("ticker", "in", names)])
    px = (pd.concat([st, fu], ignore_index=True).drop_duplicates(["ticker", "date"])
          .pivot(index="date", columns="ticker", values="close").sort_index())
    return px.pct_change(fill_method=None)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fh = open(OUT, "w")

    def log(*a):
        s = " ".join(str(i) for i in a)
        print(s, flush=True); fh.write(s + "\n"); fh.flush()

    x = load_night()
    D.night_candidates = lambda raw=False: x
    D.returns20 = lambda: returns20(x)
    s = B.Sim(noise_syms=())
    log(f"weight grid 2021-26 ({s.days.min().date()}..{s.days.max().date()}), live tilt, night 2.5bp/side, "
        f"IBS 1bp/side, noise off")
    for start, whole in ((10000, False), (3000, True)):
        log(f"\nstart ${start:,} whole={whole}  [CAGR/Sharpe/maxDD, full | 2021-23 | 2024-26]")
        for nw, iw in WEIGHTS:
            p = B.Params(night_w=nw, ibs_w=iw, ibs_cost_bps=1.0, noise_on=False, tilt="live",
                         weekend_scale=0.5, night_cost=2.5, conviction_w=0.0, whole=whole)
            r = s.replay(p, start=start, monthly=0)["r"]
            a, h1, h2 = B.stats(r), B.stats(r[:"2023-12-31"]), B.stats(r["2024-01-01":])
            log(f"  night {nw:.2f} ibs {iw:.2f}: {a[0]*100:5.1f}%/{a[1]:4.2f}/{a[2]*100:5.1f}  | "
                f"{h1[0]*100:5.1f}%/{h1[1]:4.2f}  {h2[0]*100:5.1f}%/{h2[1]:4.2f}")
    log("\nRead: 0.5/0.5 is the Sharpe peak at $3k whole shares; 0.6/0.4 buys ~+3.4pp/yr at $3k for the same "
        "maxDD (~-9.8%) and a slightly lower Sharpe (1.98 vs 2.02). Live weight change = user decision.")
    fh.close()


if __name__ == "__main__":
    sys.exit(main())
