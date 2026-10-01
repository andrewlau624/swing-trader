"""Round 20 data: full opening/closing cross history (price + size) for every night-pick symbol.

    PYTHONPATH=. .venv/bin/python -m research.sim.auction_hist_fetch      # resumable

Alpaca /v2/stocks/auctions (SIP), 2020-09-01 .. 2026-09-30, batches of 40 symbols, cached as
data/research/night/auction_hist/<batch>.json (raw API rows). Fetch only.
"""
from __future__ import annotations

import json
import pathlib
import time

from . import book as B
from .auction_fetch import _env, fetch

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/night/auction_hist"


def symbols():
    N = B.night_days(raw_price=True, max_corr=0.7)
    return sorted({str(x) for nd in N.values() for x in nd.syms})


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    H = _env(); syms = symbols(); t0 = time.time()
    for i in range(0, len(syms), 40):
        f = OUT / f"b{i:05d}.json"
        if f.exists():
            continue
        json.dump(fetch(syms[i:i + 40], "2020-09-01", "2026-09-30", H), open(f, "w"))
        print(f"{i}/{len(syms)} {time.time()-t0:.0f}s", flush=True)
    print("done", f"{time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
