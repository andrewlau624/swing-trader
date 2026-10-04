"""Contest hunt Step 2: real NBBO for QQQ 0DTE options (Databento OPRA.PILLAR cbbo-1m).

Per trading day: calls and puts expiring that day, $1 strikes within +/-3% of that day's
regular-hours open (QQQ minute matrix via research/daily-strategies/intra.load, data to 2026-09-21). One
request per month; the cost of every request is checked first and the whole pull aborts
past CAP_USD (the shared free credit has ~$9 left, NEXT.md).

  PYTHONPATH=. .venv/bin/python -m research.sim.contest_opra_fetch [--dry]
Output: data/research/contest/opra/QQQ_<YYYY-MM>.parquet (ts_event, symbol, bid_px, ask_px,
bid_sz, ask_sz), minute bars of the consolidated best bid/offer.
"""
import os
import sys

import numpy as np
import pandas as pd
from dotenv import dotenv_values

sys.path.insert(0, "research/daily-strategies")
import intra  # noqa: E402

intra.SP = "data/research/night"   # minute matrices live in data/research/night/m1

OUT = "data/research/contest/opra"
START, END = "2023-01-01", "2026-10-01"
BAND = 0.03
CAP_USD = 5.0


def osi(day: pd.Timestamp, cp: str, strike: int) -> str:
    return f"QQQ   {day:%y%m%d}{cp}{strike * 1000:08d}"


def day_symbols(day: pd.Timestamp, open_px: float) -> list[str]:
    lo, hi = int(np.floor(open_px * (1 - BAND))), int(np.ceil(open_px * (1 + BAND)))
    return [osi(day, cp, k) for k in range(lo, hi + 1) for cp in "CP"]


def main(dry: bool) -> None:
    import databento as db
    client = db.Historical(dotenv_values(".env")["DATABENTO_API_KEY"])
    M = intra.load("QQQ")
    opens = M["open"][0]
    opens = opens[(opens.index >= START) & (opens.index < END)]
    os.makedirs(OUT, exist_ok=True)
    months = sorted({d.strftime("%Y-%m") for d in opens.index})
    plan, total = [], 0.0
    for mo in months:
        days = opens[opens.index.strftime("%Y-%m") == mo]
        syms = sorted({s for d, px in days.items() for s in day_symbols(d, px)})
        start = days.index[0].strftime("%Y-%m-%d")
        end = (days.index[-1] + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        path = f"{OUT}/QQQ_{mo}.parquet"
        if os.path.exists(path):
            continue
        cost = client.metadata.get_cost(dataset="OPRA.PILLAR", symbols=syms, stype_in="raw_symbol",
                                        schema="cbbo-1m", start=start, end=end)
        total += cost
        plan.append((mo, syms, start, end, path, cost))
        print(f"{mo}: {len(syms)} symbols, ${cost:.3f} (running ${total:.2f})", flush=True)
        if total > CAP_USD:
            sys.exit(f"ABORT: planned cost ${total:.2f} > cap ${CAP_USD}")
    print(f"planned total ${total:.2f} for {len(plan)} months")
    if dry:
        return
    for mo, syms, start, end, path, cost in plan:
        data = client.timeseries.get_range(dataset="OPRA.PILLAR", symbols=syms, stype_in="raw_symbol",
                                           schema="cbbo-1m", start=start, end=end)
        df = data.to_df().reset_index()
        keep = [c for c in ("ts_event", "ts_recv", "symbol", "bid_px_00", "ask_px_00",
                            "bid_sz_00", "ask_sz_00") if c in df.columns]
        df = df[keep].rename(columns=lambda c: c.replace("_00", ""))
        df.to_parquet(path)
        print(f"{mo}: {len(df):,} rows -> {path}", flush=True)


if __name__ == "__main__":
    main("--dry" in sys.argv)
