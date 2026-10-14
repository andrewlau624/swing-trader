"""Study LEVEL-BOUNCE (round1_prose.md "## Study LEVEL-BOUNCE"): QUIET first touch of the prior-day low in $50M-$500M names -> long reversal scalp, TAQ ms.
usage: level_bounce.py sanity DATE | build ERA [NDAYS] | report ERA   (cache data/research/level_bounce/)
Derived from stop_run.py. Single WRDS connection, sequential. No parameter below was changed after seeing outcomes.
Disclosed choices (most conservative reading):
 - Quiet: mean per-minute volume over minutes m..m+2 < 1.5 x mean per-minute volume 09:30..m-1 (per-minute-rate reading, as STOP-RUN).
   Burst control (a): same breach with rate >= 3x. Breach needs lit session low before m > PDL (a pre-10:00 breach disqualifies the name-day).
 - Decision t = (m+4)*60 s; entry NBBO ask at t+1s; G=S=40bp, T=30min; pess/opt fills, c, 2x cost exactly as STOP-RUN/ISO-BURST.
 - PDL/PDH: prior CRSP trading day, 09:30-16:00 lit regular trades (tr_corr 00, size>=100, ex<>D, scond in [@F ]*). Volume = all regular non-BAD trades.
 - Ctrl (b): first minute with low <= PDL*1.005*(1-.001) with session low before m > PDL*1.005, quiet (<1.5x), traded like the event.
 - Ctrl (c): per event name-day, ONE random minute in [10:00,15:00) (RandomState(seed*100003+date ordinal+permno)), no level, drift only
   (not traded; same t=(m+4)*60 and entry +1s). Matched to the event on name-day.
 - Mirror 'mir': PDH quiet breach (hi >= PDH*1.001, session high before m < PDH), drift only; sign-check = -drift expected positive if symmetric.
 - Universe inputs strictly before d (late_flow_univ), common shrcd 10/11, pclose >= 5, 20d median $vol in [50M, 500M].
 - Day-level mean diff t for 'beats (b)/(c) on +30m drift' = t of per-day mean differences (event day mean minus control day mean)."""

import sys, time
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, "research/sim")
import sect_lag as SL
from sect_lag import conn, hms, tstat_clustered, LIT_OK, BAD
import iso_burst as IB
from iso_burst import link, summarize
SL.TOUT = 1800
from sect_lag import sim_trade
D = Path("data/research/level_bounce"); (D / "trades").mkdir(parents=True, exist_ok=True)
G = S = 40e-4; TOUT = 1800; BR = 0.001; FP, FPC = 3.0, 1.5; HZ = (60, 300, 900, 1800)
SEEDS = {"disc": (988, "2010-01-01", "2014-12-31"), "judge": (989, "2015-01-01", "2019-12-31")}
LITSQL = "c.ex <> 'D' and c.size >= 100 and coalesce(c.tr_scond,'') ~ '^[@F ]*$'"

SEEDS_ERA = 988

def universe(f, nm, d):
    x = f[f.date == d].dropna(subset=["adv_dv", "pclose"])
    x = x[(x.pclose >= 5) & (x.adv_dv >= 50e6) & (x.adv_dv < 500e6)]
    nn = nm[(nm.namedt <= d) & (nm.nameendt >= d) & nm.shrcd.isin([10, 11])]
    return x[x.permno.isin(nn.permno)][["permno", "adv_dv"]].drop_duplicates("permno").set_index("permno").adv_dv

def minute_sql(vals, roots, ds):
    return f"""with u(root,sfx,pid) as (values {vals})
select u.pid, floor(extract(epoch from c.time_m)/60)::int mn,
  min(c.price) filter (where {LITSQL}) lo, max(c.price) filter (where {LITSQL}) hi, sum(c.size) vol
from taqm_{ds[:4]}.ctm_{ds} c join u on u.root=c.sym_root and u.sfx=coalesce(c.sym_suffix,'')
where c.sym_root in ({roots}) and c.time_m >= '09:30:00' and c.time_m < '15:05:00' and c.tr_corr='00' and c.price>0 and c.size>0
  and coalesce(c.tr_scond,'') !~ '{BAD}'
group by 1,2"""

def prior_sql(vals, roots, ds):
    return f"""with u(root,sfx,pid) as (values {vals})
select u.pid, min(c.price) filter (where {LITSQL}) pdl, max(c.price) filter (where {LITSQL}) pdh
from taqm_{ds[:4]}.ctm_{ds} c join u on u.root=c.sym_root and u.sfx=coalesce(c.sym_suffix,'')
where c.sym_root in ({roots}) and c.time_m >= '09:30:00' and c.time_m < '16:00:00' and c.tr_corr='00' and c.price>0 and c.size>0
  and coalesce(c.tr_scond,'') !~ '{BAD}'
group by 1"""

