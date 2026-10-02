"""Discovery DL5: dated-term CEFs in their final year. Registered in round1_prose.md (amendment "deal rule DL5")
before this ran. Termination dates come from each fund's own N-CSR/N-2 sentence."""
from __future__ import annotations

import datetime as dt
import html
import re

import pandas as pd

from research.sim.event_fetch import doc, fts_years, raw_bars, ticker_of

QS = ['"will terminate on or about"', '"Termination Date" "Target Term"', '"term trust" "will terminate"',
      '"Term Trust" "terminate on or about"', '"Target Term Fund" "terminate"']
# Benchmark by fund name keywords (first match wins).
BENCH = [(r"Municipal|Muni|Tax.Free", "MUB"), (r"Floating|Senior|Loan", "BKLN"), (r"Emerging", "EMB"),
         (r"Preferred", "PFF"), (r"Convertible", "CWB"), (r"Mortgage", "MBB"), (r"Corporate Income|Corporate Opport", "LQD"),
         (r"High Income|High Yield|Credit|Income", "HYG")]
MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"


def funds() -> pd.DataFrame:
    R = []
    for q in QS:
        R += fts_years(q, "N-CSR,N-CSRS,N-2,497", 2016, 2026)
    rows = {}
    for r in sorted(R, key=lambda r: r["date"]):
        tk = [t for t in ticker_of(r["names"][0]) if "-" not in t]
        if not tk:
            continue
        cik = r["ciks"][0]
        t = re.sub(r"\s+", " ", html.unescape(doc(cik, r["adsh"], r["id"].split(":")[1])))
        name = re.sub(r"\s+\(.*", "", r["names"][0]).strip()
        # the sentence must name this fund (shared family reports list many funds)
        for m in re.finditer(rf"terminate on or (?:about|before) ((?:{MONTHS}) \d{{1,2}}, 20\d\d)", t):
            ctx = t[max(0, m.start() - 600):m.start()]
            key = re.sub(r"(?i)\b(fund|trust|inc|the)\b|[^A-Za-z ]", "", name).split()[:3]
            if all(k.lower() in ctx.lower() for k in key) or ("Fund" not in ctx[-300:] and "Trust" not in ctx[-300:]):
                d = dt.datetime.strptime(m.group(1), "%B %d, %Y").date()
                rows.setdefault(tk[0], dict(sym=tk[0], name=name, cik=cik, term=d, src=r["date"]))
                break
    D = pd.DataFrame(rows.values())
    D["bench"] = [next(b for p, b in BENCH if re.search(p, n, re.I)) if any(re.search(p, n, re.I) for p, _ in BENCH) else "HYG" for n in D.name]
    return D


if __name__ == "__main__":
    pd.set_option("display.width", 220)
    F = funds()
    F.to_csv("data/research/events/term_cef_funds.csv", index=False)
    print(F.sort_values("term").to_string())


# Second pass (the shared-report pass above mis-attributed dates): term funds by registered name (EDGAR full index,
# names with "Term Trust/Target Term/<year> Term"), date from FTS restricted to the fund's own CIK.
NAMED = ["1181249", "1181250", "1666735", "1639457", "1647933", "1655544", "1665817", "1687081", "1686142", "1708261",
         "1679033", "1701167", "1682811", "1698508", "1753217", "1701809", "1627854", "1557915", "1564584", "1547994",
         "1479238", "1486298", "1660803", "1704299", "1817518", "1817488", "1730633", "1794287", "1855066", "1836057",
         "1768666", "1785971", "1809541", "1832871", "1864843", "1546429", "1563696", "1528437", "1745059", "879535",
         "1810523", "1703079", "1843305", "1982067"]


