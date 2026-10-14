"""Study RETAIL-HERD (round1_prose.md "## Study RETAIL-HERD"): first-hour BJZZ retail buy imbalance -> 10:30 long scalp, TAQ ms.
usage: retail_herd.py sanity DATE | build ERA [NDAYS] | report ERA | all   (cache data/research/retail_herd/ERA/)
No parameter below was changed after seeing outcomes.
Disclosed choices (most conservative reading):
 - 09:30->10:30 return = last eligible trade (<10:30:00, scond not in BAD) / first eligible trade (>=09:30:00) - 1.
 - Retail $ = ex 'D', price>=1, tr_corr '00', no scond filter; Z = (round(p*1e4) mod 100)/100; buy .6<Z<1, sell 0<Z<.4.
 - Control (a): same universe/floor, RIB<=0, top 5 by return (no return>0 requirement). Control (b): same picks entered 11:30:01.
 - Universe inputs strictly before d (late_flow_univ: adv_dv/pclose shifted 1 day); exchanges all; shrcd 10/11."""
import sys, time
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, "research/sim")
import sect_lag as SL
from sect_lag import conn, hms, sim_trade, tstat_clustered, LIT_OK, BAD
T_SIM = 3600
SL.TOUT = T_SIM
D = Path("data/research/retail_herd"); D.mkdir(parents=True, exist_ok=True)
OUT = Path("data/research/program/retail_herd_out.txt")
G, S = 40e-4, 40e-4
RETAIL_MIN, RIB_MIN, TOPN = 0.005, 0.5, 5
ADV_LO, ADV_HI = 50e6, 1e9
HZ = (300, 900, 1800, 3600)
SEEDS = {"disc": (982, "2010-01-01", "2014-12-31"), "judge": (983, "2015-01-01", "2019-12-31")}
ENTRY_MIN = 10 * 60 + 30   # 10:30 boundary; shift arm 11:30

def universe(f, nm, d):
    x = f[f.date == d].dropna(subset=["adv_dv", "pclose"])
    x = x[(x.pclose >= 5) & (x.adv_dv >= ADV_LO) & (x.adv_dv <= ADV_HI)]
    nn = nm[(nm.namedt <= d) & (nm.nameendt >= d) & nm.shrcd.isin([10, 11])]
    return x[x.permno.isin(nn.permno)][["permno", "adv_dv"]].drop_duplicates("permno").set_index("permno").adv_dv

def link(db, d, pids):
    lk = db.raw_sql(f"select sym_root,sym_suffix,permno,match_lvl from wrdsapps_link_crsp_taqm.taqmclink where date='{d:%Y-%m-%d}' and permno in ({','.join(map(str, pids))})")
    lk = lk.sort_values("match_lvl").drop_duplicates("permno"); lk["sfx"] = lk.sym_suffix.fillna(""); lk["permno"] = lk.permno.astype(int)
    return {r.permno: (r.sym_root, r.sfx) for r in lk.itertuples()}

def hour_sql(vals, roots, ds):
    """09:30:00 <= time_m < 10:30:00 ONLY: nothing at/after the decision time."""
    return f"""with u(root,sfx,pid) as (values {vals}),
t as (select u.pid, c.time_m tm, coalesce(c.tr_seqnum,0) sq, c.price p, c.size z, coalesce(c.tr_scond,'') sc, c.ex ex,
        mod(round(c.price*10000)::bigint, 100)/100.0 zf
      from taqm_{ds[:4]}.ctm_{ds} c join u on u.root=c.sym_root and u.sfx=coalesce(c.sym_suffix,'')
      where c.sym_root in ({roots}) and c.time_m >= '09:30:00' and c.time_m < '10:30:00' and c.tr_corr='00' and c.price>0 and c.size>0)
select pid,
  sum(p*z) filter (where ex='D' and p>=1 and zf>0.6 and zf<1) rb,
  sum(p*z) filter (where ex='D' and p>=1 and zf>0 and zf<0.4) rs,
  sum(p*z) filter (where ex='D') dtot, sum(p*z) tot,
  count(*) filter (where ex='D' and zf>0) nsub, count(*) filter (where ex='D') nd,
  (array_agg(p order by tm, sq) filter (where sc !~ '{BAD}'))[1] p0,
  (array_agg(p order by tm desc, sq desc) filter (where sc !~ '{BAD}'))[1] p1
from t group by 1"""

