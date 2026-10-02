"""Jump hunt R3-7: LLM-extracted contract value vs revenue in small companies' 8-K Item 1.01 filings (prompt 3a:
extraction of FACTS printed in the document, validated verbatim; no judgment, no outcome knowledge needed).

Candidates: EDGAR FTS 8-Ks matching "Item 1.01" with "purchase order" / "supply agreement" / "master services
agreement" / "customer", 2015-2026, ticker via jump_common.resolve, 20-day ADV$ < $20M, first per company in 90 days.
For each, the filing's main document text (<= 8,000 chars from "Item 1.01") goes to OpenCode Go (deepseek-v4-flash,
<= 3,000 calls, cached) with: is this an agreement under which the company SELLS goods/services to a customer?
counterparty (verbatim)? total contract value (verbatim text + USD number, or null)? Kept only if the value text
appears verbatim in the document and the counterparty name does too. Revenue: XBRL frames (Revenues /
RevenueFromContractWithCustomerExcludingAssessedTax, annual CY frames) for the last fiscal year whose 10-K was
surely out (fd before April 1 -> year-2, else year-1). Event: value >= 25% of max(revenue, $1M); fd = 8-K file date.

    PYTHONPATH=. .venv/bin/python -m research.sim.jump_r3_7
"""
from __future__ import annotations

import json
import re

import pandas as pd

from . import event_fetch as F
from .jump_common import ROOT, cik_sym, first_in, resolve, save, small_only
from .tender_fetch import get

C = ROOT / "data/research/jump/r3_7"
MODEL = "deepseek-v4-flash"
PROMPT = ("Below is text from a company's SEC Form 8-K. Extract facts only.\n"
          "Return JSON with keys: sells (true if the agreement is one under which THIS company sells goods or services "
          "to a customer, else false), counterparty (the customer's name exactly as written, or null), value_text "
          "(the exact text of the total contract value or minimum purchase commitment as written, e.g. '$12.5 million', "
          "or null if none is stated), value_usd (that value as a number of US dollars, or null).\n\nTEXT:\n")


def candidates() -> pd.DataFrame:
    from .jump_edgar import _fts
    qs = ['"Item 1.01" "purchase order"', '"Item 1.01" "supply agreement"', '"Item 1.01" "master services agreement"',
          '"Item 1.01" "customer"']
    rows = []
    for q in qs:
        for y in range(2015, 2027):
            for h in F.fts(q, "8-K", f"{y}-01-01", f"{y}-06-30") + F.fts(q, "8-K", f"{y}-07-01", f"{y}-12-31"):
                if h["form"] != "8-K":
                    continue
                for cik, nm in zip(h["ciks"], h["names"]):
                    rows.append(dict(adsh=h["adsh"], doc=h["id"].split(":", 1)[-1], cik=str(int(cik)), name=nm,
                                     fd=pd.Timestamp(h["date"])))
    X = pd.DataFrame(rows).drop_duplicates(["adsh", "cik"])
    X = resolve(X[X.fd >= "2016-01-01"])
    X = small_only(X, 20e6)
    return first_in(X, 90)


def extract(c, r) -> dict | None:
    f = C / f"{r.adsh}.json"
    if f.exists():
        return json.load(open(f))
    t = F.doc(r.cik, r.adsh, r.doc) or ""
    i = t.find("Item 1.01")
    t = t[i: i + 8000] if i >= 0 else t[:8000]
    out = None
    try:
        j = c.chat({"model": MODEL, "messages": [{"role": "user", "content": PROMPT + t}],
                    "response_format": {"type": "json_object"}, "temperature": 0})
        s = j["choices"][0]["message"]["content"]
        out = json.loads(s[s.find("{"): s.rfind("}") + 1])
        vt, cp = out.get("value_text") or "", out.get("counterparty") or ""
        out["valid"] = bool(out.get("sells")) and bool(vt) and vt in t and bool(cp) and cp in t
    except Exception as e:                                     # a failed call is logged and skipped
        out = {"error": repr(e)[:200], "valid": False}
    C.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(f, "w"))
    return out


def revenue() -> pd.DataFrame:
    rows = []
    for y in range(2014, 2026):
        for con in ("Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax"):
            f = ROOT / f"data/research/jump/xbrl/fr_{con}_CY{y}.json"
            if not f.exists():
                f.parent.mkdir(parents=True, exist_ok=True)
                j = get(f"https://data.sec.gov/api/xbrl/frames/us-gaap/{con}/USD/CY{y}.json") or {}
                json.dump(j.get("data", []), open(f, "w"))
            for x in json.load(open(f)):
                rows.append((str(x["cik"]), y, float(x["val"])))
    R = pd.DataFrame(rows, columns=["cik", "year", "rev"])
    return R.groupby(["cik", "year"]).rev.max()


def build(max_calls: int = 3000) -> pd.DataFrame:
    from swingtrader.daily.news_judge import make_client
    c = make_client("opencode-go")
    X = candidates()
    print(len(X), "candidate 8-Ks", flush=True)
    X = X.sample(min(max_calls, len(X)), random_state=0).sort_values("fd")      # a fixed sample across all years
    rev = revenue()
    rows = []
    for r in X.itertuples():
        o = extract(c, r)
        if not o or not o.get("valid") or not o.get("value_usd"):
            continue
        y = r.fd.year - (2 if r.fd.month < 4 else 1)
        rv = rev.get((r.cik, y), 0.0)
        if float(o["value_usd"]) >= 0.25 * max(rv, 1e6):
            rows.append(dict(sym=r.sym, fd=r.fd))
    print(sum(1 for _ in C.glob("*.json")), "LLM calls cached", flush=True)
    return pd.DataFrame(rows, columns=["sym", "fd"])


if __name__ == "__main__":
    save(build(), "r3_7")
