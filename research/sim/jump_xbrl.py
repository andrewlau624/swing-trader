"""Jump hunt XBRL ideas: R2-1 first executed buyback, R2-3 net cash above market cap.

Frames (one request per period, every filer) screen candidates; companyfacts (one request per candidate CIK) give each
fact's ORIGINAL filing (`filed`, `form`), so events are dated when the number was first public (frames keep the last
filed value, which can be a later comparative). Tickers via jump_common.resolve; small caps only (ADV$ < $20M).

    PYTHONPATH=. .venv/bin/python -m research.sim.jump_xbrl r2_1|r2_3
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from . import event_fetch as F
from .jump_common import ROOT, first_in, resolve, save, small_only
from .tender_fetch import get

C = ROOT / "data/research/jump/xbrl"
KEEP = {"us-gaap": ["PaymentsForRepurchaseOfCommonStock", "CashAndCashEquivalentsAtCarryingValue", "ShortTermInvestments",
                    "AvailableForSaleSecuritiesDebtSecuritiesCurrent", "Liabilities", "NetIncomeLoss"],
        "dei": ["EntityCommonStockSharesOutstanding"]}


def frame(tax: str, concept: str, unit: str, period: str) -> list[dict]:
    f = C / f"fr_{concept}_{period}.json"
    if not f.exists():
        C.mkdir(parents=True, exist_ok=True)
        j = get(f"https://data.sec.gov/api/xbrl/frames/{tax}/{concept}/{unit}/{period}.json") or {}
        json.dump(j.get("data", []), open(f, "w"))
    return json.load(open(f))


def facts(cik: int) -> dict:
    f = C / f"cf2_{cik}.json"
    if not f.exists():
        j = get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json") or {}
        out = {"name": j.get("entityName", "")}
        for tax, cs in KEEP.items():
            for c in cs:
                u = (((j.get("facts") or {}).get(tax) or {}).get(c) or {}).get("units", {})
                out[c] = u.get("USD") or u.get("shares") or []
        json.dump(out, open(f, "w"))
    return json.load(open(f))


def _df(rows) -> pd.DataFrame:
    X = pd.DataFrame(rows)
    if not len(X):
        return X
    for c in ("start", "end", "filed"):
        if c in X:
            X[c] = pd.to_datetime(X[c])
    return X[X.form.isin(["10-Q", "10-K", "10-Q/A", "10-K/A"])]


# ---- R2-1 first executed buyback -----------------------------------------------------------------------------------
def r2_1() -> pd.DataFrame:
    """First ORIGINAL filing reporting PaymentsForRepurchaseOfCommonStock > 0, for a company with >= 730 days of prior
    XBRL filings (NetIncomeLoss facts) and no positive repurchase fact filed in those 730 days."""
    pos = {}
    for y in range(2013, 2026):
        for x in frame("us-gaap", "PaymentsForRepurchaseOfCommonStock", "USD", f"CY{y}"):
            if x["val"] > 0:
                pos.setdefault(x["cik"], []).append(y)
    cands = [c for c, ys in pos.items() if min(ys) >= 2015 or any(b - a >= 3 for a, b in zip(sorted(ys), sorted(ys)[1:]))]
    print(len(cands), "candidate CIKs", flush=True)
    rows = []
    for cik in cands:
        j = facts(cik)
        R, N = _df(j["PaymentsForRepurchaseOfCommonStock"]), _df(j["NetIncomeLoss"])
        if not len(R) or not len(N):
            continue
        first_filed = N.filed.min()
        P = R[R.val > 0].sort_values("filed")
        for d in P.filed.drop_duplicates():
            prior = P[(P.filed < d) & (P.filed >= d - pd.Timedelta(days=730))]
            if d - first_filed >= pd.Timedelta(days=730) and not len(prior):
                rows.append(dict(cik=cik, name=j["name"], fd=d))
    E = pd.DataFrame(rows)
    E = E[E.fd >= "2016-01-01"]
    return small_only(resolve(E), 20e6)


# ---- R2-3 net cash above market cap --------------------------------------------------------------------------------
def r2_3() -> pd.DataFrame:
    """At each ORIGINAL 10-Q/10-K filing: (cash + short-term investments - total liabilities) > shares outstanding x the
    raw close on the filing date; first time in 365 days. Candidates: companies whose frames ever show cash > liabilities."""
    cands = set()
    for q in pd.period_range("2015Q4", "2026Q2", freq="Q"):
        p = f"CY{q.year}Q{q.quarter}I"
        cash = {x["cik"]: x["val"] for x in frame("us-gaap", "CashAndCashEquivalentsAtCarryingValue", "USD", p)}
        liab = {x["cik"]: x["val"] for x in frame("us-gaap", "Liabilities", "USD", p)}
        cands |= {c for c, v in cash.items() if c in liab and v > liab[c] and v < 5e8}
    print(len(cands), "candidate CIKs", flush=True)
    rows = []
    for cik in sorted(cands):
        j = facts(cik)
        cash, liab, sh = _df(j["CashAndCashEquivalentsAtCarryingValue"]), _df(j["Liabilities"]), _df(j["EntityCommonStockSharesOutstanding"])
        sti = pd.concat([_df(j["ShortTermInvestments"]), _df(j["AvailableForSaleSecuritiesDebtSecuritiesCurrent"])])
        if not len(cash) or not len(liab) or not len(sh):
            continue
        for acc, g in cash.groupby("accn"):
            filed, end = g.filed.iat[0], g.end.max()
            c = g[g.end == end].val.iat[0]
            l = liab[(liab.accn == acc) & (liab.end == end)].val
            s = sh[sh.accn == acc].val
            t = sti[(sti.accn == acc) & (sti.end == end)].val if len(sti) else pd.Series(dtype=float)
            if len(l) and len(s):
                rows.append(dict(cik=cik, name=j["name"], fd=filed, net=c + (t.max() if len(t) else 0) - l.iat[0], shares=s.iat[-1]))
    X = pd.DataFrame(rows)
    X = X[(X.net > 0) & (X.fd >= "2016-01-01")]
    X = resolve(X)
    bars = F.raw_bars(sorted(X.sym.unique()))
    keep = []
    for r in X.itertuples():
        b = bars.get(r.sym)
        if b is None or not len(b):
            keep.append(False); continue
        c = b.close[pd.to_datetime(b.index) <= r.fd]
        keep.append(len(c) > 0 and r.net > r.shares * c.iat[-1])
    E = first_in(X[keep][["sym", "fd"]], 365)
    return small_only(E, 20e6)


if __name__ == "__main__":
    what = sys.argv[1]
    E = globals()[what]()
    save(E, what)
