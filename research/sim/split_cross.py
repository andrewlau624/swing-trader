"""Study SPLIT-CROSS: forward-split ex-date night at official SIP crosses 2016-20. See round1_prose.md.
    PYTHONPATH=. .venv/bin/python -m research.sim.split_cross"""
import json, pathlib, subprocess
import numpy as np, pandas as pd
from research.sim import book
from swingtrader.daily import exdate_open_shadow as M

S = pathlib.Path.home() / "data" / "sharadar"
OUT = []
def P(s=""):
    print(s); OUT.append(s)
H = M._headers()
CACHE = pathlib.Path("data/research/program/split_cross_cache.json")

st = pd.read_parquet(S / "stocks.parquet", columns=["ticker", "date", "open", "close", "volume", "closeunadj"])
st["date"] = pd.to_datetime(st["date"]); st = st.sort_values(["ticker", "date"])
tk = pd.read_parquet(S / "tickers.parquet", columns=["table", "ticker", "category"])
common = set(tk[(tk.table == "SEP") & tk.category.str.contains("Common", na=False)].ticker)
st["ropen"] = st.open * st.closeunadj / st.close
g = st.groupby("ticker")
st["pclose"] = g.closeunadj.shift(1); st["pdate"] = g.date.shift(1); st["pvol"] = g.volume.shift(1)
st["padv"] = g.apply(lambda d: (d.closeunadj * d.volume).rolling(20, min_periods=5).mean().shift(1), include_groups=False).reset_index(level=0, drop=True)
key = st.set_index(["ticker", "date"])
a = pd.read_parquet(S / "actions.parquet"); a["date"] = pd.to_datetime(a["date"])
a = a[(a.action == "split") & (a.value > 1) & (a.date >= "2016-01-04") & (a.date <= "2020-12-31")]
ev = []
for e in a.itertuples():
    k = (e.ticker, e.date)
    if k not in key.index or e.ticker not in common: continue
    x = key.loc[k]
    if not np.isfinite(x.pclose) or x.pclose < 5 or x.pclose * x.pvol < 1e6 or (e.date - x.pdate).days > 5: continue
    ev.append(dict(sym=e.ticker, ex=e.date, ratio=e.value, px=x.pclose, adv=x.padv, dopen=x.ropen, dclose=x.pclose, d0=x.pdate))
ev = pd.DataFrame(ev).drop_duplicates(["sym", "ex"])
P(f"events after filters: {len(ev)}")

def fetch(sym, d0, d1):
    q = {"symbols": sym, "start": (d0 - pd.Timedelta(days=1)).strftime("%Y-%m-%d"), "end": (d1 + pd.Timedelta(days=1)).strftime("%Y-%m-%d"), "feed": "sip", "limit": 10000}
    j = M._get(M.AU_URL, q, H); out = {}
    for x in (j.get("auctions") or {}).get(sym, []):
        o = max(x["o"], key=lambda p: p.get("s", 0)) if x.get("o") else None
        c = max(x["c"], key=lambda p: p.get("s", 0)) if x.get("c") else None
        out[x["d"]] = [o and o["p"], o and o.get("s"), c and c["p"], c and c.get("s")]
    return out
cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
for r in ev.itertuples():
    k = f"{r.sym}|{r.ex.date()}"
    if k not in cache:
        try: cache[k] = fetch(r.sym, r.d0, r.ex)
        except Exception as e: cache[k] = {"err": str(e)}
sp = {}
for r in ev.itertuples():
    pass
spy_k = "SPY|all"
if spy_k not in cache:
    cache[spy_k] = {}
    for y in range(2016, 2021):
        for h in ((f"{y}-01-01", f"{y}-06-30"), (f"{y}-07-01", f"{y}-12-31")):
            q = {"symbols": "SPY", "start": h[0], "end": h[1], "feed": "sip", "limit": 10000}
            for x in (M._get(M.AU_URL, q, H).get("auctions") or {}).get("SPY", []):
                o = x["o"][0]["p"] if x.get("o") else None; c = max(x["c"], key=lambda p: p.get("s", 0))["p"] if x.get("c") else None
                cache[spy_k][x["d"]] = [o, c]
