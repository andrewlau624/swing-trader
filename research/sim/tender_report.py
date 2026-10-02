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


BAD = ("par value", "dividend", "deemed", "nominal", "exercise price", "conversion price", "warrant")
FINAL = [r"(?:at|for) a (?:final |clearing )?(?:purchase |cash )?price of " + MONEY + r",? (?:per|a) (?:[Ss]hare|[Uu]nit)",
         r"(?:final |clearing )?purchase price (?:of|was|is|equal to) " + MONEY,
         r"(?:accepted|purchased|acquired|taken up)[^.]{0,120}?(?:at|for) " + MONEY + r" per (?:[Ss]hare|[Uu]nit)"]


def _prices(t, pats):
    out = []
    for pat in pats:
        for m in re.finditer(pat, t):
            ctx = t[max(0, m.start() - 160):m.end()].lower()
            if not any(w in ctx for w in BAD):
                out.append(num(m.group(m.lastindex)))
    return out


def parse_offer(texts, filings):
    first = filings[0]["adsh"]; lastk = filings[-1]["adsh"]
    orig = " ".join(t for k, t in texts.items() if k.split("/")[0] == first)
    amend = [(k.split("/")[0], t) for k, t in texts.items() if k.split("/")[0] != first]
    rng = re.search(r"not (?:greater|more) than " + MONEY + r"[^$]{0,40}(?:nor|and not|or|and) (?:less|lower) than " + MONEY, orig, re.I) \
        or re.search(r"price (?:range )?(?:of )?(?:between|from) " + MONEY + r" (?:and|to) " + MONEY, orig, re.I)
    lo = hi = fixed = np.nan
    if rng:
        a, b = num(rng.group(1)), num(rng.group(2)); lo, hi = min(a, b), max(a, b)
    else:
        c = _prices(orig, FINAL[:2])
        fixed = c[0] if c else np.nan
    kind = ("exchange" if re.search(r"exchange offer|offer to exchange|split-off", orig, re.I) and not np.isfinite(fixed) and not rng
            else "nav" if re.search(r"(?:\d{2}(?:\.\d+)?%|percent) of (?:the )?(?:\w+ )?(?:net asset value|NAV)", orig, re.I)
            else "dutch" if rng else "fixed" if np.isfinite(fixed) else "unknown")
    odd = bool(re.search(r"odd[ -]lot", orig + " ".join(t for _, t in amend), re.I))
    # final price: latest amendment first
    final = np.nan
    order = sorted({a for a, _ in amend}, key=lambda a: [f["adsh"] for f in filings].index(a) if a in [f["adsh"] for f in filings] else -1, reverse=True)
    for a in order:
        c = _prices(" ".join(t for k, t in amend if k == a), FINAL)
        if np.isfinite(lo):
            c = [x for x in c if lo * 0.999 <= x <= hi * 1.001]
        if c:
            final = c[0]; break
    if not np.isfinite(final) and np.isfinite(fixed):
        final = fixed
    pr = re.findall(r"proration factor[^.%]{0,80}?(\d{1,3}(?:\.\d+)?)\s?%", " ".join(t for _, t in amend), re.I)
    return dict(kind=kind, lo=lo, hi=hi, fixed=fixed, odd_lot=odd, final=final, proration=float(pr[-1]) if pr else np.nan)


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
    print(len(X), "offers;", X.odd_lot.sum(), "mention odd lots;", X.final.notna().sum(), "with a final price")




