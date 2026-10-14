"""Study SCALP-OFI (round1_prose.md "## Study SCALP-OFI"): HGB classifier on order-flow features for P(+20bp before -20bp, 15m), large caps, TAQ.
usage: scalp_ofi.py sanity DATE | shift DATE | build ERA [NWORK] | run      (ERA = wf|judge ; cache data/research/scalp_ofi/ERA/)
No parameter below was changed after seeing outcomes. Disclosed choices are printed at the end of the output file."""
import sys, time, warnings
from pathlib import Path
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, "research/sim")
from sect_lag import conn, tstat_clustered
ROOT = Path(__file__).resolve().parents[2]; D = ROOT / "data/research/scalp_ofi"; D.mkdir(parents=True, exist_ok=True)
OUT = ROOT / "data/research/program/scalp_ofi_out.txt"
G = S = 20e-4; HZN = 900; STEP = 300; T0, T1 = 36000, 55800   # decision seconds-of-day 10:00..15:30 every 5 min
S0, S1 = 34200, 57960                                          # dense grid 09:30:00 .. 15:46:00
N = S1 - S0
ERAS = {"wf": (984, "2011-01-01", "2013-12-31", 120), "judge": (985, "2015-01-01", "2015-12-31", 60)}
NAMES_PER_DAY = 120; BAD = "[OQ6MIZU]"
FEATS = ["ofi1", "ofi5", "ofi15", "qi", "qi5", "sg1", "sg5", "sg15", "iso5", "bjzz15", "inten5", "spr_rel", "odd15",
         "ret5", "ret15", "spy5", "spy15", "mod"]

def sql_q(vals, roots, ds):
    return f"""with u(root,sfx,pid) as (values {vals}),
q as (select u.pid, n.time_m tm, n.best_bid bb, n.best_ask ba, n.best_bidsizeshares bs, n.best_asksizeshares az
      from taqm_{ds[:4]}.complete_nbbo_{ds} n join u on u.root=n.sym_root and u.sfx=coalesce(n.sym_suffix,'')
      where n.sym_root in ({roots}) and n.time_m >= '09:30:00' and n.time_m < '15:46:00' and n.best_bid>0 and n.best_ask>n.best_bid),
o as (select *, lag(bb) over w pb, lag(ba) over w pa, lag(bs) over w pbs, lag(az) over w paz from q window w as (partition by pid order by tm)),
e as (select pid, tm, bb, ba, bs, az,
        case when pb is null then 0 else (case when bb>=pb then bs else 0 end) - (case when bb<=pb then pbs else 0 end)
                                       - (case when ba<=pa then az else 0 end) + (case when ba>=pa then paz else 0 end) end ofi,
        (bs+az)/2.0 dep from o)
select pid, floor(extract(epoch from tm))::int sec, min(bb) minbid, (array_agg(bb order by tm desc))[1] lbb, (array_agg(ba order by tm desc))[1] lba,
  (array_agg(bs order by tm desc))[1] lbs, (array_agg(az order by tm desc))[1] laz, sum(ofi)::float8 ofi, sum(dep)::float8 dsum, count(*) nq
from e group by 1,2"""

def sql_t(vals, roots, ds):
    return f"""with u(root,sfx,pid) as (values {vals}),
t as (select u.pid, c.time_m tm, coalesce(c.tr_seqnum,0) sq, c.price p, c.size z, c.ex, coalesce(c.tr_scond,'') sc
      from taqm_{ds[:4]}.ctm_{ds} c join u on u.root=c.sym_root and u.sfx=coalesce(c.sym_suffix,'')
      where c.sym_root in ({roots}) and c.time_m >= '09:30:00' and c.time_m < '15:46:00' and c.tr_corr='00' and c.price>0 and c.size>0
        and coalesce(c.tr_scond,'') !~ '{BAD}'),
d as (select *, sign(p - lag(p) over w) dsg from t window w as (partition by pid order by tm, sq)),
g as (select *, count(nullif(dsg,0)) over (partition by pid order by tm, sq) grp from d),
s as (select *, max(nullif(dsg,0)) over (partition by pid, grp) sg,
        (mod(round(p*10000)::bigint,100))/100.0 zz from g)
select pid, floor(extract(epoch from tm))::int sec,
  sum(p*z) filter (where sg>0)::float8 buy, sum(p*z) filter (where sg<0)::float8 sell,
  sum(p*z) filter (where sc ~ 'F')::float8 iso, sum(p*z)::float8 tot, count(*) cnt, count(*) filter (where z<100) odd,
  sum(p*z) filter (where ex='D' and p>=1 and zz>0.6)::float8 rb, sum(p*z) filter (where ex='D' and p>=1 and zz>0 and zz<0.4)::float8 rs,
  max(p) filter (where ex<>'D' and z>=100 and sc ~ '^[@F ]*$') maxlit
from s group by 1,2"""

