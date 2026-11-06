"""Rebuild a daily CEF NAV/price history 2007-2026 from the Nasdaq Fund Network (CEFConnect history is not on disk any more).

Reuses swingtrader.daily.cef_nav.hist (the server's weekly-refresh source). NAV symbols come from the server's map
(state/cef-rv-navmap.json, copied to data/research/cefconnect/navmap_server.json). Nasdaq serves NAV history from ~2007-04
(5000-row limit) and fund prices for ~10y only, so the runner (cef_stress.py) takes pre-2016 prices from Sharadar SFP.
Same survivorship as the CEFConnect panel: funds alive in 2026 only (and only the ~314 with a Nasdaq NAV symbol).

    python3 research/sim/cef_nasdaq_hist.py     # -> data/research/cefconnect/nasdaq_daily.parquet
"""
from __future__ import annotations

import json
import pathlib
import sys
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from swingtrader.daily.cef_nav import hist  # noqa: E402

CEF = ROOT / "data/research/cefconnect"
SINCE = "2007-01-01"


def one(item):
    sym, navsym = item
    nav = hist(navsym, "mutualfunds", SINCE)
    px = hist(sym, "stocks", SINCE)
    return sym, nav, px


def main() -> int:
    m = json.loads((CEF / "navmap_server.json").read_text())
    items = [(s, v["nav"]) for s, v in sorted(m.items()) if v.get("nav")]
    recs = []
    with ThreadPoolExecutor(4) as ex:
        for k, (sym, nav, px) in enumerate(ex.map(one, items), 1):
            for d, v in nav.items():
                recs.append((sym, d, v, px.get(d)))
            print(f"{k}/{len(items)} {sym} nav {len(nav)} px {len(px)} first {min(nav) if nav else '-'}", flush=True)
    df = pd.DataFrame(recs, columns=["ticker", "date", "nav", "px_nasdaq"])
    df["date"] = pd.to_datetime(df["date"])
    df.to_parquet(CEF / "nasdaq_daily.parquet")
    print("rows", len(df), "funds", df.ticker.nunique(), df.date.min(), df.date.max())
    return 0


if __name__ == "__main__":
    sys.exit(main())