def snippets(out_dir):
    """Per offer, the few sentences that state its terms and result (for hand/agent extraction into terms.csv)."""
    out_dir = pathlib.Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    sent = lambda t: re.split(r"(?<=[.;])\s+", t)
    blocks = []
    for f in sorted(glob.glob(str(DIR / "0*.json"))):
        j = json.load(open(f))
        F = sorted(j["filings"], key=lambda x: x["date"])
        offers, cur = [], []
        for x in F:
            if x["form"] == "SC TO-I" and cur:
                offers.append(cur); cur = []
            cur.append(x)
        if cur:
            offers.append(cur)
        for o in offers:
            if o[0]["form"] != "SC TO-I" or o[0]["date"] < "2016-01-01":
                continue
            oid = f"{j['ticker'].split(',')[0].strip()}_{o[0]['date']}"
            first = o[0]["adsh"]; later = [x["adsh"] for x in o[1:]][::-1]
            orig = " ".join(t for k, t in j["texts"].items() if k.split("/")[0] == first)
            amend = " ".join(t for a in later for k, t in j["texts"].items() if k.split("/")[0] == a)
            pick = lambda t, pat, n, cap: [s_[:cap] for s_ in sent(t) if re.search(pat, s_, re.I)][:n]
            terms = pick(orig, r"\$\s?\d.*per (share|unit)|net asset value|not (greater|more) than \$|for each \$|exchange ratio|odd[ -]lot", 6, 400)
            res = pick(amend, r"(accepted|purchased|taken up|final|exchange ratio|proration).*\$\s?\d|proration factor|\$\s?\d.*(accepted|purchased)", 5, 400)
            blocks.append(f"### {oid} | {j['name']} | start {o[0]['date']} | last filing {o[-1]['date']} | {len(o)} filings\n"
                          + "TERMS: " + " || ".join(terms) + "\nRESULT: " + " || ".join(res) + "\n")
    k = 4
    for i in range(k):
        (out_dir / f"offers_{i}.txt").write_text("\n".join(blocks[i::k]))
    print(len(blocks), "offers ->", out_dir)


if __name__ == "__main__":
    {"parse": parse, "snippets": lambda: snippets(sys.argv[2])}[sys.argv[1]]()


def report(terms_dir):
    """Odd-lot economics per offer from the extracted terms (terms_*.csv) and raw daily prices.
    Entry A: the close of the first session after the offer starts. Entry B: the close 5 sessions before the last
    filing (a few sessions before expiry; Dutch prices are better known). Cash arrives ~2 sessions after the last
    filing. Financing charge 12%/yr on the capital for the hold (the book's margin rate; conservative)."""
    T = pd.concat([pd.read_csv(f, dtype=str) for f in sorted(glob.glob(str(pathlib.Path(terms_dir) / "terms_*.csv")))])
    for c in ("lo", "hi", "fixed", "final", "nav_pct", "discount_pct", "proration_pct"):
        T[c] = pd.to_numeric(T[c], errors="coerce")
    T["ticker"] = T.oid.str.rsplit("_", n=1).str[0].str.replace("-", ".")
    T["start"] = pd.to_datetime(T.oid.str.rsplit("_", n=1).str[1])
    # last filing date from the offers' own filing lists
    last = {}
    for f in glob.glob(str(DIR / "0*.json")):
        j = json.load(open(f)); F = sorted(j["filings"], key=lambda x: x["date"]); cur = []
        for x in F + [dict(form="SC TO-I", date="9999")]:
            if x["form"] == "SC TO-I" and cur:
                last[f"{j['ticker'].split(',')[0].strip()}_{cur[0]['date']}"] = cur[-1]["date"]; cur = []
            cur.append(x)
    T["end"] = pd.to_datetime(T.oid.map(last))
    R = pd.concat([pd.read_parquet(f) for f in glob.glob(str(DIR / "raw/raw*.parquet"))])
    R["d"] = R.timestamp.dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
    C = R.pivot_table(index="d", columns="symbol", values="close")
    cal = C.index
    rows = []
    for r in T.itertuples():
        if r.kind not in ("cash_fixed", "cash_dutch", "nav") or str(r.withdrawn).upper() == "Y" or not np.isfinite(r.final) \
                or str(r.odd_lot).upper() == "N" or r.ticker not in C.columns or pd.isna(r.end):
            continue
        i0 = cal.searchsorted(r.start + pd.Timedelta(days=1)); ie = cal.searchsorted(r.end)
        if i0 >= len(cal) or ie + 2 >= len(cal) or ie <= i0:
            continue
        ib = max(i0, ie - 5); ip = ie + 2
        for lab, i in (("A", i0), ("B", ib)):
            px = C.iat[i, C.columns.get_loc(r.ticker)]
            if not np.isfinite(px) or px <= 0:
                continue
            days = (cal[ip] - cal[i]).days
            g = r.final / px - 1
            rows.append(dict(oid=r.oid, kind=r.kind, entry=lab, date=cal[i], px=px, final=r.final, gain=g, days=days,
                             net=g - 0.12 * days / 365, odd=r.odd_lot, prorate=r.proration_pct))
    X = pd.DataFrame(rows)
    X.to_csv(DIR / "oddlot_trades.csv", index=False)
    return T, X
