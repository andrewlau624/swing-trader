"""SCALP-COST (Alpaca SIP): what a long scalp pays by liquidity bucket x time of day. No signal outcomes. No WRDS.
  PYTHONPATH=. .venv/bin/python -m research.sim.scalp_cost_alpaca plan | run [NTHREADS] | report
Design: years 2018, 2025; 10 random days each (seed 11, Feb-Nov, no early closes) -> data/research/scalp_cost/days_alpaca.txt.
Per day, 3 common stocks (price>=5, prior-20d median $vol from Sharadar SEP, closeunadj*volume) per $vol bucket (DEVIATION: drawn per day,
not 8 fixed names/year) + SPY QQQ IWM SMH TQQQ. Per name-day, 1 random decision second in each of 6 time-of-day buckets; fetch quotes+trades
decision..+30m (page cap QCAP/TCAP; horizon truncated to the covered span when capped, flagged)."""
import sys, json, time, random, datetime as dt
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import numpy as np, pandas as pd, requests
from .auction_fetch import _env

ROOT = Path(__file__).resolve().parents[2]; D = ROOT / "data/research/scalp_cost"; SAM = D / "alpaca_samples"; SAM.mkdir(parents=True, exist_ok=True)
OUT = ROOT / "data/research/program/scalp_cost_out.txt"
YEARS = [2018, 2025]; NDAY = 10; PERB = 3; SEED = 11; QCAP = 60; TCAP = 40; TMIN = 30
ETFS = ["SPY", "QQQ", "IWM", "SMH", "TQQQ"]
TOD = [("0930-0945", 9.5, 9.75), ("0945-1030", 9.75, 10.5), ("1030-1200", 10.5, 12), ("1200-1400", 12, 14), ("1400-1530", 14, 15.5), ("1530-1600", 15.5, 16)]
BUCKETS = [("A>1B", 1e9, 1e30), ("B200M-1B", 2e8, 1e9), ("C50-200M", 5e7, 2e8), ("D10-50M", 1e7, 5e7), ("E2-10M", 2e6, 1e7)]
GS = [10, 20, 30, 50]; SS = [10, 20, 30]; REG = {"@", "F", "E"}
H = None

def plan():
    st = pd.read_parquet("/Users/andrewlau/data/sharadar/stocks.parquet", columns=["ticker", "date", "volume", "closeunadj"])
    st["date"] = pd.to_datetime(st.date); tk = pd.read_parquet("/Users/andrewlau/data/sharadar/tickers.parquet", columns=["table", "ticker", "category", "isdelisted"])
    ok = set(tk[(tk.table == "SEP") & tk.category.fillna("").str.startswith("Domestic Common Stock")].ticker)
    rows = []; days = {}
    for y in YEARS:
        s = st[(st.date >= f"{y-1}-11-15") & (st.date <= f"{y}-12-31") & st.ticker.isin(ok)].copy()
        ds = sorted(d for d in s.date.unique() if pd.Timestamp(f"{y}-02-01") <= d <= pd.Timestamp(f"{y}-11-20"))
        ds = [d for d in ds if (d.month, d.day) not in {(7, 3), (11, 23), (11, 24), (11, 28), (12, 24)}]
        pick = sorted(random.Random(SEED + y).sample(ds, NDAY)); days[y] = pick
        s["dv"] = s.closeunadj * s.volume; s = s.sort_values(["ticker", "date"]); g = s.groupby("ticker")
        s["adv"] = g.dv.transform(lambda x: x.shift(1).rolling(20, min_periods=15).median()); s["pc"] = g.closeunadj.shift(1)
        for d in pick:
            x = s[(s.date == d) & (s.pc >= 5) & (s.closeunadj >= 4)]
            rnd = random.Random(f"{SEED}{d}")
            for b, lo, hi in BUCKETS:
                c = sorted(x[(x.adv >= lo) & (x.adv < hi)].ticker)
                for t in rnd.sample(c, min(PERB, len(c))): rows.append((str(d.date()), t, b, "stock"))
            for t in ETFS: rows.append((str(d.date()), t, "ETF", "etf"))
    (D / "days_alpaca.txt").write_text("\n".join(f"{y}: " + ", ".join(str(d.date()) for d in v) for y, v in days.items()) + "\n")
    pd.DataFrame(rows, columns=["date", "sym", "bucket", "kind"]).to_csv(D / "alpaca_plan.csv", index=False); print(len(rows), "name-days")

def get(sym, ep, start, end, cap, **kw):
    out, tok, capped = [], None, False
    for pg in range(cap):
        q = {"start": start, "end": end, "feed": "sip", "limit": 10000, **kw}
        if tok: q["page_token"] = tok
        for k in range(8):
            try: r = requests.get(f"https://data.alpaca.markets/v2/stocks/{sym}/{ep}", params=q, headers=H, timeout=60)
            except Exception: time.sleep(3); continue
            if r.status_code == 429: time.sleep(4 * (k + 1)); continue
            break
        else: return None, True
        if r.status_code >= 400: return None, True
        j = r.json(); out += j.get(ep) or []; tok = j.get("next_page_token")
        if not tok: return out, False
    return out, True

