"""Study TAC runner (pre-reg research/drafts/study_tac_treasury.md).

Treasury note/bond auction concession: does TLT/IEF dip into the auction and recover after?

Run: PYTHONPATH=. .venv/bin/python -m research.sim.tac_treasury
"""
from __future__ import annotations

import json
import pathlib
import urllib.request

import numpy as np
import pandas as pd

from . import data as D

ROOT = pathlib.Path(__file__).resolve().parents[2]
CACHE = ROOT / "data/research/program/tac_auctions.parquet"
OUT = ROOT / "data/research/program/tac_treasury_out.txt"
API = ("https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/"
       "auctions_query?filter=security_type:in:(Note,Bond)&sort=auction_date"
       "&fields=auction_date,issue_date,security_type,security_term,high_yield,bid_to_cover_ratio,"
       "offering_amt,primary_dealer_accepted,indirect_bidder_accepted,direct_bidder_accepted,total_accepted"
       "&page[size]=10000")


def auctions() -> pd.DataFrame:
    if CACHE.exists():
        return pd.read_parquet(CACHE)
    import urllib.parse
    allrows, page = [], 1
    url = API if "?" in API else API
    while True:
        u = f"{url}&page[number]={page}"
        with urllib.request.urlopen(u, timeout=60) as r:
            j = json.load(r)
        allrows += j["data"]
        if page >= j["meta"]["total-pages"]:
            break
        page += 1
    a = pd.DataFrame(allrows)
    for c in ["high_yield", "bid_to_cover_ratio", "offering_amt", "primary_dealer_accepted",
              "indirect_bidder_accepted", "direct_bidder_accepted", "total_accepted"]:
        a[c] = pd.to_numeric(a[c], errors="coerce")
    a["auction_date"] = pd.to_datetime(a["auction_date"])
    a = a.dropna(subset=["high_yield", "auction_date"])
    a.to_parquet(CACHE)
    return a


def term_years(s):
    if not isinstance(s, str):
        return np.nan
    import re
    m = re.findall(r"(\d+)", s)
    if not m:
        return np.nan
    return int(m[0])


def main():
    a = auctions()
    a["yrs"] = a["security_term"].map(term_years)
    a = a[(a.yrs >= 2)].copy()
    P = D.etf()
    C = P["close"]
    days = C.index
    b = 1e4

    def td(d):  # first trading day >= d
        j = days.searchsorted(pd.Timestamp(d))
        return j if j < len(days) else None

    def ret(sym, i, j):  # close-to-close
        if i is None or j is None or j <= i:
            return np.nan
        p = C[sym]
        return p.iloc[j] / p.iloc[i] - 1 if np.isfinite(p.iloc[i]) and np.isfinite(p.iloc[j]) else np.nan

    recs = []
    spy = C["SPY"]
    for _, r in a.iterrows():
        d = r["auction_date"]
        etf = "TLT" if r.yrs >= 10 else "IEF"
        ia = td(d)
        if ia is None or ia < 5 or ia + 4 >= len(days):
            continue
        pre = ret(etf, ia - 3, ia) - ret("SPY", ia - 3, ia)         # concession
        post = ret(etf, ia, ia + 3) - ret("SPY", ia, ia + 3)        # reversal
        exe = ret(etf, ia + 1, ia + 3)                              # exec: buy open-ish d+1
        recs.append(dict(date=d, etf=etf, yrs=r.yrs, btc=r.bid_to_cover_ratio,
                         size=r.offering_amt, pre=pre, post=post, exe=exe))
    R = pd.DataFrame(recs).dropna(subset=["pre", "post"])
    R = R[(R.date >= "2016-01-01")]
    lines = ["Study TAC: Treasury note/bond auction concession (TLT/IEF vs SPY, 2016-2026)",
             f"auctions={len(R)}  TLT={ (R.etf=='TLT').sum() }  IEF={ (R.etf=='IEF').sum() }", ""]

    def blk(x, lab):
        x = x.dropna()
        if len(x) < 10:
            lines.append(f"{lab:34s} n={len(x)}"); return
        t = x.mean() / x.std() * np.sqrt(len(x))
        lines.append(f"{lab:34s} n={len(x):4d} mean={x.mean()*b:6.1f}bp med={x.median()*b:6.1f} "
                     f"t={t:5.2f} hit={(x>0).mean()*100:3.0f}% ex5={x.sort_values().iloc[:-5].mean()*b:6.1f}")

    for lab, col in [("concession A-3 -> A", "pre"), ("reversal A -> A+3", "post"),
                     ("executable A+1 -> A+3", "exe")]:
        blk(R[col], lab)
    lines.append("")
    for etf, g in R.groupby("etf"):
        for lab, col in [("concession", "pre"), ("reversal", "post")]:
            blk(g[col], f"{etf} {lab}")
    lines.append("")
    lines.append("by bid-to-cover tercile (reversal):")
    try:
        R["btcq"] = pd.qcut(R.btc, 3, labels=["low", "mid", "high"])
        for q, g in R.groupby("btcq", observed=True):
            blk(g["post"], f"  btc {q}")
    except ValueError as exc:          # pd.qcut: too few rows or duplicate bin edges
        lines.append(f"  tercile split skipped: {exc}")
    lines.append("")
    lines.append("by year (reversal):")
    for y, g in R.groupby(R.date.dt.year):
        if len(g) >= 10:
            blk(g["post"], f"  {y}")
    text = "\n".join(lines) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
