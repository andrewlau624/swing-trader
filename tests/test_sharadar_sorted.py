"""Canary: the Sharadar bulk CSVs arrive shuffled within ticker (2026-11-10 audit, docs/memory). funds.parquet was
re-sorted on disk and the loader now sorts on write; this fails if an unsorted file comes back. Reads one ticker."""
import pathlib

import pandas as pd
import pytest

STORE = pathlib.Path.home() / "data" / "sharadar"


@pytest.mark.parametrize("table,ticker", [
    ("funds", "SPY"),
    # stocks.parquet is still shuffled on disk (re-sort not yet approved); readers must sort. Flip when re-sorted.
    pytest.param("stocks", "AAPL", marks=pytest.mark.xfail(reason="stocks.parquet unsorted on disk", strict=True)),
])
def test_sharadar_price_table_sorted(table, ticker):
    p = STORE / f"{table}.parquet"
    if not p.exists():
        pytest.skip(f"{p} not on this machine")
    d = pd.to_datetime(pd.read_parquet(p, columns=["date"], filters=[("ticker", "==", ticker)])["date"])
    assert len(d) > 1000
    assert d.is_monotonic_increasing, f"{table}.parquet not sorted by date within {ticker}: sort by (ticker, date)"
