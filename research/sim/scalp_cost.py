"""SCALP-COST: what an intraday long scalp pays, per liquidity bucket x time of day (TAQ ms, WRDS server-side). No signal outcomes.
usage: scalp_cost.py run [NWORK] [LIMIT]   (resumable, per-day cache data/research/scalp_cost/days/)
       scalp_cost.py report                (writes data/research/program/scalp_cost_out.txt)
Days: 15 random trading days/yr (seed 7) for 2012, 2018, 2025. Names/day: 12 per (dollar-volume bucket x price<20/>=20) cell + SPY QQQ IWM SMH TQQQ.
Universe: CRSP dsf_v2 (EQTY/COM, price>=5, prior-20d median $vol); bare tickers only (no share-class suffix). Regular hours 09:30-16:00 ET."""
import sys, time, random
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path("data/research/scalp_cost"); DAYS = ROOT / "days"; DAYS.mkdir(parents=True, exist_ok=True)
YEARS = [2012, 2018, 2025]; NDAY = 10; NPER = 6; K = 3; NW = 3; WMIN = 5; SEED = 7
ETFS = ["SPY", "QQQ", "IWM", "SMH", "TQQQ"]
TOD = [("0930-0945", "09:30:00", "09:45:00"), ("0945-1030", "09:45:00", "10:30:00"), ("1030-1200", "10:30:00", "12:00:00"),
       ("1200-1400", "12:00:00", "14:00:00"), ("1400-1530", "14:00:00", "15:30:00"), ("1530-1600", "15:30:00", "16:00:00")]
TODCASE = "case " + " ".join(f"when {{t}}>=time '{a}' and {{t}}<time '{b}' then '{n}'" for n, a, b in TOD) + " end"
BUCKETS = [("A>1B", 1e9, 1e30), ("B200M-1B", 2e8, 1e9), ("C50-200M", 5e7, 2e8), ("D10-50M", 1e7, 5e7), ("E2-10M", 2e6, 1e7)]
BAD = "[OQ6MIZUW]"; GS = [10, 20, 30, 50]; SS = [10, 20, 30]; TMIN = 30

def conn():
    import wrds
    db = wrds.Connection(wrds_username=open(Path.home() / ".pgpass").readline().split(":")[3].strip())
    return db.engine.connect()

def dsf(year):
    fn = ROOT / f"dsf_{year}.parquet"
    if fn.exists(): return pd.read_parquet(fn)
    c = conn()
    x = pd.read_sql_query(f"select permno, dlycaldt date, ticker, abs(dlyprc) prc, dlyvol vol, securitytype st, securitysubtype ss, primaryexch ex "
                          f"from crsp.dsf_v2 where dlycaldt between '{year-1}-12-01' and '{year}-12-31' and securitytype='EQTY'", c)
    x["date"] = pd.to_datetime(x.date); x.to_parquet(fn); return x

def pick_days(year):
    f = dsf(year); ds = sorted(f.date.unique()); ds = [d for d in ds if d.year == year and pd.Timestamp(f"{year}-02-01") <= d <= pd.Timestamp(f"{year}-11-20")]
    bad = {(7, 3), (11, 27), (11, 28), (12, 24)}   # early-close days to avoid
    ds = [d for d in ds if (d.month, d.day) not in bad and not (d.month == 11 and d.day in (23, 24, 25, 26, 27, 28, 29))]
    rnd = random.Random(SEED + year); return sorted(rnd.sample(ds, NDAY))

def names_for(year, d, rnd):
    f = dsf(year); f = f[f.ss == "COM"].copy(); f["dv"] = f.prc * f.vol
    f = f.sort_values(["permno", "date"]); g = f.groupby("permno")
    f["adv"] = g.dv.transform(lambda s: s.shift(1).rolling(20, min_periods=15).median()); f["pcl"] = g.prc.shift(1)
    x = f[(f.date == d) & (f.pcl >= 5) & f.ticker.str.fullmatch(r"[A-Z]{1,5}", na=False) & f.ex.isin(["N", "Q", "A"])]
    out = []
    for bn, lo, hi in BUCKETS:
        for pn, pl, ph in (("p<20", 0, 20), ("p>=20", 20, 1e9)):
            c = x[(x.adv >= lo) & (x.adv < hi) & (x.pcl >= pl) & (x.pcl < ph)]
            c = c.drop_duplicates("ticker").sort_values("ticker")
            idx = rnd.sample(range(len(c)), min(NPER, len(c)))
            for i in idx:
                r = c.iloc[i]; out.append((r.ticker, bn, pn, float(r.adv), float(r.pcl)))
    for e in ETFS: out.append((e, "ETF", e, np.nan, np.nan))
    return pd.DataFrame(out, columns=["sym", "bucket", "pxb", "adv", "pcl"])