def find_events(g, pdl, pdh, upto=None):
    """g: minute table of one name (mn, lo, hi, vol). Uses only minutes < upto when given (causality check).
    returns dict arm -> (m, ratio) for arms evt/a/b/c (first breach of each level, classified by footprint)."""
    g = g.sort_values("mn")
    if upto is not None: g = g[g.mn < upto]
    mn = g.mn.values; lo = g.lo.astype(float).values; hi = g.hi.astype(float).values; vol = g.vol.astype(float).values
    vm = dict(zip(mn, vol))
    cl = np.fmin.accumulate(np.where(np.isnan(lo), np.inf, lo)); ch = np.fmax.accumulate(np.where(np.isnan(hi), -np.inf, hi))
    res = {}
    def first(level, side):
        for i, m in enumerate(mn):
            if m < 600 or m >= 900: continue
            prev_ok = (cl[i - 1] > level) if side == "dn" else (ch[i - 1] < level) if i > 0 else True
            if i == 0: prev_ok = True
            if side == "dn":
                if not (prev_ok and lo[i] <= level * (1 - BR)): continue
            else:
                if not (prev_ok and hi[i] >= level * (1 + BR)): continue
            base = sum(vm.get(k, 0.0) for k in range(570, m)) / max(1, m - 570)
            if base <= 0: return None
            fp = np.mean([vm.get(k, 0.0) for k in (m, m + 1, m + 2)]) / base
            return int(m), float(fp)
        return None
    r = first(pdl, "dn")
    if r:
        if r[1] < FPC: res["evt"] = r
        elif r[1] >= FP: res["a"] = r
    r = first(pdl * 1.005, "dn")
    if r and r[1] < FPC: res["b"] = r
    r = first(pdh, "up")
    if r and r[1] < FPC: res["mir"] = r
    return res

def prior_day(days_all, d):
    i = days_all.index(d); return days_all[i - 1]

def prep(db, f, nm, days_all, d):
    u = universe(f, nm, d)
    sym = link(db, d, list(u.index)) if len(u) else {}
    if not sym: return None
    vals = ",".join("('%s','%s',%d)" % (r.replace("'", "''"), s.replace("'", "''"), p) for p, (r, s) in sym.items())
    roots = ",".join("'%s'" % r.replace("'", "''") for r in sorted({v[0] for v in sym.values()}))
    ds = d.strftime("%Y%m%d"); dp = prior_day(days_all, d).strftime("%Y%m%d")
    mm = db.raw_sql(minute_sql(vals, roots, ds)); mm["pid"] = mm.pid.astype(int)
    pr = db.raw_sql(prior_sql(vals, roots, dp)); pr["pid"] = pr.pid.astype(int)
    pr = pr.set_index("pid")
    return u, sym, mm, pr

