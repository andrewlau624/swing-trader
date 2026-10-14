"""Study ISO-BURST (round1_prose.md "## Study ISO-BURST"): ISO (sale cond 'F') buy bursts in large caps -> 1-10 min continuation, TAQ ms.
usage: iso_burst.py sanity DATE | build ERA [NDAYS] [NWORK] | report ERA   (cache data/research/iso_burst/ERA/)
No parameter below was changed after seeing outcomes."""
import sys, time, re
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, "research/sim")
import sect_lag as SL
from sect_lag import conn, hms, sim_trade, tstat_clustered, LIT_OK, BAD
SL.TOUT = 600
D = Path("data/research/iso_burst"); D.mkdir(parents=True, exist_ok=True)
BURST_PCT, RATIO, G, S, TOUT = 0.0025, 3.0, 20e-4, 20e-4, 600
M0, M1 = 600, 930          # boundary minute-of-day for signal end t
HZ = (60, 300, 600)
SEEDS = {"disc": (980, "2010-01-01", "2014-12-31"), "judge": (981, "2015-01-01", "2019-12-31")}

def universe(f, nm, d):
    x = f[f.date == d].dropna(subset=["adv_dv", "pclose"])
    x = x[(x.pclose >= 10) & (x.adv_dv >= 200e6)]
    nn = nm[(nm.namedt <= d) & (nm.nameendt >= d) & nm.shrcd.isin([10, 11])]
    return x[x.permno.isin(nn.permno)][["permno", "adv_dv"]].drop_duplicates("permno").set_index("permno").adv_dv

def minute_sql(vals, roots, ds):
    return f"""with u(root,sfx,pid) as (values {vals}),
t as (select u.pid, c.time_m tm, coalesce(c.tr_seqnum,0) sq, c.price p, c.size z, coalesce(c.tr_scond,'') sc
      from taqm_{ds[:4]}.ctm_{ds} c join u on u.root=c.sym_root and u.sfx=coalesce(c.sym_suffix,'')
      where c.sym_root in ({roots}) and c.time_m >= '09:30:00' and c.time_m < '15:31:00' and c.tr_corr='00' and c.price>0 and c.size>0
        and coalesce(c.tr_scond,'') !~ '{BAD}'),
d as (select *, sign(p - lag(p) over w) ds from t window w as (partition by pid order by tm, sq)),
g as (select *, count(nullif(ds,0)) over (partition by pid order by tm, sq) grp from d),
s as (select *, max(nullif(ds,0)) over (partition by pid, grp) sg from g)
select pid, floor(extract(epoch from tm)/60)::int mn,
  sum(p*z) filter (where sc ~ 'F' and sg>0) isob, sum(p*z) filter (where sc ~ 'F' and sg<0) isos,
  (array_agg(p order by tm desc, sq desc))[1] lastp, sum(p*z) tot, count(*) filter (where sc ~ 'F') niso
from s group by 1,2"""

def link(db, d, pids):
    lk = db.raw_sql(f"select sym_root,sym_suffix,permno,match_lvl from wrdsapps_link_crsp_taqm.taqmclink where date='{d:%Y-%m-%d}' and permno in ({','.join(map(str, pids))})")
    lk = lk.sort_values("match_lvl").drop_duplicates("permno"); lk["sfx"] = lk.sym_suffix.fillna(""); lk["permno"] = lk.permno.astype(int)
    return {r.permno: (r.sym_root, r.sfx) for r in lk.itertuples()}

def find_events(mm, adv, rs):
    """mm: minute table for one name (index mn). returns (buy_evt_t or None, sell_evt_t or None, ctrl_t or None). t = boundary = mn+1."""
    mm = mm.sort_values("mn")
    lp = mm.set_index("mn").lastp.astype(float)
    ret = lp / lp.shift(1) - 1
    ib = mm.set_index("mn").isob.fillna(0).astype(float); isl = mm.set_index("mn").isos.fillna(0).astype(float)
    thr = BURST_PCT * adv
    buy = (ib >= thr) & (ib >= RATIO * isl) & (ret > 0)
    sell = (isl >= thr) & (isl >= RATIO * ib) & (ret < 0)
    inwin = pd.Series((lp.index + 1 >= M0) & (lp.index + 1 <= M1), index=lp.index)
    bt = lp.index[buy & inwin]; st = lp.index[sell & inwin]
    anyb = set(lp.index[((ib >= thr) | (isl >= thr))])   # control: no burst of either side
    cand = [m for m in range(M0 - 1, M1) if m not in anyb and m in lp.index]
    return (int(bt[0]) + 1 if len(bt) else None, int(st[0]) + 1 if len(st) else None,
            int(cand[rs.randint(len(cand))]) + 1 if cand else None)