def dense(qd, td):
    """qd,td: per-name frames (sec-indexed) -> dict of dense arrays length N (quote state forward-filled)."""
    A = {}
    qd = qd[(qd.sec >= S0) & (qd.sec < S1)].set_index("sec"); idx = np.arange(S0, S1)
    q = qd.reindex(idx)
    for k in ("ofi", "dsum", "nq"): A[k] = q[k].fillna(0).values.astype(float)
    ff = q[["lbb", "lba", "lbs", "laz"]].astype(float).ffill()
    A["bid"], A["ask"], A["bs"], A["az"] = (ff[c].values for c in ("lbb", "lba", "lbs", "laz"))
    mb = q.minbid.astype(float).values; A["minbid"] = np.where(np.isnan(mb), A["bid"], np.minimum(mb, A["bid"] * 0 + mb))  # bucket min bid (state bid if no update)
    A["minbid"] = np.where(np.isnan(mb), A["bid"], mb)
    A["mid"] = (A["bid"] + A["ask"]) / 2
    td = td[(td.sec >= S0) & (td.sec < S1)].set_index("sec"); t = td.reindex(idx)
    for k in ("buy", "sell", "iso", "tot", "cnt", "odd", "rb", "rs"): A[k] = t[k].fillna(0).values.astype(float)
    A["maxlit"] = t.maxlit.astype(float).values
    return A

def feats_at(A, SPY, i, adv):
    """features at decision index i (= t_s - S0); uses ONLY indices < i. returns dict."""
    def sm(a, w): return a[i - w:i].sum()
    dep = sm(A["dsum"], 900) / max(1.0, sm(A["nq"], 900))
    f = {}
    for w, nm in ((60, "ofi1"), (300, "ofi5"), (900, "ofi15")): f[nm] = sm(A["ofi"], w) / dep if dep > 0 else np.nan
    qi = lambda j: (A["bs"][j] - A["az"][j]) / (A["bs"][j] + A["az"][j])
    f["qi"] = qi(i - 1); f["qi5"] = np.nanmean([qi(i - 1 - 60 * m) for m in range(5)])
    for w, nm in ((60, "sg1"), (300, "sg5"), (900, "sg15")): f[nm] = (sm(A["buy"], w) - sm(A["sell"], w)) / adv
    tt = sm(A["tot"], 300); f["iso5"] = sm(A["iso"], 300) / tt if tt > 0 else np.nan
    rb, rs = sm(A["rb"], 900), sm(A["rs"], 900); f["bjzz15"] = (rb - rs) / (rb + rs) if rb + rs > 0 else np.nan
    f["cnt5"] = sm(A["cnt"], 300)
    spr = (A["ask"][:i] - A["bid"][:i]) / A["mid"][:i]; f["spr_rel"] = spr[i - 1] / np.nanmedian(spr)
    c15 = sm(A["cnt"], 900); f["odd15"] = sm(A["odd"], 900) / c15 if c15 > 0 else np.nan
    m = A["mid"]; f["ret5"] = m[i - 1] / m[i - 301] - 1; f["ret15"] = m[i - 1] / m[i - 901] - 1
    sp = SPY["mid"]; f["spy5"] = sp[i - 1] / sp[i - 301] - 1; f["spy15"] = sp[i - 1] / sp[i - 901] - 1
    f["mod"] = (i + S0) / 60
    return f

def label_at(A, i):
    """entry = ask at t_s+1s (last quote at/before: bucket i); scan buckets i+1..i+900 (strictly after entry). pessimistic."""
    ask0, bid0 = A["ask"][i], A["bid"][i]
    if not np.isfinite(ask0) or not np.isfinite(bid0) or i + HZN >= N: return None
    mid0 = (ask0 + bid0) / 2; up = ask0 * (1 + G); dn = ask0 * (1 - S)
    sl = slice(i + 1, i + HZN + 1)
    ml = A["maxlit"][sl]; mb = A["minbid"][sl]
    tp = np.where(np.nan_to_num(ml, nan=-1) > up)[0]; st = np.where(mb <= dn)[0]
    jtp = tp[0] if len(tp) else 10**9; jst = st[0] if len(st) else 10**9
    if jst <= jtp and jst < 10**9: kind, j = "SL", jst; px = mb[j]
    elif jtp < 10**9: kind, j = "TP", jtp; px = up
    else: kind, j = "TO", HZN - 1; px = A["bid"][i + HZN]
    ix = i + 1 + j; midx = A["mid"][ix]
    row = dict(kind=kind, y=int(kind == "TP"), ret=px / ask0 - 1, spr0=(ask0 - bid0) / mid0, c=(ask0 - mid0) / mid0 + (midx - px) / midx, ask0=ask0, tx=j + 1)
    for h in (60, 300, 900): row[f"drift{h}"] = A["mid"][i + h] / mid0 - 1
    return row

