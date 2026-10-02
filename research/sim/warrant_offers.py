"""Discovery DL2: issuer offers for its own listed warrants (share exchange or cash), registered in round1_prose.md
(amendment "deal rule DL2") before this ran. Terms are parsed from the original SC TO-I documents."""
from __future__ import annotations

import html
import re

import pandas as pd

from research.sim.event_fetch import doc, fts_years, full_index, raw_bars, ticker_of
from research.sim.tender_fetch import get

QS = ['"offer to exchange" "warrants" "consent solicitation"', '"exchange offer" "warrants" "warrant amendment"',
      '"offer to purchase" "warrants" "consent solicitation"', '"offer to purchase" "warrants" "warrant amendment"']


def originals() -> list[dict]:
    R = []
    for q in QS:
        R += fts_years(q, "SC TO-I", 2019, 2026)
    first = {}
    for r in sorted({x["id"]: x for x in R}.values(), key=lambda r: r["date"]):
        if r["form"] == "SC TO-I":
            first.setdefault((r["ciks"][0], r["adsh"]), r)
    return list(first.values())


def texts(cik: str, adsh: str) -> str:
    idx = get(f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{adsh.replace('-', '')}/index.json") or {}
    names = [i["name"] for i in idx.get("directory", {}).get("item", []) if i["name"].endswith((".htm", ".txt"))
             and "index" not in i["name"] and not i["name"].startswith(adsh)]
    return html.unescape(" ".join(doc(cik, adsh, n) for n in names[:6]))


def terms(t: str) -> dict:
    t = re.sub(r"\s+", " ", t)
    r = re.search(r"receive (\d*\.\d+) (?:shares?|of a share)[^.]{0,160}?(?:for|in exchange for) each", t)
    c = re.search(r"\$(\d+\.\d+) in cash[^.]{0,80}?for each", t) or re.search(r"purchase price of \$(\d+\.\d+)[^.]{0,40}? in cash", t)
    s = re.findall(r"under the symbol[s]? [“\"]([A-Z]{1,6}(?:\.WS|\.W|W|WS)(?:\.[A-Z])?)[”\"]", t)
    return dict(r=float(r.group(1)) if r else 0.0, c=float(c.group(1)) if c else 0.0, wsym=s[0] if s else None)


def last_amend(cik: str, d0: str) -> str | None:
    y, q = int(d0[:4]), (int(d0[5:7]) - 1) // 3 + 1
    D = pd.concat([full_index(yy, qq) for yy, qq in [(y, q), (y + (q == 4), q % 4 + 1)] if (yy, qq) <= (2026, 3)])
    A = D[(D.cik == str(int(cik))) & (D.form == "SC TO-I/A") & (D.date >= d0) & (D.date <= str(pd.Timestamp(d0) + pd.Timedelta(days=150))[:10])]
    return A.date.max() if len(A) else None


def build() -> pd.DataFrame:
    rows = []
    for o in originals():
        cik = o["ciks"][0]
        T = terms(texts(cik, o["adsh"]))
        tick = [x for x in ticker_of(o["names"][0]) if not re.search(r"W$|WS$|\.W", x)]
        rows.append(dict(date=o["date"], name=o["names"][0][:40], cik=cik, adsh=o["adsh"], stock=tick[0] if tick else None,
                         L=last_amend(cik, o["date"]), **T))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    D = build()
    pd.set_option("display.width", 250)
    print(D.to_string())
    D.to_csv("data/research/events/warrant_offer_terms.csv", index=False)


# Terms read by hand from each original offer's sentence (2026-10-02, before any price): stock, warrant symbol
# candidates, r shares and c cash per public warrant. Rows that are not offers for listed warrants are excluded:
# A.M. Castle (notes), Voya (fund), Centrus x2 / Hertz / Kimco (preferred), Theravance (notes), Assure (debentures),
# Legacy Acquisition and Pershing Square Tontine (share tenders), FOXO (unlisted private-placement warrants).
# Bioceres offered 0.12 shares OR $0.45: valued at the cash $0.45. Zura: 0.30 is the amendment rate in the sentence
# found (the offer rate may be higher: conservative). Organogenesis: 0.095 offer rate.
HAND = {
    0: ("WTRH", ["WTRHW"], 0.18, 0), 1: ("IMXI", ["IMXIW"], 0.201, 1.12), 2: ("BBCP", ["BBCPW"], 0.2105, 0),
    3: ("MGY", ["MGY.WS"], 0.29, 0), 4: ("LIND", ["LINDW"], 0.385, 0), 5: ("ORGO", ["ORGOW"], 0.095, 0),
    6: ("FPAY", ["FPAYW"], 0.62, 0), 7: ("YTRA", ["YTRAW"], 0.075, 0), 9: ("BIOX", ["BIOX.WS"], 0, 0.45),
    10: ("PACK", ["PACK.WS"], 0.22, 0), 13: ("ATCX", ["ATCXW"], 0.185, 0), 14: ("SFT", ["SFTTW"], 0.25, 1.00),
    17: ("PAYA", ["PAYAW"], 0.26, 0), 19: ("BTRS", ["BTRSW"], 0.30, 0), 21: ("MYPS", ["MYPSW"], 0, 1.00),
    22: ("BBLN", ["BBLNW"], 0.295, 0), 23: ("SEAT", ["SEATW"], 0.24, 0), 24: ("PWP", ["PWPPW"], 0.20, 0),
    26: ("MKTW", ["MKTWW"], 0.1925, 0), 27: ("REE", ["REEAW"], 0.20, 0), 28: ("GBTG", ["GBTG.WS"], 0.275, 0),
    29: ("MOND", ["MONDW"], 0, 0.65), 30: ("SGHC", ["SGHC.WS"], 0.25, 0), 31: ("SPIR", ["SPIR.WS"], 0.20, 0),
    32: ("OPAL", ["OPALW"], 0.25, 0), 35: ("ALTI", ["ALTIW"], 0.25, 0), 36: ("BTMD", ["BTMDW"], 0.23, 0),
    37: ("THCH", ["THCHW"], 0.24, 0), 38: ("GRNT", ["GRNT.WS"], 0.25, 0), 39: ("OTMO", ["OTMOW"], 0.25, 0),
    40: ("IGIC", ["IGICW"], 0, 0.95), 41: ("NRDY", ["NRDY.WS"], 0.25, 0), 42: ("ALLG", ["ALLG.WS"], 0.23, 0),
    43: ("DRCT", ["DRCTW"], 0, 1.20), 44: ("INDI", ["INDIW"], 0.285, 0), 45: ("MRT", ["MRT.WS"], 0, 0.10),
    46: ("TLSI", ["TLSIW"], 0.30, 0), 47: ("HGTY", ["HGTY.WS"], 0.20, 0), 49: ("JTAI", ["JTAIW"], 0.3054, 0),
    50: ("ZURA", ["ZURAW"], 0.30, 0), 51: ("PAYO", ["PAYOW"], 0, 0.78), 52: ("AVPT", ["AVPTW"], 0, 2.50),
    53: ("WEST", ["WESTW"], 0.29, 0), 55: ("NESR", ["NESRW"], 0.10, 0), 56: ("ABL", ["ABLLW"], 0.23, 0),
}


def alts(w: str, stock: str) -> list[str]:
    return list(dict.fromkeys([w, w.replace(".WS", "WS"), w.replace(".WS", ".W"), stock + "W", stock + ".WS", stock + "WS"]))


def run(sizes=(2300, 10000, 25000)) -> pd.DataFrame:
    T = pd.read_csv("data/research/events/warrant_offer_terms.csv", dtype=str)
    out = []
    for i, (stock, ws, r, c) in HAND.items():
        o = T.iloc[i]
        if pd.isna(o.L):
            out.append(dict(i=i, stock=stock, note="no SC TO-I/A")); continue
        sb = raw_bars([stock], tag="raw")[stock]
        sb.index = pd.to_datetime(sb.index)
        wb, wsym = None, None
        for w in [a for x in ws for a in alts(x, stock)]:
            b = raw_bars([w], tag="raw")[w]
            if len(b):
                wb, wsym = b, w; break
        if wb is None or not len(sb):
            out.append(dict(i=i, stock=stock, note="no bars")); continue
        wb.index = pd.to_datetime(wb.index)
        days = sb.index
        L = pd.Timestamp(o.L)
        iL = days.searchsorted(L)
        i0 = max(iL - 5, days.searchsorted(pd.Timestamp(o.date)) + 1)
        e_day = days[i0]
        if e_day not in wb.index:
            out.append(dict(i=i, stock=stock, w=wsym, note="no warrant bar at entry")); continue
        entry = wb.close.loc[e_day]
        x2 = days[min(iL + 2, len(days) - 1)]
        after = wb.index[wb.index > days[min(iL + 10, len(days) - 1)]]
        done = len(after) == 0
        if done:
            val = c + r * sb.close.loc[x2]
        else:
            val = wb.close.asof(x2)
        pre = wb.loc[:e_day].tail(20)
        adv = float((pre.close * pre.volume).median())
        row = dict(i=i, stock=stock, w=wsym, offer=o.date, L=o.L, entry_day=e_day.date(), entry=entry, r=r, c=c,
                   done=done, value=val, ret=val / entry - 1, adv=adv)
        for s in sizes:
            stake = min(0.10 * s, 0.05 * adv)
            row[f"usd{s}"] = int(stake // entry) * (val - entry)
        out.append(row)
    return pd.DataFrame(out)
