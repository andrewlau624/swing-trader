"""Runbook snippet B (events by 8-K full-text phrase), for the overnight loop. Each hit -> (ticker, filing date):
tickers from the hit's display name, else company_tickers() by CIK. One row per (sym, fd).

    PYTHONPATH=. .venv/bin/python -m research.sim.events_fts_build NAME '"exact phrase"' [FORMS]
"""
import sys

import pandas as pd

from research.sim import event_fetch as F


def build(name: str, q: str, forms: str = "8-K", y0: int = 2020, y1: int = 2026) -> pd.DataFrame:
    hits = F.fts_years(q, forms, y0, y1)
    tick = F.company_tickers()
    rows = []
    for h in hits:
        syms = set()
        for nm, cik in zip(h["names"], h["ciks"]):
            syms |= set(F.ticker_of(nm)) or set(tick.get(str(int(cik)), []))
        rows += [(s.upper().replace("-", "."), h["date"], h["adsh"]) for s in syms]
    X = pd.DataFrame(rows, columns=["sym", "fd", "adsh"])
    X["fd"] = pd.to_datetime(X.fd)
    X = X.drop_duplicates(["sym", "fd"])[["sym", "fd"]].sort_values("fd")
    X.to_parquet(f"data/research/program/events_{name}.parquet")
    print(f"{len(hits)} hits -> {len(X)} events, {X.fd.min()}..{X.fd.max()}")
    print(X.groupby(X.fd.dt.year).size().to_dict())
    return X


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "8-K")
