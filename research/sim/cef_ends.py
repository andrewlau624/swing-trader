"""Study CEF-SURV99 Arm E (N 896): how delisted CEFs end, by era (price endgame + EDGAR N-8F).
    .venv/bin/python research/sim/cef_ends.py
"""
from __future__ import annotations
import json, pathlib, re, time
import numpy as np, pandas as pd, requests
from swingtrader.daily.news_judge import sec_headers

ROOT = pathlib.Path(__file__).resolve().parents[2]
STORE = pathlib.Path.home() / "data" / "sharadar"
CACHE = ROOT / "data" / "research" / "cef_surv"; (CACHE / "sub").mkdir(parents=True, exist_ok=True); (CACHE / "n8f").mkdir(exist_ok=True)
OUT = pathlib.Path(__file__).resolve().parent / "cef_ends_out.txt"
H = sec_headers(); _last = [0.0]
def get(url):
    dt = time.time() - _last[0]
    if dt < 0.14: time.sleep(0.14 - dt)
    _last[0] = time.time()
    for k in range(3):
        try:
            r = requests.get(url, headers=H, timeout=30)
            if r.status_code == 200: return r
            if r.status_code in (404, 403): return None
        except requests.RequestException: pass
        time.sleep(1.5)
    return None

tk = pd.read_parquet(STORE / "tickers.parquet")
c = tk[(tk.category == "CEF") & (tk.isdelisted == "Y")].drop_duplicates("permaticker").copy()
c["last"] = pd.to_datetime(c.lastpricedate)
c["cik"] = c.secfilings.str.extract(r"CIK=(\d+)")[0]
f = pd.read_parquet(STORE / "funds.parquet", columns=["ticker", "date", "closeadj"])
f = f[f.ticker.isin(set(c.ticker))]; f["dt"] = pd.to_datetime(f.date)
rows = []
for t, g in f.sort_values("dt").groupby("ticker"):
    g = g[g.closeadj > 0]
    if len(g) < 40: continue
    last = g.dt.iloc[-1]; px = g.closeadj.to_numpy()
    a6 = g[g.dt <= last - pd.Timedelta(days=182)]
    a20 = px[-21] if len(px) > 21 else np.nan
    rows.append(dict(ticker=t, last=last, r6m=px[-1] / a6.closeadj.iloc[-1] - 1 if len(a6) else np.nan,
                     r20=px[-1] / a20 - 1, vs_med60=px[-1] / np.median(px[-61:-1]) - 1 if len(px) > 61 else np.nan,
                     r_all_last=px[-1] / px[-2] - 1))
pe = pd.DataFrame(rows).merge(c[["ticker", "cik", "name"]], on="ticker")
pe["era"] = pd.cut(pe["last"].dt.year, [1997, 2004, 2009, 2014, 2026], labels=["1998-2004", "2005-09", "2010-14", "2015-26"])