def build_day(db, d, f, nm):
    fn = D / "trades" / f"{d:%Y%m%d}.parquet"
    if fn.exists(): return "cached"
    fn.parent.mkdir(parents=True, exist_ok=True); (D / "cov").mkdir(exist_ok=True)
    u = universe(f, nm, d); ds = d.strftime("%Y%m%d")
    sym = link(db, d, list(u.index)) if len(u) else {}
    if not sym: pd.DataFrame().to_parquet(fn); return "no names"
    vals = ",".join("('%s','%s',%d)" % (r.replace("'", "''"), s.replace("'", "''"), p) for p, (r, s) in sym.items())
    roots = ",".join("'%s'" % r.replace("'", "''") for r in sorted({v[0] for v in sym.values()}))
    h = db.raw_sql(hour_sql(vals, roots, ds)); h["pid"] = h.pid.astype(int)
    for c in ("rb", "rs", "dtot", "tot", "p0", "p1"): h[c] = pd.to_numeric(h[c], errors="coerce").astype(float)
    h["rb"] = h.rb.fillna(0); h["rs"] = h.rs.fillna(0)
    h["adv"] = h.pid.map(u).astype(float); h["rt"] = h.rb + h.rs
    h["rib"] = np.where(h.rt > 0, (h.rb - h.rs) / h.rt, np.nan); h["ret"] = h.p1 / h.p0 - 1
    fl = h[(h.rt >= RETAIL_MIN * h.adv) & h.ret.notna()]
    sig = fl[(fl.rib >= RIB_MIN) & (fl.ret > 0)].sort_values(["rib", "rt"], ascending=False).head(TOPN)
    ctl = fl[fl.rib <= 0].sort_values("ret", ascending=False).head(TOPN)
    pd.DataFrame([dict(date=d, n_univ=len(u), n_linked=len(sym), n_traded=len(h), n_floor=len(fl), n_sig=int(((fl.rib >= RIB_MIN) & (fl.ret > 0)).sum()),
        n_ctrl_elig=int((fl.rib <= 0).sum()), med_rt_adv=float((h.rt / h.adv).median()), med_dshare=float((h.dtot / h.tot).median()),
        med_rt_dshare=float((h.rt / h.dtot).median()), med_nsub=float(h.nsub.median()), n_buy0=int((h.rb == 0).sum()), n_sell0=int((h.rs == 0).sum()))]).to_parquet(D / "cov" / f"{d:%Y%m%d}.parquet")
    wins = []
    for arm, g in (("herd", sig), ("ctrl", ctl), ("shift", sig)):
        for r in g.itertuples():
            wins.append(dict(pid=r.pid, arm=arm, t=ENTRY_MIN + (60 if arm == "shift" else 0), adv=r.adv, rb=r.rb, rs=r.rs, rib=r.rib, ret1h=r.ret))
    if not wins: pd.DataFrame().to_parquet(fn); return f"no signals (floor {len(fl)})"
    W = pd.DataFrame(wins).reset_index(drop=True); W["wid"] = W.index
    wv = ",".join("('%s','%s',%d,%s::time,%s::time)" % (sym[r.pid][0].replace("'", "''"), sym[r.pid][1].replace("'", "''"), r.wid,
                  "'" + hms(r.t * 60 - 60) + "'", "'" + hms(r.t * 60 + 1 + T_SIM + 6) + "'") for r in W.itertuples())
    rts = ",".join("'%s'" % r.replace("'", "''") for r in sorted({sym[p][0] for p in W.pid}))
    qs = db.raw_sql(f"""with w(root,sfx,wid,a,b) as (values {wv})
        select w.wid, n.time_m tm, n.best_bid bb, n.best_ask ba from taqm_{ds[:4]}.complete_nbbo_{ds} n
        join w on w.root=n.sym_root and w.sfx=coalesce(n.sym_suffix,'') and n.time_m>=w.a and n.time_m<=w.b
        where n.sym_root in ({rts}) and n.best_bid>0 and n.best_ask>n.best_bid order by w.wid, n.time_m""")
    ts = db.raw_sql(f"""with w(root,sfx,wid,a,b) as (values {wv})
        select w.wid, c.time_m tm, c.price p, c.size z, c.ex, coalesce(c.tr_scond,'') sc from taqm_{ds[:4]}.ctm_{ds} c
        join w on w.root=c.sym_root and w.sfx=coalesce(c.sym_suffix,'') and c.time_m>=w.a and c.time_m<=w.b
        where c.sym_root in ({rts}) and c.tr_corr='00' and c.price>0 and c.size>0 order by w.wid, c.time_m""")
    def secs(x): return pd.to_timedelta(x.astype(str)).dt.total_seconds().values if len(x) else np.array([])
    qs["ts"] = secs(qs.tm); ts["ts"] = secs(ts.tm)
    ts = ts[~ts.sc.str.contains(BAD)]
    ts["lit"] = (ts.ex != "D") & (ts.z >= 100) & ts.sc.apply(lambda s: bool(LIT_OK.match(s)))
    qg = {k: v for k, v in qs.groupby("wid")}; tg = {k: v for k, v in ts.groupby("wid")}
    rows = []
    for w in W.itertuples():
        if w.wid not in qg: continue
        q = qg[w.wid]; qt = q.ts.values; qb = q.bb.astype(float).values; qa = q.ba.astype(float).values
        te = w.t * 60 + 1.0
        j = np.searchsorted(qt, te, side="right") - 1
        if j < 0: continue
        ask0, bid0 = qa[j], qb[j]; mid0 = (ask0 + bid0) / 2
        row = dict(date=d, wid=w.wid, pid=w.pid, arm=w.arm, t=w.t, adv=w.adv, rb=w.rb, rs=w.rs, rib=w.rib, ret1h=w.ret1h, G=G, S=S, ask0=ask0, mid0=mid0, spr0=(ask0 - bid0) / mid0)
        def mid_at(x):
            k = np.searchsorted(qt, x, side="right") - 1
            return (qb[k] + qa[k]) / 2
        for hh in HZ: row[f"drift{hh}"] = mid_at(te + hh) / mid0 - 1
        if w.wid in tg:
            tr = tg[w.wid]; tt = tr.ts.values; tp = tr.p.astype(float).values; tz = tr.z.values; tl = tr.lit.values
        else:
            tt = tp = tz = np.array([]); tl = np.array([], bool)
        r = sim_trade(te, ask0, G, S, qt, qb, qa, tt, tp, tz, tl, np.ones(len(tt), bool))
        for m in ("pess", "opt"):
            o = r[m]
            row.update({f"{m}_kind": o["kind"], f"{m}_ret": o["ret"], f"{m}_mid_ret": o["mid_x"] / mid0 - 1,
                        f"{m}_c": (ask0 - mid0) / mid0 + (o["mid_x"] - o["px"]) / o["mid_x"], f"{m}_tx": o["tx"] - te})
        rows.append(row)
    pd.DataFrame(rows).to_parquet(fn)
    return f"ok {len(rows)} (herd {sum(r['arm']=='herd' for r in rows)} ctrl {sum(r['arm']=='ctrl' for r in rows)} shift {sum(r['arm']=='shift' for r in rows)}) names {len(sym)} floor {len(fl)}"