def build_day(db, d, f, nm):
    fn = D / "trades" / f"{d:%Y%m%d}.parquet"
    if fn.exists(): return "cached"
    fn.parent.mkdir(exist_ok=True)
    u = universe(f, nm, d); ds = d.strftime("%Y%m%d")
    sym = link(db, d, list(u.index)) if len(u) else {}
    if not sym: pd.DataFrame().to_parquet(fn); return "no names"
    vals = ",".join("('%s','%s',%d)" % (r.replace("'", "''"), s.replace("'", "''"), p) for p, (r, s) in sym.items())
    roots = ",".join("'%s'" % r.replace("'", "''") for r in sorted({v[0] for v in sym.values()}))
    mm = db.raw_sql(minute_sql(vals, roots, ds)); mm["pid"] = mm.pid.astype(int)
    rs = np.random.RandomState(int(ds) % 2**31)
    wins = []; nsig_all = 0
    for p, g in mm.groupby("pid"):
        b, s_, c = find_events(g, float(u[p]), rs)
        gg = g.set_index("mn")
        for arm, t in (("buy", b), ("sell", s_), ("ctrl", c)):
            if t is None: continue
            row = gg.loc[t - 1] if (t - 1) in gg.index else None
            wins.append(dict(pid=p, arm=arm, t=t, adv=float(u[p]), isob=float(row.isob) if row is not None and pd.notna(row.isob) else 0.0,
                             isos=float(row.isos) if row is not None and pd.notna(row.isos) else 0.0))
    if not wins: pd.DataFrame().to_parquet(fn); return "no signals"
    W = pd.DataFrame(wins).reset_index(drop=True); W["wid"] = W.index
    wv = ",".join("('%s','%s',%d,%s::time,%s::time)" % (sym[r.pid][0].replace("'", "''"), sym[r.pid][1].replace("'", "''"), r.wid,
                  "'" + hms(r.t * 60 - 60) + "'", "'" + hms(r.t * 60 + 1 + TOUT + 6) + "'") for r in W.itertuples())
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
        row = dict(date=d, wid=w.wid, pid=w.pid, arm=w.arm, t=w.t, adv=w.adv, isob=w.isob, isos=w.isos, G=G, S=S, ask0=ask0, mid0=mid0, spr0=(ask0 - bid0) / mid0)
        def mid_at(x):
            k = np.searchsorted(qt, x, side="right") - 1
            return (qb[k] + qa[k]) / 2
        for h in HZ: row[f"drift{h}"] = mid_at(te + h) / mid0 - 1
        if w.arm != "sell":
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
    return f"ok {len(rows)} (buy {sum(r['arm']=='buy' for r in rows)} sell {sum(r['arm']=='sell' for r in rows)} ctrl {sum(r['arm']=='ctrl' for r in rows)}) names {len(sym)}"

def era_days(era):
    seed, a, b = SEEDS[era]
    f = pd.read_parquet("data/research/late_flow/dsf.parquet", columns=["date"])
    alld = [pd.Timestamp(x) for x in sorted(f.date.unique())]
    return [x for x in alld if pd.Timestamp(a) <= x <= pd.Timestamp(b)], seed

_G = {}
def _work(d):
    try:
        if "db" not in _G:
            import late_flow_univ as U
            f = U.load(); _G["p"] = (f[f.date >= "2009-10-01"], U.names()); _G["db"] = conn()
        return d, build_day(_G["db"], d, *_G["p"])
    except Exception:
        _G.pop("db", None)
        import traceback; return d, "ERR " + traceback.format_exc()[-500:]

def build(era, ndays=100, nwork=2):
    from concurrent.futures import ProcessPoolExecutor
    ed, seed = era_days(era)
    rs = np.random.RandomState(seed)
    sel = [ed[k] for k in sorted(rs.choice(len(ed), size=min(ndays, len(ed)), replace=False))]
    (D / f"{era}_days.txt").write_text("\n".join(f"{d:%Y-%m-%d}" for d in sel))
    t0 = time.time(); n = 0
    with ProcessPoolExecutor(nwork) as ex:
        for d, st in ex.map(_work, sel):
            n += 1; print(f"{d:%Y-%m-%d} {st}  [{n}/{len(sel)} {time.time()-t0:.0f}s]", flush=True)

