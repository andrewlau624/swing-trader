"""CEFConnect weekly NAV/price/discount panel (third-robot session, forwarded data collector).

Source: https://www.cefconnect.com/api/v3/funds (live-funds list; survivorship caveat documented:
dead CEFs are absent entirely — a positive backtest must later be replicated on a
delisted-inclusive source before any claim).

Cache: data/research/cefconnect/pricing_{SYM}.json -> data/research/cefconnect/cef_panel.parquet
  .venv/bin/python research/sim/cef_panel.py --refetch
"""
from __future__ import annotations

import json
import pathlib
import time
import urllib.request

import pandas as pd

OUT_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "data" / "research" / "cefconnect"
HEAD = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) research-personal"}


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers=HEAD)
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def fund_list() -> pd.DataFrame:
    return pd.DataFrame(fetch_json("https://www.cefconnect.com/api/v3/funds"))


def fetch_one(sym: str) -> list[dict]:
    row = fetch_json(f"https://www.cefconnect.com/api/v3/pricinghistory/{sym}/All")
    a = row.get("Data", {})
    return a.get("PriceHistory", [])[::-1] if isinstance(a, dict) else []


def build(refetch: bool) -> pd.DataFrame:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    funds = fund_list()
    funds.to_csv(OUT_DIR / "fund_list.csv", index=False)
    recs = []
    for n, (sym, name) in enumerate(zip(funds["Ticker"], funds["Name"]), 1):
        p = OUT_DIR / f"pricing_{sym}.json"
        if not p.exists() or refetch:
            try:
                p.write_text(json.dumps(fetch_json(f"https://www.cefconnect.com/api/v3/pricinghistory/{sym}/All")))
                time.sleep(0.3)
            except Exception as e:
                print(sym, "ERR", type(e).__name__, str(e)[:60], flush=True)
                continue
        try:
            d = json.loads(p.read_text())
            hist = d["Data"]["PriceHistory"]
        except Exception:
            print(sym, "parse-ERR", flush=True)
            continue
        for r in hist:
            recs.append(dict(ticker=sym, name=name, date=pd.Timestamp(r["DataDate"]),
                             price=r["Data"], nav=r["NAVData"],
                             disc=r.get("DiscountData")))
        print(f"{sym} {n}/{len(funds)} {len(hist)} rows", flush=True)
    df = pd.DataFrame(recs)
    df.to_parquet(OUT_DIR / "cef_panel.parquet")
    print("total", len(df), "funds", df["ticker"].nunique(),
          "range", df["date"].min(), "->", df["date"].max(), flush=True)
    return df


if __name__ == "__main__":
    import sys
    build(refetch="--refetch" in sys.argv)
