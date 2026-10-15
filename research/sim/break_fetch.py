"""Study BREAK-REV: fetch EDGAR full-text-search METADATA for 8-Ks about merger-agreement terminations (2001-2026), keep hits
whose items include 1.02 (Termination of a Material Definitive Agreement). Metadata only (no documents, no prices) -> outcome-free.
  PYTHONPATH=. .venv/bin/python -m research.sim.break_fetch"""
import json, pathlib, time, urllib.request, urllib.parse
from swingtrader.daily.news_judge import sec_headers
OUT = pathlib.Path("data/research/events/break_hits.json")
H = sec_headers()
QS = ['"termination of the merger agreement"', '"terminated the merger agreement"', '"terminate the merger agreement"',
      '"termination of the agreement and plan of merger"', '"terminated the agreement and plan of merger"']
def page(q, y0, y1, frm):
    p = {"q": q, "forms": "8-K", "dateRange": "custom", "startdt": f"{y0}-01-01", "enddt": f"{y1}-12-31", "from": frm}
    for k in range(4):
        try:
            req = urllib.request.Request("https://efts.sec.gov/LATEST/search-index?" + urllib.parse.urlencode(p), headers=H)
            return json.loads(urllib.request.urlopen(req, timeout=40).read())
        except Exception as e:
            time.sleep(2 + 3 * k)
    return {"hits": {"hits": [], "total": {"value": 0}}}
hits = {}
for y in range(2001, 2027):
    for q in QS:
        frm = 0
        while True:
            d = page(q, y, y, frm); hh = d["hits"]["hits"]
            for x in hh:
                s = x["_source"]
                if "1.02" in (s.get("items") or []):
                    hits[s["adsh"]] = dict(adsh=s["adsh"], names=s["display_names"], ciks=s["ciks"], file_date=s["file_date"], items=s["items"], q=q)
            frm += 100; time.sleep(0.15)
            if frm >= min(d["hits"]["total"]["value"], 10000) or not hh: break
    print(y, len(hits), flush=True)
OUT.write_text(json.dumps(list(hits.values())))
print("saved", len(hits))
