"""Study SECT-LAG (round1_prose.md "## Study SECT-LAG"): sector ETF 5-min spike -> laggard constituent catch-up scalp, TAQ ms.
usage: sect_lag.py build ERA [NDAYS] [NWORK]   (ERA = disc|judge ; per-day cache data/research/sect_lag/ERA/)
       sect_lag.py report ERA                  (aggregate to stdout)
       sect_lag.py sanity DATE                 (one-day print)
No parameter below was changed after seeing outcomes."""
import sys, time, re
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, "research/sim")
D = Path("data/research/sect_lag"); D.mkdir(parents=True, exist_ok=True)
SECT = {  # sector -> (ETF candidates in order, SIC predicate)
    "banks": (["XLF", "KRE"], lambda s: 6020 <= s <= 6029),
    "biotech": (["XBI"], lambda s: 2833 <= s <= 2836),
    "oil_gas": (["XLE"], lambda s: s in (1311, 2911) or 1381 <= s <= 1389),
    "semis": (["SMH"], lambda s: s == 3674),
    "gold": (["GDX"], lambda s: s == 1040),
    "homebuilders": (["XHB"], lambda s: 1520 <= s <= 1531),
}
ETFS = sorted({e for v in SECT.values() for e in v[0]})
K_SD, LAG_MAX, SPREAD_MAX, SPACING, MAXN, TOUT = 2.0, 0.25, 30e-4, 15, 3, 900
CTRL_MIN, SHIFT = 0.75, 60
M0, M1 = 10 * 60, 15 * 60 + 30   # signal minutes 10:00..15:30 (boundary minute-of-day)
SEEDS = {"disc": (978, "2010-01-01", "2014-12-31"), "judge": (979, "2015-01-01", "2019-12-31")}
BAD = "[OQ6MIZU]"

def conn():
    import wrds
    return wrds.Connection(wrds_username=open(Path.home() / ".pgpass").readline().split(":")[3].strip())