def era_days(era):
    seed, a, b = SEEDS[era]
    f = pd.read_parquet("data/research/late_flow/dsf.parquet", columns=["date"])
    alld = [pd.Timestamp(x) for x in sorted(f.date.unique())]
    return [x for x in alld if pd.Timestamp(a) <= x <= pd.Timestamp(b)], seed

def build(era, ndays=100):
    import late_flow_univ as U
    ed, seed = era_days(era)
    rs = np.random.RandomState(seed)
    sel = [ed[k] for k in sorted(rs.choice(len(ed), size=min(ndays, len(ed)), replace=False))]
    (D / f"{era}_days.txt").write_text("\n".join(f"{d:%Y-%m-%d}" for d in sel))
    f = U.load(); f = f[f.date >= "2009-10-01"]; nm = U.names(); db = conn(); t0 = time.time()
    for n, d in enumerate(sel, 1):
        try: st = build_day(db, d, f, nm)
        except Exception:
            import traceback; st = "ERR " + traceback.format_exc()[-400:]
            try: db.close()
            except Exception as e: print(f"close of broken connection failed (reconnecting anyway): {e!r}", flush=True)
            db = conn()
        print(f"{d:%Y-%m-%d} {st}  [{n}/{len(sel)} {time.time()-t0:.0f}s]", flush=True)