def iso(d, h): 
    t = pd.Timestamp(d).tz_localize("America/New_York") + pd.Timedelta(hours=h); return t
def qdf(v):
    q = pd.DataFrame(v); q["t"] = pd.to_datetime(q.t, utc=True, format="ISO8601"); q = q[(q.bp > 0) & (q.ap > q.bp) & (q.ap / q.bp < 1.2)]; return q.reset_index(drop=True)

def sample(d, sym, bucket, ti, rnd):
    name, a, b = TOD[ti]; t0 = iso(d, a) + pd.Timedelta(seconds=rnd.randrange(int((b - a) * 3600 - 1)))
    if t0 + pd.Timedelta(minutes=TMIN) > iso(d, 16): t0 = iso(d, 16) - pd.Timedelta(minutes=TMIN)
    key = SAM / f"{d}_{sym}_{ti}.json"
    if key.exists(): return
    t1 = t0 + pd.Timedelta(minutes=TMIN)
    pre, e1 = get(sym, "quotes", iso(d, 4).isoformat(), t0.isoformat(), 1, sort="desc", limit=50) if False else (None, 0)
    # decision quote: last valid quote before t0 (desc, small page)
    pq, bad = get_pre(sym, d, t0)
    qs, qc = get(sym, "quotes", t0.isoformat(), t1.isoformat(), QCAP)
    ts, tc = get(sym, "trades", t0.isoformat(), t1.isoformat(), TCAP)
    if qs is None or ts is None or pq is None: return
    rec = dict(date=d, sym=sym, bucket=bucket, tod=name, t0=t0.isoformat(), qcap=qc, tcap=tc, nq=len(qs), nt=len(ts), pq=pq, q=[(x["t"], x["bp"], x["ap"]) for x in qs], tr=[(x["t"], x["p"], x["s"], x.get("x"), "".join(x.get("c") or [])) for x in ts])
    key.write_text(json.dumps(rec))

def get_pre(sym, d, t0):
    q = {"start": iso(d, 4).isoformat(), "end": t0.isoformat(), "feed": "sip", "limit": 50, "sort": "desc"}
    for k in range(8):
        try: r = requests.get(f"https://data.alpaca.markets/v2/stocks/{sym}/quotes", params=q, headers=H, timeout=60)
        except Exception: time.sleep(3); continue
        if r.status_code == 429: time.sleep(4 * (k + 1)); continue
        if r.status_code >= 400: return None, True
        for x in r.json().get("quotes") or []:
            if x["bp"] > 0 and x["ap"] > x["bp"] and x["ap"] / x["bp"] < 1.2: return (x["t"], x["bp"], x["ap"]), False
        return [], False
    return None, True

def run(nth=6):
    global H; H = _env(); P = pd.read_csv(D / "alpaca_plan.csv"); jobs = []
    for r in P.itertuples():
        rnd = random.Random(f"{SEED}{r.date}{r.sym}")
        for ti in range(6):
            sd = random.Random(f"{SEED}{r.date}{r.sym}{ti}"); jobs.append((r.date, r.sym, r.bucket, ti, sd))
    jobs = [j for j in jobs if not (SAM / f"{j[0]}_{j[1]}_{j[3]}.json").exists()]; print(len(jobs), "samples todo", flush=True); n = [0]; t0 = time.time()
    def w(j):
        try: sample(*j)
        except Exception as e: print("ERR", j[:4], e, flush=True)
        n[0] += 1
        if n[0] % 100 == 0: print(n[0], round(time.time() - t0), "s", flush=True)
    with ThreadPoolExecutor(nth) as ex: list(ex.map(w, jobs))

