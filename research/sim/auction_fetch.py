"""Study AW (Round 19) data: official opening/closing cross prints for every night pick.

    PYTHONPATH=. .venv/bin/python -m research.sim.auction_fetch      # ~10 min, resumable

Alpaca `/v2/stocks/auctions` (SIP): for each pick day d, the picks' closing cross on d and opening
cross on the next session. Cached per day in data/research/night/auctions/<d>.json (raw API rows).
Fetches only; no returns are computed here.
"""
from __future__ import annotations

import json
import os
import pathlib
import time

import requests

from . import book as B

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/night/auctions"
URL = "https://data.alpaca.markets/v2/stocks/auctions"


def _env():
    for line in open(ROOT / ".env"):
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.strip().split("=", 1)
            os.environ.setdefault(k, v.strip().strip('"').strip("'"))
    return {"APCA-API-KEY-ID": os.environ["ALPACA_API_KEY"],
            "APCA-API-SECRET-KEY": os.environ["ALPACA_SECRET_KEY"]}


def fetch(syms, start, end, H):
    rows, tok = {}, None
    while True:
        q = {"symbols": ",".join(syms), "start": start, "end": end, "feed": "sip", "limit": 10000}
        if tok:
            q["page_token"] = tok
        for k in range(5):
            r = requests.get(URL, params=q, headers=H, timeout=30)
            if r.status_code == 429:
                time.sleep(5 * (k + 1)); continue
            r.raise_for_status(); break
        j = r.json()
        for s, v in (j.get("auctions") or {}).items():
            rows.setdefault(s, []).extend(v)
        tok = j.get("next_page_token")
        if not tok:
            return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    H = _env()
    N = B.night_days(raw_price=True, max_corr=0.7)
    days = sorted(N)
    cal = list(B.D.etf()["close"].index)
    nxt = {a: b for a, b in zip(cal[:-1], cal[1:])}
    t0 = time.time()
    for i, d in enumerate(days):
        f = OUT / f"{d.date()}.json"
        if f.exists():
            continue
        e = nxt.get(d)
        if e is None:
            continue
        syms = sorted({str(s) for s in N[d].syms})
        rows = fetch(syms, str(d.date()), str(e.date()), H)
        json.dump(rows, open(f, "w"))
        time.sleep(0.3)
        if i % 100 == 0:
            print(f"{i}/{len(days)} {time.time()-t0:.0f}s", flush=True)
    print("done", len(days), f"{time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
