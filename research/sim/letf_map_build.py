"""Build swingtrader/daily/letf_map.json: single-stock leveraged ETF -> underlying, from Sharadar fund names
(the SS-LETF / LETF-NIGHT name patterns). Refresh from the Mac (Sharadar is local only):
    PYTHONPATH=.:$HOME/sharadar-data .venv/bin/python -m research.sim.letf_map_build"""
import json, pathlib, re, datetime as dt
from sharadar import tickers
ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "swingtrader/daily/letf_map.json"
PATS = [r"2X (?:LONG|SHORT|INVERSE) ([A-Z]{1,5})\b", r"DAILY ([A-Z]{1,5}) (?:BULL|BEAR) 2X", r"CORGI ([A-Z]{1,5}) 2X",
        r"2X ([A-Z]{1,5}) DAILY", r"(?:LONG|SHORT) ([A-Z]{1,5}) DAILY", r"1\.5X (?:LONG|SHORT) ([A-Z]{1,5})"]
INV = re.compile(r"\b(SHORT|BEAR|INVERSE)\b")
if __name__ == "__main__":
    t = tickers(); f = t[t.category.isin(["ETF", "ETN"])]
    m = {}
    for r in f.itertuples():
        nm = str(r.name).upper()
        for p in PATS:
            x = re.search(p, nm)
            if x:
                m[r.ticker] = dict(under=x.group(1), inverse=bool(INV.search(nm)), active=r.isdelisted == "N", name=nm[:70]); break
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(dict(built=dt.date.today().isoformat(), n=len(m), map=m), indent=0))
    print(f"{len(m)} single-stock LETFs ({sum(v['active'] for v in m.values())} active), {len({v['under'] for v in m.values()})} underlyings -> {OUT}")
