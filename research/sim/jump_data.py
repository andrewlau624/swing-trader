"""Jump hunt raw data (fetch only, resumable): the Alpaca/Benzinga news archive and Reddit posts (Arctic Shift).

- `news`: every Alpaca news item (id, created_at UTC, headline, summary, symbols, source), one parquet per month
  under data/research/jump/news/YYYY-MM.parquet. Public at `created_at`.
- `reddit SUB`: every post in a subreddit (id, created_utc, title, score, num_comments, flair), one parquet per month
  under data/research/jump/reddit/SUB/YYYY-MM.parquet. Arctic Shift archives posts as first seen; `score` and
  `num_comments` are as archived (often later than the post), so only `created_utc` and `title` are point in time.

    PYTHONPATH=. .venv/bin/python -m research.sim.jump_data news 2016-01 2026-09
    PYTHONPATH=. .venv/bin/python -m research.sim.jump_data reddit pennystocks 2016-01 2026-09
"""
from __future__ import annotations

import argparse
import pathlib
import time

import pandas as pd
import requests

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/jump"
UA = {"User-Agent": "swing-trader personal research (jump hunt; polite, one request at a time)"}


def _months(a: str, b: str) -> list[pd.Period]:
    return list(pd.period_range(a, b, freq="M"))


def _get(url, params, headers, tries=6):
    for k in range(tries):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=60)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(3 * (k + 1)); continue
            if r.status_code == 404:
                return {}
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            time.sleep(3 * (k + 1))
    raise RuntimeError(f"failed: {url} {params}")


def news_month(m: pd.Period) -> pathlib.Path:
    f = OUT / "news" / f"{m}.parquet"
    if f.exists():
        return f
    from swingtrader.data import require_alpaca_keys
    k, s = require_alpaca_keys()
    H = {"APCA-API-KEY-ID": k, "APCA-API-SECRET-KEY": s}
    rows, tok = [], None
    start, end = m.start_time.strftime("%Y-%m-%dT00:00:00Z"), (m.end_time + pd.Timedelta(seconds=1)).strftime("%Y-%m-%dT00:00:00Z")
    while True:
        p = {"start": start, "end": end, "limit": 50, "sort": "asc"}
        if tok:
            p["page_token"] = tok
        j = _get("https://data.alpaca.markets/v1beta1/news", p, H)
        for x in j.get("news", []):
            rows.append(dict(id=x["id"], created_at=x["created_at"], headline=x.get("headline", ""),
                             summary=(x.get("summary") or "")[:400], symbols=",".join(x.get("symbols") or []),
                             source=x.get("source", ""), author=x.get("author", "")))
        tok = j.get("next_page_token")
        if not tok:
            break
        time.sleep(0.25)                                    # ~200/min limit
    f.parent.mkdir(parents=True, exist_ok=True)
    D = pd.DataFrame(rows)
    if len(D):
        D["created_at"] = pd.to_datetime(D.created_at, utc=True)
    D.to_parquet(f)
    return f


def reddit_month(sub: str, m: pd.Period) -> pathlib.Path:
    f = OUT / "reddit" / sub / f"{m}.parquet"
    if f.exists():
        return f
    rows = []
    after = int(m.start_time.tz_localize("UTC").timestamp())
    before = int((m.end_time + pd.Timedelta(seconds=1)).tz_localize("UTC").timestamp())
    while True:
        j = _get("https://arctic-shift.photon-reddit.com/api/posts/search",
                 {"subreddit": sub, "after": after, "before": before, "limit": "auto", "sort": "asc",
                  "fields": "id,created_utc,title,score,num_comments,link_flair_text"}, UA)
        d = j.get("data") or []
        rows += d
        if len(d) < 100:
            break
        nxt = int(d[-1]["created_utc"])
        after = nxt if nxt > after else after + 1
        time.sleep(0.4)
    f.parent.mkdir(parents=True, exist_ok=True)
    D = pd.DataFrame(rows).drop_duplicates("id") if rows else pd.DataFrame(columns=["id", "created_utc", "title"])
    D.to_parquet(f)
    return f


def wiki_views() -> pathlib.Path:
    """Daily en.wikipedia user pageviews 2016-01-01..2026-09-30 for every article in wikidata_tickers.parquet
    (Wikidata: NASDAQ/NYSE/NYSE American/Cboe tickers with an enwiki article; tickers as of today)."""
    W = pd.read_parquet(OUT / "wikidata_tickers.parquet")
    d = OUT / "wiki"
    d.mkdir(parents=True, exist_ok=True)
    from urllib.parse import quote
    from urllib.parse import unquote
    from concurrent.futures import ThreadPoolExecutor

    def one(t):
        name = unquote(t)
        fk = d / (quote(name, safe="")[:150] + ".parquet")
        if fk.exists():
            return
        url = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/"
               f"{quote(name, safe='')}/daily/20160101/20260930")
        try:
            j = _get(url, None, UA, tries=3)
            D = pd.DataFrame([(x["timestamp"][:8], x["views"]) for x in j.get("items", [])], columns=["date", "views"])
        except RuntimeError:
            D = pd.DataFrame(columns=["date", "views"])
        D["title"] = t
        D.to_parquet(fk)

    with ThreadPoolExecutor(6) as ex:
        list(ex.map(one, sorted(W.title.unique())))
    return d


def load_news(a: str = "2016-01", b: str = "2026-09") -> pd.DataFrame:
    fs = [OUT / "news" / f"{m}.parquet" for m in _months(a, b)]
    return pd.concat([pd.read_parquet(f) for f in fs if f.exists()], ignore_index=True)


def load_reddit(sub: str, a: str = "2016-01", b: str = "2026-09") -> pd.DataFrame:
    fs = [OUT / "reddit" / sub / f"{m}.parquet" for m in _months(a, b)]
    D = pd.concat([pd.read_parquet(f) for f in fs if f.exists()], ignore_index=True)
    D["created"] = pd.to_datetime(D.created_utc.astype(int), unit="s", utc=True)
    return D


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["news", "reddit", "wiki"])
    ap.add_argument("args", nargs="*")
    a = ap.parse_args(argv)
    if a.what == "wiki":
        wiki_views()
    elif a.what == "news":
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(int(a.args[2]) if len(a.args) > 2 else 3) as ex:   # ~3 x 50 req/min, under 200/min
            for m in ex.map(news_month, _months(*a.args[:2])):
                print("news", m, flush=True)
    else:
        sub, lo, hi = a.args
        for m in _months(lo, hi):
            reddit_month(sub, m); print("reddit", sub, m, flush=True)


if __name__ == "__main__":
    main()
