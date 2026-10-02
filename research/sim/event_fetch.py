"""Round 32 event pipeline: cached, point-in-time EDGAR and Alpaca event data (fetch only, resumable).

- `fts(q, forms, start, end)`: EDGAR full-text search hits (adsh, form, file date, CIKs, display names, doc id).
- `hdr(cik, adsh)`: a filing's SGML header -> acceptance time (ET), subject company / filer CIKs.
- `doc(cik, adsh, name)`: one document of a filing as plain text.
- `full_index(year, qtr)`: EDGAR's quarterly form.idx (every filing: form, company, CIK, date, path).
- `reverse_splits(start, end)`: Alpaca corporate actions (ex-date, old/new rate, symbol).
- `raw_bars(symbols, start, end)`: Alpaca SIP daily bars, adjustment=raw (never adjusted prices), by session date.

Point in time: a filing is public at its acceptance time (`hdr`), not its filing date.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
import re

import pandas as pd
import requests

from .tender_fetch import get

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/events"


def _cache(*parts) -> pathlib.Path:
    p = OUT.joinpath(*parts)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def fts(q: str, forms: str, start: str, end: str) -> list[dict]:
    key = hashlib.md5(f"{q}|{forms}|{start}|{end}".encode()).hexdigest()[:16]
    f = _cache("fts", f"{key}.json")
    if f.exists():
        return json.load(open(f))
    rows, frm = [], 0
    while True:
        u = (f"https://efts.sec.gov/LATEST/search-index?q={requests.utils.quote(q)}&forms={requests.utils.quote(forms)}"
             f"&dateRange=custom&startdt={start}&enddt={end}&from={frm}")
        j = get(u)
        if not j:
            break
        hh = j["hits"]["hits"]
        for x in hh:
            s = x["_source"]
            rows.append(dict(id=x["_id"], adsh=s["adsh"], form=s["form"], date=s["file_date"], ciks=s["ciks"],
                             names=s["display_names"], file_num=(s.get("file_num") or [""])[0]))
        frm += len(hh)
        if not hh or frm >= j["hits"]["total"]["value"] or frm >= 9900:
            break
    json.dump(rows, open(f, "w"))
    return rows


def fts_years(q: str, forms: str, y0: int = 2016, y1: int = 2026) -> list[dict]:
    """Year by year (full-text search returns at most ~10k hits per query)."""
    out = []
    for y in range(y0, y1 + 1):
        out += fts(q, forms, f"{y}-01-01", f"{y}-12-31")
    return list({r["id"]: r for r in out}.values())


def ticker_of(name: str) -> list[str]:
    """Tickers in an FTS display name, e.g. 'Acme Corp  (ACME, ACMEW)  (CIK 0000123)'."""
    m = re.search(r"\(([A-Z][A-Z0-9.\-, ]{0,30})\)\s+\(CIK", name)
    return [t.strip() for t in m.group(1).split(",")] if m else []


def hdr(cik: str | int, adsh: str) -> dict:
    f = _cache("hdr", f"{adsh}.json")
    if f.exists():
        return json.load(open(f))
    t = get(f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{adsh.replace('-', '')}/{adsh}.hdr.sgml", as_json=False) or ""
    acc = re.search(r"<ACCEPTANCE-DATETIME>(\d{14})", t)
    subj = re.search(r"<SUBJECT-COMPANY>.*?<CIK>(\d+)", t, re.S)
    filer = re.findall(r"<FILER>.*?<CIK>(\d+)", t, re.S)
    r = dict(accepted=acc.group(1) if acc else None, subject=subj.group(1).lstrip("0") if subj else None,
             filers=[x.lstrip("0") for x in filer], form=(re.search(r"<TYPE>([^\n<]+)", t) or [None, None])[1])
    if t:
        json.dump(r, open(f, "w"))
    return r


def accepted_et(h: dict) -> pd.Timestamp | None:
    """EDGAR acceptance stamps are Eastern time."""
    return pd.Timestamp(dt.datetime.strptime(h["accepted"], "%Y%m%d%H%M%S")) if h.get("accepted") else None


def doc(cik: str | int, adsh: str, name: str) -> str:
    f = _cache("doc", adsh, f"{name}.txt")
    if f.exists():
        return f.read_text()
    t = get(f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{adsh.replace('-', '')}/{name}", as_json=False)
    if t is None:
        return ""
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"&nbsp;|&#160;|&#xa0;", " ", t)
    t = re.sub(r"&amp;", "&", t)
    t = re.sub(r"&#8217;|&rsquo;", "'", t)
    t = re.sub(r"\s+", " ", t)[:600000]
    f.write_text(t)
    return t


def full_index(year: int, qtr: int) -> pd.DataFrame:
    f = _cache("index", f"form_{year}Q{qtr}.parquet")
    if f.exists():
        return pd.read_parquet(f)
    t = get(f"https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{qtr}/form.idx", as_json=False) or ""
    rows = []
    for line in t.splitlines():
        m = re.match(r"^(.{12,}?)\s{2,}(.+?)\s{2,}(\d+)\s+(\d{4}-\d{2}-\d{2})\s+(edgar/\S+)", line)
        if m:
            rows.append(dict(form=m.group(1).strip(), company=m.group(2).strip(), cik=m.group(3), date=m.group(4),
                             path=m.group(5)))
    D = pd.DataFrame(rows)
    if len(D):
        D.to_parquet(f)
    return D


def company_tickers() -> dict[str, list[str]]:
    """CIK -> current tickers (EDGAR company_tickers.json)."""
    f = _cache("company_tickers.json")
    if not f.exists():
        json.dump(get("https://www.sec.gov/files/company_tickers.json"), open(f, "w"))
    out: dict[str, list[str]] = {}
    for v in json.load(open(f)).values():
        out.setdefault(str(v["cik_str"]), []).append(v["ticker"].upper().replace("-", "."))
    return out


def reverse_splits(start: str = "2016-01-01", end: str = "2026-09-30") -> pd.DataFrame:
    f = _cache("alpaca_reverse_splits.parquet")
    if f.exists():
        return pd.read_parquet(f)
    from alpaca.data.enums import CorporateActionsType
    from alpaca.data.historical.corporate_actions import CorporateActionsClient
    from alpaca.data.requests import CorporateActionsRequest
    from swingtrader.daily.marketdata import _clients
    d, _ = _clients()
    c = CorporateActionsClient(d._api_key, d._secret_key)
    rows = []
    for y in range(int(start[:4]), int(end[:4]) + 1):
        r = c.get_corporate_actions(CorporateActionsRequest(types=[CorporateActionsType.REVERSE_SPLIT],
                                                            start=dt.date(y, 1, 1), end=dt.date(y, 12, 31), limit=None))
        for x in r.data.get("reverse_splits", []):
            x = dict(x) if not isinstance(x, dict) else x
            rows.append(dict(symbol=x["symbol"], ex=pd.Timestamp(x["ex_date"]), old=float(x["old_rate"]),
                             new=float(x["new_rate"]), old_cusip=x.get("old_cusip"), new_cusip=x.get("new_cusip")))
    D = pd.DataFrame(rows).drop_duplicates(["symbol", "ex"])
    D.to_parquet(f)
    return D


def raw_bars(symbols: list[str], start: str = "2015-10-01", end: str = "2026-09-30", tag: str = "raw") -> dict[str, pd.DataFrame]:
    """Alpaca SIP daily raw bars, cached one parquet per symbol (whole window; label = ET session date)."""
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from swingtrader.daily.marketdata import _clients, trade_date
    data, _ = _clients()
    out, need = {}, []
    for s in sorted(set(symbols)):
        f = _cache("bars", tag, f"{s.replace('/', '_')}.parquet")
        if f.exists():
            out[s] = pd.read_parquet(f)
        else:
            need.append(s)
    for i in range(0, len(need), 50):
        chunk = need[i:i + 50]
        try:
            df = data.get_stock_bars(StockBarsRequest(symbol_or_symbols=chunk, timeframe=TimeFrame.Day,
                                                      start=pd.Timestamp(start, tz="UTC"), end=pd.Timestamp(end, tz="UTC"),
                                                      feed="sip", adjustment="raw")).df
        except Exception:
            df = None
        got = {}
        if df is not None and len(df):
            df = df.reset_index()
            df["date"] = trade_date(df["timestamp"])
            got = {s: g.set_index("date")[["open", "high", "low", "close", "volume"]] for s, g in df.groupby("symbol")}
        for s in chunk:
            g = got.get(s, pd.DataFrame(columns=["open", "high", "low", "close", "volume"]))
            g.to_parquet(_cache("bars", tag, f"{s.replace('/', '_')}.parquet"))
            out[s] = g
        print(f"  bars {i + len(chunk)}/{len(need)}", flush=True)
    return out