# ---------------- report ----------------
def summarize(x, label, ndays, out):
    if len(x) == 0: out.append(f"{label}: n=0"); return
    x = x.copy(); bp = 1e4
    x["net1"] = x.pess_ret; x["net2"] = x.pess_ret - x.spr0; x["gross"] = x.pess_ret + x.pess_c
    x["opt1"] = x.opt_ret; x["opt2"] = x.opt_ret - x.spr0
    x["pstar"] = (x.S + x.pess_c) / (x.G + x.S)
    tp = x.pess_kind == "TP"; sl = x.pess_kind == "SL"
    top5 = x.net1.sort_values(ascending=False).index[:5]
    out.append(f"{label}: n={len(x)} days={x.date.nunique()}/{ndays} trades/day={len(x)/ndays:.2f}")
    out.append(f"  pess: gross {x.gross.mean()*bp:+.2f}bp  net1x {x.net1.mean()*bp:+.2f}bp (t {tstat_clustered(x,'net1'):.2f})  net2x {x.net2.mean()*bp:+.2f}bp (t {tstat_clustered(x,'net2'):.2f})  median net1 {x.net1.median()*bp:+.1f}  ex-top5 net1 {x.drop(top5).net1.mean()*bp:+.2f}  ex-top5 net2 {x.drop(top5).net2.mean()*bp:+.2f}")
    out.append(f"  opt : net1x {x.opt1.mean()*bp:+.2f}bp (t {tstat_clustered(x,'opt1'):.2f})  net2x {x.opt2.mean()*bp:+.2f}bp (t {tstat_clustered(x,'opt2'):.2f})")
    out.append(f"  c (measured, entry-half + exit-half) = {x.pess_c.mean()*bp:.2f}bp  mean entry quoted spread {x.spr0.mean()*bp:.2f}bp  G=S {x.G.mean()*bp:.0f}bp")
    out.append(f"  p(TP/all) {tp.mean():.3f}  p(TP/(TP+SL)) {tp.sum()/max(1,(tp|sl).sum()):.3f}  p*(mean) {x.pstar.mean():.3f}  p-p* {tp.mean()-x.pstar.mean():+.3f}  exits TP/SL/TO = {tp.sum()}/{sl.sum()}/{(x.pess_kind=='TO').sum()}  net>0 rate {(x.net1>0).mean():.3f}")

def drift_lines(X, out, ndays):
    bp = 1e4
    B = X[X.arm == "buy"]; C = X[X.arm == "ctrl"]; Sx = X[X.arm == "sell"]
    out.append("-- mid drift from t+1s (bp, gross mid-to-mid)")
    for h in HZ:
        c = f"drift{h}"
        out.append(f"  +{h//60}m: buy {B[c].mean()*bp:+.2f} (t {tstat_clustered(B,c):.2f}, n {len(B)})  ctrl {C[c].mean()*bp:+.2f} (n {len(C)})  sell-mirror {Sx[c].mean()*bp:+.2f} (n {len(Sx)}, t {tstat_clustered(Sx,c):.2f})")
        # matched: same name same day
        m = B.merge(C[["date", "pid", c]], on=["date", "pid"], suffixes=("", "_c"))
        m["diff"] = m[c] - m[c + "_c"]
        out.append(f"       matched buy-minus-ctrl (same name-day, n {len(m)}): {m['diff'].mean()*bp:+.2f}bp  day-clustered t {tstat_clustered(m,'diff'):.2f}")
        ms = Sx.merge(C[["date", "pid", c]], on=["date", "pid"], suffixes=("", "_c")); ms["diff"] = -(ms[c] - ms[c + "_c"])
        out.append(f"       matched sell-mirror (sign flipped) minus ctrl (n {len(ms)}): {ms['diff'].mean()*bp:+.2f}bp t {tstat_clustered(ms,'diff'):.2f}")

def report(era):
    seed = SEEDS[era][0]
    days = (D / f"{era}_days.txt").read_text().split(); nd = len(days)
    fs = [pd.read_parquet(p) for p in sorted((D / "trades").glob("*.parquet")) if p.stem in {d.replace("-", "") for d in days}]
    X = pd.concat([f for f in fs if len(f)]); X["date"] = pd.to_datetime(X.date)
    out = [f"ISO-BURST {era} era report; days sampled {nd} (seed {seed}); days with rows {X.date.nunique()}"]
    L = X[X.arm == "buy"].copy()
    summarize(L, "== LONG TRADES (buy bursts)", nd, out)
    drift_lines(X, out, nd)
    mid = pd.Timestamp("2012-07-01") if era == "disc" else pd.Timestamp("2017-07-01")
    L["half"] = np.where(L.date < mid, "H1", "H2")
    out.append(f"-- halves (split at {mid:%Y-%m-%d})")
    for h, g in L.groupby("half"): summarize(g, f"  half {h}", nd, out)
    out.append("-- by time of day (signal minute)")
    L["tod"] = pd.cut(L.t / 60, [10, 11, 12, 13, 14, 15, 15.6], right=False)
    for k, g in L.groupby("tod", observed=True): summarize(g, f"  hour {k}", nd, out)
    out.append("-- by 20d median $vol bucket ($M)")
    L["vb"] = pd.cut(L.adv / 1e6, [0, 400, 800, 2000, 1e9])
    for k, g in L.groupby("vb", observed=True): summarize(g, f"  advM {k}", nd, out)
    return "\n".join(out), X

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "build": build(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 100, int(sys.argv[4]) if len(sys.argv) > 4 else 2)
    elif cmd == "sanity":
        import late_flow_univ as U
        db = conn(); f = U.load(); f = f[f.date >= "2009-10-01"]; nm = U.names(); d = pd.Timestamp(sys.argv[2])
        t0 = time.time(); print(build_day(db, d, f, nm), f"{time.time()-t0:.0f}s")
    elif cmd == "report":
        t, _ = report(sys.argv[2]); print(t)