# ---------------- report ----------------
def summ(x, label, nd, out):
    if len(x) == 0: out.append(f"{label}: n=0"); return
    x = x.copy(); bp = 1e4
    x["net1"] = x.pess_ret; x["net2"] = x.pess_ret - x.spr0; x["gross"] = x.pess_ret + x.pess_c
    x["opt1"] = x.opt_ret; x["opt2"] = x.opt_ret - x.spr0; x["pstar"] = (x.S + x.pess_c) / (x.G + x.S)
    tp = x.pess_kind == "TP"; sl = x.pess_kind == "SL"
    top5 = x.net1.sort_values(ascending=False).index[:5]
    out.append(f"{label}: n={len(x)} days={x.date.nunique()}/{nd} trades/day={len(x)/nd:.2f}")
    out.append(f"  pess: gross {x.gross.mean()*bp:+.2f}bp  net1x {x.net1.mean()*bp:+.2f}bp (t {tstat_clustered(x,'net1'):.2f})  net2x {x.net2.mean()*bp:+.2f}bp (t {tstat_clustered(x,'net2'):.2f})  median net1 {x.net1.median()*bp:+.1f}  ex-top5 net1 {x.drop(top5).net1.mean()*bp:+.2f}  ex-top5 net2 {x.drop(top5).net2.mean()*bp:+.2f}")
    out.append(f"  opt : net1x {x.opt1.mean()*bp:+.2f}bp (t {tstat_clustered(x,'opt1'):.2f})  net2x {x.opt2.mean()*bp:+.2f}bp (t {tstat_clustered(x,'opt2'):.2f})")
    out.append(f"  c (measured, entry-half + exit-half) = {x.pess_c.mean()*bp:.2f}bp  mean entry quoted spread {x.spr0.mean()*bp:.2f}bp  G=S {x.G.mean()*bp:.0f}bp")
    out.append(f"  p(TP/all) {tp.mean():.3f}  p(TP/(TP+SL)) {tp.sum()/max(1,(tp|sl).sum()):.3f}  p*(mean) {x.pstar.mean():.3f}  p-p* {tp.mean()-x.pstar.mean():+.3f}  exits TP/SL/TO = {tp.sum()}/{sl.sum()}/{(x.pess_kind=='TO').sum()}  net>0 rate {(x.net1>0).mean():.3f}")

