"""CLOSE-DISLOC data: 15:50-15:56 ET one-minute SIP bars + official crosses for 200 mid-liquidity stocks, 2024-07..2026-09.

    PYTHONPATH=. .venv/bin/python -m research.sim.close_disloc_fetch      # resumable

Universe: Sharadar common stocks with 20d $vol $10M-$200M and raw close >= $10 on 2024-06-28 (top 200 by $vol in that
band; chosen on a date before the window). Cached under data/research/close_disloc/.
"""
from __future__ import annotations

import json
import pathlib
import time
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from .auction_fetch import _env, fetch

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/close_disloc"
BARS = "https://data.alpaca.markets/v2/stocks/bars"
ET = ZoneInfo("America/New_York")


def universe() -> list[str]:
    import sys
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    from lh_panel import Panel
    P = Panel.load()
    import numpy as np
    d = np.searchsorted(P.dates, np.datetime64("2024-06-28"))
    rows = np.flatnonzero((P.di == d) & (P.src == 0))
    out = []
    for g in rows:
        t = P.tickers[P.tid[g]]
        if not isinstance(t, str) or not t.isalpha() or len(t) > 5 or g < 20 or P.tid[g - 20] != P.tid[g]:
            continue
        dv = float((P.c[g - 19:g + 1] * P.v[g - 19:g + 1]).mean())
        if 1e7 <= dv <= 2e8 and P.cu[g] >= 10:
            out.append((dv, t))
    return [t for _, t in sorted(out, reverse=True)[:200]]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    H = _env()
    uf = OUT / "universe.json"
    syms = json.load(open(uf)) if uf.exists() else universe()
    json.dump(syms, open(uf, "w"))
    af = OUT / "auctions.json"
    if not af.exists():
        A = {}
        for i in range(0, len(syms + ["SPY"]), 40):
            A.update(fetch((syms + ["SPY"])[i:i + 40], "2024-07-01", "2026-10-02", H))
        json.dump(A, open(af, "w"))
    days = pd.bdate_range("2024-07-01", "2026-10-01")
    t0 = time.time()
    for k, d in enumerate(days):
        f = OUT / f"m_{d.date()}.json"
        if f.exists():
            continue
        s = pd.Timestamp(f"{d.date()} 15:50", tz=ET).tz_convert("UTC")
        e = pd.Timestamp(f"{d.date()} 15:57", tz=ET).tz_convert("UTC")
        rows, tok = {}, None
        while True:
            q = {"symbols": ",".join(syms), "timeframe": "1Min", "start": s.isoformat(), "end": e.isoformat(),
                 "feed": "sip", "limit": 10000, "adjustment": "raw"}
            if tok:
                q["page_token"] = tok
            r = requests.get(BARS, params=q, headers=H, timeout=30)
            if r.status_code == 429:
                time.sleep(5); continue
            r.raise_for_status(); j = r.json()
            for sym, v in (j.get("bars") or {}).items():
                rows.setdefault(sym, []).extend(v)
            tok = j.get("next_page_token")
            if not tok:
                break
        json.dump(rows, open(f, "w"))
        if k % 50 == 0:
            print(f"{k}/{len(days)} {time.time()-t0:.0f}s", flush=True)
    print("done", f"{time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
