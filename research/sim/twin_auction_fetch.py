"""Round 30: opening/closing cross prints for the LETF twin list (Alpaca /v2/stocks/auctions, SIP).

    PYTHONPATH=. .venv/bin/python -m research.sim.twin_auction_fetch sel

sel = 2020-09-01..2023-12-31 (exploration), judge (2024-26) was never fetched: nothing survived exploration.
Cached as data/research/night/twin_auctions_<part>.json. Fetch only.
"""
from __future__ import annotations

import json
import pathlib
import sys

from .auction_fetch import _env, fetch
from .outside_box import LETFS

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPANS = {"sel": ("2020-09-01", "2023-12-31")}

if __name__ == "__main__":
    part = sys.argv[1]
    syms = sorted({a for a, _, _ in LETFS} | {b for _, b, _ in LETFS})
    a, z = SPANS[part]
    H = _env(); rows = {}
    for i in range(0, len(syms), 20):
        rows.update(fetch(syms[i:i + 20], a, z, H)); print(i, flush=True)
    json.dump(rows, open(ROOT / f"data/research/night/twin_auctions_{part}.json", "w"))
    print("done", len(rows))