def sub(cik):
    p = CACHE / "sub" / f"{cik}.json"
    if p.exists(): return json.loads(p.read_text())
    r = get(f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json")
    if r is None: p.write_text("{}"); return {}
    j = r.json(); rec = j["filings"]["recent"]
    forms = {k: list(v) for k, v in rec.items()}
    for ex in j["filings"].get("files", []):
        rr = get("https://data.sec.gov/submissions/" + ex["name"])
        if rr is not None:
            for k, v in rr.json().items(): forms.setdefault(k, []).extend(v)
    out = {"name": j.get("name"), "filings": forms}; p.write_text(json.dumps(out)); return out

def classify_doc(txt):
    t = re.sub(r"<[^>]+>", " ", txt); t = re.sub(r"&#\d+;|&nbsp;|&[a-z]+;", " ", t); t = re.sub(r"\s+", " ", t)
    m = re.search(r"reason for deregistration", t, re.I)
    seg = t[m.start(): m.start() + 900] if m else t[:6000]
    lab = {}
    for key, pat in (("MERGER", r"merger"), ("LIQUIDATION", r"liquidation"), ("ABANDON", r"abandonment"), ("BDC", r"election of status as a business")):
        mm = re.search(r"([\[\(/]\s*[xX☒☑]\s*[\]\)/]|[☒☑]|\bX\b)\s*(?:\w+\s){0,1}" + pat, seg, re.I)
        lab[key] = bool(mm)
    hits = [k for k, v in lab.items() if v]
    if len(hits) == 1: return hits[0], "box"
    low = t.lower()
    kw = {"MERGER": len(re.findall(r"merg|reorganiz|acquir", low)), "LIQUIDATION": len(re.findall(r"liquidat|dissol", low))}
    if kw["MERGER"] + kw["LIQUIDATION"] == 0: return "UNKNOWN", "none"
    return ("MERGER" if kw["MERGER"] > kw["LIQUIDATION"] else "LIQUIDATION"), "kw"

res = []
for i, r in enumerate(pe.itertuples()):
    cls, how, nf, n8 = "UNKNOWN", "nocik", "", ""
    if isinstance(r.cik, str):
        s = sub(r.cik); F = s.get("filings", {}) if s else {}
        if F:
            fd = pd.to_datetime(pd.Series(F["filingDate"])); fm = pd.Series(F["form"])
            win = (fd >= r.last - pd.Timedelta(days=270)) & (fd <= r.last + pd.Timedelta(days=900))
            cand = [j for j in fm[win & fm.str.fullmatch(r"N-8F(/A)?")].index
                    if str(F["primaryDocument"][j]).lower().endswith((".htm", ".txt"))]
            n8 = f"{len(cand)} N-8F"
            late = fm[(fd > r.last + pd.Timedelta(days=120)) & fm.str.contains(r"N-CSR|N-1A|485BPOS|497|N-Q|N-PORT", regex=True)]
            if cand:
                j = cand[0]; acc = F["accessionNumber"][j].replace("-", "")
                cp = CACHE / "n8f" / f"{r.ticker}.txt"
                if cp.exists(): txt = cp.read_text()
                else:
                    rr = get(f"https://www.sec.gov/Archives/edgar/data/{int(r.cik)}/{acc}/{F['primaryDocument'][j]}")
                    txt = rr.text if rr is not None else ""; cp.write_text(txt)
                cls, how = classify_doc(txt) if txt else ("UNKNOWN", "nodoc")
            elif len(late):
                cls, how = "OPEN-END/CONVERSION", "late-filings"
            else:
                cls, how = "UNKNOWN", "no-N8F"
        else: how = "nosub"
    res.append((cls, how, n8))
    if i % 100 == 0: print(i, len(pe), flush=True)
pe["end"] = [x[0] for x in res]; pe["how"] = [x[1] for x in res]
pe.to_csv(CACHE / "ends.csv", index=False)

L = []
def p(s): L.append(s); print(s)
p(f"[0] delisted CEFs with >=40 SFP bars: {len(pe)} of {len(c)}; with CIK {pe.cik.notna().sum()}")
tab = pe.groupby("era", observed=True).agg(n=("ticker", "size"), r6m_med=("r6m", "median"), r6m_mean=("r6m", "mean"),
      share_lt_m10=("r6m", lambda s: (s < -0.10).mean()), share_lt_m25=("r6m", lambda s: (s < -0.25).mean()),
      r20_med=("r20", "median"), last_vs_med60=("vs_med60", "median"), last_day_ret_med=("r_all_last", "median"))
p("[1] price endgame (closeadj total return, final window) by delist era:\n" + tab.round(3).to_string())
p("[2] end class by era (counts):\n" + pd.crosstab(pe.era, pe.end).to_string())
p("[2b] end class by era (shares):\n" + pd.crosstab(pe.era, pe.end, normalize="index").round(2).to_string())
p("[3] classification method:\n" + pd.crosstab(pe.era, pe.how).to_string())
p("[4] final-6m return by era x class (median, share < -10%, n):")
for (e, k), g in pe.groupby(["era", "end"], observed=True):
    p(f"    {e} {k:20s} n {len(g):3d} med r6m {g.r6m.median():+.3f} share<-10% {(g.r6m<-0.10).mean():.2f}")
pre, rec = pe[pe["last"].dt.year <= 2009], pe[pe["last"].dt.year >= 2015]
d = (pre.r6m < -0.10).mean() - (rec.r6m < -0.10).mean()
p(f"[5] share final-6m < -10%: pre-2010 {(pre.r6m<-0.10).mean():.1%} (n {len(pre)}) vs 2015-26 {(rec.r6m<-0.10).mean():.1%} (n {len(rec)}); diff {d*100:+.1f}pp -> "
  f"{'FLAG: older eras die less benignly' if d > 0.10 else 'no flag (<=10pp)'}")
OUT.write_text("\n".join(L) + "\n")
