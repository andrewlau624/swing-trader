"""Round 29 data (free): Nasdaq earnings calendar by date, FINRA consolidated short interest by settlement date.

    PYTHONPATH=. .venv/bin/python -m research.sim.ds_fetch earnings
    PYTHONPATH=. .venv/bin/python -m research.sim.ds_fetch finra

Cached one file per date under data/research/night/earn_cal/ and data/research/night/finra_si/ (gitignored);
re-runs skip what is cached.
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

import pandas as pd
import requests

ROOT = pathlib.Path(__file__).resolve().parents[2]
EARN = ROOT / "data/research/night/earn_cal"
SI = ROOT / "data/research/night/finra_si"
UA = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}


def earnings(start="2019-10-01", end="2026-09-30"):
    EARN.mkdir(parents=True, exist_ok=True)
    for d in pd.bdate_range(start, end):
        f = EARN / f"{d.date()}.json"
        if f.exists():
            continue
        for k in range(4):
            try:
                r = requests.get("https://api.nasdaq.com/api/calendar/earnings", params={"date": str(d.date())},
                                 headers=UA, timeout=30)
                rows = ((r.json().get("data") or {}).get("rows")) or []
                json.dump(rows, open(f, "w"))
                break
            except Exception as e:                    # noqa: BLE001
                print(d.date(), "retry", k, e, flush=True); time.sleep(3 * (k + 1))
        time.sleep(0.25)
    print("earnings done", flush=True)


def finra(start="2020-06-01", end="2026-09-30"):
    SI.mkdir(parents=True, exist_ok=True)
    url = "https://api.finra.org/data/group/otcMarket/name/consolidatedShortInterest"
    # settlement dates: mid-month and month-end business days; probe every business day once, keep non-empty
    for d in pd.bdate_range(start, end):
        if not (10 <= d.day <= 17 or d.day >= 24):
            continue
        f = SI / f"{d.date()}.parquet"
        if f.exists() or (SI / f"{d.date()}.empty").exists():
            continue
        rows, off = [], 0
        while True:
            body = {"limit": 5000, "offset": off, "fields": ["symbolCode", "settlementDate",
                    "currentShortPositionQuantity", "averageDailyVolumeQuantity", "daysToCoverQuantity"],
                    "compareFilters": [{"compareType": "EQUAL", "fieldName": "settlementDate",
                                        "fieldValue": str(d.date())}]}
            for k in range(4):
                try:
                    r = requests.post(url, json=body, headers={"Accept": "application/json"}, timeout=60)
                    part = r.json() if r.text.strip() else []
                    break
                except Exception as e:                # noqa: BLE001
                    print(d.date(), "retry", k, e, flush=True); time.sleep(3 * (k + 1)); part = []
            rows += part
            if len(part) < 5000:
                break
            off += 5000
        if rows:
            pd.DataFrame(rows).to_parquet(f)
            print(d.date(), len(rows), flush=True)
        else:
            (SI / f"{d.date()}.empty").touch()
    print("finra done", flush=True)


if __name__ == "__main__":
    {"earnings": earnings, "finra": finra}[sys.argv[1]]()