CACHE.write_text(json.dumps(cache))
spy = cache[spy_k]; sd = sorted(spy)

rows = []
for r in ev.itertuples():
    c = cache[f"{r.sym}|{r.ex.date()}"]
    ex = str(r.ex.date()); d0 = str(r.d0.date())
    if ex not in c or d0 not in c:
        rows.append(dict(sym=r.sym, ex=r.ex, status="no_data")); continue
    oc, osz, _, _ = c[ex]; _, _, cc, csz = c[d0]
    prev = [d for d in sd if d < ex]
    s0 = spy.get(prev[-1])[1] if prev else None; s1 = spy.get(ex, [None])[0]
    spy_on = s1 / s0 - 1 if (s0 and s1) else np.nan
    row = dict(sym=r.sym, ex=r.ex, ratio=r.ratio, px=r.px, adv=r.adv, ocross=oc, osz=osz, ccross=cc, csz=csz,
               dopen=r.dopen, dclose=r.dclose, spy=spy_on)
    row["status"] = "ok" if (oc and cc) else ("no_open_cross" if cc else "no_close_cross")
    if cc: row["t_fb"] = r.dopen * r.ratio / cc - 1       # fallback: daily-bar first print as exit
    if oc and cc: row["t0"] = oc * r.ratio / cc - 1
    if oc: row["gap"] = r.dopen / oc - 1                  # daily open vs official open cross (raw)
    if cc: row["cgap"] = r.dclose / cc - 1
    rows.append(row)
d = pd.DataFrame(rows)
P("status counts: " + str(d.status.value_counts().to_dict()))
d["yr"] = d.ex.dt.year
d["liq"] = pd.cut(d.adv, [0, 5e6, 5e7, 1e12], labels=["<5M", "5-50M", ">50M"])
d["rb"] = pd.cut(d.ratio, [1, 1.6, 2.01, 3.01, 1e9], labels=["1.5:1", "2:1", "3:1", ">3:1"])
d["osz_usd"] = d.osz * d.ocross
d["tiny"] = d.osz_usd < 5000
d["c2"] = 2 * 2 * book.cost_bps("tier", d.px.to_numpy(), d.adv.fillna(1e6).to_numpy()) / 1e4   # 2x tier round trip
m = d[d.status == "ok"].dropna(subset=["spy"]).copy()
m["x"] = m.t0 - m.spy; m["net2"] = m.x - m.c2
fb = d[d.status.isin(["ok", "no_open_cross"])].dropna(subset=["spy"]).copy(); fb["x"] = fb.t_fb - fb.spy

def stat(x, col="x"):
    v = x[col].dropna()
    if len(v) < 3: return f"n {len(v)}"
    day = x.groupby("ex")[col].mean()
    t = day.mean() / (day.std(ddof=1) / np.sqrt(len(day))) if len(day) > 2 else np.nan
    t5 = v.sort_values().iloc[:-5].mean() if len(v) > 8 else np.nan
    return f"n {len(v):4d} mean {v.mean()*1e4:+7.1f}bp med {v.median()*1e4:+6.1f} hit {(v>0).mean():.2f} t {t:5.2f} ex-top5 {t5*1e4:+7.1f}"
