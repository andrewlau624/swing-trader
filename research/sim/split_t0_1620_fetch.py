"""SPLIT-NIGHT data: official SIP crosses for each 2016-2020 forward-split ticker, ex-date -45d .. +20d.

    PYTHONPATH=. .venv/bin/python -m research.sim.split_night_fetch      # resumable

Cached as data/research/exdiv/splitnight/<ticker>_<date>.json. Fetch only.
"""
from __future__ import annotations

import json
import pathlib
import time

import pandas as pd

from .auction_fetch import _env, fetch

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/exdiv/splitnight1620"
STORE = pathlib.Path.home() / "data" / "sharadar"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    a = pd.read_parquet(STORE / "actions.parquet", columns=["date", "action", "ticker", "value"])
    a["date"] = pd.to_datetime(a["date"])
    ev = a[(a.action == "split") & (a.value > 1) & (a.date >= "2016-01-01") & (a.date <= "2020-12-31") & a.ticker.str.fullmatch(r"[A-Z]{1,5}")]
    ev = ev.drop_duplicates(["ticker", "date"])
    H = _env(); t0 = time.time()
    for i, r in enumerate(ev.itertuples()):
        f = OUT / f"{r.ticker}_{r.date.date()}.json"
        if f.exists():
            continue
        try:
            rows = fetch([r.ticker], str((r.date - pd.Timedelta(days=45)).date()),
                         str((r.date + pd.Timedelta(days=20)).date()), H)
        except Exception as e:  # noqa: BLE001
            rows = {"_error": str(e)[:200]}
        json.dump(rows, open(f, "w"))
        if i % 100 == 0:
            print(f"{i}/{len(ev)} {time.time()-t0:.0f}s", flush=True)
    print("done", len(ev), f"{time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
