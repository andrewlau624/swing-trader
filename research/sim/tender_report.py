"""Round 31 #11: odd-lot priority in issuer tender offers -- a report (no N): what a < 100-share holder earned by
buying after the offer started and tendering everything (odd lots are not prorated).

    PYTHONPATH=. .venv/bin/python -m research.sim.tender_report parse|prices|report
"""
from __future__ import annotations

import glob
import json
import pathlib
import re
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIR = ROOT / "data/research/night/tender"
MONEY = r"\$\s?(\d[\d,]*\.\d{2,4})"


def num(x):
    return float(x.replace(",", ""))


def parse_offer(texts, filings):
    orig = [t for k, t in texts.items() if k.split("/")[0] == filings[0]["adsh"]]
    last = [t for k, t in texts.items() if k.split("/")[0] == filings[-1]["adsh"]] if len(filings) > 1 else []
    allt = " ".join(orig)
    rng = re.search(r"not (?:greater|more) than " + MONEY + r"[^$]{0,40}(?:nor|and not|or) less than " + MONEY, allt, re.I) \
        or re.search(r"(?:range|between) (?:of )?" + MONEY + r" (?:and|to) " + MONEY, allt, re.I)
    lo = hi = fixed = np.nan
    if rng:
        a, b = num(rng.group(1)), num(rng.group(2)); lo, hi = min(a, b), max(a, b)
    else:
        m = re.search(r"(?:at a|purchase) price of " + MONEY + r" per [Ss]hare", allt)
        if m:
            fixed = num(m.group(1))
    nav = bool(re.search(r"(?:\d{2}(?:\.\d)?%|percent) of (?:the )?(?:net asset value|NAV)", allt, re.I))
    odd = bool(re.search(r"odd[ -]lot", allt + " ".join(last), re.I))
    final = np.nan; prorate = np.nan
    for t in last:
        for m in re.finditer(r"([^.]{0,200}?)" + MONEY + r"(?: per [Ss]hare)", t):
            ctx = m.group(1).lower()
            if any(w in ctx for w in ("accepted", "purchase", "final", "acquire", "repurchase")) and not any(
                    w in ctx for w in ("not greater", "not less", "range", "minimum", "maximum")):
                final = num(m.group(2)); break
        p = re.search(r"proration factor[^.%]{0,80}?(\d{1,3}(?:\.\d+)?)\s?%", t, re.I)
        if p:
            prorate = float(p.group(1))
        if np.isfinite(final):
            break
    if not np.isfinite(final) and np.isfinite(fixed):
        final = fixed
    return dict(lo=lo, hi=hi, fixed=fixed, nav_based=nav, odd_lot=odd, final=final, proration=prorate)


def parse():
    rows = []
    for f in sorted(glob.glob(str(DIR / "0*.json"))):
        j = json.load(open(f))
        F = sorted(j["filings"], key=lambda x: x["date"])
        # split into offers: each original SC TO-I starts one
        offers, cur = [], []
        for x in F:
            if x["form"] == "SC TO-I" and cur:
                offers.append(cur); cur = []
            cur.append(x)
        if cur:
            offers.append(cur)
        for o in offers:
            if o[0]["form"] != "SC TO-I":
                continue
            ad = {x["adsh"] for x in o}
            tx = {k: v for k, v in j["texts"].items() if k.split("/")[0] in ad}
            r = parse_offer(tx, o)
            r.update(ticker=j["ticker"].split(",")[0].strip(), name=j["name"], start=o[0]["date"], end=o[-1]["date"],
                     n_filings=len(o))
            rows.append(r)
    X = pd.DataFrame(rows)
    X.to_csv(DIR / "offers.csv", index=False)
    print(len(X), "offers;", X.odd_lot.sum(), "mention odd lots;", X.final.notna().sum(), "with a final price;",
          X.nav_based.sum(), "NAV-based")
    print(X.head(20).to_string())


if __name__ == "__main__":
    {"parse": parse}[sys.argv[1]]()
