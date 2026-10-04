"""Reg SHO threshold lists, daily, free: Nasdaq (2007+) and the NYSE family (2012+). Data only: no returns here.

  PYTHONPATH=. .venv/bin/python -m research.sim.threshold_lists fetch     # raw daily files -> data/research/threshold/
  PYTHONPATH=. .venv/bin/python -m research.sim.threshold_lists clock     # episodes + day counts (structure, no prices)

A list dated D names the threshold securities for settlement date D (published by the SRO the evening before / before
the open, so its contents are known at D's open). Rule 203(b)(3): a fail that persists 13 consecutive settlement days in
a threshold security must be closed out by purchase. The clock: list day k = k-th consecutive session the symbol is on
the list (any market); day 13 is the deadline session, the close-out buy is due by the start of day 14.
"""
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import requests

OUT = "data/research/threshold"
UA = {"User-Agent": "Mozilla/5.0"}
NASDAQ = "https://www.nasdaqtrader.com/dynamic/symdir/regsho/nasdaqth{:%Y%m%d}.txt"
NYSE = ("https://www.nyse.com/api/regulatory/threshold-securities/filter?selectedDate={:%Y-%m-%d}"
        "&pageNumber=1&maxResultsPerPage=1000")


def sessions():
    """Trading sessions from Alpaca's calendar (regular sessions, holidays excluded)."""
    from swingtrader.daily.brokers import regular_sessions
    import datetime as dt
    return [o.date() for o, _ in regular_sessions(dt.date(2007, 1, 1), dt.date(2026, 10, 2))]


def get(url, tries=3):
    for i in range(tries):
        try:
            r = requests.get(url, headers=UA, timeout=30, allow_redirects=False)
            if r.status_code == 200:
                return r.text
            if r.status_code in (301, 302, 404):
                return None
        except requests.RequestException:
            pass
        time.sleep(2 + 3 * i)
    return "ERROR"


def fetch_day(d):
    rows, status = [], {}
    t = get(NASDAQ.format(d))
    status["nasdaq"] = "ok" if t not in (None, "ERROR") else str(t)
    if t not in (None, "ERROR"):
        for line in t.splitlines()[1:]:
            p = line.split("|")
            if len(p) >= 4 and p[0] and not p[0].startswith("File Creation"):
                rows.append(("nasdaq", p[0].strip(), p[1].strip(), p[3].strip()))
    if d.year >= 2012:
        t = get(NYSE.format(d))
        status["nyse"] = "ok" if t not in (None, "ERROR") else str(t)
        if t not in (None, "ERROR"):
            try:
                j = json.loads(t)
                for x in j.get("results") or []:
                    sym = re.sub(r"<[^>]+>", "", str(x.get("symbolLink") or x.get("symbol") or "")).strip()
                    rows.append(("nyse:" + str(x.get("market", "")), sym, str(x.get("description", "")).strip(), "Y"))
                if (j.get("totalCount") or 0) > 1000:
                    status["nyse"] = "truncated"
            except ValueError:
                status["nyse"] = "badjson"
    return d, rows, status


def fetch():
    os.makedirs(OUT, exist_ok=True)
    days = sessions()
    allrows, stat = [], []
    with ThreadPoolExecutor(6) as ex:
        for d, rows, st in ex.map(fetch_day, days):
            allrows += [(d, *r) for r in rows]
            stat.append((d, st.get("nasdaq"), st.get("nyse")))
    df = pd.DataFrame(allrows, columns=["day", "src", "sym", "name", "flag"])
    df["day"] = pd.to_datetime(df.day)
    df.to_parquet(f"{OUT}/lists.parquet")
    pd.DataFrame(stat, columns=["day", "nasdaq", "nyse"]).to_parquet(f"{OUT}/fetch_status.parquet")
    print(len(df), df.day.min(), df.day.max())


FUND_WORDS = r"\b(ETF|ETN|FUND|TRUST|SHARES|PROSHARES|ISHARES|DIREXION|INVESCO|SPDR|ULTRA|INVERSE|LEVERAGED|2X|3X|NOTES|INDEX)\b"


def clock():
    df = pd.read_parquet(f"{OUT}/lists.parquet")
    df = df[(df.flag == "Y") & df.sym.str.fullmatch(r"[A-Z]{1,5}(\.[A-Z])?")]
    st = pd.read_parquet(f"{OUT}/fetch_status.parquet")
    cal = pd.DatetimeIndex(pd.to_datetime(st.day))
    ok = set(pd.to_datetime(st[st.nasdaq == "ok"].day))            # sessions with a readable Nasdaq file
    pos = {d: i for i, d in enumerate(cal)}
    on = df.groupby("sym").day.apply(lambda s: sorted(set(s)))
    names = df.groupby("sym").name.last()
    rows = []
    for sym, days in on.items():
        start = prev = None
        for d in days:
            if prev is not None and pos[d] - pos[prev] == 1:
                prev = d
                continue
            if start is not None:
                rows.append((sym, start, prev))
            start = prev = d
        rows.append((sym, start, prev))
    ep = pd.DataFrame(rows, columns=["sym", "first", "last"])
    ep["days"] = [pos[b] - pos[a] + 1 for a, b in zip(ep["first"], ep["last"])]
    ep["name"] = ep.sym.map(names)
    ep["fund"] = ep.name.str.upper().str.contains(FUND_WORDS, regex=True, na=False)
    prev_end = ep.sort_values("first").groupby("sym")["last"].shift()
    ep["reentry_gap"] = [(pos[a] - pos[b]) if pd.notna(b) else None for a, b in zip(ep["first"], prev_end.reindex(ep.index))]
    ep.to_parquet(f"{OUT}/episodes.parquet")
    c = ep[~ep.fund]
    print(f"sessions {len(cal)} (Nasdaq file ok {len(ok)}), list rows {len(df)}, episodes {len(ep)} "
          f"(non-fund {len(c)})")
    print("non-fund episodes by length:", c.days.clip(upper=30).value_counts().sort_index().to_dict())
    print("reach day 10 / 13 / 14:", int((c.days >= 10).sum()), int((c.days >= 13).sum()), int((c.days >= 14).sum()))
    print("by year (first day), reaching day 10:", c[c.days >= 10].groupby(c["first"].dt.year).size().to_dict())


if __name__ == "__main__":
    {"fetch": fetch, "clock": clock}[sys.argv[1]]()
