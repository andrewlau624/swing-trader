"""Study BOND-LEAD (pre-reg round1_prose.md, commit 740422a). Run: .venv/bin/python -m research.sim.bond_lead
Needs data/research/bond_lead/{trace_YYYYMM,crsp_*}.parquet from bond_lead_pull.py. Signal days 2006-01-03..2015-12-31 only.
Choices not fixed by the registration (disclosed): prior close = |prc| on d-1; decile = rank pct > 0.9 of BRET (ties included),
day skipped if universe < 10; ambiguous issuer6->permno (>1 permno valid on d) dropped; net = excess - 4bp (2bp/side round trip on the
pick leg each day); ex-top-5 drops the 5 best days; within-tercile: terciles of own ret(d), spread = mean over terciles that hold picks
of (pick mean - universe mean) of ret(d+1); IG/HY skipped (FISD not pulled)."""
import glob, pathlib, numpy as np, pandas as pd
D = pathlib.Path("data/research/bond_lead"); OUT = pathlib.Path("data/research/program/bond_lead_out.txt"); LOG = []
def P(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); LOG.append(s)
def tstat(x):
    x = np.asarray(x, float); x = x[~np.isnan(x)]
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else np.nan
J0, J1 = pd.Timestamp("2006-01-03"), pd.Timestamp("2015-12-31")

# ---- CRSP
dsf = pd.read_parquet(D / "crsp_dsf.parquet"); dsf["date"] = pd.to_datetime(dsf["date"])
dsf = dsf.drop_duplicates(["permno", "date"])
cal = np.sort(dsf.date.unique()); cal = pd.DatetimeIndex(cal)
cidx = {d: i for i, d in enumerate(cal)}
dsf["ti"] = dsf.date.map(cidx)
dsf["ap"] = dsf.prc.abs(); dsf["dv"] = dsf.ap * dsf.vol
dsf = dsf.sort_values(["permno", "ti"])
g = dsf.groupby("permno")
dsf["adv20"] = g.dv.transform(lambda s: s.shift(1).rolling(20, min_periods=15).median())   # d-20..d-1
dsf["pclose"] = g.ap.shift(1)
nm = pd.read_parquet(D / "crsp_names.parquet")
for c in ("namedt", "nameendt"): nm[c] = pd.to_datetime(nm[c])
nm = nm[nm.shrcd.isin([10, 11]) & nm.exchcd.isin([1, 2, 3])].copy()
nm["i6"] = nm.ncusip.str[:6]; nm = nm[nm.i6.str.len() == 6][["i6", "permno", "namedt", "nameendt"]]
dl = pd.read_parquet(D / "crsp_delist.parquet"); dl["dlstdt"] = pd.to_datetime(dl.dlstdt)
for c in ("dlret", "dlstcd"): dl[c] = pd.to_numeric(dl[c], errors="coerce").astype("float64")
dl["dre"] = np.where(dl.dlret.isna(), np.where(dl.dlstcd.between(500, 599), -0.30, 0.0), dl.dlret)   # Shumway as CRSP-EARLY
dl["ti"] = cal.searchsorted(dl.dlstdt.values)                                                         # first trading day >= dlstdt
dl = dl.sort_values("dlstdt").drop_duplicates("permno", keep="last")[["permno", "ti", "dre"]]

