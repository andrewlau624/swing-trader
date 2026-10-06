"""Study OVX: overnight-venue (Blue Ocean ATS) exit for night picks (pre-reg round1_prose.md, N 870).

    PYTHONPATH=. .venv/bin/python -m research.sim.ovx fetch     # resumable, cached per night
    PYTHONPATH=. .venv/bin/python -m research.sim.ovx           # judge

Per pick night d (entry = official close cross on d, base exit = next session's official open cross): 1-min bars from
SIP extended hours (post 16:00-20:00 on d, pre 04:00-09:28 on d+1) and BOATS (20:00 d -> 04:00 d+1). Window VWAPs vs
the open cross.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys
import time
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pyarrow.dataset as ds
import requests

from .auction_fetch import _env

ROOT = pathlib.Path(__file__).resolve().parents[2]
CACHE = ROOT / "data/research/ovx"
OUT = ROOT / "data/research/program/ovx_out.txt"
S = pathlib.Path.home() / "data" / "sharadar"
URL = "https://data.alpaca.markets/v2/stocks/bars"
ET = ZoneInfo("America/New_York")
START, SPLIT = "2024-10-01", "2025-09-30"
WINDOWS = {"post 16-20": ("d", 16, 0, "d", 20, 0, "sip"), "boats 20-24": ("d", 20, 0, "n", 0, 0, "boats"),
           "boats 00-04": ("n", 0, 0, "n", 4, 0, "boats"), "pre 04-08": ("n", 4, 0, "n", 8, 0, "sip"),
           "pre 08-0928": ("n", 8, 0, "n", 9, 28, "sip")}


def picks() -> pd.DataFrame:
    p = pd.read_pickle(ROOT / "data/research/program/auction_audit_picks.pkl")
    p = p[p.ok & (p.d >= START)].copy()
    cal = ds.dataset(S / "funds.parquet").to_table(columns=["date"], filter=ds.field("ticker") == "SPY").to_pandas()
    cal = pd.DatetimeIndex(sorted(pd.to_datetime(cal.date)))
    p["n"] = [cal[cal.get_loc(d) + 1] if d in cal and cal.get_loc(d) + 1 < len(cal) else pd.NaT for d in p.d]
    return p.dropna(subset=["n"])


def _utc(day: pd.Timestamp, h: int, m: int) -> str:
    return dt.datetime(day.year, day.month, day.day, h, m, tzinfo=ET).astimezone(dt.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def _bars(syms, start, end, feed, H):
    out, tok = {}, None
    while True:
        q = {"symbols": ",".join(syms), "timeframe": "1Min", "start": start, "end": end, "feed": feed,
             "limit": 10000, "adjustment": "raw"}
        if tok:
            q["page_token"] = tok
        for k in range(5):
            r = requests.get(URL, params=q, headers=H, timeout=60)
            if r.status_code == 200:
                break
            time.sleep(2 * (k + 1))
        j = r.json()
        for s, b in (j.get("bars") or {}).items():
            out.setdefault(s, []).extend(b)
        tok = j.get("next_page_token")
        if not tok:
            return out


def fetch():
    CACHE.mkdir(parents=True, exist_ok=True)
    p, H = picks(), _env()
    for i, ((d, n), x) in enumerate(p.groupby(["d", "n"])):
        f = CACHE / f"{d.date()}.json"
        if f.exists():
            continue
        syms = sorted(set(x.sym))
        j = {"sip": _bars(syms, _utc(d, 16, 0), _utc(n, 9, 30), "sip", H),
             "boats": _bars(syms, _utc(d, 20, 0), _utc(n, 4, 0), "boats", H)}
        json.dump(j, open(f, "w"))
        if i % 50 == 0:
            print(i, d.date(), flush=True)


def vwap(bars, lo, hi):
    v = [(b["vw"], b["v"]) for b in bars if lo <= b["t"] < hi and b.get("v")]
    if not v:
        return np.nan, 0.0
    px, vol = np.array(v).T
    return float((px * vol).sum() / vol.sum()), float((px * vol).sum())


def table() -> pd.DataFrame:
    p = picks()
    rows = []
    for (d, n), x in p.groupby(["d", "n"]):
        f = CACHE / f"{d.date()}.json"
        if not f.exists():
            continue
        j = json.load(open(f))
        for r in x.itertuples():
            row = dict(d=d, sym=r.sym, adv=r.adv, c=r.c_auc, o=r.o_auc)
            for w, (a, h0, m0, b, h1, m1, feed) in WINDOWS.items():
                lo = _utc(d if a == "d" else n, h0, m0)
                hi = _utc(d if b == "d" else n, h1, m1)
                row[w], row[w + " $"] = vwap(j[feed].get(r.sym, []), lo, hi)
            bl = [b for b in j["boats"].get(r.sym, []) if b.get("v")]
            row["boats"], row["boats $"] = vwap(bl, "0", "9")
            rows.append(row)
    return pd.DataFrame(rows)


def stat(x: pd.Series, d: pd.Series) -> str:
    x, d = x.dropna(), d[x.dropna().index]
    if len(x) < 20:
        return f"n {len(x)}"
    day = x.groupby(d).mean()
    t = day.mean() / day.std() * np.sqrt(len(day))
    return (f"n {len(x):5d} mean {x.mean()*1e4:+7.1f} med {x.median()*1e4:+6.1f} t(day) {t:+5.2f} "
            f"ex-top5 {np.sort(x.values)[:-5].mean()*1e4:+7.1f} hit {(x > 0).mean():.2f}")


def main():
    t = table()
    L = [f"OVX: {len(t)} picks, {t.d.nunique()} nights {t.d.min().date()}..{t.d.max().date()}", ""]
    L.append(f"base close->open cross: {stat(t.o / t.c - 1, t.d)}")
    L.append("")
    L.append("== window VWAP vs the next open cross (x = vwap/o - 1; > 0 means selling in the window beats the open) ==")
    for w in ["post 16-20", "boats 20-24", "boats 00-04", "boats", "pre 04-08", "pre 08-0928"]:
        cov = t[w].notna().mean()
        L.append(f"{w:12s} cov {cov:4.0%} med $ {t.loc[t[w].notna(), w + ' $'].median():>9,.0f} | {stat(t[w] / t.o - 1, t.d)}")
    L.append("")
    x = t.boats / t.o - 1
    L.append("== H1 (BOATS 20-04 VWAP vs open) ==")
    for lab, q in [("half 1", t.d <= SPLIT), ("half 2", t.d > SPLIT), ("ADV top half", t.adv >= t.adv.median()),
                   ("ADV bottom half", t.adv < t.adv.median())]:
        L.append(f"{lab:16s} {stat(x[q], t.d[q])}")
    L.append("")
    L.append("== decomposition: close -> window VWAP (bp), same picks with BOATS coverage ==")
    c = t[t.boats.notna()]
    for w in ["post 16-20", "boats 20-24", "boats 00-04", "pre 04-08", "pre 08-0928"]:
        L.append(f"close -> {w:12s} {stat(c[w] / c.c - 1, c.d)}")
    L.append(f"close -> open cross    {stat(c.o / c.c - 1, c.d)}")
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    fetch() if sys.argv[1:] == ["fetch"] else main()
