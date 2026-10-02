"""Jump hunt R3-3: run-up into an FDA advisory committee meeting on a listed sponsor's product.

Federal Register API: FDA NOTICE documents with "advisory committee" and "notice of meeting", 2015-2026; full text of
each. Sponsor = the first "sponsored by <name>" / "submitted by <name>"; meeting date = the first "on <Month day, year>"
after "meeting will be held" (else the first date in the text after the publication date). Sponsor -> ticker by exact
normalized-name match to Alpaca assets. fd = 6 sessions before the meeting date (hold5 ends the session before),
kept only if the notice was published on/before fd. No ADV cap (big pharma drops out on its own: no lift).

    PYTHONPATH=. .venv/bin/python -m research.sim.jump_r3_3
"""
from __future__ import annotations

import json
import re
import time

import pandas as pd
import requests

from .jump_common import ROOT, _norm, save
from .jump_news import parse_date, sessions, shift_sessions

C = ROOT / "data/research/jump/fedreg_adcom.json"
UA = {"User-Agent": "swing-trader personal research (jump hunt)"}


def fetch() -> list[dict]:
    if C.exists():
        return json.load(open(C))
    docs, page = [], 1
    while True:
        j = requests.get("https://www.federalregister.gov/api/v1/documents.json", params={
            "conditions[term]": '"advisory committee" "notice of meeting"', "conditions[agencies][]": "food-and-drug-administration",
            "conditions[type][]": "NOTICE", "conditions[publication_date][gte]": "2015-06-01", "per_page": 100, "page": page,
            "fields[]": ["title", "publication_date", "raw_text_url"]}, headers=UA, timeout=60).json()
        docs += j.get("results", [])
        if page >= j.get("total_pages", 1):
            break
        page += 1
    out = []
    for d in docs:
        try:
            t = requests.get(d["raw_text_url"], headers=UA, timeout=60).text
        except requests.RequestException:
            continue
        time.sleep(0.4)
        out.append(dict(pub=d["publication_date"], title=d["title"], text=t[:20000]))
    json.dump(out, open(C, "w"))
    return out


def build() -> pd.DataFrame:
    alp = json.load(open(ROOT / "data/research/events/alpaca_asset_names.json"))
    by_name: dict[str, str] = {}
    for sym, nm in alp.items():
        if re.fullmatch(r"[A-Z]{1,5}", sym):
            by_name.setdefault(_norm(nm), sym)
    S = sessions()
    rows = []
    for d in fetch():
        txt = re.sub(r"\s+", " ", d["text"])
        m = re.search(r"(?:sponsored|submitted) by ([A-Z][\w.&,' -]{2,80}?)(?:,| for | to | \(|\.)", txt)
        if not m:
            continue
        sym = by_name.get(_norm(m.group(1)))
        if not sym:
            continue
        pub = pd.Timestamp(d["pub"])
        k = txt.find("will be held")
        day = parse_date(txt[k:k + 300] if k >= 0 else txt, pub)
        if day is None or day <= pub:
            continue
        fd = shift_sessions(day, 6, S)
        if fd is not None and pub <= fd:
            rows.append(dict(sym=sym, fd=fd, sponsor=m.group(1), meeting=day))
    E = pd.DataFrame(rows).drop_duplicates(["sym", "fd"])
    E.to_csv(ROOT / "data/research/jump/r3_3_events.csv", index=False)
    return E


if __name__ == "__main__":
    save(build(), "r3_3")
