"""Study BREAK-REV (N 924 -> 927): post-deal-break reversal after merger-arb liquidation. Pre-reg research/drafts/round1_prose.md. Run once.
  PYTHONPATH=. .venv/bin/python -m research.sim.break_rev"""
import json, re, numpy as np, pandas as pd, pyarrow.parquet as pq
from research.sim import shar_surv as ss
from sharadar import prices as sh_prices
OUT = ss.ROOT / "data/research/program/break_rev_out.txt"; HITS = ss.ROOT / "data/research/events/break_hits.json"
COST = 25e-4; SHOCK = -0.07; CRASH = {2001, 2002, 2008, 2009, 2020}; ZBAR = 3.06; SPLIT = 2014
L = []
def P(s=""): print(s, flush=True); L.append(s)
rng = np.random.default_rng(0)

# ---- data
bars = pq.read_table(ss.STORES / "stocks.parquet", columns=["ticker", "date", "open", "close", "closeunadj"],
                     filters=[("date", ">=", pd.Timestamp("2000-10-01")), ("date", "<=", pd.Timestamp("2026-10-05"))]).to_pandas()
bars["date"] = pd.to_datetime(bars["date"]); bars = bars.dropna(subset=["close"]).sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
bars["ret"] = bars.close / bars.groupby("ticker").close.shift(1) - 1
spy = sh_prices(["SPY"], "2000-10-01", "2026-10-05", adjust="split", source="funds"); spy = spy[spy.ticker == "SPY"].assign(date=pd.to_datetime(spy.date)).set_index("date").close.sort_index()
sess = spy.index.to_numpy(); spyv = spy.to_numpy(float)
grp = {tk: (g.date.to_numpy(), g.open.to_numpy(float), g.close.to_numpy(float), g.closeunadj.to_numpy(float), g.ret.to_numpy(float)) for tk, g in bars.groupby("ticker", sort=False)}
P(f"bars {len(bars):,} rows, tickers {len(grp):,}, sessions {len(sess)} ({pd.Timestamp(sess[0]).date()}..{pd.Timestamp(sess[-1]).date()})")

def at(tk, si, kind):
    """price of ticker tk at session index si (exact date match; None if no bar)."""
    d, o, c, cu, r = grp[tk]; j = np.searchsorted(d, sess[si])
    if j >= len(d) or d[j] != sess[si]: return None
    return (o if kind == "o" else c)[j]

def window(tk, si0, e_lag, x_lag, e_kind="c", x_kind="c"):
    """abnormal return entering at session si0+e_lag, exiting si0+x_lag (SPY-adjusted); last available close if the name ends early."""
    si_e, si_x = si0 + e_lag, si0 + x_lag
    if si_x >= len(sess): return np.nan
    pe = at(tk, si_e, e_kind)
    if pe is None or not np.isfinite(pe) or pe <= 0: return np.nan
    px = at(tk, si_x, x_kind)
    if px is None:
        d, o, c, _, _ = grp[tk]; m = (d > sess[si_e]) & (d <= sess[si_x])
        if not m.any(): return np.nan
        px = c[m][-1]
    return (px / pe - 1) - (spyv[si_x] / spyv[si_e] - 1)

# ---- events
hits = json.loads(HITS.read_text()); P(f"FTS hits with item 1.02: {len(hits)}")
rows = []
for h in hits:
    fd = pd.Timestamp(h["file_date"]); fi = int(np.searchsorted(sess, np.datetime64(fd)))
    if fi >= len(sess): continue
    for nm in h["names"]:
        m = re.search(r"\(([A-Z][A-Z0-9.\-]{0,6})\)\s+\(CIK", nm)
        if not m or m.group(1) not in grp: continue
        tk = m.group(1); d, o, c, cu, r = grp[tk]
        lo, hi = max(fi - 3, 0), min(fi + 1, len(sess) - 1)
        best = None
        for si in range(lo, hi + 1):
            j = np.searchsorted(d, sess[si])
            if j < len(d) and d[j] == sess[si] and np.isfinite(r[j]) and (best is None or r[j] < best[1]): best = (si, r[j], cu[j - 1] if j > 0 else np.nan)
        if best and best[1] <= SHOCK and np.isfinite(best[2]) and best[2] >= 2:
            rows.append(dict(ticker=tk, d0=pd.Timestamp(sess[best[0]]), si=best[0], shock=best[1], file_date=fd, adsh=h["adsh"]))
ev = pd.DataFrame(rows).sort_values(["ticker", "d0"])
keep = []; last = {}
for _, e in ev.iterrows():
    if e.ticker in last and e.si - last[e.ticker] < 60: continue
    last[e.ticker] = e.si; keep.append(e)
ev = pd.DataFrame(keep).sort_values("d0").reset_index(drop=True)
P(f"events (filer with a <= -7% day in [file-3, file+1], $>=2, one per ticker/60 sessions): n {len(ev)}, {ev.d0.min().date()}..{ev.d0.max().date()}, median shock {ev.shock.median()*100:.1f}%, by era <{SPLIT}: {(ev.d0.dt.year < SPLIT).sum()} / >= : {(ev.d0.dt.year >= SPLIT).sum()}")
P("  per year: " + " ".join(f"{y}:{n}" for y, n in ev.d0.dt.year.value_counts().sort_index().items()))
ev.to_csv(ss.ROOT / "data/research/events/break_events.csv", index=False)

