"""Jump hunt D4: a small company's first 8-K naming a hot theme (theme pivot by filing text; death-dodge of
REGIME/price-first theme momentum: a family of themes, filing-first).

EDGAR full-text search, forms 8-K, quarter by quarter 2014..2026. Event = a CIK's first 8-K mentioning theme T in
`fd` = the 8-K file date (traded at the next open), with no 8-K mentioning T in the prior 730 days (2014-15 are
lookback only). Ticker via jump_common.resolve. Small only: 20-day ADV$ before fd < $20M (raw bars).

THEMES (fixed before any outcome): blockchain, bitcoin, metaverse, "artificial intelligence", "generative AI",
"quantum computing", cannabidiol, psilocybin, "small modular reactor", eVTOL, lithium, uranium, "hydrogen fuel",
"GLP-1".

    PYTHONPATH=. .venv/bin/python -m research.sim.jump_d4
"""
from __future__ import annotations

import pandas as pd

from . import event_fetch as F
from .jump_common import ROOT, resolve, save, small_only

THEMES = ['"blockchain"', '"bitcoin"', '"metaverse"', '"artificial intelligence"', '"generative AI"',
          '"quantum computing"', '"cannabidiol"', '"psilocybin"', '"small modular reactor"', '"eVTOL"', '"lithium"',
          '"uranium"', '"hydrogen fuel"', '"GLP-1"']


def hits() -> pd.DataFrame:
    rows = []
    for t in THEMES:
        for q in pd.period_range("2014Q1", "2026Q3", freq="Q"):
            for h in F.fts(t, "8-K", str(q.start_time.date()), str(q.end_time.date())):
                for cik, nm in zip(h["ciks"], h["names"]):
                    rows.append(dict(theme=t, cik=str(int(cik)), name=nm, date=pd.Timestamp(h["date"])))
        print(t, len(rows), flush=True)
    return pd.DataFrame(rows)


def build() -> pd.DataFrame:
    H = hits().sort_values(["theme", "cik", "date"])
    H["prev"] = H.groupby(["theme", "cik"]).date.shift(1)
    E = H[(H.date >= "2016-01-01") & (H.prev.isna() | ((H.date - H.prev).dt.days > 730))]
    E = E.drop_duplicates(["cik", "date"])
    E = resolve(E.rename(columns={"date": "fd"}))
    return small_only(E, 20e6)


if __name__ == "__main__":
    E = build()
    E.to_csv(ROOT / "data/research/jump/d4_events.csv", index=False)
    save(E, "d4")