def build_day(db, d, f, nm):
    import late_flow_univ as U
    fn = D / "days" / f"{d:%Y%m%d}.parquet"
    if fn.exists(): return "cached"
    fn.parent.mkdir(exist_ok=True); (D / "slots").mkdir(exist_ok=True)
    x = f[f.date == d].dropna(subset=["adv_dv", "pclose"]); x = x[(x.pclose >= 10) & (x.adv_dv >= 500e6)]
    nn = nm[(nm.namedt <= d) & (nm.nameendt >= d) & nm.shrcd.isin([10, 11])]
    u = x[x.permno.isin(nn.permno)][["permno", "adv_dv"]].drop_duplicates("permno").set_index("permno").adv_dv
    ds = d.strftime("%Y%m%d"); rs = np.random.RandomState(int(ds))
    if len(u) > NAMES_PER_DAY: u = u.loc[sorted(rs.choice(u.index.values, NAMES_PER_DAY, replace=False))]
    if not len(u): pd.DataFrame().to_parquet(fn); return "no names"
    lk = db.raw_sql(f"select sym_root,sym_suffix,permno,match_lvl from wrdsapps_link_crsp_taqm.taqmclink where date='{d:%Y-%m-%d}' and permno in ({','.join(map(str, u.index))})")
    lk = lk.sort_values("match_lvl").drop_duplicates("permno"); lk["sfx"] = lk.sym_suffix.fillna(""); lk["permno"] = lk.permno.astype(int)
    sym = {r.permno: (r.sym_root, r.sfx) for r in lk.itertuples()}
    if not sym: pd.DataFrame().to_parquet(fn); return "no link"
    sym[-1] = ("SPY", "")
    vals = ",".join("('%s','%s',%d)" % (r.replace("'", "''"), s.replace("'", "''"), p) for p, (r, s) in sym.items())
    roots = ",".join("'%s'" % r.replace("'", "''") for r in sorted({v[0] for v in sym.values()}))
    Q = db.raw_sql(sql_q(vals, roots, ds)); T = db.raw_sql(sql_t(vals, roots, ds))
    Q["pid"] = Q.pid.astype(int); T["pid"] = T.pid.astype(int)
    Qg = {k: v for k, v in Q.groupby("pid")}; Tg = {k: v for k, v in T.groupby("pid")}
    if -1 not in Qg: pd.DataFrame().to_parquet(fn); return "no SPY"
    SPY = dense(Qg[-1], Tg.get(-1, T.iloc[:0]))
    rows = []; slots = []
    for p in u.index:
        if p not in Qg or p not in Tg: continue
        A = dense(Qg[p], Tg[p]); adv = float(u[p])
        sc = A["cnt"][:79 * 300].reshape(-1, 300).sum(1); slots += [(d, p, s_, sc[s_]) for s_ in range(len(sc))]
        for ts in range(T0, T1 + 1, STEP):
            i = ts - S0
            try: ft = feats_at(A, SPY, i, adv)
            except Exception: continue
            lb = label_at(A, i)
            if lb is None: continue
            rows.append(dict(date=d, pid=p, t=ts, adv=adv, **ft, **lb))
    df = pd.DataFrame(rows); df.to_parquet(fn)
    pd.DataFrame(slots, columns=["date", "pid", "slot", "cnt"]).to_parquet(D / "slots" / f"{d:%Y%m%d}.parquet")
    return f"ok rows {len(df)} names {df.pid.nunique() if len(df) else 0} base y {df.y.mean() if len(df) else np.nan:.3f}"

def era_days(era):
    seed, a, b, nd = ERAS[era]
    f = pd.read_parquet("data/research/late_flow/dsf.parquet", columns=["date"])
    alld = [pd.Timestamp(x) for x in sorted(f.date.unique())]; ed = [x for x in alld if pd.Timestamp(a) <= x <= pd.Timestamp(b)]
    rs = np.random.RandomState(seed)
    return [ed[k] for k in sorted(rs.choice(len(ed), size=nd, replace=False))]

