"""Jump hunt H24: a small cap's first appearance on Yahoo Finance's trending-tickers page (Wayback snapshots).

Wayback CDX: one 200-status snapshot per day of finance.yahoo.com/trending-tickers (2016-2024). Each snapshot's
tickers are the `/quote/XXXX` links on the page. A snapshot taken at UTC time t is public at t: fd = fd_of(t).
Event = a ticker on the list that was on none of the snapshots in the prior 180 days, with 20-day ADV$ < $20M.

    PYTHONPATH=. .venv/bin/python -m research.sim.jump_h24 fetch     # resumable, ~1 request/s
    PYTHONPATH=. .venv/bin/python -m research.sim.jump_h24
"""
from __future__ import annotations

import json
import re
import sys
import time

import pandas as pd
import requests

from .jump_common import ROOT, fd_of, first_in, save, small_only

D = ROOT / "data/research/jump/yahoo_trending"
UA = {"User-Agent": "swing-trader personal research (jump hunt; one request at a time)"}
URL = "finance.yahoo.com/trending-tickers"


def snapshots() -> list[str]:
    f = D / "cdx.json"
    if not f.exists():
        D.mkdir(parents=True, exist_ok=True)
        for k in range(6):
            try:
                r = requests.get("http://web.archive.org/cdx/search/cdx", params={"url": URL, "output": "json",
                                 "filter": "statuscode:200", "collapse": "timestamp:8"}, headers=UA, timeout=120)
                json.dump([x[1] for x in r.json()[1:]], open(f, "w"))
                break
            except (requests.RequestException, ValueError):
                time.sleep(10 * (k + 1))
    return json.load(open(f))


def fetch():
    from concurrent.futures import ThreadPoolExecutor
    for ts in snapshots():
        _one(ts)
        time.sleep(4)          # archive.org refused connections at 3 threads: one request every ~4 s


def _one(ts: str):
    f = D / f"{ts}.json"
    if f.exists():
        return
    syms = None
    for k in range(4):
        try:
            r = requests.get(f"http://web.archive.org/web/{ts}id_/https://{URL}", headers=UA, timeout=60)
            if r.ok:
                syms = sorted(set(re.findall(r'/quote/([A-Z]{1,5})[?/"]', r.text)))
                break
        except requests.RequestException:
            pass
        time.sleep(5 * (k + 1))
    if syms is not None:
        json.dump(syms, open(f, "w"))


def build() -> pd.DataFrame:
    rows = []
    for f in sorted(D.glob("2*.json")):
        for s in json.load(open(f)):
            rows.append(dict(sym=s, ts=pd.Timestamp(f.stem, tz="UTC")))
    X = pd.DataFrame(rows)
    X["fd"] = fd_of(X.ts)
    X = X.drop_duplicates(["sym", "fd"])
    E = first_in(X[["sym", "fd"]], 180)
    E = E[E.fd >= X.fd.min() + pd.Timedelta(days=180)]           # need a 180-day history to call it "first"
    return small_only(E, 20e6)


if __name__ == "__main__":
    if sys.argv[1:] == ["fetch"]:
        fetch()
    else:
        save(build(), "h24")
