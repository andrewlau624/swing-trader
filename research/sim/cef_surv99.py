"""Study CEF-SURV99 Arm S (N 895): price-only proxy entry on live vs delisted CEFs, 1999-2014.
Pre-registered in round1_prose.md ("Study CEF-SURV99").
    .venv/bin/python research/sim/cef_surv99.py
"""
from __future__ import annotations
import pathlib
import numpy as np, pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
STORE = pathlib.Path.home() / "data" / "sharadar"
OUT = pathlib.Path(__file__).resolve().parent / "cef_surv99_out.txt"
COST, BETA, HOLD = 0.005, 0.53, 14
rng = np.random.default_rng(7)
L: list[str] = []
def p(s): L.append(s); print(s, flush=True)

tk = pd.read_parquet(STORE / "tickers.parquet")
cef = tk[tk.category == "CEF"].drop_duplicates("permaticker")
dead_set = set(cef[cef.isdelisted == "Y"].ticker); live_set = set(cef[cef.isdelisted == "N"].ticker)
panel_set = set(pd.read_csv(ROOT / "data/research/cefconnect/cef_rv_trades_1999_2014.csv").ticker)
f = pd.read_parquet(STORE / "funds.parquet", columns=["ticker", "date", "closeunadj", "closeadj"],
                    filters=[("date", "<=", pd.Timestamp("2015-12-31"))])
f["dt"] = pd.to_datetime(f.date).dt.normalize()
spy = f[f.ticker == "SPY"].set_index("dt").closeadj.sort_index()
f = f[f.ticker.isin(set(cef.ticker))].sort_values(["ticker", "dt"])
f = f[f.closeadj > 0]
# ticker reuse guard: a ticker is one permaticker in this table (drop_duplicates above) -- check
p(f"[0] CEF tickers with SFP bars <=2015: {f.ticker.nunique()} (dead {len(set(f.ticker)&dead_set)}, live {len(set(f.ticker)&live_set)}, panel276 {len(set(f.ticker)&panel_set)})")

# weekly grid
f["wk"] = f.dt.dt.strftime("%G-%V")
wkl = f.groupby(["ticker", "wk"]).tail(1)  # last close of each week
wkl = wkl.sort_values(["ticker", "dt"]).reset_index(drop=True)
wkl["r26"] = wkl.groupby("ticker").closeadj.pct_change(26)
wkl["nhist"] = wkl.groupby("ticker").cumcount() + 1
wkl["elig"] = (wkl.nhist >= 53) & (wkl.closeunadj >= 3) & wkl.r26.notna()
w = wkl[wkl.elig & (wkl.dt >= "1999-01-01") & (wkl.dt <= "2014-12-31")].copy()
ncs = w.groupby("wk").ticker.transform("size")
w = w[ncs >= 30]
w["cut"] = w.groupby("wk").r26.transform(lambda s: s.quantile(0.10))
sig = w[w.r26 <= w.cut]
p(f"[1] eligible fund-weeks {len(w)} (dead share {w.ticker.isin(dead_set).mean():.1%}); signal fund-weeks {len(sig)}")

by_t = {t: g.reset_index(drop=True) for t, g in f.groupby("ticker")}
def spyret(a, b): return spy.asof(b) / spy.asof(a) - 1
rows = []
for t, g in sig.sort_values("dt").groupby("ticker"):
    d = by_t[t]; dd = d.dt.to_numpy("datetime64[ns]"); free = pd.Timestamp("1900-01-01")
    for _, r in g.iterrows():
        if r["dt"] <= free: continue
        pos = int(np.searchsorted(dd, np.datetime64(r["dt"]), side="right"))
        if pos >= len(d) or (d.dt[pos] - r["dt"]).days > 14: continue
        ent = d.dt[pos]; epx = d.closeadj[pos]
        tgt = ent + pd.Timedelta(weeks=HOLD)
        xp = int(np.searchsorted(dd, np.datetime64(tgt), side="right")) - 1
        ended = False
        if xp >= len(d) - 1 and d.dt.iloc[-1] < tgt - pd.Timedelta(days=7):
            xp = len(d) - 1; ended = True  # delisted before the hold ended: last close, final return kept
        elif xp >= len(d): xp = len(d) - 1
        if xp <= pos: continue
        xd = d.dt[xp]
        rows.append(dict(ticker=t, edate=ent, xdate=xd, ret=d.closeadj[xp] / epx - 1, ended=ended,
                         grp="DEAD" if t in dead_set else ("PANEL" if t in panel_set else "LIVE_OTHER"),
                         spy=spyret(ent, xd), wk=r.wk))
        free = xd