_G = {}
def _work(d):
    try:
        if "db" not in _G:
            import late_flow_univ as U
            f = U.load(); _G["p"] = (f[f.date >= "2009-10-01"], U.names()); _G["db"] = conn()
        return d, build_day(_G["db"], d, *_G["p"])
    except Exception:
        _G.pop("db", None)
        import traceback; return d, "ERR " + traceback.format_exc()[-600:]

def build(era, nwork=2):
    from concurrent.futures import ProcessPoolExecutor
    sel = era_days(era); (D / f"{era}_days.txt").write_text("\n".join(f"{d:%Y-%m-%d}" for d in sel))
    t0 = time.time(); n = 0
    with ProcessPoolExecutor(nwork) as ex:
        for d, st in ex.map(_work, sel):
            n += 1; print(f"{d:%Y-%m-%d} {st}  [{n}/{len(sel)} {time.time()-t0:.0f}s]", flush=True)

def raw_day(db, d, f, nm, k=6):
    """for tests: return (A dict per pid, SPY, adv) for first k names."""
    x = f[f.date == d].dropna(subset=["adv_dv", "pclose"]); x = x[(x.pclose >= 10) & (x.adv_dv >= 500e6)]
    nn = nm[(nm.namedt <= d) & (nm.nameendt >= d) & nm.shrcd.isin([10, 11])]
    u = x[x.permno.isin(nn.permno)][["permno", "adv_dv"]].drop_duplicates("permno").set_index("permno").adv_dv.nlargest(k)
    ds = d.strftime("%Y%m%d")
    lk = db.raw_sql(f"select sym_root,sym_suffix,permno,match_lvl from wrdsapps_link_crsp_taqm.taqmclink where date='{d:%Y-%m-%d}' and permno in ({','.join(map(str, u.index))})")
    lk = lk.sort_values("match_lvl").drop_duplicates("permno"); lk["sfx"] = lk.sym_suffix.fillna(""); lk["permno"] = lk.permno.astype(int)
    sym = {r.permno: (r.sym_root, r.sfx) for r in lk.itertuples()}; sym[-1] = ("SPY", "")
    vals = ",".join("('%s','%s',%d)" % (r, s, p) for p, (r, s) in sym.items()); roots = ",".join("'%s'" % r for r in sorted({v[0] for v in sym.values()}))
    t0 = time.time(); Q = db.raw_sql(sql_q(vals, roots, ds)); t1 = time.time(); T = db.raw_sql(sql_t(vals, roots, ds))
    print(f"  {d:%Y-%m-%d}: {len(sym)} names; quote sec-rows {len(Q)} in {t1-t0:.1f}s; trade sec-rows {len(T)} in {time.time()-t1:.1f}s")
    Q["pid"] = Q.pid.astype(int); T["pid"] = T.pid.astype(int)
    return {p: dense(Q[Q.pid == p], T[T.pid == p]) for p in u.index if (Q.pid == p).any() and (T.pid == p).any()}, dense(Q[Q.pid == -1], T[T.pid == -1]), u

def shift_test(d):
    import late_flow_univ as U
    f = U.load(); f = f[f.date >= "2009-10-01"]; db = conn()
    As, SPY, u = raw_day(db, pd.Timestamp(d), f, U.names(), k=6)
    rs = np.random.RandomState(1); bad = 0; n = 0
    for p, A in list(As.items())[:4]:
        for ts in (T0, T0 + 3600, 46800, T1):
            i = ts - S0; f0 = feats_at(A, SPY, i, float(u[p]))
            A2 = {k: v.copy() for k, v in A.items()}; S2 = {k: v.copy() for k, v in SPY.items()}
            for B in (A2, S2):
                for k, v in B.items(): v[i:] = rs.rand(len(v) - i) * (np.nanmax(np.abs(v)) + 1) * 3   # corrupt everything at/after t
            f1 = feats_at(A2, S2, i, float(u[p])); n += 1
            if any(not (f0[k] == f1[k] or (np.isnan(f0[k]) and np.isnan(f1[k]))) for k in f0): bad += 1; print("LEAK", p, ts, {k: (f0[k], f1[k]) for k in f0 if f0[k] != f1[k]})
            lb = label_at(A, i); lb2 = label_at(A2, i)
            if lb and lb["y"] is None: print("?")
    print(f"shift test {d}: {n} (name,t) checked, features changed under post-t corruption: {bad}")

