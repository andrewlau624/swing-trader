"""CEF-TXT (N 888-889) fetch: N-CSR / N-CSRS shareholder reports for every CEF-RV fund, from EDGAR.

    PYTHONPATH=. .venv/bin/python -m research.sim.cef_txt_fetch

Writes data/research/cef_txt/filings.parquet (ticker, cik, form, accession, accepted, url) and one gzip text per
accession (HTML stripped, first 60,000 characters) under data/research/cef_txt/text/. Resumable; ~8 req/s.
"""
from __future__ import annotations

import gzip
import html
import json
import pathlib
import re
import time

import pandas as pd
import requests

from swingtrader.daily.news_judge import sec_headers

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/cef_txt"
TXT = OUT / "text"
FORMS = {"N-CSR", "N-CSRS", "N-CSR/A", "N-CSRS/A"}
KEEP = 60_000
RAW_CAP = 1_500_000   # bytes of HTML read per document (the letter is at the front)

_last = [0.0]


def get(url: str, stream: bool = False):
    for k in range(5):
        dt = time.time() - _last[0]
        if dt < 0.125:
            time.sleep(0.125 - dt)
        _last[0] = time.time()
        try:
            r = requests.get(url, headers=sec_headers(), timeout=30, stream=stream)
        except requests.RequestException:
            time.sleep(2 * (k + 1))
            continue
        if r.status_code == 200:
            return r
        if r.status_code in (429, 503):
            time.sleep(5 * (k + 1))
            continue
        return None
    return None


def strip(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>|</h\d>", "\n", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    raw = re.sub(r"[ \t\xa0]+", " ", raw)
    return re.sub(r"\n\s*\n+", "\n", raw).strip()


def cik_map() -> dict[str, int]:
    j = get("https://www.sec.gov/files/company_tickers.json").json()
    mp = {v["ticker"].upper(): int(v["cik_str"]) for v in j.values()}
    try:   # Sharadar SFP tickers carry an EDGAR link with the CIK for funds missing from the SEC file
        from sharadar import tickers
        t = tickers()
        t = t[t["secfilings"].notna()] if "secfilings" in t else t.iloc[0:0]
        for tk, link in zip(t["ticker"], t["secfilings"]):
            m = re.search(r"CIK=(\d+)", str(link))
            if m and tk.upper() not in mp:
                mp[tk.upper()] = int(m.group(1))
    except Exception as e:   # noqa: BLE001
        print("sharadar cik fallback unavailable:", e)
    return mp


def filings(cik: int) -> list[dict]:
    sub = get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
    if sub is None:
        return []
    sub = sub.json()
    blocks = [sub["filings"]["recent"]]
    for f in sub["filings"].get("files", []):
        r = get(f"https://data.sec.gov/submissions/{f['name']}")
        if r is not None:
            blocks.append(r.json())
    out = []
    for b in blocks:
        for i, form in enumerate(b.get("form", [])):
            if form in FORMS and b["filingDate"][i] >= "2014-01-01":
                acc = b["accessionNumber"][i]
                out.append(dict(cik=cik, form=form, accession=acc, accepted=b["acceptanceDateTime"][i],
                                url=f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/"
                                    f"{b['primaryDocument'][i]}"))
    return out


def main() -> int:
    TXT.mkdir(parents=True, exist_ok=True)
    tr = pd.read_csv(ROOT / "data/research/cefconnect/cef_rv_trades.csv")
    syms = sorted(tr.loc[tr["edate"] >= "2016", "ticker"].unique())
    mp = cik_map()
    miss = [s for s in syms if s.upper() not in mp]
    print(f"funds {len(syms)}; no CIK {len(miss)}: {miss[:30]}", flush=True)
    fp = OUT / "filings.parquet"
    rows = pd.read_parquet(fp).to_dict("records") if fp.exists() else []
    done = {r["ticker"] for r in rows}
    for k, s in enumerate(syms):
        if s in done or s.upper() not in mp:
            continue
        for f in filings(mp[s.upper()]):
            rows.append(dict(ticker=s, **f))
        if k % 20 == 0:
            pd.DataFrame(rows).to_parquet(fp)
            print("index", k, len(syms), len(rows), flush=True)
    fl = pd.DataFrame(rows)
    fl.to_parquet(fp)
    accs = fl.drop_duplicates("accession")
    print("filings", len(fl), "unique docs", len(accs), flush=True)
    bad = 0
    for k, (acc, url) in enumerate(zip(accs["accession"], accs["url"])):
        p = TXT / f"{acc}.txt.gz"
        if p.exists():
            continue
        r = get(url, stream=True)
        if r is None:
            bad += 1
            continue
        raw = b""
        for chunk in r.iter_content(65536):
            raw += chunk
            if len(raw) >= RAW_CAP:
                break
        r.close()
        txt = strip(raw.decode("utf-8", "ignore"))[:KEEP]
        with gzip.open(p, "wt") as g:
            g.write(txt)
        if k % 200 == 0:
            print("doc", k, len(accs), "bad", bad, flush=True)
    print("DONE bad", bad, json.dumps({"docs": len(accs)}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