tr = pd.DataFrame(rows)
tr["net"] = tr.ret - COST
tr["alpha"] = tr.net - BETA * tr.spy
tr["yr"] = tr.edate.dt.year
tr.to_csv(ROOT / "data/research/cef_surv/proxy_trades.csv", index=False)
p(f"[2] proxy trades {len(tr)}: " + str(tr.grp.value_counts().to_dict()) + f"; ended-early {tr.ended.mean():.1%} (dead {tr[tr.grp=='DEAD'].ended.mean():.1%})")

def clus_t(x, cl):
    x = np.asarray(x, float); m = x.mean(); s = pd.Series(x - m).groupby(np.asarray(cl)).sum()
    n = len(s); return m / np.sqrt((s ** 2).sum() / (n - 1) / n) if n > 1 else float("nan")
def row(lab, g):
    if len(g) == 0: return f"    {lab}: n 0"
    o = np.delete(g.alpha.to_numpy(), np.argsort(-g.alpha.to_numpy())[:5]).mean() if len(g) > 5 else float("nan")
    return (f"    {lab:11s} n {len(g):5d} funds {g.ticker.nunique():3d} net {g.net.mean()*1e4:+7.1f} med {g.net.median()*1e4:+7.1f} "
            f"spy {g.spy.mean()*1e4:+6.0f} alpha {g.alpha.mean()*1e4:+7.1f} med {g.alpha.median()*1e4:+7.1f} "
            f"t {clus_t(g.alpha, g.wk):+5.2f} exTop5 {o*1e4:+7.1f} hit {(g.net>0).mean():.2f} 5pct {np.percentile(g.alpha,5)*1e4:+7.0f}")
p(f"[3] proxy results, alpha = net - {BETA}*SPY (bp):")
for g in ("PANEL", "LIVE_OTHER", "DEAD"): p(row(g, tr[tr.grp == g]))
p(row("ALL", tr)); p(row("LIVE(all)", tr[tr.grp != "DEAD"]))
p("    by entry-year DEAD vs PANEL alpha (bp, n): " + ", ".join(
    f"{y}: {tr[(tr.yr==y)&(tr.grp=='DEAD')].alpha.mean()*1e4:+.0f}({(tr[(tr.yr==y)&(tr.grp=='DEAD')]).shape[0]})/"
    f"{tr[(tr.yr==y)&(tr.grp=='PANEL')].alpha.mean()*1e4:+.0f}({(tr[(tr.yr==y)&(tr.grp=='PANEL')]).shape[0]})" for y in range(1999, 2015)))
# beta refit
b = np.polyfit(tr.spy, tr.net, 1)[0]; tr["alpha_b"] = tr.net - b * tr.spy
p(f"[4] refit beta {b:.2f}: alpha PANEL {tr[tr.grp=='PANEL'].alpha_b.mean()*1e4:+.1f}, LIVE_OTHER {tr[tr.grp=='LIVE_OTHER'].alpha_b.mean()*1e4:+.1f}, DEAD {tr[tr.grp=='DEAD'].alpha_b.mean()*1e4:+.1f}")

pn, dd_ = tr[tr.grp == "PANEL"], tr[tr.grp == "DEAD"]
live = tr[tr.grp != "DEAD"]
def delta(a, d):  # a=live-side, d=dead; year-reweighted: dead mean by year weighted by live's year mix
    wy = a.groupby("yr").size() / len(a)
    dm = d.groupby("yr").alpha.mean().reindex(wy.index)
    ok = dm.notna(); dr = (dm[ok] * wy[ok]).sum() / wy[ok].sum()
    return a.alpha.mean() - d.alpha.mean(), a.alpha.mean() - dr
for lab, a in (("PANEL", pn), ("LIVE(all)", live)):
    raw, rw = delta(a, dd_)
    se_t = (a.alpha.mean() - dd_.alpha.mean()) / np.sqrt(a.alpha.var() / len(a) + dd_.alpha.var() / len(dd_))
    p(f"[5] delta {lab}-DEAD: raw {raw*1e4:+.1f}bp (naive t {se_t:.2f}), year-reweighted {rw*1e4:+.1f}bp")
# bootstrap by entry-year clusters
yrs = np.arange(1999, 2015)
def boot(a):
    out = []
    for _ in range(2000):
        ys = rng.choice(yrs, len(yrs))
        A = pd.concat([a[a.yr == y] for y in ys]); D = pd.concat([dd_[dd_.yr == y] for y in ys])
        if len(A) and len(D): out.append((A.alpha.mean() - D.alpha.mean()) * 1e4)
    return np.array(out)
