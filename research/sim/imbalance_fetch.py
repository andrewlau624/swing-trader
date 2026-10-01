"""Round 26 (Study BD) data: the first closing-auction imbalance message per night pick, 15:50:00-15:52:00 ET.

    PYTHONPATH=. .venv/bin/python -m research.sim.imbalance_fetch      # resumable; ~$6-15 of Databento usage

Databento `imbalance` schema on the pick's listing exchange (asset_meta exchange: NYSE -> XNYS.PILLAR,
NASDAQ -> XNAS.ITCH, ARCA -> ARCX.PILLAR, AMEX -> XASE.PILLAR; BATS listings skipped). Keeps auction_type
'C' (closing) only; side 'A' = sell imbalance, 'B' = buy. One parquet per pick day in
data/research/night/imbalance/. Fetch only.
"""
from __future__ import annotations

import json
import pathlib
import time
from collections import defaultdict

import pandas as pd

from swingtrader.config import get_env

from . import book as B

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/night/imbalance"
DS = {"NYSE": "XNYS.PILLAR", "NASDAQ": "XNAS.ITCH", "ARCA": "ARCX.PILLAR", "AMEX": "XASE.PILLAR"}
ET = "America/New_York"


def fetch_day(c, meta, d, nd):
    f = OUT / f"{d.date()}.parquet"
    if f.exists():
        return 0
    by = defaultdict(list)
    for s in map(str, nd.syms):
        ds = DS.get(meta.get(s, {}).get("exchange"))
        if ds:
            by[ds].append(s)
    st = pd.Timestamp(f"{d.date()} 15:50:00", tz=ET).tz_convert("UTC").isoformat()
    en = pd.Timestamp(f"{d.date()} 15:52:00", tz=ET).tz_convert("UTC").isoformat()
    rows = []
    for ds, syms in by.items():
        df = pd.DataFrame()
        for k in range(4):
            try:
                df = c.timeseries.get_range(dataset=ds, symbols=syms, schema="imbalance", start=st, end=en).to_df()
                break
            except Exception:                                    # noqa: BLE001 — transient: back off and retry
                time.sleep(3 * (k + 1))
        if df.empty:
            continue
        df = df[df.auction_type == "C"].reset_index()
        first = df.sort_values("ts_recv").groupby("symbol").head(1)
        for r in first.itertuples():
            rows.append(dict(date=str(d.date()), sym=r.symbol, dataset=ds, ts=str(r.ts_recv), side=r.side,
                             imb=float(r.total_imbalance_qty), paired=float(r.paired_qty), ref=float(r.ref_price)))
    pd.DataFrame(rows, columns=["date", "sym", "dataset", "ts", "side", "imb", "paired", "ref"]).to_parquet(f)
    return 1


def main():
    import warnings
    from concurrent.futures import ThreadPoolExecutor, as_completed

    import databento as db
    warnings.filterwarnings("ignore")
    OUT.mkdir(parents=True, exist_ok=True)
    c = db.Historical(get_env("DATABENTO_API_KEY"))
    meta = json.load(open(ROOT / "data/research/night/asset_meta.json"))
    N = B.night_days(raw_price=True, max_corr=0.7)
    t0, done = time.time(), 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(fetch_day, c, meta, d, nd) for d, nd in sorted(N.items())]
        for k, fu in enumerate(as_completed(futs)):
            done += fu.result()
            if k % 100 == 0:
                print(f"{k}/{len(N)} {time.time()-t0:.0f}s", flush=True)
    print(f"done {time.time()-t0:.0f}s ({done} new days)")


if __name__ == "__main__":
    main()
