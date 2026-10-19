import wrds,pathlib,pandas as pd,numpy as np
D=pathlib.Path("research/sim/branch_s_probe/out")
U=open(pathlib.Path.home()/".pgpass").readline().split(":")[3]
iss=pd.read_parquet(D/"iss.parquet")
iss=iss.sample(500,random_state=7).reset_index(drop=True); iss.to_parquet(D/"samp.parquet")
db=wrds.Connection(wrds_username=U)
out=[]
for i in range(0,len(iss),50):
    ch=iss.iloc[i:i+50]
    v=",".join("('%s'::text,'%s'::date,'%s'::date)"%(r.cusip,r.offering_date.date() if hasattr(r.offering_date,'date') else r.offering_date,(pd.Timestamp(r.offering_date)+pd.Timedelta(days=16)).date()) for r in ch.itertuples())
    q=f"""select t.cusip_id,t.trd_exctn_dt d,t.trd_exctn_tm tm,t.rptd_pr px,t.entrd_vol_qt vol,t.rpt_side_cd side,t.cntra_mp_id cp,t.wis_fl,t.yld_pt
 from wrdsapps_bondret.trace_enhanced_clean t join (values {v}) v(c,a,b) on t.cusip_id=v.c and t.trd_exctn_dt between v.a and v.b
 where t.rptd_pr>0 and t.asof_cd is null and t.cmsn_trd is distinct from 'Y'"""
    out.append(db.raw_sql(q)); print(i,len(out[-1]),flush=True)
pd.concat(out).to_parquet(D/"trace.parquet")
