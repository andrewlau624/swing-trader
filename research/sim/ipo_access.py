"""Discovery DL7: IPO allocations via retail IPO-access platforms, a bound. Registered in round1_prose.md
(amendment "deal rule DL7") before this ran."""
from __future__ import annotations

import html
import re

import pandas as pd

from research.sim.event_fetch import doc, fts_years, raw_bars, ticker_of

NOT_OP = re.compile(r"Acquisition|Blank Check|Capital Corp\b.*(?:I|II|III|IV|V)$|SPAC|Merger Corp|Fund\b|Trust\b|ETF", re.I)


def ipos() -> pd.DataFrame:
    R = [r for r in fts_years('"initial public offering price" "per share"', "424B4", 2019, 2026) if r["form"] == "424B4"]
    first = {}
    for r in sorted(R, key=lambda r: r["date"]):
        first.setdefault(r["ciks"][0], r)
    rows = []
    for r in first.values():
        name = r["names"][0]
        tk = [t for t in ticker_of(name) if not re.search(r"W$|WS$|U$|R$|\.", t)]
        if not tk or NOT_OP.search(re.sub(r"\s+\(.*", "", name)) or r["date"] > "2026-06-30":
            continue
        t = html.unescape(doc(r["ciks"][0], r["adsh"], r["id"].split(":")[1])[:60000])
        if re.search(r"(?i)\bunits?\b[^.]{0,60}each consisting|American Depositary Shares", t[:20000]):
            continue
        m = re.search(r"initial public offering price (?:is|of|will be) \$(\d+(?:\.\d+)?) per (?:share|ordinary share)", t)
        if m and float(m.group(1)) >= 4:
            rows.append(dict(date=r["date"], name=name[:40], sym=tk[0], X=float(m.group(1))))
    return pd.DataFrame(rows)


def run(stake: float = 500.0) -> pd.DataFrame:
    D = ipos()
    out = []
    for _, d in D.iterrows():
        b = raw_bars([d.sym])[d.sym]
        if len(b) < 31:
            continue
        b.index = pd.to_datetime(b.index)
        aft = b.index[b.index >= pd.Timestamp(d.date)]
        if not len(aft) or (aft[0] - pd.Timestamp(d.date)).days > 8 or b.index[0] < pd.Timestamp(d.date) - pd.Timedelta(days=5):
            continue  # first bar must be the debut (not a reused/older symbol)
        i0 = b.index.get_loc(aft[0])
        if i0 + 29 >= len(b):
            continue
        o, c1, c30 = b.open.iloc[i0], b.close.iloc[i0], b.close.iloc[i0 + 29]
        out.append(dict(**d.to_dict(), debut=aft[0].date(), open=o, r1=c1 / d.X - 1, r30=c30 / d.X - 1, cold=o <= 1.10 * d.X))
    return pd.DataFrame(out)


if __name__ == "__main__":
    D = run()
    D.to_csv("data/research/events/ipo_access_deals.csv", index=False)
    yrs = 7.5
    print("IPOs", len(D), f"({len(D)/yrs:.0f}/yr); cold (open <= 1.10 X): {int(D.cold.sum())}")
    for lab, X in [("opt: all filled", D), ("pess: cold only", D[D.cold])]:
        print(f"{lab:18s} n {len(X)} r30 mean {X.r30.mean():.1%} median {X.r30.median():.1%} hit {(X.r30 > 0).mean():.0%} |"
              f" r1 mean {X.r1.mean():.1%} median {X.r1.median():.1%} | $/yr at $500/deal {500 * X.r30.sum() / yrs:.0f}")
    print(D.groupby(pd.to_datetime(D.debut).dt.year).apply(lambda g: pd.Series(dict(n=len(g), cold=int(g.cold.sum()),
          r30_all=g.r30.median(), r30_cold=g[g.cold].r30.median()))).round(3).to_string())