bs = boot(pn); bl = boot(live)
p(f"[6] bootstrap delta PANEL-DEAD bp: mean {bs.mean():+.0f} p10 {np.percentile(bs,10):+.0f} p90 {np.percentile(bs,90):+.0f}; "
  f"LIVE(all)-DEAD: mean {bl.mean():+.0f} p90 {np.percentile(bl,90):+.0f}")
# dead share p
pd_share_tr = len(dd_) / (len(pn) + len(dd_))
pd_share_live = len(dd_) / len(tr)
pd_share_fw = w.ticker.isin(dead_set).mean()
p(f"[7] dead share: of PANEL+DEAD proxy trades {pd_share_tr:.1%}; of all proxy trades {pd_share_live:.1%}; of eligible fund-weeks {pd_share_fw:.1%}")
# cost shocks and ex-0809 and halves
for lab, mask in (("ex-2008-09", ~tr.yr.isin([2008, 2009])), ("1999-2006", tr.yr <= 2006), ("2007-2014", tr.yr >= 2007)):
    s = tr[mask]; a, d = s[s.grp == "PANEL"], s[s.grp == "DEAD"]
    p(f"[8] {lab}: PANEL alpha {a.alpha.mean()*1e4:+.0f} (n {len(a)}), DEAD {d.alpha.mean()*1e4:+.0f} (n {len(d)}), delta {(a.alpha.mean()-d.alpha.mean())*1e4:+.0f}")
for k in (2, 3):
    c = (k - 1) * COST
    p(f"[9] {k}x cost: PANEL alpha {(pn.alpha.mean()-c)*1e4:+.0f}, DEAD {(dd_.alpha.mean()-c)*1e4:+.0f} (delta unchanged)")
# calibration: overlap of proxy entries with actual CEF-RV entries
crv = pd.read_csv(ROOT / "data/research/cefconnect/cef_rv_trades_1999_2014.csv", parse_dates=["edate", "xdate"])
hit = 0
for _, r in pn.iterrows():
    c = crv[(crv.ticker == r.ticker) & (crv.edate <= r.edate) & (crv.xdate >= r.edate)]
    hit += len(c) > 0
p(f"[10] calibration: PANEL proxy entries falling inside an actual CEF-RV hold: {hit}/{len(pn)} = {hit/len(pn):.1%} "
  f"(CEF-RV holds cover {sum((crv.xdate-crv.edate).dt.days)/ (len(set(crv.ticker))*365.25*16):.1%} of fund-time); "
  f"PANEL proxy alpha {pn.alpha.mean()*1e4:+.0f} vs CEF-RV alpha +237")
# bound
A0 = 237.0; pp = pd_share_tr
raw, rw = delta(pn, dd_)
for lab, dl in (("point (raw delta)", raw * 1e4), ("year-reweighted", rw * 1e4), ("bootstrap p90 PANEL", np.percentile(bs, 90)), ("bootstrap p90 LIVE(all)", np.percentile(bl, 90))):
    p(f"[11] BOUND {lab}: delta {dl:+.0f}bp, p {pp:.3f} -> adj_alpha = 237 - p*delta = {A0 - pp*dl:+.0f}bp")
p(f"[12] break-even: dead-fund CEF-RV alpha needed for pooled alpha 0 = {-A0*(1-pp)/pp:+.0f}bp/trade (actual DEAD proxy alpha {dd_.alpha.mean()*1e4:+.0f}, p5 {np.percentile(dd_.alpha,5)*1e4:+.0f}); "
  f"with p = dead share of all trades {pd_share_live:.3f}: {-A0*(1-pd_share_live)/pd_share_live:+.0f}")
OUT.write_text("\n".join(L) + "\n")
lvl = (1 - pp) * A0 + pp * dd_.alpha.mean() * 1e4
lvl90 = (1 - pp) * A0 + pp * np.percentile([x.alpha.mean() * 1e4 for x in [dd_.sample(len(dd_), replace=True, random_state=i) for i in range(200)]], 10)
mult = A0 / (pn.alpha.mean() * 1e4)
p(f"[13] LEVEL bound (dead funds' CEF-RV alpha = DEAD proxy alpha {dd_.alpha.mean()*1e4:+.0f}): pooled = (1-p)*237 + p*dead = {lvl:+.0f}bp; "
  f"p10 of resampled dead mean -> {lvl90:+.0f}")
p(f"[14] scaled-delta bound (delta x CEF-RV/proxy PANEL alpha ratio {mult:.2f}): {A0 - pp*raw*1e4*mult:+.0f}bp (ERASED if <=0)")
OUT.write_text("\n".join(L) + "\n")
