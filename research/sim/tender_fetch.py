"""Round 31: issuer tender offers (SC TO-I) that mention odd lots, via EDGAR full-text search; then every filing
in each offer's file number (original + amendments) with its main documents. Fetch only, resumable.

    PYTHONPATH=. .venv/bin/python -m research.sim.tender_fetch hits|docs
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import time

import requests

from swingtrader.daily.news_judge import sec_headers

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/night/tender"
H = None


def get(url, as_json=True):
    global H
    H = H or sec_headers()
    for k in range(6):
        try:
            r = requests.get(url, headers=H, timeout=40)
            if r.status_code in (429, 503):
                time.sleep(2 * (k + 1)); continue
            r.raise_for_status()
            time.sleep(0.12)                                   # stay under SEC's 10 req/s
            return r.json() if as_json else r.text
        except requests.RequestException:
            time.sleep(2 * (k + 1))
    return None


def hits():
    rows = []
    for q, form in [(q, f) for q in ('"odd lot"', '"odd lots"', '"odd-lot"') for f in ("SC TO-I", "SC TO-I/A")]:
        frm = 0
        while True:
            u = (f"https://efts.sec.gov/LATEST/search-index?q={requests.utils.quote(q)}&forms={requests.utils.quote(form)}"
                 f"&dateRange=custom&startdt=2015-06-01&enddt=2026-09-30&from={frm}")
            j = get(u)
            if not j:
                break
            hh = j["hits"]["hits"]
            for x in hh:
                s = x["_source"]
                rows.append(dict(id=x["_id"], adsh=s["adsh"], form=s["form"], date=s["file_date"],
                                 cik=s["ciks"][0], name=s["display_names"][0], file_num=(s.get("file_num") or [""])[0]))
            frm += len(hh)
            if not hh or frm >= j["hits"]["total"]["value"]:
                break
    rows = list({r["id"]: r for r in rows}.values())
    json.dump(rows, open(OUT / "hits.json", "w"))
    print(len(rows), "hits", len({r["file_num"] for r in rows}), "file numbers")


def docs():
    """For each (cik, file_num) with a ticker in the display name: list the issuer's SC TO-I/TO-I/A filings in that
    file number from the submissions API and download each filing's primary doc + exhibit (a)(1)(A)/(a)(5) texts."""
    rows = json.load(open(OUT / "hits.json"))
    offers = {}
    for r in rows:
        m = re.search(r"\(([A-Z][A-Z0-9.\-, ]{0,20})\)\s+\(CIK", r["name"])
        if not m:
            continue
        offers.setdefault((r["cik"], r["file_num"]), m.group(1))
    print(len(offers), "offers with a ticker", flush=True)
    for i, ((cik, fnum), tick) in enumerate(sorted(offers.items())):
        f = OUT / f"{cik}_{fnum}.json"
        if f.exists():
            continue
        sub = get(f"https://data.sec.gov/submissions/CIK{cik}.json")
        if not sub:
            continue
        recs = []
        blocks = [sub["filings"]["recent"]] + [get("https://data.sec.gov/submissions/" + x["name"]) or {} for x in sub["filings"].get("files", [])]
        for b in blocks:
            for k in range(len(b.get("form", []))):
                if b["form"][k].startswith("SC TO-I") and b.get("fileNumber", [""] * 999)[k] == fnum:
                    recs.append(dict(form=b["form"][k], date=b["filingDate"][k], adsh=b["accessionNumber"][k],
                                     doc=b["primaryDocument"][k]))
        texts = {}
        for rc in recs:
            base = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{rc['adsh'].replace('-', '')}"
            idx = get(base + "/index.json")
            names = [x["name"] for x in (idx or {}).get("directory", {}).get("item", []) if x["name"].lower().endswith((".htm", ".html", ".txt"))]
            pick = [n for n in names if n == rc["doc"] or re.search(r"(ex|exh)[-_]?99|a1a|a1i|a5|dsc|sctoi|ex-?\(?a\)?", n.lower())][:4]
            for n in pick:
                t = get(f"{base}/{n}", as_json=False)
                if t:
                    t = re.sub(r"<[^>]+>", " ", t); t = re.sub(r"&nbsp;|&#160;", " ", t); t = re.sub(r"\s+", " ", t)
                    texts[f"{rc['adsh']}/{n}"] = t[:400000]
        json.dump(dict(cik=cik, file_num=fnum, ticker=tick, name=sub.get("name"), filings=recs, texts=texts), open(f, "w"))
        print(i, tick, len(recs), "filings", len(texts), "docs", flush=True)


if __name__ == "__main__":
    {"hits": hits, "docs": docs}[sys.argv[1]]()
