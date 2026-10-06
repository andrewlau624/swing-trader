"""SSR-RD data: official SIP crosses on T+1 and T+2 for 2021-2026 Rule 201 trigger days (liquid common stock,
intraday low <= -10% of prior close on T, not re-triggered on T+1), plus SPY.

    PYTHONPATH=. .venv/bin/python -m research.sim.ssr_fetch      # resumable

Events -> data/research/ssr/events.parquet; crosses -> data/research/ssr/x/<T+1 date>.json (Alpaca auctions rows).
"""
from __future__ import annotations

import json
import pathlib
import time

import pandas as pd

from .auction_fetch import _env, fetch
from . import ssr_rd as m

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/ssr"


def events() -> pd.DataFrame:
    b = m.load()
    g = b.groupby("ticker", sort=False)
    pc = g.close.shift(1)
    b["L"] = b.low / pc - 1
    b["R"] = b.close / pc - 1
    b["praw"] = g.closeunadj.shift(1)
    b["adv"] = (b.close * b.volume).groupby(b.ticker).transform(
        lambda s: s.shift(1).rolling(20, min_periods=15).mean())
    b["L1"] = g.low.shift(-1) / b.close - 1
    b["d1"], b["d2"] = g.date.shift(-1), g.date.shift(-2)
    e = b[(b.praw >= 5) & (b.adv >= 5e6) & (b.L <= -0.07) & (b.L1 > -0.10) & (b.date >= "2021-01-01")
          & b.ticker.str.fullmatch(r"[A-Z]{1,5}")].dropna(subset=["d2"])
    return e[["ticker", "date", "d1", "d2", "L", "R", "L1", "adv", "praw"]].reset_index(drop=True)


def main():
    (OUT / "x").mkdir(parents=True, exist_ok=True)
    ef = OUT / "events.parquet"
    if not ef.exists():
        events().to_parquet(ef)
    e = pd.read_parquet(ef)
    H = _env(); t0 = time.time()
    grp = list(e.groupby("d1"))
    for i, (d1, x) in enumerate(grp):
        f = OUT / "x" / f"{pd.Timestamp(d1).date()}.json"
        if f.exists():
            continue
        syms = sorted(set(x.ticker) | {"SPY"})
        d2 = str(pd.Timestamp(x.d2.max()).date())
        rows = {}
        for k in range(0, len(syms), 100):
            rows.update(fetch(syms[k:k + 100], str(pd.Timestamp(d1).date()), d2, H))
        json.dump(rows, open(f, "w"))
        time.sleep(0.2)
        if i % 100 == 0:
            print(f"{i}/{len(grp)} {time.time()-t0:.0f}s", flush=True)
    print("done", len(grp), f"{time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