def funds_by_cik() -> pd.DataFrame:
    import requests
    from research.sim.tender_fetch import get
    rows = []
    for cik in NAMED:
        hit = None
        for q in ['"terminate on or about"', '"terminate on or before"', '"Termination Date"']:
            j = get(f"https://efts.sec.gov/LATEST/search-index?q={requests.utils.quote(q)}&ciks={int(cik):010d}"
                    f"&forms=N-CSR,N-CSRS,N-2,497") or {}
            for h in j.get("hits", {}).get("hits", [])[:6]:
                s = h["_source"]
                t = re.sub(r"\s+", " ", html.unescape(doc(cik, s["adsh"], h["_id"].split(":")[1])))
                m = re.search(rf"(?:terminate|dissolve|liquidate)[^.]{{0,40}}on or (?:about|before) ((?:{MONTHS}) \d{{1,2}}, 20\d\d)", t) or \
                    re.search(rf"Termination Date[^.]{{0,80}}((?:{MONTHS}) \d{{1,2}}, 20\d\d)", t)
                if m:
                    tk = [x for x in ticker_of(s["display_names"][0]) if "-" not in x]
                    hit = dict(cik=cik, name=re.sub(r"\s+\(.*", "", s["display_names"][0]).strip(), sym=tk[0] if tk else None,
                               term=dt.datetime.strptime(m.group(1), "%B %d, %Y").date(), src=s["file_date"])
                    break
            if hit:
                break
        rows.append(hit or dict(cik=cik))
    D = pd.DataFrame(rows)
    D["bench"] = [next((b for p, b in BENCH if re.search(p, str(n), re.I)), "HYG") for n in D.get("name", [])]
    return D


# Final deal set: dates from the fund's own sentence (funds_by_cik), else the registered fallback (the name's year:
# 1st of the named month, else Dec 1). CBH's parsed 2031 date came from a shared Virtus/Allianz report (AIO's term):
# a data error, so CBH uses its name year. Tickers are a lookup (EDGAR display names / fund sites). Terms 2017-2025 only.
DEALS = [("JMT", "2019-11-30", "MBB"), ("BGB", "2020-05-31", "HYG"), ("BSL", "2020-05-31", "BKLN"), ("BKK", "2020-12-31", "MUB"),
         ("BFO", "2020-12-31", "MUB"), ("FIV", "2022-02-01", "BKLN"), ("JPT", "2022-03-01", "PFF"), ("EFL", "2022-10-31", "BKLN"),
         ("NID", "2023-01-31", "MUB"), ("NIQ", "2023-06-30", "MUB"), ("JPI", "2024-08-31", "PFF"), ("DCF", "2024-12-01", "HYG"),
         ("CBH", "2024-12-01", "CWB"), ("JHD", "2019-12-01", "HYG"), ("JHY", "2020-12-01", "HYG"), ("JHB", "2021-11-01", "HYG"),
         ("NHA", "2021-12-01", "MUB"), ("EHT", "2021-12-01", "HYG"), ("JCO", "2022-12-01", "HYG"), ("JEMD", "2022-12-01", "EMB"),
         ("IHIT", "2023-12-01", "HYG"), ("JHAA", "2023-12-01", "HYG"), ("IHTA", "2024-12-01", "HYG")]


def tr(sym: str, d0, d1) -> float | None:
    """Total return close d0 -> close d1 from raw bars + Alpaca cash dividends with ex in (d0, d1]."""
    from research.sim.etf_closures import dividends
    b = raw_bars([sym])[sym]
    if not len(b):
        return None
    b.index = pd.to_datetime(b.index)
    c0, c1 = b.close.asof(d0), b.close.asof(d1)
    dv = dividends(sym)
    ds = dv[(dv.ex > d0) & (dv.ex <= d1)].rate.sum() if len(dv) else 0.0
    return (c1 + ds) / c0 - 1


def run(sizes=(2300, 10000, 25000)) -> pd.DataFrame:
    out = []
    for sym, term, bench in DEALS:
        b = raw_bars([sym])[sym]
        if len(b) < 260:
            out.append(dict(sym=sym, note="no bars")); continue
        b.index = pd.to_datetime(b.index)
        T = pd.Timestamp(term)
        days = b.index
        iT = days.searchsorted(T, side="right") - 1          # last session on/before the scheduled date
        if iT - 250 < 0:
            out.append(dict(sym=sym, note="< 250 sessions before term")); continue
        d0 = days[iT - 250]
        liquidated = days[-1] <= T + pd.Timedelta(days=60)
        d1 = days[-1] if liquidated and days[-1] <= T + pd.Timedelta(days=30) else days[iT]
        f, m = tr(sym, d0, d1), tr(bench, d0, d1)
        row = dict(sym=sym, term=term, bench=bench, entry_day=d0.date(), exit_day=d1.date(), liquidated=liquidated,
                   fund=f, bench_tr=m, excess=None if f is None or m is None else f - m, last_bar=days[-1].date())
        for s in sizes:
            px = b.close.loc[d0]
            row[f"usd{s}"] = int(0.10 * s // px) * px * (row["excess"] or 0)
        out.append(row)
    return pd.DataFrame(out)


if __name__ == "__main__" and False:
    pass
