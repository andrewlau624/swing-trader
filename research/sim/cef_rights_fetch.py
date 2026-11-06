"""CEF-RIGHTS event list builder (N 1084): seasoned-CEF rights offerings from EDGAR (www.sec.gov / data.sec.gov only).

efts.sec.gov full-text search returns 403 from this host, so the list is built per fund:
  1. every SFP 'CEF' in Sharadar tickers (delisted included) -> CIK from `secfilings`;
  2. data.sec.gov submissions JSON per CIK (+ older pages) -> final prospectuses (497 / 424B*) filed >= 365 days
     after the fund's first price (seasoned fund, so not an IPO prospectus);
  3. the first 120k chars of each candidate document; a document is a rights offering when it says
     "rights offering" or "subscription rights" AND "subscription price"; the expiration date is parsed from
     "expire ... on <Month D, YYYY>" (first match on the cover).

    python3 research/sim/cef_rights_fetch.py      # -> data/research/cef_rights/events.csv
Downloaded files live in data/research/cef_rights/raw/ (untrusted; parsed as text only).
"""
from __future__ import annotations

import json
import pathlib
import re
import time
import urllib.request

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
RAW = ROOT / "data/research/cef_rights/raw"
OUT = ROOT / "data/research/cef_rights/events.csv"
UA = {"User-Agent": "swing-trader research research@example.com"}
FORMS = {"497", "424B3", "424B2", "424B5", "424B4", "424B1"}
MONTH = r"(January|February|March|April|May|June|July|August|September|October|November|December)"
EXP = re.compile(r"expir\w*[^.]{0,300}?" + MONTH + r"\s+(\d{1,2}),\s*(\d{4})", re.I | re.S)


DATE = re.compile(MONTH + r"\s+(\d{1,2}),\s*(\d{4})")


def expiry(s: str, filed: pd.Timestamp) -> pd.Timestamp:
    """Earliest date within 200 chars before / 300 after any 'expir' that falls in [filed, filed+120d] (prospectuses also cite
    past offerings' expiries, so the first match is not enough)."""
    best = pd.NaT
    for m in re.finditer(r"expir", s, re.I):
        for d in DATE.finditer(s[max(0, m.start() - 200):m.end() + 300]):
            x = pd.to_datetime(f"{d.group(1)} {d.group(2)} {d.group(3)}", errors="coerce")
            if pd.notna(x) and filed <= x <= filed + pd.Timedelta(days=120) and (pd.isna(best) or x < best):
                best = x
    return best


def get(url: str, path: pathlib.Path, limit: int | None = None) -> bytes:
    if path.exists():
        return path.read_bytes()
    for k in range(4):
        try:
            time.sleep(0.12)
            b = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40).read()
            b = b[:limit] if limit else b
            path.write_bytes(b)
            return b
        except Exception as e:  # noqa: BLE001
            if "404" in str(e):
                path.write_bytes(b"")
                return b""
            time.sleep(2 * (k + 1))
    return b""


def cefs() -> pd.DataFrame:
    t = pd.read_parquet(pathlib.Path.home() / "data/sharadar/tickers.parquet")
    c = t[(t["table"] == "SFP") & (t["category"] == "CEF")].copy()
    c["cik"] = c["secfilings"].str.extract(r"CIK=(\d+)")[0].astype(float)
    return c.dropna(subset=["cik"])[["ticker", "name", "cik", "firstpricedate", "lastpricedate"]]


def filings(cik: int) -> pd.DataFrame:
    p = RAW / f"sub_{cik}.json"
    b = get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", p)
    if not b:
        return pd.DataFrame()
    j = json.loads(b)
    parts = [pd.DataFrame(j["filings"]["recent"])]
    for f in j["filings"].get("files", []):
        bb = get(f"https://data.sec.gov/submissions/{f['name']}", RAW / f["name"])
        if bb:
            parts.append(pd.DataFrame(json.loads(bb)))
    d = pd.concat(parts, ignore_index=True)
    return d[["accessionNumber", "filingDate", "form", "primaryDocument"]]


def text(cik: int, acc: str, doc: str) -> str:
    a = acc.replace("-", "")
    url = (f"https://www.sec.gov/Archives/edgar/data/{cik}/{a}/{doc}" if doc
           else f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}.txt")
    return clean(get(url, RAW / f"doc_{cik}_{a}.bin", limit=120_000))


def clean(b: bytes) -> str:
    """Prospectus bytes -> one-line plain text (tags and nbsp stripped)."""
    s = b.decode("latin-1", "ignore")
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"&nbsp;|&#160;|&#xa0;", " ", s, flags=re.I)
    return re.sub(r"\s+", " ", s)


def classify(s: str, filed: pd.Timestamp) -> dict | None:
    """None unless the document is a rights offering; else its expiry (NaT if unparsed), transferable, preferred.
    Shared with the forward shadow swingtrader/daily/cef_rights_shadow.py (CEF-RIGHTS-FWD)."""
    lo = s.lower()
    if not (("rights offering" in lo or "subscription rights" in lo) and "subscription price" in lo):
        return None
    return dict(expiry=expiry(s, pd.Timestamp(filed)),
                transferable=("non-transferable" not in lo[:40_000] and "nontransferable" not in lo[:40_000]),
                preferred=("preferred" in lo[:3000]))


def one(cik: int, g: pd.DataFrame) -> list[dict]:
    f = filings(cik)
    if f.empty:
        return []
    first = pd.to_datetime(g["firstpricedate"]).min()
    f = f[f["form"].isin(FORMS) & (pd.to_datetime(f["filingDate"]) >= first + pd.Timedelta(days=365))]
    rows = []
    for acc, fd, form, doc in f.itertuples(index=False):
        c = classify(text(cik, acc, doc), pd.Timestamp(fd))
        if c is None:
            continue
        rows.append(dict(cik=cik, tickers="|".join(sorted(g["ticker"])), filed=fd, form=form, acc=acc, **c))
    return rows


def main() -> int:
    from concurrent.futures import ThreadPoolExecutor
    c = cefs()
    groups = [(int(k), g) for k, g in c.groupby("cik")]
    rows = []
    with ThreadPoolExecutor(3) as ex:   # 3 workers x ~0.12s sleep + latency: under SEC's 10 req/s
        for n, r in enumerate(ex.map(lambda a: one(*a), groups), 1):
            rows += r
            if n % 50 == 0:
                print(n, len(rows), flush=True)
    ev = pd.DataFrame(rows)
    ev.to_csv(OUT, index=False)
    print("candidates", len(ev), "with expiry", ev["expiry"].notna().sum())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