P("\n== JUDGED: cross->cross, minus SPY cross overnight (both crosses present)")
P(" gross x   " + stat(m)); P(" raw        " + stat(m, "t0")); P(" net 2x tier " + stat(m, "net2"))
P(" halves 16-18: " + stat(m[m.yr <= 2018])); P(" halves 19-20: " + stat(m[m.yr >= 2019]))
P(" net2 halves: " + stat(m[m.yr <= 2018], "net2") + " || " + stat(m[m.yr >= 2019], "net2"))
P("\n== by $ADV20 (x gross | net2)")
for k, x in m.groupby("liq", observed=True): P(f" {k}: " + stat(x) + f" | net2 mean {x.net2.mean()*1e4:+.1f} med {x.net2.median()*1e4:+.1f}")
P("== by ratio")
for k, x in m.groupby("rb", observed=True): P(f" {k}: " + stat(x) + f" | net2 mean {x.net2.mean()*1e4:+.1f}")
P("== open cross size ($)")
for k, x in m.groupby("tiny"): P(f" tiny(<$5k)={k}: " + stat(x))
P("== by year (median x bp, n)"); P(" " + "  ".join(f"{y}:{g_.x.median()*1e4:+.0f}({len(g_)})" for y, g_ in m.groupby("yr")))
P("\n== missing crosses")
n = len(d); P(f" events {n}; no_data/no close cross {(d.status.isin(['no_data','no_close_cross'])).sum()}; no open cross {(d.status=='no_open_cross').sum()} ({(d.status=='no_open_cross').mean():.1%})")
mm = d[d.status != "no_data"]
for k, x in mm.groupby("liq", observed=True): P(f"  {k}: no-open share {(x.status=='no_open_cross').mean():.1%} (n {len(x)}) ; tiny-open share among ok {x[x.status=='ok'].tiny.mean():.1%}")
for k, x in mm.groupby("rb", observed=True): P(f"  ratio {k}: no-open share {(x.status=='no_open_cross').mean():.1%} (n {len(x)})")
P("\n== FALLBACK (daily open as exit when no open cross; proxy for first trade, not judged)")
P(" all with fallback " + stat(fb)); P(" only no-open-cross events " + stat(fb[fb.status == "no_open_cross"]))
P("\n== daily open vs official open cross, raw gap bp (dopen/ocross-1)")
P(f" median {m.gap.median()*1e4:+.1f}  mean {m.gap.mean()*1e4:+.1f}  p10 {m.gap.quantile(.1)*1e4:+.0f} p90 {m.gap.quantile(.9)*1e4:+.0f}")
for k, x in m.groupby("liq", observed=True): P(f"  {k}: median {x.gap.median()*1e4:+.1f} mean {x.gap.mean()*1e4:+.1f}")
P(f" daily-close vs close cross: median {m.cgap.median()*1e4:+.1f} bp")
P("\n== 2021-26 shadow backfill (him:state/exdate-open.jsonl, splits, scored, eligible, not fund, ex<2026-10-07)")
try:
    txt = subprocess.run(["ssh", "him", "cat llm-trader/state/exdate-open.jsonl"], capture_output=True, text=True, timeout=60).stdout
    b = pd.DataFrame([json.loads(l) for l in txt.splitlines() if l.strip()])
    allsp = b[(b.kind == "split") & (b.ex < "2026-10-07")]
    P(" status counts: " + str(allsp.status.value_counts().to_dict()))
    s = allsp[(allsp.status == "scored") & (allsp.eligible == True) & (allsp.fund == False)].copy()
    s["liq"] = pd.cut(s.close_dollars, [0, 5e6, 5e7, 1e13], labels=["<5M", "5-50M", ">50M"])  # close_dollars = close cross $, not ADV
    v = s.x.dropna()
    P(f" x vs SPY: n {len(v)} mean {v.mean()*1e4:+.1f} med {v.median()*1e4:+.1f} hit {(v>0).mean():.2f}; raw pnl med {s.pnl.median()*1e4:+.1f}")
    s["cdv"] = pd.cut(s.close_dollars, [0, 1e5, 1e6, 1e13], labels=["<$100k", "$100k-1M", ">$1M"])
    for k, x in s.groupby("cdv", observed=True): P(f"  close-cross$ {k}: n {len(x)} mean {x.x.mean()*1e4:+.1f} med {x.x.median()*1e4:+.1f}")
    P(f" no_cross share of splits: {(allsp.status=='no_cross').mean():.1%}")
except Exception as e:
    P(" backfill read failed: " + str(e))
gate = (m.x.median() * 1e4 >= 15, m.net2.mean() > 0, m.net2.sort_values().iloc[:-5].mean() > 0 if len(m) > 8 else False,
        m[m.yr <= 2018].net2.mean() > 0, m[m.yr >= 2019].net2.mean() > 0)
P(f"\nGATE (median>=15, net2 mean>0, net2 ex-top5>0, halves>0 x2): {gate}; day-clustered t of net2 above.")
pathlib.Path("data/research/program/split_cross_out.txt").write_text("\n".join(OUT))
