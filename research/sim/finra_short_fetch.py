"""Round 21 data: FINRA Reg SHO daily short-sale volume (consolidated off-exchange, CNMS files).

    PYTHONPATH=. .venv/bin/python -m research.sim.finra_short_fetch      # resumable

https://cdn.finra.org/equity/regsho/daily/CNMSshvolYYYYMMDD.txt (public, no account). Keeps only
night-pick symbols; one parquet per session in data/research/night/finra_short/. Fetch only.
Note: published after the close of day t, so a decision on d may use t <= d-1 only.
"""
from __future__ import annotations

import io
import pathlib
import time

import pandas as pd
import requests

from . import book as B
from . import data as D

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/night/finra_short"
URL = "https://cdn.finra.org/equity/regsho/daily/CNMSshvol{:%Y%m%d}.txt"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    N = B.night_days(raw_price=True, max_corr=0.7)
    syms = {str(x) for nd in N.values() for x in nd.syms}
    cal = D.etf()["close"].index
    cal = cal[(cal >= "2020-10-01") & (cal <= "2026-09-30")]
    t0 = time.time()
    for i, d in enumerate(cal):
        f = OUT / f"{d.date()}.parquet"
        if f.exists():
            continue
        r = requests.get(URL.format(d), timeout=30)
        if r.status_code != 200:
            print("missing", d.date(), r.status_code); continue
        x = pd.read_csv(io.StringIO(r.text), sep="|")
        x = x[x.Symbol.isin(syms)][["Symbol", "ShortVolume", "ShortExemptVolume", "TotalVolume"]]
        x.to_parquet(f)
        if i % 100 == 0:
            print(f"{i}/{len(cal)} {time.time()-t0:.0f}s", flush=True)
    print("done", f"{time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
