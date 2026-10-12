"""WIKI-ATTN data fetch: Wikidata ticker->enwiki map, Wikimedia daily pageviews."""
import sys, time, urllib.parse, requests, pandas as pd, numpy as np, pathlib
UA = {"User-Agent": "swing-trader-research/0.1 (research script)"}
D = pathlib.Path("data/research/wiki"); D.mkdir(parents=True, exist_ok=True)
EXCH = {"Q13677": "NYSE", "Q82059": "NASDAQ", "Q846626": "NYSEMKT", "Q4047205": "NYSEARCA"}

def build_map():
    q = """SELECT ?item ?ex ?tick ?art ?start ?end WHERE {
      VALUES ?ex { wd:Q13677 wd:Q82059 wd:Q846626 wd:Q4047205 wd:Q1329573 }
      ?item p:P414 ?st . ?st ps:P414 ?ex . ?st pq:P249 ?tick .
      OPTIONAL { ?st pq:P580 ?start } OPTIONAL { ?st pq:P582 ?end }
      ?art schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> . }"""
    r = requests.get("https://query.wikidata.org/sparql", params={"query": q, "format": "json"}, headers=UA, timeout=300)
    r.raise_for_status()
    rows = []
    for b in r.json()["results"]["bindings"]:
        rows.append(dict(qid=b["item"]["value"].rsplit("/", 1)[1], exch=b["ex"]["value"].rsplit("/", 1)[1],
                         ticker=b["tick"]["value"].strip().upper(),
                         article=urllib.parse.unquote(b["art"]["value"].rsplit("/wiki/", 1)[1]),
                         start=b.get("start", {}).get("value"), end=b.get("end", {}).get("value")))
    return pd.DataFrame(rows)

if __name__ == "__main__":
    m = build_map(); m.to_parquet(D / "ticker_map_raw.parquet"); print(len(m), m.ticker.nunique(), m.article.nunique())


def fetch_views(articles, out=D / "views.parquet", rate=0.7):
    """Daily enwiki user pageviews 2015-07-01..2026-09-30, one request per article. Cached, resumable, paced
    (<= `rate` req/s, global cooldown on 429)."""
    f404 = D / "views_404.parquet"
    have = pd.read_parquet(out) if out.exists() else pd.DataFrame(columns=["article", "date", "views"])
    m404 = list(pd.read_parquet(f404).article) if f404.exists() else []
    done = set(have.article.unique()) | set(m404)
    todo = [a for a in articles if a not in done]
    print(f"views: {len(done)} cached, {len(todo)} to fetch", flush=True)
    s = requests.Session(); s.headers.update(UA)
    chunks = []; t_last = 0.0; nfail = 0
    def flush():
        nonlocal have, chunks
        if chunks:
            new = pd.DataFrame([x for c in chunks for x in c], columns=["article", "date", "views"])
            new["date"] = pd.to_datetime(new.date, format="%Y%m%d"); have["date"] = pd.to_datetime(have.date)
            have = pd.concat([have, new], ignore_index=True); chunks = []
        have.to_parquet(out); pd.DataFrame({"article": m404}).to_parquet(f404)
    for i, a in enumerate(todo):
        url = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/"
               + urllib.parse.quote(a.replace(" ", "_"), safe="") + "/daily/20150701/20260930")
        for k in range(8):
            w = t_last + 1.0 / rate - time.time()
            if w > 0: time.sleep(w)
            t_last = time.time()
            try: r = s.get(url, timeout=20)
            except Exception: time.sleep(2 ** min(k, 5)); continue
            if r.status_code == 200:
                chunks.append([(a, x["timestamp"][:8], x["views"]) for x in r.json()["items"]]); break
            if r.status_code == 404: m404.append(a); break
            if r.status_code == 429 or r.status_code >= 500: print("429/5xx",r.status_code,a,k,flush=True); time.sleep(5 * 2 ** min(k, 2)); continue
            m404.append(a); break
        else: nfail += 1
        if (i + 1) % 25 == 0: flush(); print(i + 1, "fail", nfail, flush=True)
    flush(); print("views done; unfetched after retries:", nfail, flush=True)
    return have