def run_day(c, d, year):
    rnd = random.Random(SEED * 1000 + int(d.strftime("%Y%m%d")))
    nm = names_for(year, d, rnd); ds = d.strftime("%Y%m%d")
    dec = []
    for n, a, b in TOD:
        h0, m0, _ = map(int, a.split(":")); h1, m1, _ = map(int, b.split(":"))
        s0 = h0 * 3600 + m0 * 60; s1 = h1 * 3600 + m1 * 60 - 60
        for s in sorted(rnd.sample(range(s0, s1), K)): dec.append((f"{s//3600:02d}:{s%3600//60:02d}:{s%60:02d}", n))
    rq = lambda q: pd.read_sql_query(q, c)
    U = "u(sym) as (values " + ",".join(f"('{x}')" for x in nm.sym) + ")"
    TR = f"""tr as (select c.sym_root sym, c.time_m tm, c.tr_seqnum sq, c.price::float8 p, c.size::float8 z,
          (coalesce(c.tr_scond,'') ~ '{BAD}') bad, (coalesce(c.tr_scond,'') ~ 'I') odd, (c.ex <> 'D') lit,
          (abs(c.price*100 - round(c.price*100)) > 0.000001) subp
          from taqm_{year}.ctm_{ds} c join u on u.sym=c.sym_root
          where c.sym_suffix is null and c.time_m >= '09:30:00' and c.time_m < '16:00:00' and c.tr_corr='00' and c.price>0 and c.size>0)"""
    QQ = f"""q as (select n.sym_root sym, n.time_m tm, 0::bigint nano, n.best_bid::float8 bb, n.best_ask::float8 ba
          from taqm_{year}.complete_nbbo_{ds} n join u on u.sym=n.sym_root
          where n.sym_suffix is null and n.time_m >= '09:00:00' and n.time_m < '16:00:00' and n.best_bid>0 and n.best_ask>n.best_bid
            and n.best_ask/n.best_bid-1 < 0.3)"""
    # as-of: non-quote events (k=0) see the last quote strictly before them in (tm,k,sq) order (same-ms quotes are not used)
    def merge(nonq):
        return f"""ev as ({nonq} union all select sym, tm, 1 k, nano sq, null::float8 p, null::float8 z, null::float8 ts, null::float8 lit, null::bigint did, bb, ba from q),
          g as (select *, sum(k) over (partition by sym order by tm, k, sq rows unbounded preceding) qg from ev),
          m as (select *, max(bb) over (partition by sym, qg) mb, max(ba) over (partition by sym, qg) ma from g where true)"""
    # 1) effective + quoted spreads inside random 5-min windows (3 per tod bucket); quotes looked up 10 min back
    wl = []
    for n, a, b in TOD:
        h0, m0, _ = map(int, a.split(":")); h1, m1, _ = map(int, b.split(":"))
        s0 = h0 * 3600 + m0 * 60; s1 = h1 * 3600 + m1 * 60 - WMIN * 60
        for s in sorted(rnd.sample(range(s0, s1), NW)): wl.append((s, n))
    WW = "ww(wid,ws,we,tod) as (values " + ",".join(f"({i},'{s//3600:02d}:{s%3600//60:02d}:{s%60:02d}'::time,'{(s+WMIN*60)//3600:02d}:{(s+WMIN*60)%3600//60:02d}:{(s+WMIN*60)%60:02d}'::time,'{n}')" for i, (s, n) in enumerate(wl)) + ")"
    TRW = f"""tr as (select c.sym_root sym, c.time_m tm, c.tr_seqnum sq, c.price::float8 p, c.size::float8 z,
          (coalesce(c.tr_scond,'') ~ '{BAD}') bad, (coalesce(c.tr_scond,'') ~ 'I') odd, (c.ex <> 'D') lit,
          (abs(c.price*100 - round(c.price*100)) > 0.000001) subp
          from taqm_{year}.ctm_{ds} c join u on u.sym=c.sym_root
          where c.sym_suffix is null and c.time_m >= '09:30:00' and c.time_m < '16:00:00' and c.tr_corr='00' and c.price>0 and c.size>0)"""
    both = rq(f"""with {U}, {WW}, {TRW}, {QQ},
      trw as (select tr.*, ww.wid, ww.tod from tr join ww on tr.tm >= ww.ws and tr.tm < ww.we where not bad),
      t1 as (select sym, wid, tod, tm, sq, p, z, lit, sign(p - lag(p) over (partition by sym, wid order by tm, sq)) tk from trw),
      t2 as (select *, count(nullif(tk,0)) over (partition by sym, wid order by tm, sq) tg from t1),
      t3 as (select *, sum(tk) over (partition by sym, wid, tg) tsum from t2),
      qw as (select q.sym, ww.wid, q.tm, q.nano, q.bb, q.ba from q join ww on q.tm >= ww.ws - interval '10 minutes' and q.tm < ww.we),
      gr as (select u.sym, ww.wid, ww.tod, ww.ws + g*interval '1 minute' tm from u, ww, generate_series(0,{WMIN-1}) g),
      ev as (select sym, wid, tod, tm, 0 k, sq, p, z, tsum::float8 ts, lit::int lit, null::float8 bb, null::float8 ba from t3
             union all select sym, wid, tod, tm, 0, -1::bigint, null::float8, null::float8, null::float8, -1, null::float8, null::float8 from gr
             union all select sym, wid, null, tm, 1, nano, null::float8, null::float8, null::float8, null::int, bb, ba from qw),
      g as (select *, sum(k) over (partition by sym, wid order by tm, k, sq rows unbounded preceding) qg from ev),
      m as (select *, max(bb) over (partition by sym, wid, qg) mb, max(ba) over (partition by sym, wid, qg) ma from g),
      h as (select sym, tod, z, lit, (mb+ma)/2 mid, (ma-mb)/((ma+mb)/2)*10000 sp,
              case when p>(mb+ma)/2 then 1 when p<(mb+ma)/2 then -1 else coalesce(sign(ts),0) end sgn, p
            from m where k=0 and mb is not null)
      select sym, tod, sgn::int sgn, count(*) n, sum(z) shr, avg(hs) hs_mean, percentile_cont(0.5) within group (order by hs) hs_med,
             avg(hs) filter (where lit>0) hs_lit_mean, count(*) filter (where lit>0) n_lit, avg(hs) filter (where lit=0) hs_off_mean, count(*) filter (where lit=0) n_off,
             null::float8 qs_mean, null::float8 qs_med, null::float8 mid
      from (select *, least(greatest(sgn*(p-mid)/mid*10000,-1000),1000) hs from h where lit>=0 and sgn<>0) a group by sym, tod, sgn
      union all
      select sym, tod, 0, count(*), null, null, null, null, null, null, null, avg(sp), percentile_cont(0.5) within group (order by sp), avg(mid)
      from h where lit<0 group by sym, tod""")
    eff = both[both.sgn != 0].drop(columns=["qs_mean", "qs_med", "mid"]); qs = both[both.sgn == 0][["sym", "tod", "n", "qs_mean", "qs_med", "mid"]]
    # 2) decisions: entry = last ask in prior 10 min; touch / through; stop slippage
    DV = "dv(dt,tod) as (values " + ",".join(f"('{t}'::time,'{n}')" for t, n in dec) + ")"
    DEC = f"""dc as (select row_number() over () did, u.sym, dv.dt, dv.tod, least(dv.dt + interval '{TMIN} minutes', time '15:59:59.999') te from u cross join dv),
      d2 as (select distinct on (dc.did) dc.did, dc.sym, dc.dt, dc.tod, dc.te, q.ba a0, q.bb b0 from dc join q on q.sym=dc.sym and q.tm<dc.dt and q.tm>=dc.dt - interval '10 minutes'
             order by dc.did, q.tm desc, q.nano desc)"""
    tt = rq(f"""with {U}, {DV}, {TRW}, {QQ}, {DEC},
      ag as (select d.did, d.sym, d.tod, d.dt, d.a0, d.b0,
        {",".join(f"max(t.p) >= d.a0*(1+{g}/10000.0) touch{g}" for g in GS)},
        {",".join(f"coalesce(sum(t.z) filter (where t.lit and not t.bad and not t.odd and not t.subp and t.p > d.a0*(1+{g}/10000.0)),0) >= 100 thru{g}" for g in GS)},
        count(t.p) ntr
        from d2 d left join tr t on t.sym=d.sym and t.tm>d.dt and t.tm<=d.te group by d.did, d.sym, d.tod, d.dt, d.a0, d.b0),
      tq as (select d.did, {",".join(f"case when d.b0 <= d.a0*(1-{S}/10000.0) then d.dt else min(q.tm) filter (where q.bb <= d.a0*(1-{S}/10000.0)) end tq{S}" for S in SS)}
             from d2 d left join q on q.sym=d.sym and q.tm>d.dt and q.tm<=d.te group by d.did, d.b0, d.a0, d.dt),
      x as (select ag.did, ag.sym, ag.a0, ag.dt, 10 S, tq10 tq from ag join tq using (did) where tq10 is not null
            union all select ag.did, ag.sym, ag.a0, ag.dt, 20, tq20 from ag join tq using (did) where tq20 is not null
            union all select ag.did, ag.sym, ag.a0, ag.dt, 30, tq30 from ag join tq using (did) where tq30 is not null),
      nx as (select distinct on (x.did, x.S) x.did, x.S, (x.tq = x.dt) imm, x.a0*(1-x.S/10000.0) lvl, t.p stp
             from x join tr t on t.sym=x.sym and t.tm>x.tq and t.tm<=x.tq + interval '10 minutes' and not t.bad
             order by x.did, x.S, t.tm, t.sq)
      select ag.*, {",".join(f"max(nx.stp) filter (where nx.S={S}) stp{S}, max(nx.lvl) filter (where nx.S={S}) lvl{S}, bool_or(nx.imm) filter (where nx.S={S}) imm{S}" for S in SS)}
      from ag left join nx using (did) group by ag.did, ag.sym, ag.tod, ag.dt, ag.a0, ag.b0, {",".join(f"ag.touch{g}, ag.thru{g}" for g in GS)}, ag.ntr""")
    tt["dt"] = tt.dt.astype(str)
    for df in (eff, qs, tt): df["date"] = d
    return eff.merge(nm, on="sym"), qs.merge(nm, on="sym"), tt.merge(nm, on="sym")