def hms(sec):
    sec = float(sec); h = int(sec // 3600); m = int(sec % 3600 // 60); s = sec - h * 3600 - m * 60
    return "%02d:%02d:%09.6f" % (h, m, s)

def marks_sql(d, vals, t0, t1):
    roots = ','.join(sorted({v.split("'")[1] for v in vals.split('),(')}) and ['\'%s\'' % r for r in sorted({v.split("'")[1] for v in vals.split('),(')})])
    ds = d.strftime("%Y%m%d"); y = ds[:4]
    return f"""with u(root,sfx,pid) as (values {vals}),
q as (select u.pid, (extract(epoch from n.time_m)/60)::int mn, n.time_m tm, n.best_bid bb, n.best_ask ba
      from taqm_{y}.complete_nbbo_{ds} n join u on u.root=n.sym_root and u.sfx=coalesce(n.sym_suffix,'')
      where n.sym_root in ({roots}) and n.time_m >= '{hms(t0*60)}' and n.time_m < '{hms(t1*60)}' and n.best_bid>0 and n.best_ask>n.best_bid)
select distinct on (pid, mn) pid, mn, bb, ba from q order by pid, mn, tm desc"""

def to_grid(raw, pids):
    """raw (pid,mn,bb,ba) -> dict pid -> DataFrame indexed by boundary minute m (570..931): mark = last quote with mn < m, ffilled."""
    out = {}
    idx = np.arange(9 * 60 + 25, 15 * 60 + 40)  # bucket minutes
    for pid, g in raw.groupby("pid"):
        g = g.set_index("mn")[["bb", "ba"]].astype(float).reindex(idx).ffill()
        g.index = g.index + 1  # boundary m uses bucket m-1
        g["mid"] = (g.bb + g.ba) / 2
        out[pid] = g
    return out

def etf_marks(db, d):
    vals = ",".join("('%s','',%d)" % (e, i) for i, e in enumerate(ETFS))
    raw = db.raw_sql(marks_sql(d, vals, 9 * 60 + 25, 15 * 60 + 31))
    if len(raw) == 0: return {}
    raw["pid"] = raw.pid.astype(int); g = to_grid(raw, None)
    return {ETFS[i]: v for i, v in g.items()}

def ret5(mid):
    r = mid / mid.shift(5) - 1
    return r.loc[M0:M1]

def etf_stats(db, d):
    fn = D / "etf_stats" / f"{d:%Y%m%d}.parquet"
    if fn.exists(): return pd.read_parquet(fn)
    fn.parent.mkdir(exist_ok=True)
    rows = []
    for e, g in etf_marks(db, d).items():
        r = ret5(g.mid).dropna()
        rows.append(dict(etf=e, n=len(r), sx=r.sum(), sxx=(r * r).sum()))
    df = pd.DataFrame(rows, columns=["etf", "n", "sx", "sxx"]); df.to_parquet(fn); return df

def sd_for(days, i, k=20):
    """pooled 5-min return std over the k trading days before days[i]"""
    fr = pd.concat([pd.read_parquet(D / "etf_stats" / f"{d:%Y%m%d}.parquet") for d in days[max(0, i - k):i]])
    g = fr.groupby("etf")[["n", "sx", "sxx"]].sum()
    mu = g.sx / g.n; return np.sqrt((g.sxx / g.n - mu ** 2).clip(lower=0))

# ---------------- trade simulation ----------------
LIT_OK = re.compile(r"^[@F ]*$")
def sim_trade(t_entry, ask0, G, S, qt, qb, qa, tt, tp, ts, tlit, tany):
    """arrays are numpy, already restricted to name; returns dict for pessimistic + optimistic."""
    end = t_entry + TOUT
    up = ask0 * (1 + G); dn = ask0 * (1 - S)
    out = {}
    mq = (qt > t_entry) & (qt <= end)
    qtt, qbb, qaa = qt[mq], qb[mq], qa[mq]
    mt = (tt > t_entry) & (tt <= end)
    ttt, tpp, tlitt, tanyy = tt[mt], tp[mt], tlit[mt], tany[mt]
    # last quote at/before time x
    def last_q(x):
        j = np.searchsorted(qt, x, side="right") - 1
        return (qb[j], qa[j]) if j >= 0 else (np.nan, np.nan)
    for mode in ("pess", "opt"):
        if mode == "pess":
            tp_idx = np.where(tlitt & (tpp > up))[0]
            st_idx = np.where(qbb <= dn)[0]
        else:
            tp_idx = np.where(tanyy & (tpp >= up))[0]
            st_idx = np.where((qbb + qaa) / 2 <= dn)[0]
        t_tp = ttt[tp_idx[0]] if len(tp_idx) else np.inf
        t_st = qtt[st_idx[0]] if len(st_idx) else np.inf
        if t_tp < t_st:
            kind, tx, px = "TP", t_tp, up
        elif t_st < np.inf:
            kind, tx = "SL", t_st
            b, a = last_q(tx)
            px = b if mode == "pess" else (b + a) / 2
            if mode == "pess":  # or next trade (any lit) within 5s if lower
                m5 = (ttt > tx) & (ttt <= tx + 5) & tlitt
                if m5.any(): px = min(px, tpp[m5][0])
        else:
            kind, tx = "TO", end
            b, a = last_q(end)
            px = b if mode == "pess" else (b + a) / 2
        b, a = last_q(tx); mid_x = (b + a) / 2
        out[mode] = dict(kind=kind, tx=tx, px=px, ret=px / ask0 - 1, mid_x=mid_x)
    return out

def ttt_first(ttt, tpp, m):
    return tpp[m][0]

# ---------------- per-day build ----------------
def load_panel():
    import late_flow_univ as U
    f = U.load()
    f = f[(f.date >= "2009-10-01")]
    sic = pd.read_parquet(D / "sic.parquet"); sic["permno"] = sic.permno.astype("int64"); sic["namedt"] = pd.to_datetime(sic.namedt); sic["nameendt"] = pd.to_datetime(sic.nameendt)
    return f, U.names(), sic

def sector_universe(f, nm, sic, days, i):
    """names per sector for day days[i]: all inputs strictly before d (adv/pclose via shift(1)); SIC as of prior day."""
    d = days[i]; pd_ = days[i - 1]
    x = f[f.date == d].dropna(subset=["adv_dv", "pclose"])
    x = x[(x.pclose >= 5) & (x.adv_dv >= 10e6) & (x.adv_dv <= 1e9)]
    nn = nm[(nm.namedt <= d) & (nm.nameendt >= d) & nm.shrcd.isin([10, 11])]
    x = x[x.permno.isin(nn.permno)]
    s = sic[(sic.namedt <= pd_) & (sic.nameendt >= pd_)].drop_duplicates("permno", keep="last").set_index("permno")
    x = x.assign(sic=x.permno.map(s.siccd))
    x["sic"] = x.sic.where(x.sic.notna() & (x.sic > 0), x.permno.map(s.hsiccd))
    res = {}
    for sec, (_, pred) in SECT.items():
        res[sec] = x[x.sic.apply(lambda v: bool(pd.notna(v) and pred(int(v))))].permno.astype(int).tolist()
    return res

def find_signals(g_etf, sd, grids, names, mode):
    """returns list of dict(t, etf_ret, names=[(pid, own_ret, spread)]) with spacing; mode 'lag' or 'ctrl'."""
    er = ret5(g_etf.mid)
    thr = K_SD * sd
    own = {p: ret5(grids[p].mid) for p in names if p in grids}
    sp = {p: ((grids[p].ba - grids[p].bb) / grids[p].mid) for p in own}
    used, sigs, last = set(), [], -999
    for t in er.index:
        r = er.loc[t]
        if not (r >= thr) or t - last < SPACING: continue
        cand = []
        for p, o in own.items():
            if p in used or pd.isna(o.loc[t]): continue
            ok = (o.loc[t] <= LAG_MAX * r) if mode == "lag" else (o.loc[t] >= CTRL_MIN * r)
            if ok and sp[p].loc[t] <= SPREAD_MAX: cand.append((float(o.loc[t]), p, float(sp[p].loc[t])))
        if not cand: continue
        cand.sort(); cand = cand[:MAXN]
        for _, p, _ in cand: used.add(p)
        last = t
        sigs.append(dict(t=int(t), etf_ret=float(r), names=[(p, o, s) for o, p, s in cand]))
    return sigs

def build_day(db, d, days, i, f, nm, sic, link_cache=None):
    fn = D / "trades" / f"{d:%Y%m%d}.parquet"
    if fn.exists(): return "cached"
    fn.parent.mkdir(exist_ok=True)
    sdv = sd_for(days, i)
    uni = sector_universe(f, nm, sic, days, i)
    allp = sorted({p for v in uni.values() for p in v})
    ds = d.strftime("%Y%m%d")
    em = etf_marks(db, d)
    if not allp:
        pd.DataFrame().to_parquet(fn); return "no names"
    lk = db.raw_sql(f"select sym_root,sym_suffix,permno,match_lvl from wrdsapps_link_crsp_taqm.taqmclink where date='{d:%Y-%m-%d}' and permno in ({','.join(map(str, allp))})")
    lk = lk.sort_values("match_lvl").drop_duplicates("permno")
    lk["sfx"] = lk.sym_suffix.fillna(""); lk["permno"] = lk.permno.astype(int)
    sym = {r.permno: (r.sym_root, r.sfx) for r in lk.itertuples()}
    vals = ",".join("('%s','%s',%d)" % (r.replace("'", "''"), s.replace("'", "''"), p) for p, (r, s) in sym.items())
    raw = db.raw_sql(marks_sql(d, vals, 9 * 60 + 25, 15 * 60 + 31))
    raw["pid"] = raw.pid.astype(int)
    grids = to_grid(raw, None)
    arms = {}
    for sec, (etfs, _) in SECT.items():
        e = next((x for x in etfs if x in em and x in sdv.index and sdv[x] > 0), None)
        if e is None: continue
        names = [p for p in uni[sec] if p in grids]
        for mode in ("lag", "ctrl"):
            for s in find_signals(em[e], float(sdv[e]), grids, names, mode):
                arms.setdefault((sec, e, mode), []).append(s)
    # trade windows: (pid, arm, sec, etf, sig_t, shift) -> entry at (t+shift)*60+1s
    wins = []
    for (sec, e, mode), sigs in arms.items():
        for s in sigs:
            G = min(max(0.5 * s["etf_ret"], 15e-4), 50e-4)
            for p, o, sp_ in s["names"]:
                wins.append(dict(pid=p, sec=sec, etf=e, arm=mode, t=s["t"], shift=0, etf_ret=s["etf_ret"], own=o, G=G, spr_sig=sp_))
                if mode == "lag" and s["t"] + SHIFT <= M1:  # placebo: same names, signal minute +60min, same day
                    g = grids[p]; tt = s["t"] + SHIFT
                    if g.loc[tt, "ba"] > g.loc[tt, "bb"] and (g.loc[tt, "ba"] - g.loc[tt, "bb"]) / g.loc[tt, "mid"] <= SPREAD_MAX:
                        wins.append(dict(pid=p, sec=sec, etf=e, arm="plc", t=tt, shift=SHIFT, etf_ret=s["etf_ret"], own=o, G=G, spr_sig=(g.loc[tt, "ba"] - g.loc[tt, "bb"]) / g.loc[tt, "mid"]))
    if not wins:
        pd.DataFrame().to_parquet(fn); return "no signals"
    W = pd.DataFrame(wins).reset_index(drop=True); W["wid"] = W.index
    # tick windows [t*60-120s, t*60+1+900+5+...]
    wv = ",".join("('%s','%s',%d,%s::time,%s::time)" % (sym[r.pid][0].replace("'", "''"), sym[r.pid][1].replace("'", "''"), r.wid,
                  "'" + hms(r.t * 60 - 120) + "'", "'" + hms(r.t * 60 + 1 + TOUT + 6) + "'") for r in W.itertuples())
    roots = ','.join("'%s'" % r.replace("'", "''") for r in sorted({sym[p][0] for p in W.pid}))
    qs = db.raw_sql(f"""with w(root,sfx,wid,a,b) as (values {wv})
        select w.wid, n.time_m tm, n.best_bid bb, n.best_ask ba from taqm_{ds[:4]}.complete_nbbo_{ds} n
        join w on w.root=n.sym_root and w.sfx=coalesce(n.sym_suffix,'') and n.time_m>=w.a and n.time_m<=w.b
        where n.sym_root in ({roots}) and n.best_bid>0 and n.best_ask>n.best_bid order by w.wid, n.time_m""")
    ts = db.raw_sql(f"""with w(root,sfx,wid,a,b) as (values {wv})
        select w.wid, c.time_m tm, c.price p, c.size z, c.ex, coalesce(c.tr_scond,'') sc from taqm_{ds[:4]}.ctm_{ds} c
        join w on w.root=c.sym_root and w.sfx=coalesce(c.sym_suffix,'') and c.time_m>=w.a and c.time_m<=w.b
        where c.sym_root in ({roots}) and c.tr_corr='00' and c.price>0 and c.size>0 order by w.wid, c.time_m""")
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
        S = G = w.G
        if w.wid in tg:
            tr = tg[w.wid]; tt = tr.ts.values; tp = tr.p.astype(float).values; tz = tr.z.values; tl = tr.lit.values
        else:
            tt = tp = tz = np.array([]); tl = np.array([], bool)
        r = sim_trade(te, ask0, G, S, qt, qb, qa, tt, tp, tz, tl, np.ones(len(tt), bool))
        row = dict(date=d, wid=w.wid, pid=w.pid, sec=w.sec, etf=w.etf, arm=w.arm, t=w.t, etf_ret=w.etf_ret, own=w.own, G=G, S=S,
                   ask0=ask0, mid0=mid0, spr0=(ask0 - bid0) / mid0, spr_sig=w.spr_sig)
        for m in ("pess", "opt"):
            o = r[m]
            row.update({f"{m}_kind": o["kind"], f"{m}_ret": o["ret"], f"{m}_mid_ret": o["mid_x"] / mid0 - 1,
                        f"{m}_c": (ask0 - mid0) / mid0 + (o["mid_x"] - o["px"]) / o["mid_x"], f"{m}_tx": o["tx"] - te})
        rows.append(row)
    pd.DataFrame(rows).to_parquet(fn)
    return f"ok {len(rows)}"

def era_days(era):
    seed, a, b = SEEDS[era]
    f = pd.read_parquet("data/research/late_flow/dsf.parquet", columns=["date"])
    alld = [pd.Timestamp(x) for x in sorted(f.date.unique())]
    return alld, [x for x in alld if pd.Timestamp(a) <= x <= pd.Timestamp(b)], seed

_G = {}
def _work(args):
    d, i, days = args
    try:
        if "db" not in _G:
            _G["db"] = conn(); _G["p"] = load_panel()
        f, nm, sic = _G["p"]
        for k in range(max(1, i - 20), i): etf_stats(_G["db"], days[k])
        return d, build_day(_G["db"], d, days, i, f, nm, sic)
    except Exception as e:
        _G.pop("db", None)
        import traceback; return d, "ERR " + traceback.format_exc()[-400:]

def build(era, ndays=120, nwork=2, only=None):
    from concurrent.futures import ProcessPoolExecutor
    alld, ed, seed = era_days(era)
    rs = np.random.RandomState(seed)
    pick = sorted(rs.choice(len(ed), size=min(ndays, len(ed)), replace=False))
    sel = [ed[k] for k in pick]
    if only: sel = [d for d in sel if d in only]
    jobs = [(d, alld.index(d), alld) for d in sel]
    t0 = time.time(); n = 0
    with ProcessPoolExecutor(nwork) as ex:
        for d, st in ex.map(_work, jobs):
            n += 1; print(f"{d:%Y-%m-%d} {st}  [{n}/{len(jobs)} {time.time()-t0:.0f}s]", flush=True)
    (D / f"{era}_days.txt").write_text("\n".join(f"{d:%Y-%m-%d}" for d in sel))

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "build":
        build(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 120, int(sys.argv[4]) if len(sys.argv) > 4 else 2)
    elif cmd == "sanity":
        d = pd.Timestamp(sys.argv[2]); alld = [pd.Timestamp(x) for x in sorted(pd.read_parquet("data/research/late_flow/dsf.parquet", columns=["date"]).date.unique())]
        db = conn(); f, nm, sic = load_panel(); i = alld.index(d)
        for k in range(i - 20, i): etf_stats(db, alld[k])
        print(build_day(db, d, alld, i, f, nm, sic))

# ---------------- report ----------------
def tstat_clustered(df, col):
    g = df.groupby("date")[col].agg(["sum", "count"])
    n = g["count"].sum(); mu = df[col].mean()
    # day-clustered SE of the pooled mean: residual sums per day
    r = (df[col] - mu).groupby(df.date).sum()
    se = np.sqrt((r ** 2).sum()) / n
    return mu / se if se > 0 else np.nan

def summarize(x, label, ndays, out):
    if len(x) == 0:
        out.append(f"{label}: n=0"); return
    x = x.copy()
    x["net1"] = x.pess_ret; x["net2"] = x.pess_ret - x.spr0
    x["gross"] = x.pess_ret + x.pess_c   # mid-to-mid at the exit time
    x["opt1"] = x.opt_ret
    x["opt2"] = x.opt_ret - x.spr0
    x["pstar"] = (x.S + x.pess_c) / (x.G + x.S)
    tp = (x.pess_kind == "TP"); sl = (x.pess_kind == "SL")
    bp = 1e4
    top5 = x.net1.sort_values(ascending=False).index[:5]
    out.append(f"{label}: n={len(x)} days={x.date.nunique()}/{ndays} trades/day={len(x)/ndays:.2f}")
    out.append(f"  pess: gross {x.gross.mean()*bp:+.2f}bp  net1x {x.net1.mean()*bp:+.2f}bp (t {tstat_clustered(x,'net1'):.2f})  net2x {x.net2.mean()*bp:+.2f}bp (t {tstat_clustered(x,'net2'):.2f})  median net1 {x.net1.median()*bp:+.1f}  ex-top5 net1 {x.drop(top5).net1.mean()*bp:+.2f}")
    out.append(f"  opt : net1x {x.opt1.mean()*bp:+.2f}bp (t {tstat_clustered(x,'opt1'):.2f})  net2x {x.opt2.mean()*bp:+.2f}bp (t {tstat_clustered(x,'opt2'):.2f})")
    out.append(f"  c (measured, mean entry-half + exit-half) = {x.pess_c.mean()*bp:.2f}bp  mean entry quoted spread {x.spr0.mean()*bp:.2f}bp  mean G=S {x.G.mean()*bp:.2f}bp")
    out.append(f"  p(TP/all) {tp.mean():.3f}  p(TP/(TP+SL)) {tp.sum()/max(1,(tp|sl).sum()):.3f}  p*(mean) {x.pstar.mean():.3f}  exits TP/SL/TO = {tp.sum()}/{sl.sum()}/{(x.pess_kind=='TO').sum()}  net>0 rate {(x.net1>0).mean():.3f}")

def report(era):
    seed, _, _ = SEEDS[era]
    days = (D / f"{era}_days.txt").read_text().split()
    nd = len(days)
    fs = [pd.read_parquet(p) for p in sorted((D / "trades").glob("*.parquet")) if p.stem in {d.replace("-", "") for d in days}]
    fs = [f for f in fs if len(f)]
    X = pd.concat(fs); X["date"] = pd.to_datetime(X.date)
    out = [f"SECT-LAG {era} era report; days sampled {nd} (seed {seed}); days with any trade rows {X.date.nunique()}"]
    for arm in ("lag", "ctrl", "plc"):
        summarize(X[X.arm == arm], f"== ARM {arm}", nd, out)
    L = X[X.arm == "lag"].copy()
    L["half"] = np.where(L.date < pd.Timestamp("2015-01-01") if era == "disc" else L.date < pd.Timestamp("2018-01-01"), "H1", "H2")
    out.append("-- laggard arm by half (disc: split at 2012-07-01 midpoint by date; judge: 2015-17 / 2018-19)")
    if era == "disc": L["half"] = np.where(L.date < pd.Timestamp("2012-07-01"), "H1", "H2")
    for h, g in L.groupby("half"): summarize(g, f"  half {h}", nd, out)
    out.append("-- laggard arm by sector")
    for k, g in L.groupby("sec"): summarize(g, f"  sector {k}", nd, out)
    out.append("-- laggard arm by entry-spread bucket (bp)")
    L["sb"] = pd.cut(L.spr0 * 1e4, [0, 5, 10, 20, 30.0001, 1e9])
    for k, g in L.groupby("sb", observed=True): summarize(g, f"  spread {k}", nd, out)
    out.append("-- laggard arm by time of day")
    L["tod"] = pd.cut(L.t / 60, [10, 11, 12, 13, 14, 15, 15.6], right=False)
    for k, g in L.groupby("tod", observed=True): summarize(g, f"  hour {k}", nd, out)
    text = "\n".join(out)
    return text, X

if __name__ == "__main__" and sys.argv[1] == "report":
    t, _ = report(sys.argv[2]); print(t)