def build_day(db, d, f, nm, days_all):
    fn = D / "trades" / f"{d:%Y%m%d}.parquet"
    if fn.exists(): return "cached"
    r = prep(db, f, nm, days_all, d)
    if r is None: pd.DataFrame().to_parquet(fn); return "no names"
    u, sym, mm, pr = r; ds = d.strftime("%Y%m%d")
    wins = []
    for p, g in mm.groupby("pid"):
        if p not in pr.index or pd.isna(pr.pdl[p]) or pd.isna(pr.pdh[p]): continue
        evs = find_events(g, float(pr.pdl[p]), float(pr.pdh[p]))
        for arm, (m, fp) in evs.items():
            wins.append(dict(pid=p, arm=arm, m=m, t=(m + 4) * 60, fp=fp, adv=float(u[p])))
        if "evt" in evs:
            rr = np.random.RandomState((SEEDS_ERA * 100003 + d.toordinal() + int(p)) % (2**31 - 1))
            mc = int(rr.randint(600, 900))
            wins.append(dict(pid=p, arm="c", m=mc, t=(mc + 4) * 60, fp=float("nan"), adv=float(u[p])))
    if not wins: pd.DataFrame().to_parquet(fn); return "no signals"
    W = pd.DataFrame(wins).reset_index(drop=True); W["wid"] = W.index
    wv = ",".join("('%s','%s',%d,%s::time,%s::time)" % (sym[r.pid][0].replace("'", "''"), sym[r.pid][1].replace("'", "''"), r.wid,
                  "'" + hms(r.t - 60) + "'", "'" + hms(r.t + 1 + TOUT + 6) + "'") for r in W.itertuples())
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
        te = w.t + 1.0
        j = np.searchsorted(qt, te, side="right") - 1
        if j < 0: continue
        ask0, bid0 = qa[j], qb[j]; mid0 = (ask0 + bid0) / 2
        row = dict(date=d, wid=w.wid, pid=w.pid, arm=w.arm, m=w.m, t=w.t, fp=w.fp, adv=w.adv, G=G, S=S, ask0=ask0, mid0=mid0, spr0=(ask0 - bid0) / mid0)
        def mid_at(x):
            k = np.searchsorted(qt, x, side="right") - 1
            return (qb[k] + qa[k]) / 2
        for h in HZ: row[f"drift{h}"] = mid_at(te + h) / mid0 - 1
        if w.arm in ("evt", "a", "b"):
            if w.wid in tg:
                tr = tg[w.wid]; tt = tr.ts.values; tp = tr.p.astype(float).values; tz = tr.z.values; tl = tr.lit.values
            else:
                tt = tp = tz = np.array([]); tl = np.array([], bool)
            r = sim_trade(te, ask0, G, S, qt, qb, qa, tt, tp, tz, tl, np.ones(len(tt), bool))
            for md in ("pess", "opt"):
                o = r[md]
                row.update({f"{md}_kind": o["kind"], f"{md}_ret": o["ret"], f"{md}_mid_ret": o["mid_x"] / mid0 - 1,
                            f"{md}_c": (ask0 - mid0) / mid0 + (o["mid_x"] - o["px"]) / o["mid_x"], f"{md}_tx": o["tx"] - te})
        rows.append(row)
    pd.DataFrame(rows).to_parquet(fn)
    cnt = {a: sum(r["arm"] == a for r in rows) for a in ("evt", "a", "b", "c", "mir")}
    return f"ok {len(rows)} {cnt} names {len(sym)}"

def load_all():
    import late_flow_univ as U
    f = U.load(); f = f[f.date >= "2009-10-01"]
    days_all = [pd.Timestamp(x) for x in sorted(f.date.unique())]
    return f, U.names(), days_all

def era_days(era, days_all):
    seed, a, b = SEEDS[era]
    return [x for x in days_all if pd.Timestamp(a) <= x <= pd.Timestamp(b)], seed

def build(era, ndays=100):
    f, nm, days_all = load_all()
    global SEEDS_ERA
    ed, seed = era_days(era, days_all); SEEDS_ERA = seed
    rs = np.random.RandomState(seed)
    sel = [ed[k] for k in sorted(rs.choice(len(ed), size=min(ndays, len(ed)), replace=False))]
    (D / f"{era}_days.txt").write_text("\n".join(f"{d:%Y-%m-%d}" for d in sel))
    db = conn(); t0 = time.time()
    for n, d in enumerate(sel, 1):
        try: st = build_day(db, d, f, nm, days_all)
        except Exception as e:
            import traceback; st = "ERR " + traceback.format_exc()[-400:]
            try: db.close()
            except Exception as e2: print(f"close of broken connection failed (reconnecting): {e2!r}", flush=True)
            db = conn()
        print(f"{d:%Y-%m-%d} {st}  [{n}/{len(sel)} {time.time()-t0:.0f}s]", flush=True)

def sanity(d):
    f, nm, days_all = load_all(); db = conn(); d = pd.Timestamp(d)
    t0 = time.time(); u, sym, mm, pr = prep(db, f, nm, days_all, d)
    print(f"{d:%Y-%m-%d} names {len(u)} linked {len(sym)} minute rows {len(mm)} prior {len(pr)} prior day {prior_day(days_all, d):%Y-%m-%d} {time.time()-t0:.0f}s")
    n = 0; bad = 0; cnt = {}
    for p, g in mm.groupby("pid"):
        if p not in pr.index or pd.isna(pr.pdl[p]): continue
        ev = find_events(g, float(pr.pdl[p]), float(pr.pdh[p]))
        for arm, (m, fp) in ev.items():
            cnt[arm] = cnt.get(arm, 0) + 1
            tr = find_events(g, float(pr.pdl[p]), float(pr.pdh[p]), upto=m + 3)   # only minutes <= m+2
            ok = arm in tr and tr[arm][0] == m and abs(tr[arm][1] - fp) < 1e-9
            bad += (not ok); n += 1
            if n <= 4: print(f"  pid {p} arm {arm} breach min {m//60}:{m%60:02d} fp {fp:.2f} pdl {pr.pdl[p]:.2f} decision t={(m+4)*60}s causal-recompute ok={ok}")
    print(f"events by arm {cnt}; causality failures {bad}/{n}")
    print("minute-table dtypes ok; max minute", int(mm.mn.max()), "min", int(mm.mn.min()))

