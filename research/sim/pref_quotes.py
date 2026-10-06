"""PREF-EX execution check: NBBO around the T-1 closing cross (15:58-16:00 ET) and the T opening cross (09:30-09:32 ET)
for a random sample of 2021-26 events; where do the official crosses print relative to the quote?

    PYTHONPATH=. .venv/bin/python -m research.sim.pref_quotes
"""
from __future__ import annotations

import json
import pathlib
import time

import numpy as np
import pandas as pd
import requests

from .auction_fetch import _env

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data/research/pref"
QURL = "https://data.alpaca.markets/v2/stocks/quotes"
OUT = pathlib.Path(__file__).resolve().parent / "pref_quotes_out.txt"


def last_quote(sym, start, end, H):
    q = {"symbols": sym, "start": start, "end": end, "feed": "sip", "limit": 10000}
    r = requests.get(QURL, params=q, headers=H, timeout=30)
    if r.status_code == 429:
        time.sleep(5); r = requests.get(QURL, params=q, headers=H, timeout=30)
    r.raise_for_status()
    v = (r.json().get("quotes") or {}).get(sym, [])
    v = [x for x in v if x.get("bp", 0) > 0 and x.get("ap", 0) > x.get("bp", 0)]
    return v[-1] if v else None


def main():
    H = _env()
    H = {"APCA-API-KEY-ID": __import__("os").environ["APCA_API_KEY_ID"],
         "APCA-API-SECRET-KEY": __import__("os").environ["APCA_API_SECRET_KEY"]} if not isinstance(H, dict) else H
    df = pd.read_parquet(D / "cross_rows.parquet")
    ev = pd.read_parquet(D / "events.parquet")[["ticker", "date", "sym", "d0"]].rename(columns={"ticker": "t", "date": "d"})
    df = df.merge(ev, on=["t", "d"]).sample(300, random_state=7)
    cache = D / "quotes.json"
    got = json.load(open(cache)) if cache.exists() else {}
    for r in df.itertuples():
        k = f"{r.sym}_{r.d.date()}"
        if k in got:
            continue
        d0 = pd.Timestamp(r.d0).tz_localize("America/New_York"); d1 = r.d.tz_localize("America/New_York")
        qc = last_quote(r.sym, (d0 + pd.Timedelta(hours=15, minutes=50)).isoformat(), (d0 + pd.Timedelta(hours=16)).isoformat(), H)
        qo = last_quote(r.sym, (d1 + pd.Timedelta(hours=9, minutes=30)).isoformat(), (d1 + pd.Timedelta(hours=9, minutes=33)).isoformat(), H)
        got[k] = {"qc": qc, "qo": qo}
        time.sleep(0.15)
    json.dump(got, open(cache, "w"))
    rows = []
    x = json.load(open(D / "x" / "dummy.json")) if False else None
    import glob, sys
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    from exdiv_open import crosses
    for r in df.itertuples():
        g = got.get(f"{r.sym}_{r.d.date()}", {})
        if not g.get("qc") or not g.get("qo"):
            continue
        j = json.load(open(D / "x" / f"{r.d.date()}.json"))
        c = crosses(j[r.sym]); c0 = c.loc[pd.Timestamp(r.d0), "cp"]; o1 = c.loc[r.d, "op"]
        bc, ac = g["qc"]["bp"], g["qc"]["ap"]; bo, ao = g["qo"]["bp"], g["qo"]["ap"]
        mc, mo = (bc + ac) / 2, (bo + ao) / 2
        div = r.yld * c0  # approx
        rows.append(dict(spr_c=(ac - bc) / mc, spr_o=(ao - bo) / mo, close_vs_mid=(c0 - mc) / mc, open_vs_mid=(o1 - mo) / mo,
                         co=r.co, co_mid=(mo + div) / mc - 1, co_cross_buy_ask_sell_bid=(bo + div) / ac - 1))
    q = pd.DataFrame(rows)
    L = [f"PREF-EX quotes sample: {len(q)} events with both quotes"]
    for c in q.columns:
        L.append(f"{c:26s} mean {q[c].mean()*1e4:+7.1f}bp  median {q[c].median()*1e4:+7.1f}bp")
    OUT.write_text("\n".join(L) + "\n"); print("\n".join(L))


if __name__ == "__main__":
    main()
