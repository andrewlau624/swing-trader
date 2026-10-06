"""PREF-EX data: official SIP crosses on T-1 and T for 2021-2026 preferred ex-dates (Sharadar 'XXX-PY' -> Alpaca
'XXX.PRY'), 20d median $vol >= $100k.

    PYTHONPATH=. .venv/bin/python -m research.sim.pref_fetch      # resumable
"""
from __future__ import annotations

import json
import pathlib
import re
import time

import pandas as pd
import pyarrow.dataset as ds

from .auction_fetch import _env, fetch

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/pref"
S = pathlib.Path.home() / "data" / "sharadar"


def events() -> pd.DataFrame:
    t = ds.dataset(S / "tickers.parquet").to_table(columns=["table", "ticker", "category"]).to_pandas()
    pref = set(t.loc[(t.table == "SEP") & (t.category == "Domestic Preferred Stock"), "ticker"])
    b = ds.dataset(S / "stocks.parquet").to_table(columns=["ticker", "date", "volume", "closeunadj"],
                                                  filter=ds.field("ticker").isin(list(pref))).to_pandas()
    b["date"] = pd.to_datetime(b.date)
    b = b.sort_values(["ticker", "date"])
    g = b.groupby("ticker", sort=False)
    b["pc"] = g.closeunadj.shift(1)
    b["d0"] = g.date.shift(1)
    b["dv"] = (b.closeunadj * b.volume).groupby(b.ticker).transform(lambda s: s.shift(1).rolling(20, min_periods=10).median())
    a = ds.dataset(S / "actions.parquet").to_table(columns=["date", "action", "ticker", "value"]).to_pandas()
    a = a[(a.action == "dividend") & a.ticker.isin(pref)].copy()
    a["date"] = pd.to_datetime(a.date)
    a = a.groupby(["ticker", "date"], as_index=False).value.sum().rename(columns={"value": "div"})
    e = b.merge(a, on=["ticker", "date"])
    e = e[(e.date >= "2021-01-01") & (e.dv >= 1e5) & e.pc.between(10, 60) & (e["div"] / e.pc).between(0.002, 0.04)]
    e = e[e.ticker.str.fullmatch(r"[A-Z]{1,5}-P[A-Z]{1,2}")]
    e["sym"] = e.ticker.str.replace("-P", ".PR", regex=False)
    return e[["ticker", "sym", "date", "d0", "div", "pc", "dv"]].reset_index(drop=True)


def main():
    (OUT / "x").mkdir(parents=True, exist_ok=True)
    ef = OUT / "events.parquet"
    if not ef.exists():
        events().to_parquet(ef)
    e = pd.read_parquet(ef)
    H = _env(); t0 = time.time()
    grp = list(e.groupby("date"))
    for i, (d, x) in enumerate(grp):
        f = OUT / "x" / f"{pd.Timestamp(d).date()}.json"
        if f.exists():
            continue
        syms = sorted(set(x.sym))
        rows = {}
        for k in range(0, len(syms), 100):
            rows.update(fetch(syms[k:k + 100], str(pd.Timestamp(x.d0.min()).date()), str(pd.Timestamp(d).date()), H))
        json.dump(rows, open(f, "w"))
        time.sleep(0.2)
        if i % 100 == 0:
            print(f"{i}/{len(grp)} {time.time()-t0:.0f}s", flush=True)
    print("done", len(grp), f"{time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