_c = None
def work(a):
    global _c
    d, year = a; fn = DAYS / f"{d:%Y%m%d}"
    if (DAYS / f"{d:%Y%m%d}_dec.parquet").exists(): return d, "cached", 0
    t = time.time()
    try:
        if _c is None: _c = conn()
        eff, qs, tt = run_day(_c, d, year)
        eff.to_parquet(f"{fn}_eff.parquet"); qs.to_parquet(f"{fn}_qs.parquet"); tt.to_parquet(f"{fn}_dec.parquet")
        return d, f"ok eff{len(eff)} qs{len(qs)} dec{len(tt)}", time.time() - t
    except Exception as e:
        import traceback; _c = None; return d, "ERR " + traceback.format_exc()[-600:], time.time() - t

if __name__ == "__main__":
    if sys.argv[1] == "run":
        from concurrent.futures import ProcessPoolExecutor
        nw = min(4, int(sys.argv[2]) if len(sys.argv) > 2 else 4); lim = int(sys.argv[3]) if len(sys.argv) > 3 else None
        jobs = [(d, y) for y in YEARS for d in pick_days(y)]
        (ROOT / "days_chosen.txt").write_text("\n".join(f"{d:%Y-%m-%d}" for d, _ in jobs))
        if lim: jobs = jobs[:lim] if lim > 0 else jobs[lim:]
        t0 = time.time()
        with ProcessPoolExecutor(nw) as ex:
            for d, st, dt in ex.map(work, jobs): print(f"{d:%Y-%m-%d} {st} {dt:.0f}s [{time.time()-t0:.0f}s]", flush=True)
