"""EXDIV-OPEN arms B/C data: official SIP cross prints around each 2021-2026 forward-split and spin-off parent
ex-date (Alpaca /v2/stocks/auctions), window ex-date - 70 calendar days .. ex-date.

    PYTHONPATH=. .venv/bin/python -m research.sim.exsplit_auction_fetch      # resumable

Cached as data/research/exdiv/events/<arm>_<ticker>_<date>.json. Fetch only.
"""
from __future__ import annotations

import json
import pathlib
import time

import pandas as pd

from .auction_fetch import _env, fetch

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/exdiv/events"
STORE = pathlib.Path.home() / "data" / "sharadar"


def events() -> pd.DataFrame:
    a = pd.read_parquet(STORE / "actions.parquet", columns=["date", "action", "ticker", "value"])
    a["date"] = pd.to_datetime(a["date"])
    a = a[(a.date >= "2021-01-01") & a.ticker.str.fullmatch(r"[A-Z]{1,5}")]
    b = a[(a.action == "split") & (a.value > 1)].assign(arm="B")
    c = a[a.action == "spinoff"].assign(arm="C")
    return pd.concat([b, c]).drop_duplicates(["arm", "ticker", "date"])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    H = _env(); ev = events(); t0 = time.time()
    for i, r in enumerate(ev.itertuples()):
        f = OUT / f"{r.arm}_{r.ticker}_{r.date.date()}.json"
        if f.exists():
            continue
        start = (r.date - pd.Timedelta(days=70)).date()
        try:
            rows = fetch([r.ticker], str(start), str(r.date.date()), H)
        except Exception as e:  # noqa: BLE001 - symbol unknown to the feed
            rows = {"_error": str(e)[:200]}
        json.dump(rows, open(f, "w"))
        if i % 100 == 0:
            print(f"{i}/{len(ev)} {time.time()-t0:.0f}s", flush=True)
    print("done", len(ev), f"{time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
