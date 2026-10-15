"""Download FINRA OTC Transparency WEEKLY data for the EQ18 ETFs only.

Per (symbol, week-start-Monday) sync POST with EQUAL filters; the 18 book ETFs
are the conditioning targets, so full-market downloads are unnecessary.
Types kept: ATS_W_SMBL_FIRM and OTC_W_SMBL_FIRM (and equals-if-present).

Auth: none needed for this dataset. FINRA_API_KEY (env) reserved for later
authed datasets (equity detail / short interest).

Run: PYTHONPATH=. .venv/bin/python -m research.sim.finra_ats
"""
from __future__ import annotations

import csv
import io
import random
import time

import httpx
import pandas as pd

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data/research/finra/ats_etf.parquet"
PROG = ROOT / "data/research/finra/ats_etf_progress.txt"
FIELDS = ["issueSymbolIdentifier", "weekStartDate", "totalWeeklyShareQuantity",
          "totalWeeklyTradeCount", "summaryTypeCode", "initialPublishedDate", "tierIdentifier"]
ENDPOINT = "https://api.finra.org/data/group/otcMarket/name/weeklySummary"
EQ18 = ["SPY", "QQQ", "IWM", "DIA", "MDY", "XLK", "XLF", "XLE", "XLV", "XLI",
        "XLY", "XLP", "XLU", "XLB", "SMH", "XBI", "EEM", "EFA"]


def fetch_one(c: httpx.Client, sym: str, wk: str, retries: int = 6) -> list:
    for a in range(retries):
        r = c.post(ENDPOINT, json={
            "limit": 20000, "fields": FIELDS,
            "compareFilters": [
                {"fieldName": "weekStartDate", "fieldValue": wk, "compareType": "EQUAL"},
                {"fieldName": "issueSymbolIdentifier", "fieldValue": sym, "compareType": "EQUAL"}]},
            timeout=60)
        if r.status_code == 429:
            time.sleep(3 * (a + 1))
            continue
        if r.status_code == 204 or not r.text.strip():
            return []
        if r.status_code != 200 or len(r.text) > 3_000_000:
            print(f"  {sym} {wk}: status {r.status_code} len {len(r.text)}")
            time.sleep(5)
            continue
        rows = list(csv.DictReader(io.StringIO(r.text)))
        rows = [x for x in rows if x.get("issueSymbolIdentifier") == sym
                and x.get("weekStartDate") == wk]  # server occasionally ignores filters
        if a > 0:
            time.sleep(1)
        return rows
    print(f"  {sym} {wk}: gave up")
    return []


def fetch() -> pd.DataFrame:
    weeks = [d.strftime("%Y-%m-%d") for d in pd.date_range("2018-01-01", "2026-10-05", freq="W-MON")]
    done = set(PROG.read_text().splitlines()) if PROG.exists() else set()
    todo = [(s, w) for w in weeks for s in EQ18 if f"{w}|{s}" not in done]
    results = []
    with ThreadPoolExecutor(max_workers=3) as ex:
        with httpx.Client(timeout=90) as c:
            futs = {}
            for s, w in todo:
                futs[ex.submit(fetch_one, c, s, w)] = (s, w)
            for i, fut in enumerate(as_completed(futs)):
                s, w = futs[fut]
                try:
                    rows = fut.result()
                except Exception as e:  # noqa: BLE001
                    print(f"  {s} {w}: {type(e).__name__}")
                    continue
                results += rows
                with PROG.open("a") as f:
                    f.write(f"{w}|{s}\n")
                if (i + 1) % 500 == 0:
                    print(f"{i+1}/{len(todo)}", flush=True)
    if not results:
        return pd.DataFrame()
    d = pd.DataFrame([dict(x) for x in results])
    d.to_parquet(CACHE)
    return d


if __name__ == "__main__":
    if CACHE.exists():
        old = pd.read_parquet(CACHE)
        ws = sorted(old.weekStartDate.unique())
        print("existing cache:", len(old), "rows", ws[0], "..", ws[-1])
    d = fetch()
    print("TOTAL rows:", len(d))
