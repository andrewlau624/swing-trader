"""Discovery DL4: liquidations below the proxy's low estimate. Registered in round1_prose.md (amendment "deal rule
DL4") before this ran. `entries()` builds the deal set; payoffs (cash actually distributed) are read from 8-Ks into
PAYOFF by hand and cross-checked with Alpaca corporate actions."""
from __future__ import annotations

import html
import re

import pandas as pd

from research.sim.event_fetch import doc, fts_years, raw_bars, ticker_of

# Tickers for proxies that don't print one (lookup only, no prices): EDGAR company names at the time.
TICK = {"1085621": "ACTA", "1294649": "WLKR", "1305323": "ZVO", "1634379": "MTCR", "1709401": "RUBY", "1674365": "APTX",
        "1671818": "ONCR", "1383701": "HSTO", "1274792": "MACK", "1173281": "NBSE"}

SPAC = re.compile(r"Acquisition|Capital Acquisition|Hedosophia|Holdings Corp\. [IV]+|Investment Corp|Partners III|"
                  r"Gores Holdings|Equity Partners|Principal Holdings|Special Situations|Energem|Ventures Acquisition|Lionheart", re.I)


def entries() -> pd.DataFrame:
    R = [r for r in fts_years('"plan of dissolution" "liquidating distributions" "per share" "estimate"', "DEF 14A", 2016, 2026)
         if r["form"] == "DEF 14A"]
    first = {}
    for r in sorted(R, key=lambda r: r["date"]):
        first.setdefault(r["ciks"][0], r)
    rows = []
    for r in first.values():
        if SPAC.search(r["names"][0]) or r["date"] > "2026-06-30":
            continue
        t = re.sub(r"\s+", " ", html.unescape(doc(r["ciks"][0], r["adsh"], r["id"].split(":")[1])))
        m = re.search(r"(?:between|range of|from) (?:approximately )?\$(\d+\.\d+)(?: per share)? (?:and|to) (?:approximately )?\$(\d+\.\d+)[^.]{0,60}per share", t)
        if not m:
            continue
        sym = TICK.get(str(int(r["ciks"][0]))) or (ticker_of(r["names"][0]) or [x.rstrip(".") for x in re.findall(r"under the symbol “([A-Z.]{1,6})”", t)] or [None])[0]
        row = dict(date=r["date"], name=r["names"][0][:40], cik=r["ciks"][0], sym=sym, A=float(m.group(1)), B=float(m.group(2)))
        if sym:
            b = raw_bars([sym])[sym]
            if len(b):
                b.index = pd.to_datetime(b.index)
                aft = b.index[b.index > pd.Timestamp(r["date"])]
                if len(aft) and (aft[0] - pd.Timestamp(r["date"])).days <= 7:
                    row.update(entry_day=aft[0].date(), entry=float(b.close.loc[aft[0]]), last_bar=b.index[-1].date(),
                               last_close=float(b.close.iloc[-1]))
        row["traded"] = bool(row.get("entry") and row["entry"] < row["A"])
        rows.append(row)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    E = entries()
    E.to_csv("data/research/events/liquidation_entries.csv", index=False)
    print(E.to_string())
