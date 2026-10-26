"""F-SALE2 (N 1060) data pull: CRSP MF flow-induced pressure by (permno, quarter), server-side aggregation, one year per query."""
import sys, time, pathlib
import pandas as pd, wrds
D = pathlib.Path(__file__).resolve().parents[2] / "data" / "research" / "fsale2"; D.mkdir(parents=True, exist_ok=True)
Q = """
with m as (
  select t.crsp_fundno, t.caldt, t.mtna, r.mret,
         lag(t.mtna) over (partition by t.crsp_fundno order by t.caldt) tna_prev,
         lag(t.caldt) over (partition by t.crsp_fundno order by t.caldt) dt_prev
  from crsp_q_mutualfunds.monthly_tna t
  join crsp_q_mutualfunds.monthly_returns r on r.crsp_fundno = t.crsp_fundno and r.caldt = t.caldt
  where t.caldt >= '{lo}'::date - interval '4 months' and t.caldt < '{hi}' and t.mtna > 0),
f as (select crsp_fundno, caldt, date_trunc('quarter', caldt)::date q, mtna - tna_prev*(1+coalesce(mret,0)) fl,
      case when extract(month from caldt) in (1,4,7,10) then tna_prev end tna0
      from m where tna_prev > 0 and dt_prev >= caldt - interval '45 days'),
fq as (select crsp_fundno, q, sum(fl) fl, sum(tna0) tna0 from f where q >= '{lo}' and q < '{hi}' group by 1,2),
pm as (select p.crsp_portno, fq.q, fq.crsp_fundno, fq.fl, fq.tna0
       from fq join crsp_q_mutualfunds.portnomap p on p.crsp_fundno = fq.crsp_fundno and fq.q >= p.begdt and fq.q <= coalesce(p.enddt, '2099-01-01')
       join crsp_q_mutualfunds.fund_style s on s.crsp_fundno = fq.crsp_fundno and fq.q >= s.begdt and fq.q <= coalesce(s.enddt, '2099-01-01')
         and s.crsp_obj_cd like 'ED%%'),
pq as (select crsp_portno, q, sum(fl)/nullif(sum(tna0),0) flowpct, sum(tna0) tna0 from pm group by 1,2 having sum(tna0) > 10),
pqf as (select * from pq where abs(flowpct) >= 0.05 and abs(flowpct) < 1),
hs as (select h.crsp_portno, h.report_dt, h.permno, sum(h.nbr_shares) sh
       from crsp_q_mutualfunds.holdings h
       where h.permno is not null and h.nbr_shares > 0 and h.report_dt >= '{lo}'::date - interval '6 months' and h.report_dt < '{hi}'
         and h.crsp_portno in (select crsp_portno from pqf)
       group by 1,2,3),
hq as (select pqf.crsp_portno, pqf.q, pqf.flowpct, hs.permno, hs.sh,
       dense_rank() over (partition by pqf.crsp_portno, pqf.q order by hs.report_dt desc) rk
       from pqf join hs on hs.crsp_portno = pqf.crsp_portno and hs.report_dt < pqf.q and hs.report_dt >= pqf.q - interval '6 months')
select permno, q,
       sum(case when flowpct <= -0.05 then flowpct*sh end) sell_sh, sum(case when flowpct >= 0.05 then flowpct*sh end) buy_sh,
       count(distinct case when flowpct <= -0.05 then crsp_portno end) n_sell, count(distinct case when flowpct >= 0.05 then crsp_portno end) n_buy,
       sum(case when flowpct <= -0.10 then flowpct*sh end) sell_sh10
from hq where rk = 1 group by 1,2
"""
db = wrds.Connection(wrds_username="andrewlau624", wrds_connect_attempts=2)
if not (D / "stocknames.parquet").exists():
    nm = db.raw_sql("select permno, namedt, nameenddt, ticker, ncusip, shrcd from crsp.stocknames")
    nm.to_parquet(D / "stocknames.parquet"); print("stocknames", len(nm), flush=True)
years = [int(a) for a in sys.argv[1:]] or list(range(2009, 2027))
for y in years:
    f = D / f"pressure_{y}.parquet"
    if f.exists(): continue
    t0 = time.time()
    x = db.raw_sql(Q.format(lo=f"{y}-01-01", hi=f"{y+1}-01-01"))
    x.to_parquet(f); print(y, len(x), "rows", x.permno.nunique(), "permnos", f"{time.time()-t0:.0f}s", flush=True)
print("DONE")
