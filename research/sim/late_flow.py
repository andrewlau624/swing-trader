"""Study LATE-FLOW (pre-registered round1_prose.md, N 945): bottom decile of 15:00-15:45 Lee-Ready signed flow / 20d median shr vol,
buy 16:00 close (CRSP prc), sell next open (CRSP openprc). Excess = EW pick close->open minus EW universe. Output late_flow_out.txt.
Inputs: data/research/late_flow/days/*.parquet (late_flow_run.py), dsf/dist/delist/names (late_flow_pull.py)."""
import sys, io
import numpy as np, pandas as pd
sys.path.insert(0, "research/sim")
import late_flow_univ as U
D = "data/research/late_flow/"
buf = io.StringIO()
def P(*a):
    s = " ".join(str(x) for x in a); print(s); buf.write(s + "\n")
def tstat(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 and x.std() > 0 else np.nan

f = U.load()
days = pd.concat([pd.read_parquet(p) for p in sorted((__import__("pathlib").Path(D) / "days").glob("*.parquet"))], ignore_index=True)
P("== LATE-FLOW coverage")
cov = days.groupby("date").agg(n_univ=("n_univ", "first"), n_linked=("n_linked", "first"), n_flow=("sflow", lambda s: s.notna().sum()))
P(f"days {len(cov)} {cov.index.min():%Y-%m-%d}..{cov.index.max():%Y-%m-%d}; mean universe {cov.n_univ.mean():.0f}, linked {cov.n_linked.mean():.0f} "
  f"(link rate {cov.n_linked.sum()/cov.n_univ.sum():.3f}), with flow {cov.n_flow.mean():.0f} (flow rate {cov.n_flow.sum()/cov.n_univ.sum():.3f})")
nm = days.n.mean(); P(f"mean trades/name 15:00-15:45 {nm:.0f}; share signed at mid (tick test) {days.n_mid.sum()/days.n.sum():.3f}; no-quote {days.n_nq.sum()/days.n.sum():.5f}")

# ---- returns: close d -> next open; ex-dividend/split nights dropped; delisting
f = f.sort_values(["permno", "date"]); g = f.groupby("permno")
f["nopen"] = g.openprc.shift(-1); f["ndate"] = g.date.shift(-1)
cal = pd.DatetimeIndex(sorted(f.date.unique())); nxt = pd.Series(cal[1:], index=cal[:-1])
f["cal_next"] = f.date.map(nxt)
f["ovn"] = f.nopen / f.ap - 1
f.loc[~(f.nopen > 0), "ovn"] = np.nan
dist = pd.read_parquet(D + "dist.parquet"); dist["permno"] = dist.permno.astype("int64")
dk = set(zip(dist.permno, dist.exdt))   # any distribution (cash div, split, spin) on the next session
f["exnext"] = [(p, d) in dk for p, d in zip(f.permno, f.cal_next)]
dl = pd.read_parquet(D + "delist.parquet"); dl["permno"] = dl.permno.astype("int64")
dl["dlret"] = pd.to_numeric(dl.dlret, errors="coerce"); dl["dlstcd"] = pd.to_numeric(dl.dlstcd, errors="coerce")
dl["r"] = dl.dlret.fillna(pd.Series(np.where(dl.dlstcd.between(500, 584), -0.30, np.nan), index=dl.index))
dlm = dl.dropna(subset=["r"]).drop_duplicates("permno").set_index("permno").r
# delisting: next session has no bar and the name delists on the next session or before the following one -> dlret on the night
miss = f.ovn.isna() & f.cal_next.notna() & (f.ndate.isna() | (f.ndate != f.cal_next))
dd = dl.set_index("permno").dlstdt
f["dlnight"] = miss & f.permno.map(dd).between(f.date + pd.Timedelta(days=1), f.cal_next)
f.loc[f.dlnight, "ovn"] = f.permno[f.dlnight].map(dlm)
P("delisting nights scored with dlret:", int(f.dlnight.sum() - f.loc[f.dlnight, "ovn"].isna().sum()))

m = days.merge(f[["permno", "date", "ap", "ret", "ovn", "exnext"]], on=["permno", "date"], how="left")
m["flow"] = m.sflow / m.adv_sh
n0 = len(m)
m = m[m.flow.notna() & m.ovn.notna() & ~m.exnext.fillna(True)]
P(f"universe name-days {n0}; with flow & overnight return & not ex-div/split next session: {len(m)}  (dropped ex-dist nights {int(days.merge(f[['permno','date','exnext']],on=['permno','date']).exnext.sum())})")
P("overnight return sanity: mean %.1fbp median %.1fbp; |ovn|>50%%: %d" % (m.ovn.mean() * 1e4, m.ovn.median() * 1e4, (m.ovn.abs() > .5).sum()))

# ---- per-night
def nightly(m, k=0.10, ntop=None, top=False, cost=0.0004):
    rows = []
    for d, x in m.groupby("date"):
        if len(x) < 100: continue
        x = x.sort_values("flow", ascending=top is False)  # ascending => most selling first
        if top: x = x.sort_values("flow", ascending=False)
        n = ntop or int(len(x) * k); pk = x.head(n)
        rows.append((d, pk.ovn.mean() - x.ovn.mean(), pk.ovn.mean(), x.ovn.mean(), n, (pk.ret <= -0.08).mean()))
    r = pd.DataFrame(rows, columns=["date", "ex", "pick", "uni", "n", "frac_dn8"]).set_index("date")
    r["net"] = r.ex - cost
    return r
H1 = lambda r: r[r.index < "2013-01-01"]; H2 = lambda r: r[r.index >= "2013-01-01"]
def rep(tag, r, col="net"):
    s = r[col]; top5 = s.drop(s.nlargest(5).index)
    P(f"{tag}: n {len(s)}  mean {s.mean()*1e4:+.2f}bp  t {tstat(s):.2f}  median {s.median()*1e4:+.1f}bp  ex-top5 {top5.mean()*1e4:+.2f}bp  "
      f"h1 {H1(r)[col].mean()*1e4:+.2f}(t {tstat(H1(r)[col]):.1f}) h2 {H2(r)[col].mean()*1e4:+.2f}(t {tstat(H2(r)[col]):.1f})  hit {(s>0).mean():.3f}")
P("\n== PRIMARY: bottom FLOW decile (heaviest net selling), net excess vs EW universe, 2bp/side")
prim = nightly(m); rep("PRIMARY net 2bp/side", prim)
P(f"  gross excess {prim.ex.mean()*1e4:+.2f}bp; mean names/pick {prim.n.mean():.0f}; frac of picks with day ret<=-8% {prim.frac_dn8.mean():.3f}")
rep("shock net 5bp/side", nightly(m, cost=0.0010))
P("\n== decile table (FLOW decile 1=most selling; gross excess vs universe, bp/night)")
dec = []
for d, x in m.groupby("date"):
    if len(x) < 100: continue
    q = pd.qcut(x.flow.rank(method="first"), 10, labels=False); u = x.ovn.mean()
    dec.append(x.groupby(q).ovn.mean() - u)
dec = pd.DataFrame(dec); 
P(" ".join(f"D{i+1}:{dec[i].mean()*1e4:+.1f}(t{tstat(dec[i]):.1f})" for i in range(10)))
P("  Spearman(decile, mean)", round(pd.Series(dec.mean().values).corr(pd.Series(range(10)), method="spearman"), 2))
P("\n== top-FLOW decile (buy pressure; expect negative)")
rep("TOP decile net 2bp/side (long)", nightly(m, top=True))
P("== top-10-by-FLOW arm (bottom 10 names/night)"); rep("BOTTOM-10 net 2bp/side", nightly(m, ntop=10))
P("\n== overlap with the night leg: excluding picks with day ret <= -8% (rough night-leg proxy; IBS not available in CRSP-only)")
m2 = m[~(m.ret <= -0.08)]; rep("PRIMARY ex day<=-8% names", nightly(m2))

P("\n== WITHIN-day-return-tercile spread (bottom FLOW decile vs tercile EW, averaged over terciles)")
rows = []
for d, x in m.groupby("date"):
    if len(x) < 150 or x.ret.notna().sum() < 150: continue
    x = x.dropna(subset=["ret"]).copy(); x["t"] = pd.qcut(x.ret.rank(method="first"), 3, labels=False)
    s = []
    for t_, y in x.groupby("t"):
        n = max(int(len(y) * .1), 1); y = y.sort_values("flow")
        s.append(y.head(n).ovn.mean() - y.ovn.mean())
    rows.append((d, np.mean(s), *s))
w = pd.DataFrame(rows, columns=["date", "w", "t0", "t1", "t2"]).set_index("date"); w["net"] = w.w - 0.0004
P(f"WITHIN-tercile spread: gross {w.w.mean()*1e4:+.2f}bp t {tstat(w.w):.2f}; net 2bp/side {w.net.mean()*1e4:+.2f}bp t {tstat(w.net):.2f}; "
  f"by tercile (loser/mid/winner) {w.t0.mean()*1e4:+.1f}/{w.t1.mean()*1e4:+.1f}/{w.t2.mean()*1e4:+.1f}bp")

# ---- gates
s = prim.net; top5 = s.drop(s.nlargest(5).index)
G = {"net excess >= +6.5bp": s.mean() * 1e4 >= 6.5, "night-clustered t >= 2": tstat(s) >= 2, "median night > 0": s.median() > 0,
     "ex-top-5 nights > 0": top5.mean() > 0, "both halves > 0": H1(prim).net.mean() > 0 and H2(prim).net.mean() > 0,
     "within-tercile spread > 0 and t >= 2": w.w.mean() > 0 and tstat(w.w) >= 2}
P("\n== GATES")
for k, v in G.items(): P(f"  {'PASS' if v else 'FAIL'}  {k}")
P("VERDICT:", "PASS" if all(G.values()) else "KILL")
open("data/research/program/late_flow_out.txt", "w").write(buf.getvalue())