# ---- bonds
fs = sorted(glob.glob(str(D / "trace_*.parquet")))
b = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True); b["d"] = pd.to_datetime(b.d)
b = b[b.d.isin(cidx)].copy(); b["ti"] = b.d.map(cidx)
b = b.sort_values(["cusip_id", "ti"])
gb = b.groupby("cusip_id")
b["pp"] = gb.px.shift(1); b["pti"] = gb.ti.shift(1)
b = b[(b.ti - b.pti <= 5)].copy(); b["br"] = b.px / b.pp - 1
b["i6"] = b.cusip_id.str[:6]
iss = b.groupby(["i6", "d"], as_index=False).agg(bret=("br", "median"), nb=("br", "size"))
iss = iss[(iss.d >= J0) & (iss.d <= J1)]
P("== BOND-LEAD (N 948) data header")
P(f"TRACE months {len(fs)} ({pathlib.Path(fs[0]).stem}..{pathlib.Path(fs[-1]).stem}); flags: wis_fl='N', cmsn_trd IS DISTINCT FROM 'Y' (NULL=unflagged; field NULL for all rows from 2012-02), spcl_trd_fl NULL, asof_cd NULL, vol>=100k, tm<=15:59:59, last trade by tm desc,msg_seq_nb desc")
P(f"bond-day returns {len(b):,}; judged issuer-days with BRET {len(iss):,}; trading days with BRET {iss.d.nunique()}; mean issuers/day {len(iss)/iss.d.nunique():.0f}; mean bonds/issuer-day {iss.nb.mean():.2f}")
# link
m = iss.merge(nm, on="i6", how="left")
m = m[(m.namedt <= m.d) & (m.nameendt >= m.d)]
cnt = m.groupby(["i6", "d"]).permno.nunique().rename("k").reset_index()
amb = (cnt.k > 1).sum()
m = m.merge(cnt, on=["i6", "d"]); m = m[m.k == 1].drop_duplicates(["i6", "d"])
P(f"link rate (issuer-days -> unique CRSP common permno, NYSE/AMEX/Nasdaq): {len(m)/len(iss):.3f}  ambiguous dropped {amb}")
m["ti"] = m.d.map(cidx)
m = m.merge(dsf[["permno", "ti", "ret", "pclose", "adv20", "ap"]].rename(columns={"ap": "cl"}), on=["permno", "ti"], how="inner")
m = m[(m.pclose >= 5) & (m.adv20 >= 10e6)].copy()
# next-day return with delisting; overnight
m["nti"] = m.ti + 1; m = m[m.nti < len(cal)]
nx = dsf[["permno", "ti", "ret", "openprc"]].rename(columns={"ti": "nti", "ret": "nret", "openprc": "nopen"})
m = m.merge(nx, on=["permno", "nti"], how="left").merge(dl.rename(columns={"ti": "nti"}), on=["permno", "nti"], how="left")
has_dl = m.dre.notna()
m["r1"] = np.where(has_dl, (1 + m.nret.fillna(0)) * (1 + m.dre) - 1, m.nret)
m = m[m.r1.notna()].copy()
m["ov"] = np.where(m.nopen > 0, m.nopen / m.cl - 1, np.nan); m.loc[m.ov.abs() > 0.5, "ov"] = np.nan
m["dy"] = (1 + m.r1) / (1 + m.ov) - 1
cntd = m.groupby("d").size(); m = m[m.d.map(cntd) >= 10].copy()
m["pct"] = m.groupby("d").bret.rank(pct=True, method="average")
m["dec"] = np.ceil(m.pct * 10).clip(1, 10).astype(int)
m["pick"] = m.pct > 0.9
m["terc"] = m.groupby("d").ret.rank(pct=True).mul(3).apply(np.ceil).clip(1, 3)
nd = m.d.nunique()
P(f"analysis days {nd} ({m.d.min().date()}..{m.d.max().date()}); universe/day mean {len(m)/nd:.1f} (median {m.groupby('d').size().median():.0f}); picks/day mean {m.pick.sum()/nd:.1f}")
P("choices: prior close=|prc| d-1 >=5; adv=median 20d |prc|*vol d-20..d-1 >=10M; decile=rank pct>0.9 ties incl; skip day if universe<10; ambiguous links dropped; delist Shumway (-30% for 500-599 if missing, else 0); net=excess-4bp (2bp/side RT on pick leg); IG/HY skipped")

def daily(col):
    u = m.groupby("d")[col].mean(); p = m[m.pick].groupby("d")[col].mean()
    return (p - u).dropna()