def analyze(f):
    r = json.loads(Path(f).read_text()); t0 = pd.Timestamp(r["t0"]); t1 = t0 + pd.Timedelta(minutes=TMIN)
    if not r["pq"] or not r["q"] or not r["tr"]: return None
    pt, pb, pa = r["pq"]; mid = (pb + pa) / 2; entry = pa
    q = qdf([dict(t=a, bp=b, ap=c) for a, b, c in r["q"]]); tr = pd.DataFrame(r["tr"], columns=["t", "p", "s", "x", "c"]); tr["t"] = pd.to_datetime(tr.t, utc=True, format="ISO8601")
    tr = tr[tr.t >= t0.tz_convert("UTC")]
    end = t1.tz_convert("UTC"); capped = r["qcap"] or r["tcap"]
    if capped:
        end = min(q.t.iloc[-1] if r["qcap"] else end, tr.t.iloc[-1] if r["tcap"] else end)
    q = q[q.t <= end]; tr = tr[tr.t <= end]
    if q.empty or tr.empty: return None
    hz = (end - t0.tz_convert("UTC")).total_seconds() / 60
    mq = (q.bp + q.ap) / 2; qh = (q.ap - q.bp) / 2 / mq * 1e4
    out = dict(date=r["date"], sym=r["sym"], bucket=r["bucket"], tod=r["tod"], hz=hz, full=(hz >= TMIN - 0.05), spread=(pa - pb) / mid * 1e4)
    out["h_in"] = out["spread"] / 2; out["h_out"] = qh.iloc[-1]; out["c"] = out["h_in"] + out["h_out"]
    lit = tr[(tr.x != "D") & tr.c.map(lambda s: all(ch in REG for ch in s))].sort_values("t")   # lit, regular, round/odd? odd-lot flagged 'I' excluded by REG
    # effective half-spread of buyer-initiated lit trades (quote rule, prevailing quote)
    a = pd.merge_asof(lit, q[["t", "bp", "ap"]], on="t")
    a = a.dropna(subset=["bp"]); m = (a.bp + a.ap) / 2; a = a[a.p > m]
    out["eff_half"] = float(np.median(((a.p - m[a.index]) / m[a.index] * 1e4))) if len(a) else np.nan
    out["n_buy"] = len(a)
    for G in GS:
        lv = entry * (1 + G / 1e4)
        out[f"touch{G}"] = bool((tr.p >= lv).any())
        ab = lit[lit.p > lv]; out[f"thru{G}"] = bool(ab.s.sum() >= 100)
    for S in SS:
        lv = entry * (1 - S / 1e4); hit = q[q.bp <= lv]
        if hit.empty: out[f"stop{S}"] = np.nan; out[f"trig{S}"] = False; continue
        th = hit.t.iloc[0]; nx = lit[lit.t > th]
        out[f"trig{S}"] = True; out[f"stop{S}"] = (lv - nx.p.iloc[0]) / entry * 1e4 if len(nx) else np.nan
    return out

def report():
    rows = [analyze(f) for f in sorted(SAM.glob("*.json"))]; df = pd.DataFrame([x for x in rows if x]); df["year"] = df.date.str[:4]
    df.to_csv(D / "alpaca_results.csv", index=False); L = []; p = L.append
    nb = ["A>1B", "B200M-1B", "C50-200M", "D10-50M", "E2-10M", "ETF"]; tods = [t[0] for t in TOD]
    p(f"SCALP-COST (Alpaca SIP) samples used {len(df)} of {len(list(SAM.glob('*.json')))}; full-30m horizon {df.full.mean():.0%}. bp of mid.")
    for y in ["2018", "2025"]:
        d = df[df.year == y]
        for title, col, fn in [("round-trip c = h_in + h_out (quoted), median [mean]", "c", None), ("quoted spread at decision, median", "spread", None), ("effective half-spread, buyer-initiated lit trades, median of sample medians", "eff_half", None)]:
            p(f"\n== {y}: {title}"); p("bucket      " + " ".join(f"{t:>14}" for t in tods) + "   n/cell")
            for b in nb:
                cells = []
                for t in tods:
                    x = d[(d.bucket == b) & (d.tod == t)][col].dropna()
                    cells.append(f"{x.median():6.1f}[{x.mean():5.1f}]" if col == "c" and len(x) else (f"{x.median():8.1f}" if len(x) else "      -"))
                p(f"{b:10} " + " ".join(f"{c:>14}" for c in cells) + f"   {len(d[d.bucket==b])//6}")
        p(f"\n== {y}: min G with c <= 25% of G  (= 4 x median c), bp")
        p("bucket      " + " ".join(f"{t:>10}" for t in tods))
        for b in nb:
            p(f"{b:10} " + " ".join(f"{4*d[(d.bucket==b)&(d.tod==t)].c.median():10.0f}" for t in tods))
    f = df[df.full]
    for y in ["2018", "2025"]:
        d = f[f.year == y]
        p(f"\n== {y}: P(touch) / P(through, lit, cum size>=100), full-30m-horizon samples only; entry = ask at decision, by bucket (pooled tod)")
        p("bucket     n    " + " ".join(f"G{G}:touch/thru" .rjust(16) for G in GS))
        for b in nb:
            x = d[d.bucket == b]
            p(f"{b:10} {len(x):4d} " + " ".join(f"{x[f'touch{G}'].mean():6.2f}/{x[f'thru{G}'].mean():5.2f}".rjust(16) if len(x) else "-".rjust(16) for G in GS))
        p(f"-- {y} stop slippage past stop level (bp of entry; positive = worse), next lit trade after bid<=stop; trig rate / median / mean / p90")
        for b in nb:
            x = d[d.bucket == b]; s = []
            for S in SS:
                v = x[f"stop{S}"].dropna(); s.append(f"S{S}: {x[f'trig{S}'].mean():.2f}/{v.median() if len(v) else float('nan'):.1f}/{v.mean() if len(v) else float('nan'):.1f}/{v.quantile(.9) if len(v) else float('nan'):.1f}")
            p(f"{b:10} " + "   ".join(s))
    p("\nhorizon coverage (median minutes covered) by bucket: " + ", ".join(f"{b} {df[df.bucket==b].hz.median():.1f}" for b in nb))
    OUT.write_text("\n".join(L) + "\n"); print("\n".join(L))

if __name__ == "__main__":
    c = sys.argv[1]
    if c == "plan": plan()
    elif c == "run": run(int(sys.argv[2]) if len(sys.argv) > 2 else 6)
    else: report()
