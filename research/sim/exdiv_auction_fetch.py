"""EXDIV-OPEN verification data: official SIP opening/closing cross prints (Alpaca /v2/stocks/auctions)
for the liquid high-yield names with the most ex-dividend dates 2021-2026.

    PYTHONPATH=. .venv/bin/python -m research.sim.exdiv_auction_fetch      # resumable

Cached as data/research/exdiv/auction/<batch>.json (raw API rows). Fetch only.
"""
from __future__ import annotations

import json
import pathlib
import time

import numpy as np
import pandas as pd

from .auction_fetch import _env, fetch

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/exdiv/auction"
STORE = pathlib.Path.home() / "data" / "sharadar"
N_SYMS = 400


def symbols() -> list[str]:
    a = pd.read_parquet(STORE / "actions.parquet", columns=["date", "action", "ticker", "value"])
    a = a[(a.action == "dividend") & (a.date >= pd.Timestamp("2021-01-01").date())]
    t = pd.read_parquet(STORE / "tickers.parquet", columns=["table", "ticker", "isdelisted"])
    live = set(t[(t.table.isin(["SEP", "SFP"])) & (t.isdelisted == "N")].ticker)
    px = pd.read_parquet(STORE / "metrics.parquet", columns=["ticker", "price", "volumeavg3m"]) \
        .drop_duplicates("ticker", keep="last").set_index("ticker")
    a = a[a.ticker.isin(live)].join(px, on="ticker")
    a = a[(a.price >= 5) & (a.price * a.volumeavg3m >= 2e6)]
    a["yld"] = a.value / a.price
    a = a[a.yld >= 0.006]
    a = a[a.ticker.str.fullmatch(r"[A-Z]{1,5}")]
    return list(a.groupby("ticker").size().sort_values(ascending=False).index[:N_SYMS])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    H = _env(); syms = sorted(symbols()); t0 = time.time()
    json.dump(syms, open(OUT.parent / "symbols.json", "w"))
    for i in range(0, len(syms), 40):
        f = OUT / f"b{i:05d}.json"
        if f.exists():
            continue
        json.dump(fetch(syms[i:i + 40], "2021-01-01", "2026-10-02", H), open(f, "w"))
        print(f"{i}/{len(syms)} {time.time()-t0:.0f}s", flush=True)
    print("done", f"{time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