ex = daily("r1") * 1e4
def stats(x, cost):
    n = x - cost
    top5 = n.drop(n.nlargest(5).index).mean()
    h1 = n[n.index < "2011-01-01"].mean(); h2 = n[n.index >= "2011-01-01"].mean()
    return n.mean(), tstat(n), n.median(), top5, h1, h2
mu, t, med, t5, h1, h2 = stats(ex, 4)
P("\n== PRIMARY (EW pick - EW universe, d close -> d+1 close, net of 2bp/side)")
P(f"gross excess {ex.mean():+.2f}bp/day  net {mu:+.2f}bp/day t {t:.2f}  median {med:+.2f}  ex-top-5-days mean {t5:+.2f}  halves 2006-10 {h1:+.2f} / 2011-15 {h2:+.2f}  ndays {len(ex)}")
# within tercile
rows = []
for d, gdf in m.groupby("d"):
    sp = []
    for tr in (1, 2, 3):
        s = gdf[gdf.terc == tr]
        if s.pick.any(): sp.append(s[s.pick].r1.mean() - s.r1.mean())
    if sp: rows.append((d, np.mean(sp)))
wt = pd.Series(dict(rows)) * 1e4
wmu, wt_t = wt.mean(), tstat(wt)
P(f"within-tercile spread (pick - universe inside terciles of own ret(d)): {wmu:+.2f}bp/day t {wt_t:.2f} (gross, days {len(wt)})")
for tr in (1, 2, 3):
    s = m[m.terc == tr]; sp = (s[s.pick].groupby("d").r1.mean() - s.groupby("d").r1.mean()).dropna() * 1e4
    P(f"   tercile {tr} (low->high own ret d): {sp.mean():+.2f}bp t {tstat(sp):.2f} n {len(sp)}")
P("\n== GATES")
G = [("net excess >= +6.5bp/day", mu >= 6.5, f"{mu:+.2f}"), ("day-clustered t >= 2", t >= 2, f"{t:.2f}"), ("median day > 0", med > 0, f"{med:+.2f}"),
     ("ex-top-5 days > 0", t5 > 0, f"{t5:+.2f}"), ("both halves > 0", h1 > 0 and h2 > 0, f"{h1:+.2f}/{h2:+.2f}"),
     ("within-tercile spread > 0 and t >= 2", wmu > 0 and wt_t >= 2, f"{wmu:+.2f} t {wt_t:.2f}")]
for n, ok, v in G: P(f"  {'PASS' if ok else 'FAIL'}  {n}  [{v}]")
P(f"OVERALL VERDICT: {'PASS' if all(x[1] for x in G) else 'KILL (gate(s) failed)'}")
P("\n== REPORTED EXTRAS")
bot = (m[m.dec == 1].groupby("d").r1.mean() - m.groupby("d").r1.mean()).dropna() * 1e4
P(f"bottom decile excess (gross): {bot.mean():+.2f}bp/day t {tstat(bot):.2f}")
P("deciles 1..10 excess vs universe (gross bp/day, t):")
u = m.groupby("d").r1.mean()
for k in range(1, 11):
    x = ((m[m.dec == k].groupby("d").r1.mean() - u).dropna()) * 1e4
    P(f"   D{k:2d} {x.mean():+7.2f}  t {tstat(x):+.2f}  n {len(x)}")
for lab, col in (("overnight (close d -> open d+1)", "ov"), ("day (open d+1 -> close d+1)", "dy")):
    x = daily(col) * 1e4; P(f"{lab}: pick-universe {x.mean():+.2f}bp/day t {tstat(x):.2f}")
mu5 = stats(ex, 10); P(f"5bp/side shock: net {mu5[0]:+.2f}bp/day t {mu5[1]:.2f}")
P("per-year net excess (bp/day, t):")
for y, x in (ex - 4).groupby(ex.index.year): P(f"   {y}: {x.mean():+7.2f}  t {tstat(x):+.2f}  n {len(x)}")
P("IG vs HY: skipped (FISD ratings not pulled)")
OUT.write_text("\n".join(LOG) + "\n")