def report(era):
    seed = SEEDS[era][0]
    days = (D / f"{era}_days.txt").read_text().split(); nd = len(days); ds = {d.replace("-", "") for d in days}
    fs = [pd.read_parquet(p) for p in sorted((D / "trades").glob("*.parquet")) if p.stem in ds]
    X = pd.concat([f for f in fs if len(f)]); X["date"] = pd.to_datetime(X.date)
    out = [f"RETAIL-HERD {era} era report; days sampled {nd} (seed {seed}); days with rows {X.date.nunique()}", f"G=S={G*1e4:.0f}bp T={T_SIM//60}m top{TOPN}"]
    H = X[X.arm == "herd"].reset_index(drop=True); C = X[X.arm == "ctrl"].reset_index(drop=True); Sh = X[X.arm == "shift"].reset_index(drop=True)
    summ(H, "== HERD (long, entry 10:30:01)", nd, out); summ(C, "== CONTROL (a) momentum, RIB<=0", nd, out); summ(Sh, "== CONTROL (b) +60m shift (same picks, 11:30:01)", nd, out)
    bp = 1e4
    out.append("-- mid drift from entry+1s (bp, gross mid-to-mid)")
    for hh in HZ:
        c = f"drift{hh}"
        out.append(f"  +{hh//60}m: herd {H[c].mean()*bp:+.2f} (t {tstat_clustered(H,c):.2f}, n {len(H)})  ctrl(a) {C[c].mean()*bp:+.2f} (t {tstat_clustered(C,c):.2f}, n {len(C)})  shift(b) {Sh[c].mean()*bp:+.2f} (t {tstat_clustered(Sh,c):.2f}, n {len(Sh)})")
        d1 = H.groupby("date")[c].mean().sub(C.groupby("date")[c].mean(), fill_value=np.nan).dropna()
        out.append(f"       herd-minus-ctrl(a), day-level mean: {d1.mean()*bp:+.2f}bp  t {d1.mean()/(d1.std(ddof=1)/np.sqrt(len(d1))):.2f} (days {len(d1)})")
    # net difference vs control (a)
    for k in ("net1", "net2"):
        h = H.assign(v=H.pess_ret - (H.spr0 if k == "net2" else 0)); c_ = C.assign(v=C.pess_ret - (C.spr0 if k == "net2" else 0))
        dd = h.groupby("date").v.mean().sub(c_.groupby("date").v.mean(), fill_value=np.nan).dropna()
        out.append(f"-- herd {k} minus ctrl(a) {k}: {dd.mean()*bp:+.2f}bp day-level t {dd.mean()/(dd.std(ddof=1)/np.sqrt(len(dd))):.2f} (days {len(dd)})")
    mid = pd.Timestamp("2012-07-01") if era == "disc" else pd.Timestamp("2017-07-01")
    H["half"] = np.where(H.date < mid, "H1", "H2")
    out.append(f"-- halves (split at {mid:%Y-%m-%d})")
    for k, g in H.groupby("half"): summ(g, f"  half {k}", nd, out)
    cv = pd.concat([pd.read_parquet(p) for p in sorted((D / "cov").glob("*.parquet")) if p.stem in ds])
    out.append("-- retail $ coverage (per-day, mean over days)")
    out.append("  " + "  ".join(f"{c} {cv[c].mean():.3f}" for c in cv.columns if c != "date") + f"  days {len(cv)}")
    out.append(f"  herd retail $ mean {(H.rb+H.rs).mean():,.0f}  rb>0&rs>0 share {((H.rb>0)&(H.rs>0)).mean():.3f}  median rib {H.rib.median():.2f}  median adv ${H.adv.median()/1e6:.0f}M")
    return "\n".join(out)

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "build": build(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 100)
    elif cmd == "sanity":
        import late_flow_univ as U
        db = conn(); f = U.load(); f = f[f.date >= "2009-10-01"]; nm = U.names(); d = pd.Timestamp(sys.argv[2])
        u = universe(f, nm, d); sym = link(db, d, list(u.index)); ds = d.strftime("%Y%m%d")
        vals = ",".join("('%s','%s',%d)" % (r, s, p) for p, (r, s) in sym.items()); roots = ",".join("'%s'" % r for r in sorted({v[0] for v in sym.values()}))
        t0 = time.time(); h = db.raw_sql(hour_sql(vals, roots, ds)); print(len(u), len(sym), len(h), f"{time.time()-t0:.0f}s")
        for c in ("rb", "rs", "dtot", "tot", "p0", "p1"): h[c] = pd.to_numeric(h[c], errors="coerce")
        h["adv"] = h.pid.astype(int).map(u).astype(float)
        print(h.describe().T[["count", "mean", "50%", "min"]]); print("share both rb,rs>0:", ((h.rb > 0) & (h.rs > 0)).mean(), "min price", h[["p0", "p1"]].min().min())
        print(h.assign(rt_adv=(h.rb.fillna(0)+h.rs.fillna(0))/h.adv).rt_adv.describe())
        print(build_day(db, d, f, nm))
    elif cmd == "report":
        t = report(sys.argv[2]); print(t)
