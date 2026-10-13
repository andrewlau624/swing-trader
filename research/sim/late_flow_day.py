"""LATE-FLOW per-day TAQ aggregation (server-side). Lee-Ready vs prevailing NBBO mid (as-of via window grouping), tick test at the mid.
agg_day(db, date, pairs) -> DataFrame(permno, sflow, vol, n, n_mid, n_nq). pairs = [(sym_root, sym_suffix, permno)]."""
import pandas as pd
BAD = "[OQ6MIZU]"   # auction prints O,Q,6,M (registered) + odd-lot I + out-of-sequence Z,U

def agg_day(db, d, pairs):
    ds = pd.Timestamp(d).strftime("%Y%m%d"); y = ds[:4]
    vals = ",".join("('%s','%s',%d)" % (r.replace("'", "''"), (s or "").replace("'", "''"), p) for r, s, p in pairs)
    sql = f"""
with u(root,sfx,permno) as (values {vals}),
t0 as (select u.permno, c.sym_root r, coalesce(c.sym_suffix,'') s, c.time_m tm, c.tr_seqnum sq, c.price p, c.size z
       from taqm_{y}.ctm_{ds} c join u on u.root=c.sym_root and u.sfx=coalesce(c.sym_suffix,'')
       where c.time_m >= '15:00:00' and c.time_m < '15:45:00' and c.tr_corr='00' and c.price>0 and c.size>0
         and coalesce(c.tr_scond,'') !~ '{BAD}'),
t1 as (select *, sign(p - lag(p) over (partition by r,s order by tm,sq)) tk from t0),
t2 as (select *,
              count(nullif(tk,0)) over (partition by r,s order by tm,sq) tg from t1),
t3 as (select *, sum(tk) over (partition by r,s,tg) tsign from t2),
q as (select u.permno, n.sym_root r, coalesce(n.sym_suffix,'') s, n.time_m tm, n.best_bid bb, n.best_ask ba
      from taqm_{y}.complete_nbbo_{ds} n join u on u.root=n.sym_root and u.sfx=coalesce(n.sym_suffix,'')
      where n.time_m >= '14:50:00' and n.time_m < '15:45:00' and n.best_bid>0 and n.best_ask>n.best_bid),
ev as (select permno,r,s,tm,0 k,sq,p,z,tsign,null::numeric bb,null::numeric ba from t3
       union all select permno,r,s,tm,1,null::int,null::numeric,null::int,null::numeric,bb,ba from q),
g as (select *, sum(k) over (partition by r,s order by tm,k,sq rows unbounded preceding) qg from ev),
m as (select *, max(bb) over (partition by r,s,qg) mb, max(ba) over (partition by r,s,qg) ma from g),
sg as (select permno, z, case when mb is not null and p>(mb+ma)/2 then 1 when mb is not null and p<(mb+ma)/2 then -1
                              else coalesce(tsign,0) end sgn, (mb is not null and p=(mb+ma)/2) atmid, (mb is null) noq
       from m where k=0)
select permno, sum(sgn*z)::float8 sflow, sum(z)::float8 vol, count(*) n, sum(atmid::int) n_mid, sum(noq::int) n_nq from sg group by permno"""
    return db.raw_sql(sql)
