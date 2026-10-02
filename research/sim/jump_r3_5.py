"""Jump hunt R3-5: earnings reported >= 7 days earlier than the same fiscal quarter a year before.

Cached Nasdaq earnings calendar (data/research/night/earn_cal/<report date>.json, 2019-10..2026-09). For a symbol's
fiscal quarter 'Mon/YYYY', the year-before quarter 'Mon/YYYY-1' must exist; early = report date <= the year-before
report date + 365 - 7 days. The calendar has no announcement dates, so the date is assumed known 2 sessions ahead:
fd = 2 sessions before the report date (the trade spans the release, before- or after-market).

    PYTHONPATH=. .venv/bin/python -m research.sim.jump_r3_5
"""
from __future__ import annotations

import json

import pandas as pd

from .jump_common import ROOT, save, stock_symbols
from .jump_news import sessions, shift_sessions


def build() -> pd.DataFrame:
    rows = []
    for f in sorted((ROOT / "data/research/night/earn_cal").glob("*.json")):
        try:
            for x in json.load(open(f)):
                rows.append((x.get("symbol"), pd.Timestamp(f.stem), x.get("fiscalQuarterEnding") or ""))
        except (ValueError, TypeError):
            continue
    X = pd.DataFrame(rows, columns=["sym", "date", "fq"]).dropna()
    X = X[X.sym.isin(stock_symbols()) & X.fq.str.match(r"^[A-Z][a-z]{2}/\d{4}$")].drop_duplicates(["sym", "fq"])
    X["fq_prev"] = X.fq.str[:4] + (X.fq.str[4:].astype(int) - 1).astype(str)
    P = X[["sym", "fq", "date"]].rename(columns={"fq": "fq_prev", "date": "date_prev"})
    X = X.merge(P, on=["sym", "fq_prev"])
    X = X[(X.date - X.date_prev).dt.days <= 365 - 7]
    S = sessions()
    X["fd"] = [shift_sessions(d, 2, S) for d in X.date]
    return X.dropna(subset=["fd"])[["sym", "fd"]]


if __name__ == "__main__":
    save(build(), "r3_5")
