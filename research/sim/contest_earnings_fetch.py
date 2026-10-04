"""Contest hunt T3: Nasdaq earnings calendar (api.nasdaq.com/api/calendar/earnings?date=), one call per weekday.

  PYTHONPATH=. .venv/bin/python -m research.sim.contest_earnings_fetch
Output: data/research/contest/earnings.parquet (date, symbol, time, marketCap, fiscalQuarterEnding).
The calendar date is the scheduled report date (companies announce it weeks ahead), so it is known at entry.
"""
import time

import pandas as pd
import requests

OUT = "data/research/contest/earnings.parquet"
URL = "https://api.nasdaq.com/api/calendar/earnings"


def main():
    rows = []
    for d in pd.bdate_range("2022-12-15", "2026-09-30"):
        for attempt in range(3):
            try:
                r = requests.get(URL, params={"date": f"{d:%Y-%m-%d}"}, timeout=20,
                                 headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
                data = (r.json().get("data") or {}).get("rows") or []
                break
            except Exception:
                time.sleep(2 + 3 * attempt)
                data = []
        for x in data:
            rows.append((d, x.get("symbol"), x.get("time"), x.get("marketCap"), x.get("fiscalQuarterEnding")))
        time.sleep(0.3)
    df = pd.DataFrame(rows, columns=["date", "symbol", "time", "marketCap", "fq"])
    df["mcap"] = pd.to_numeric(df.marketCap.str.replace(r"[$,]", "", regex=True), errors="coerce")
    df.to_parquet(OUT)
    print(len(df), df.date.min(), df.date.max())


if __name__ == "__main__":
    main()
