"""ETDX data: official SIP crosses on T-1 and T for 2021-2026 ETD / CEF-preferred ex-dates (Sharadar SFP; 'XXX-PY' ->
Alpaca 'XXX.PRY', plain ETD tickers as-is), frozen PREF-EX filter + FXD dividend guard. Reuses pref_fetch's loop.

    PYTHONPATH=. .venv/bin/python -m research.sim.etdx_fetch      # resumable
"""
from __future__ import annotations

import pathlib

import pandas as pd

from . import pref_fetch as P
from .etdx import events as sfp_events

P.OUT = pathlib.Path(__file__).resolve().parents[2] / "data/research/etdx"


def events() -> pd.DataFrame:
    e, _, _ = sfp_events("SFP", "funds.parquet", ["ETD", "CEF Preferred"])
    e = e.sort_values(["ticker", "date"])
    e = e[e.date >= "2021-01-01"]
    e = e[e.ticker.str.fullmatch(r"[A-Z]{1,6}(-P[A-Z]{1,2})?")].copy()
    e["sym"] = e.ticker.str.replace("-P", ".PR", regex=False)
    return e[["ticker", "sym", "date", "d0", "div", "pc", "dv", "cat"]].reset_index(drop=True)


P.events = events

if __name__ == "__main__":
    P.main()