# ================= model / evaluation =================
def load_era(era):
    fs = sorted((D / "days").glob("*.parquet")); days = {f"{d:%Y%m%d}" for d in era_days(era)}
    P = pd.concat([pd.read_parquet(f) for f in fs if f.stem in days and f.stat().st_size > 1000]); P["date"] = pd.to_datetime(P.date)
    sl = pd.concat([pd.read_parquet(D / "slots" / f"{k}.parquet") for k in sorted(days) if (D / "slots" / f"{k}.parquet").exists()]); sl["date"] = pd.to_datetime(sl.date)
    g = {k: v for k, v in sl.groupby(["pid", "slot"])}
    inten = np.full(len(P), np.nan)
    P = P.reset_index(drop=True)
    for (pid, slot), ix in P.assign(slot=(P.t - S0) // 300 - 1).groupby(["pid", "slot"]).indices.items():
        if (pid, slot) not in g: continue
        h = g[(pid, slot)]
        for j in ix:
            dd = P.date.iat[j]; pr = h[(h.date < dd) & (h.date >= dd - pd.Timedelta(days=28))].cnt
            if len(pr) and pr.mean() > 0: inten[j] = P.cnt5.iat[j] / pr.mean()
    P["inten5"] = inten
    return P.sort_values(["date", "pid", "t"]).reset_index(drop=True)

from sklearn.ensemble import HistGradientBoostingClassifier as HGB
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import roc_auc_score
def mk(): return HGB(max_iter=200, learning_rate=0.05, random_state=0)

def wilson_lo(k, n, z=1.96):
    if n == 0: return np.nan
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n)
    return (c - z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d

def deoverlap(df):
    keep = []; last = {}
    for pid, d, t in zip(df.pid.values, df.date.values, df.t.values):
        key = (pid, d)
        if key in last and t < last[key] + HZN: keep.append(False); continue
        last[key] = t; keep.append(True)
    return df[np.array(keep)]

def label_variants(P, seed=0):
    rng = np.random.RandomState(seed); perm = P.y.values.astype(float).copy()
    for _, ix in P.groupby("date").indices.items(): perm[ix] = rng.permutation(perm[ix])
    key = P.set_index(["pid", "date", "t"]).y.to_dict()
    sh = np.array([key.get((a, b, c + 3600), np.nan) for a, b, c in zip(P.pid, P.date, P.t)], float)
    return {"real": P.y.values.astype(float), "perm": perm, "shift": sh}

def fit_score(Xtr, ytr, Xva, yva, Xte):
    ok = ~np.isnan(ytr); m = mk().fit(Xtr[ok], ytr[ok].astype(int))
    pv = m.predict_proba(Xva)[:, 1]; pt = m.predict_proba(Xte)[:, 1]; okv = ~np.isnan(yva)
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(pv[okv], yva[okv])
    return m, iso.predict(pv), iso.predict(pt)

def summarize(df, tag, L):
    n = len(df)
    if n == 0: L.append(f"{tag}: no trades"); return {}
    bp = 1e4; df = df.copy(); df["net1"] = df.ret; df["net2"] = df.ret - df.spr0
    c = df.c.mean(); ps1 = (S + c) / (G + S); ps2 = (S + 2 * c) / (G + S); p = df.y.mean(); lo = wilson_lo(df.y.sum(), n)
    ex5 = df.net2.sort_values().iloc[:-5].mean() * bp if n > 5 else np.nan
    r = dict(n=n, p=p, lo=lo, ps1=ps1, ps2=ps2, c=c * bp, net1=df.net1.mean() * bp, net2=df.net2.mean() * bp, t1=tstat_clustered(df, "net1"), t2=tstat_clustered(df, "net2"),
             ex5=ex5, days=df.date.nunique(), tpd=n / max(1, df.date.nunique()), med1=df.net1.median() * bp)
    L.append(f"{tag}: n={n} days={r['days']} trades/day(active)={r['tpd']:.1f}  p(TP)={p:.4f} [Wilson lo {lo:.4f}]  p*(1x)={ps1:.4f} p*(2x)={ps2:.4f}  c={r['c']:.2f}bp  "
             f"net/trade 1x={r['net1']:+.2f}bp (t {r['t1']:.2f}) median1x {r['med1']:+.1f}  2x={r['net2']:+.2f}bp (t {r['t2']:.2f})  ex-top5(2x)={ex5:+.2f}bp  exits TP/SL/TO={int((df.kind=='TP').sum())}/{int((df.kind=='SL').sum())}/{int((df.kind=='TO').sum())}")
    return r

def reliability(sc, y, L, tag):
    q = pd.qcut(pd.Series(sc).rank(method="first"), 10, labels=False)
    t = pd.DataFrame({"q": q.values, "s": sc, "y": y}).groupby("q").agg(n=("y", "size"), score=("s", "mean"), hit=("y", "mean"))
    L.append(f"reliability by decile ({tag}):"); L += ["  D%d  n=%d  mean score %.4f  hit %.4f" % (i + 1, r.n, r.score, r.hit) for i, r in t.iterrows()]
    return t.hit.values

def drift_lines(J, sel, L, tag):
    L.append(f"mid drift (bp, mid-to-mid from entry) {tag}: top bucket (de-overlapped n={len(sel)}) vs ALL decisions (n={len(J)})")
    for h in (60, 300, 900):
        c = f"drift{h}"; a = J[c].mean() * 1e4; b = sel[c].mean() * 1e4
        L.append(f"  +{h//60:2d}m: top {b:+.2f} (day-clustered t {tstat_clustered(sel, c):.2f})  all {a:+.2f}  diff {b-a:+.2f}")

def run():
    t0 = time.time(); P = load_era("wf"); X = P[FEATS].values.astype(float); LV = label_variants(P); sess = np.array(sorted(P.date.unique())); L = []
    months = pd.period_range("2012-01", "2013-12", freq="M"); oof = {k: np.full(len(P), np.nan) for k in LV}
    for m in months:
        ms = m.to_timestamp(); me = (m + 1).to_timestamp(); i0 = np.searchsorted(sess, np.datetime64(ms)); cut = sess[max(0, i0 - 5)]
        trm = (P.date < cut).values; te = ((P.date >= ms) & (P.date < me)).values
        if te.sum() == 0: continue
        vstart = pd.Timestamp(cut) - pd.DateOffset(months=2)
        fit = trm & (P.date < vstart - pd.Timedelta(days=7)).values; va = trm & (P.date >= vstart).values
        for nm, y in LV.items():
            _, sv, st_ = fit_score(X[fit], y[fit], X[va], y[va], X[te]); oof[nm][te] = st_
        print(m, round(time.time() - t0), flush=True)
    mask = ~np.isnan(oof["real"]); Pm = P[mask].copy()
    L.append("SCALP-OFI  (pre-reg round1_prose.md '## Study SCALP-OFI', N 981->982; WRDS TAQ ms; 15-min pessimistic label +-20bp)")
    L.append(f"WF panel rows {len(P)} ({P.date.nunique()} days 2011-13, seed 984; names/day mean {P.groupby('date').pid.nunique().mean():.1f}), base rate y={P.y.mean():.4f}, mean c={P.c.mean()*1e4:.2f}bp")
    L.append("\n== OUT-OF-FOLD 2012-01..2013-12 (walk-forward, 5-session embargo) ==")
    for nm in LV:
        sc = oof[nm]; Pm[nm] = sc[mask]; thr = np.nanpercentile(sc, 95); sel = Pm[Pm[nm] >= thr]
        if nm == "shift":
            s2 = sel.copy(); s2["y"] = LV["shift"][sel.index]; s2 = s2.dropna(subset=["y"]); L.append(f"[shift null] top-bucket hit vs SHIFTED labels: n={len(s2)} p={s2.y.mean():.4f}")
        summarize(deoverlap(sel), f"[OOF {nm}] top bucket (pooled 95th pct, thr {thr:.4f}) vs real labels", L)
    L.append(f"OOF AUC real {roc_auc_score(Pm.y, Pm.real):.4f}; perm null {roc_auc_score(Pm.y, Pm.perm):.4f}; shift null {roc_auc_score(Pm.y, Pm['shift']):.4f}")
    reliability(Pm.real.values, Pm.y.values, L, "OOF real")
    selo = deoverlap(Pm[Pm.real >= np.nanpercentile(oof["real"], 95)]); drift_lines(Pm, selo, L, "OOF")
    thr_frozen = np.nanpercentile(oof["real"], 95); thr_null = {k: np.nanpercentile(oof[k], 95) for k in ("perm", "shift")}
    L.append(f"FROZEN threshold (pooled 95th pct of 2012-13 OOF calibrated scores) = {thr_frozen:.5f}; null thresholds {thr_null}")
    # ---------- JUDGE 2015 (single look)
    J = load_era("judge"); XJ = J[FEATS].values.astype(float); LJ = label_variants(J)
    L.append(f"\n== JUDGE 2015 (single look; {J.date.nunique()} days seed 985; model retrained once on all 2011-13, inner val = last 2 months, threshold frozen) ==")
    vs = pd.Timestamp("2013-11-01"); fit = (P.date < vs - pd.Timedelta(days=7)).values; va = (P.date >= vs).values
    models = {}; jr = {}
    for nm, y in LV.items():
        mdl, sv, st_ = fit_score(X[fit], y[fit], X[va], y[va], XJ); J[nm] = st_; models[nm] = mdl
    for nm in LV:
        thr = thr_frozen if nm == "real" else thr_null[nm]; sel = J[J[nm] >= thr]
        if nm == "shift":
            s2 = sel.copy(); s2["ys"] = LJ["shift"][sel.index]; s2 = s2.dropna(subset=["ys"]); L.append(f"[judge shift null] top-bucket hit vs SHIFTED labels n={len(s2)} p={s2.ys.mean():.4f}")
        jr[nm] = summarize(deoverlap(sel), f"[judge {nm}] top bucket (score>={thr:.4f}) vs real labels", L)
    L.append(f"judge share of 2015 decisions >= frozen thr: {(J.real >= thr_frozen).mean():.4f} (nominal 0.05); AUC real {roc_auc_score(J.y, J.real):.4f} perm {roc_auc_score(J.y, J.perm):.4f} shift {roc_auc_score(J.y, J['shift']):.4f}")
    hits = reliability(J.real.values, J.y.values, L, "judge 2015 real model")
    selj = deoverlap(J[J.real >= thr_frozen]); drift_lines(J, selj, L, "JUDGE 2015")
    r = jr["real"]; nd = J.date.nunique(); ceil = r.get("net2", 0) * 1e-4 * min(r.get("tpd", 0), 13) * 252 * 0.5 * 100
    L.append("\n== GATE (2015, pessimistic) ==")
    def gl(name, ok, d): L.append(f"  {'PASS' if ok else 'FAIL'}  {name}: {d}")
    g = []
    g.append(r["p"] > r["ps2"]); gl("top-bucket p > p*(2x)", g[-1], f"p={r['p']:.4f} p*(2x)={r['ps2']:.4f}")
    g.append(r["lo"] > r["ps1"]); gl("Wilson lower 95% bound > p*(1x)", g[-1], f"lo={r['lo']:.4f} p*(1x)={r['ps1']:.4f}")
    g.append(r["net2"] > 0 and r["t2"] >= 2); gl("net/trade at 2x > 0, day-clustered t >= 2", g[-1], f"{r['net2']:+.2f}bp t {r['t2']:.2f}")
    g.append(r["p"] > max(jr["perm"].get("p", 1), jr["shift"].get("p", 1))); gl("beats BOTH nulls' top-bucket hit rate", g[-1], f"real {r['p']:.4f} perm {jr['perm'].get('p', np.nan):.4f} shift {jr['shift'].get('p', np.nan):.4f}")
    g.append(bool(hits[9] >= hits[8] >= hits[7])); gl("reliability monotone in top 3 deciles", g[-1], f"D8 {hits[7]:.4f} D9 {hits[8]:.4f} D10 {hits[9]:.4f}")
    g.append(r["ex5"] > 0); gl("ex-top-5 > 0 (2x net)", g[-1], f"{r['ex5']:+.2f}bp")
    g.append(r["n"] >= 300); gl(">= 300 trades (one open trade per name)", g[-1], f"n={r['n']}")
    g.append(ceil >= 8); gl("ceiling at $10k >= +8pp/yr", g[-1], f"{ceil:+.2f}pp = net2 x min(trades/active-day,13) x 252 x 50% capture")
    L.append(f"  trades per active day {r['tpd']:.1f}; per calendar sampled day {r['n']/max(1,nd):.2f}")
    L.append("  VERDICT: " + ("PASS" if all(g) else "KILL") + f"  ({sum(g)}/8)")
    mdl = models["real"]; vi = np.where(va)[0]; rs = np.random.RandomState(0); vi = rs.choice(vi, min(60000, len(vi)), replace=False)
    base = roc_auc_score(P.y.values[vi], mdl.predict_proba(X[vi])[:, 1]); imp = {}
    for j, f in enumerate(FEATS):
        d = []
        for _ in range(3):
            Xp = X[vi].copy(); Xp[:, j] = rs.permutation(Xp[:, j]); d.append(base - roc_auc_score(P.y.values[vi], mdl.predict_proba(Xp)[:, 1]))
        imp[f] = np.mean(d)
    L.append(f"\npermutation importance (AUC drop, judge model, inner-val 2013-11..12 n={len(vi)} (model fit excludes it; label-free of 2015), base AUC {base:.4f}) top 10:")
    L += [f"  {f:8s} {v:+.5f}" for f, v in sorted(imp.items(), key=lambda x: -x[1])[:10]]
    L.append(DISCLOSED); OUT.write_text("\n".join(L) + "\n"); print("\n".join(L))

DISCLOSED = """
== DISCLOSED CHOICES (ambiguities read conservatively) ==
1. Decisions every 5 min from 10:00 to 15:30 (boundary t). Features use only data with time < t (1-second buckets with index < t; shift test on 3 days: post-t corruption changed no feature, 0/48 checks). Entry = last NBBO ask at/before t+1s; outcomes scan seconds strictly after t+1s (as ISO-BURST).
2. Label resolved at 1-second buckets (not tick): TP = highest lit trade in bucket (exch != 'D', size >= 100, sale condition in {@,F,blank}, regular corr '00') strictly > ask0*1.002; SL = lowest NBBO bid in bucket <= ask0*0.998 (or the standing bid). Same bucket -> stop first. Stop exits at the lowest bid of the trigger bucket (>= as pessimistic as ISO-BURST's next-lit-trade rule); time-out at the standing bid at t+1s+900s. TP pays exactly +20bp (limit sell), no exit spread; c = entry half-spread + (mid-px)/mid at exit as in ISO-BURST. 1x net = pessimistic ret; 2x net = ret - quoted entry spread (ISO-BURST convention). p*(1x)=(S+c)/(G+S), p*(2x)=(S+2c)/(G+S) with c the top bucket's mean measured c.
3. Universe d-1 from CRSP dsf (strictly prior 20d median $vol >= $500M, prior close >= $10, common 10/11, TAQ-linked). The universe is only ~30-40 names/day in 2011-15, so the 120-name sampling cap never binds (all eligible names used). The $10 / $500M floors are as registered; SPY is added for the market return features.
4. Lee-Ready signing = tick test with carry-forward of the last non-zero tick (no quote-rule step; no quote join). Signed $ imbalance / 20d median $vol (CRSP, prior days). Cont OFI uses complete NBBO updates (best bid/ask and share sizes), normalised by the mean (bidsz+asksz)/2 per update over the prior 15 min. qi5 = mean of the standing quote imbalance sampled at the last 5 minute-ends.
5. ISO share = F-flagged $ / total $ over 5 min. BJZZ retail: exch 'D', price >= $1, Z = 100*(p mod 0.01) (from price rounded to 1e-4): 0.6<Z<1 buy, 0<Z<0.4 sell, $-weighted, 15 min. Odd-lot share = trades with size < 100 / all trades, 15 min (the TAQ ctm file carries no odd lots in 2011-13, so this feature is constant 0 in the training years; unused by trees).
6. Trade-count intensity = trades in the last 5 min / mean count in the SAME 5-min clock slot for the same name over earlier SAMPLED days in the previous 28 calendar days of the same era (a 20-trading-day history is not available with ~120 sampled days; NaN, which HGB handles, when no prior sampled day). Spread feature = spread at t / median spread (second-grid, forward-filled) from 09:30 to t.
7. Walk-forward: months 2012-01..2013-12, train = dates before the cut (5 sessions before the month start, i.e. embargo), inner validation = last 2 months before the cut, fit = earlier than that minus 7 days; isotonic on the validation set. HGB max_iter 200, lr 0.05, random_state 0. First folds train on ~2011 only (short history).
8. Threshold: pooled 95th pct of all 2012-13 OOF calibrated scores (the registered per-window rule has no data for the first fold); frozen for the judge; nulls use their own pooled OOF 95th pct. Nulls: labels permuted within day (fit+val), and label of the same name-day at t+60 min (NaN dropped, so late-day rows lose labels); both scored on REAL test labels in the top-bucket tables; shift null also on shifted labels.
9. Judge: one retrain on all 2011-13 with inner val = 2013-11 onward (7-day gap). The ceiling is net2 x min(trades/active-day,13) x 252 x 50% / (as in SCALP-CLF). One open trade per name: a top-bucket decision is accepted only >= 900 s after the previous accepted one for that name-day.
10. Day counts: 120 wf / 60 judge sampled days (random seeds 984/985 over CRSP trading days in the era).
"""

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "sanity":
        import late_flow_univ as U
        db = conn(); f = U.load(); f = f[f.date >= "2009-10-01"]; nm = U.names(); d = pd.Timestamp(sys.argv[2])
        t0 = time.time(); print(build_day(db, d, f, nm), f"{time.time()-t0:.0f}s")
    elif cmd == "shift": shift_test(sys.argv[2])
    elif cmd == "build": build(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 2)
    elif cmd == "run":
        run()
