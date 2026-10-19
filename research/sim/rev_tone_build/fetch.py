"""Stream McAuley Amazon Reviews 2023 (HF) for one category, keep the 20 REV-TONE firms' reviews.

usage: python fetch.py <Category>   -> data/research/reviews/raw/<Category>.parquet (+ _meta.parquet)
Nothing but the filtered rows is written; the multi-GB jsonl is streamed and discarded.
"""
import json, re, sys, time, urllib.request
from pathlib import Path
import pandas as pd

BASE = "https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023/resolve/main/raw"
OUT = Path(__file__).resolve().parents[3] / "data/research/reviews/raw"
OUT.mkdir(parents=True, exist_ok=True)

# store name (lowercase, exact) -> ticker; frozen in round1_prose.md REV-TONE
FIRMS = {
    "NKE": ["nike", "jordan", "converse"],
    "UAA": ["under armour"],
    "CROX": ["crocs", "hey dude", "heydude"],
    "SKX": ["skechers"],
    "HBI": ["hanes", "champion", "maidenform", "bali"],
    "LEVI": ["levi's", "levis", "levi strauss & co.", "dockers", "signature by levi strauss & co. gold label", "denizen from levi's"],
    "COLM": ["columbia", "sorel", "mountain hardwear", "prana"],
    "DECK": ["ugg", "hoka one one", "hoka", "teva", "sanuk", "koolaburra by ugg"],
    "YETI": ["yeti"],
    "HELE": ["oxo", "hydro flask", "pur"],
    "IRBT": ["irobot"],
    "GPRO": ["gopro"],
    "SONO": ["sonos"],
    "LOGI": ["logitech", "logitech g", "ultimate ears", "astro gaming", "blue microphones"],
    "GRMN": ["garmin"],
    "HAS": ["hasbro", "hasbro gaming", "nerf", "play-doh", "hasbro games"],
    "MAT": ["mattel", "mattel games", "barbie", "hot wheels", "fisher-price", "fisher price", "mega bloks"],
    "ELF": ["e.l.f.", "e.l.f. cosmetics", "e.l.f. skin", "elf cosmetics"],
    "NWL": ["rubbermaid", "sharpie", "crock-pot", "crockpot", "mr. coffee", "coleman", "yankee candle", "graco", "oster",
            "sunbeam", "paper mate", "papermate", "expo", "elmer's", "calphalon", "contigo", "foodsaver"],
    "ENR": ["energizer", "rayovac", "armor all"],
}
STORE2T = {s: t for t, ss in FIRMS.items() for s in ss}
STORE_RE = re.compile(r'"store": "((?:[^"\\]|\\.)*)"')
PA_RE = re.compile(r'"parent_asin": "([A-Z0-9]+)"')
T0 = 1388534400000  # 2014-01-01 ms


def lines(url):
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                for b in r:
                    yield b.decode("utf-8", "ignore")
            return
        except Exception as e:  # restart whole stream; callers dedupe
            print("retry", url, e, flush=True)
            time.sleep(30)
    raise RuntimeError(url)


def main(cat):
    t = time.time()
    meta = {}
    for ln in lines(f"{BASE}/meta_categories/meta_{cat}.jsonl"):
        m = STORE_RE.search(ln)
        if not m:
            continue
        tk = STORE2T.get(m.group(1).strip().lower())
        if tk:
            d = json.loads(ln)
            meta[d["parent_asin"]] = (tk, d.get("store"), (d.get("title") or "")[:200], d.get("rating_number"))
    pd.DataFrame([(k, *v) for k, v in meta.items()], columns=["parent_asin", "tk", "store", "title", "n_ratings"]
                 ).to_parquet(OUT / f"{cat}_meta.parquet")
    print(cat, "meta items", len(meta), round(time.time() - t), "s", flush=True)
    rows, seen = [], set()
    for ln in lines(f"{BASE}/review_categories/{cat}.jsonl"):
        m = PA_RE.search(ln)
        if not m or m.group(1) not in meta:
            continue
        d = json.loads(ln)
        if d["timestamp"] < T0:
            continue
        key = (d["user_id"], d["asin"], d["timestamp"])
        if key in seen:
            continue
        seen.add(key)
        rows.append((meta[d["parent_asin"]][0], d["parent_asin"], d["timestamp"], d["rating"], (d.get("title") or "")[:300],
                     (d.get("text") or "")[:2000], d.get("helpful_vote", 0), d.get("verified_purchase")))
    df = pd.DataFrame(rows, columns=["tk", "parent_asin", "ts", "rating", "title", "text", "helpful", "verified"])
    df.to_parquet(OUT / f"{cat}.parquet")
    print(cat, "reviews", len(df), round(time.time() - t), "s", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