ARMS = {"A1 D1c->D10c": (1, 10, "c", "c"), "A2 D0c->D5c": (0, 5, "c", "c"), "A3 D3c->D20c": (3, 20, "c", "c")}
for k, (a, b, ek, xk) in ARMS.items(): ev[k] = [window(e.ticker, e.si, a, b, ek, xk) for e in ev.itertuples()]
ev["night D0c->D1o"] = [window(e.ticker, e.si, 0, 1, "c", "o") for e in ev.itertuples()]

# ---- control: same-month <= -7% days, non-event names
evset = set(ev.ticker); bars["m"] = bars.date.dt.to_period("M")
cand = bars[(bars.ret <= SHOCK) & (bars.closeunadj.shift(1) >= 2) & (bars.date >= ev.d0.min()) & (bars.date <= ev.d0.max()) & ~bars.ticker.isin(evset)]
cand = cand.groupby("m", group_keys=False).apply(lambda g: g.sample(min(len(g), 300), random_state=0))
cand = cand.assign(si=np.searchsorted(sess, cand.date.to_numpy())); cand = cand[sess[np.minimum(cand.si, len(sess) - 1)] == cand.date.to_numpy()]
P(f"control: {len(cand):,} generic <= -7% days (<= 300/month), {cand.ticker.nunique():,} names")
ctl = {k: np.array([window(r.ticker, r.si, a, b, ek, xk) for r in cand.itertuples()]) for k, (a, b, ek, xk) in ARMS.items()}

def ct(x, cl):
    x = pd.Series(np.asarray(x, float)); cl = pd.Series(np.asarray(cl)); m = x.notna(); x, cl = x[m], cl[m]
    g = x.groupby(cl.to_numpy()).agg(["sum", "count"]); mu = x.mean(); u = g["sum"] - mu * g["count"]
    se = np.sqrt((u ** 2).sum()) / len(x); return mu / se if se > 0 else np.nan

P(f"\nnight piece D0 close -> D1 open: mean {np.nanmean(ev['night D0c->D1o'])*100:+.2f}% median {np.nanmedian(ev['night D0c->D1o'])*100:+.2f}% (n {ev['night D0c->D1o'].notna().sum()})")
path = [np.nanmean([window(e.ticker, e.si, 0, k) for e in ev.itertuples()]) for k in range(1, 21)]
P("path D0 close -> Dk close (mean abnormal, %): " + " ".join(f"{k}:{v*100:+.1f}" for k, v in enumerate(path, 1)))
P()
mon = ev.d0.dt.to_period("M").astype(str).to_numpy(); yr = ev.d0.dt.year.to_numpy()
for k in ARMS:
    x = ev[k].to_numpy(float); ok = np.isfinite(x); net = x - 2 * COST; net2 = x - 4 * COST
    n = ok.sum(); mu = np.nanmean(net); t = ct(net, mon); med = np.nanmedian(net)
    h = (np.nanmean(net[yr < SPLIT]), np.nanmean(net[yr >= SPLIT])); ex5 = np.sort(net[ok])[:-5].mean() if n > 5 else np.nan
    exc = np.nanmean(net[~np.isin(yr, list(CRASH))]); c = ctl[k]; cmu = np.nanmean(c) - 2 * COST
    diff = mu - cmu; se = np.sqrt(np.nanvar(net) / n + np.nanvar(c) / np.isfinite(c).sum()); td = diff / se
    g = mu >= 0.01 and t >= ZBAR and min(h) > 0 and med > 0 and ex5 > 0 and np.nanmean(net2) > 0 and exc > 0 and diff >= 0.01 and td >= 2
    P(f"{k}: n {n} | net mean {mu*100:+.2f}% t(month) {t:+.2f} median {med*100:+.2f} halves {h[0]*100:+.2f}/{h[1]*100:+.2f} ex-top5 {ex5*100:+.2f} 2xcost {np.nanmean(net2)*100:+.2f} ex-crash {exc*100:+.2f} "
      f"| control net {cmu*100:+.2f}% (n {np.isfinite(c).sum():,}) diff {diff*100:+.2f} t {td:+.2f} | hit {np.mean(net[ok] > 0)*100:.0f}% => {'UNDERPOWERED' if n < 60 else ('PASS' if g else 'FAIL')}")
P("\nshock buckets (A1 net by D0 shock): " + " ".join(f"{lab}:{(ev[k][m]-2*COST).mean()*100:+.2f}%(n{m.sum()})" for lab, m in [("<=-20%", ev.shock <= -0.2), ("-20..-12", (ev.shock > -0.2) & (ev.shock <= -0.12)), ("-12..-7", ev.shock > -0.12)] for k in ["A1 D1c->D10c"]))
OUT.write_text("\n".join(L))