def report(era):
    seed = SEEDS[era][0]
    days = (D / f"{era}_days.txt").read_text().split(); nd = len(days)
    fs = [pd.read_parquet(p) for p in sorted((D / "trades").glob("*.parquet")) if p.stem in {x.replace("-", "") for x in days}]
    X = pd.concat([x for x in fs if len(x)]); X["date"] = pd.to_datetime(X.date)
    out = [f"LEVEL-BOUNCE {era} era report; days sampled {nd} (seed {seed}); days with rows {X.date.nunique()}"]
    E = X[X.arm == "evt"].copy(); A = X[X.arm == "a"]; B = X[X.arm == "b"]; C = X[X.arm == "c"]; M = X[X.arm == "mir"]
    bp = 1e4
    summarize(E, "== EVENT (long, quiet first PDL touch)", nd, out)
    summarize(A, "== CONTROL (a) burst breach >=3x", nd, out)
    summarize(B, "== CONTROL (b) placebo level PDL*1.005 quiet", nd, out)
    out.append("-- mid drift from entry+1s (bp, gross mid-to-mid); (c) random minute same name-day; mirror = quiet PDH breach, raw drift (symmetric bounce would be NEGATIVE)")
    for h in HZ:
        c = f"drift{h}"
        out.append(f"  +{h//60}m: event {E[c].mean()*bp:+.2f} (t {tstat_clustered(E,c):.2f}, n {len(E)})  (a) {A[c].mean()*bp:+.2f} (t {tstat_clustered(A,c):.2f}, n {len(A)})  (b) {B[c].mean()*bp:+.2f} (t {tstat_clustered(B,c):.2f}, n {len(B)})  (c) {C[c].mean()*bp:+.2f} (t {tstat_clustered(C,c):.2f}, n {len(C)})  mirror {M[c].mean()*bp:+.2f} (t {tstat_clustered(M,c):.2f}, n {len(M)})")
        for nmc, K in (("a", A), ("b", B), ("c", C)):
            dd = E.groupby("date")[c].mean().sub(K.groupby("date")[c].mean(), fill_value=np.nan).dropna()
            if len(dd) > 2: out.append(f"       event-minus-({nmc}) day-level: {dd.mean()*bp:+.2f}bp t {dd.mean()/(dd.std(ddof=1)/np.sqrt(len(dd))):.2f} (days {len(dd)})")
        mt = E.merge(C[["date", "pid", c]], on=["date", "pid"], suffixes=("", "_c")); mt["diff"] = mt[c] - mt[c + "_c"]
        out.append(f"       event-minus-(c) matched name-day: {mt['diff'].mean()*bp:+.2f}bp day-clustered t {tstat_clustered(mt,'diff'):.2f} (n {len(mt)})")
    mid = pd.Timestamp("2012-07-01") if era == "disc" else pd.Timestamp("2017-07-01")
    E["half"] = np.where(E.date < mid, "H1", "H2")
    out.append(f"-- halves (split at {mid:%Y-%m-%d})")
    for k, g in E.groupby("half"): summarize(g, f"  half {k}", nd, out)
    out.append("-- by time of day (breach minute)")
    E["tod"] = pd.cut(E.m / 60, [10, 11, 12, 13, 14, 15], right=False)
    for k, g in E.groupby("tod", observed=True): summarize(g, f"  breach hour {k}", nd, out)
    out.append("-- by 20d median $vol sub-bucket")
    E["vb"] = pd.cut(E.adv, [50e6, 100e6, 200e6, 500e6], right=False)
    for k, g in E.groupby("vb", observed=True): summarize(g, f"  $vol {k}", nd, out)
    if len(E):
        n2 = (E.pess_ret - E.spr0).mean(); tpd = len(E) / nd
        out.append(f"-- ceiling at $10k (crude): net2x {n2*bp:+.1f}bp x {tpd:.2f} trades/day x 252 x 50% capture, full account per trade = {n2*min(tpd,12)*252*0.5*100:+.2f}pp/yr")
        out.append(f"-- EARLY KILL CHECK: n={len(E)} (<200 -> kill {len(E)<200}); net1x pess {E.pess_ret.mean()*bp:+.2f}bp (<0 -> kill {E.pess_ret.mean()<0})")
    return "\n".join(out)

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "build": build(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 100)
    elif cmd == "sanity": sanity(sys.argv[2])
    elif cmd == "report": print(report(sys.argv[2]))
