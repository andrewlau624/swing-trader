import pandas as pd,numpy as np
D="research/sim/branch_s_probe/out/"
s=pd.read_parquet(D+"samp.parquet");t=pd.read_parquet(D+"trace.parquet");r=pd.read_parquet(D+"rat.parquet")
for c in ["px","vol"]:t[c]=pd.to_numeric(t[c])
t=t[(t.wis_fl.astype(str)!="Y")]
print(len(t),t.cp.value_counts().to_dict(),t.side.value_counts().to_dict())
# rating class
def cls(g):
    g=g[g.rating_date<=g.name[1]] if False else g
    return g
sc={'AAA':1,'AA+':2,'AA':3,'AA-':4,'A+':5,'A':6,'A-':7,'BBB+':8,'BBB':9,'BBB-':10}
mc={'Aaa':1,'Aa1':2,'Aa2':3,'Aa3':4,'A1':5,'A2':6,'A3':7,'Baa1':8,'Baa2':9,'Baa3':10}
r["n"]=[sc.get(x) if a=='SPR' else mc.get(x) for x,a in zip(r.rating.astype(str).str.strip(),r.rating_type)]
rr=r.merge(s[["issue_id","offering_date"]],on="issue_id");rr["rating_date"]=pd.to_datetime(rr.rating_date,errors="coerce");rr=rr[rr.rating_date<=pd.to_datetime(rr.offering_date)+pd.Timedelta(days=30)]
rr=rr.sort_values("rating_date").groupby(["issue_id","rating_type"]).tail(1)
ig={}
for i,g in rr.groupby("issue_id"):
    nn=g.rating.astype(str).str.strip().tolist()
    ig[i]= "IG" if any(x in sc or x in mc for x in nn) else "HY"
s["cls"]=s.issue_id.map(ig); print(s.cls.value_counts(dropna=False).to_dict())
t=t.merge(s[["cusip","offering_date","offering_price","cls"]],left_on="cusip_id",right_on="cusip")
t["d"]=pd.to_datetime(t.d);t["od"]=pd.to_datetime(t.offering_date)
t["k"]=[np.busday_count(a.date(),b.date()) for a,b in zip(t.od,t.d)]
t["rel"]=(t.px/t.offering_price-1)*1e4  # bp of price vs offering, clean
c=t[t.cp=="C"]
# side check
print("side medians",c.groupby("side").rel.median().to_dict())
inst=c[c.vol>=1e6];ret_s=c[(c.vol<=1e5)&(c.side=="B")];ret_b=c[(c.vol<=1e5)&(c.side=="S")]
print("trades inst/retS/retB",len(inst),len(ret_s),len(ret_b))
rows=[]
for name,df in [("inst>=1MM",inst),("retail sell (dealer bids) <=100k",ret_s),("retail buy (dealer offers) <=100k",ret_b)]:
  for cl in ["IG","HY","all"]:
    d=df if cl=="all" else df[df.cls==cl]
    for k in [0,1,3,5,10]:
        # per-issue median, then cross-issue
        m=d[d.k==k].groupby("cusip_id").rel.median()
        if len(m)>5: rows.append((name,cl,k,len(m),m.median(),m.quantile(.25),m.quantile(.75),m.mean()))
R=pd.DataFrame(rows,columns="series class day n_issues med p25 p75 mean".split());print(R.round(1).to_string())
R.to_csv(D+"summary.csv",index=False)
# paired per issue: inst price at k vs retail bid at k
for cl in ["IG","HY"]:
  for k in [1,3,5,10]:
    a=inst[(inst.cls==cl)&(inst.k==k)].groupby("cusip_id").rel.median();b=ret_s[(ret_s.cls==cl)&(ret_s.k==k)].groupby("cusip_id").rel.median()
    j=pd.concat([a,b],axis=1,keys=["i","b"]).dropna()
    if len(j)>5:print(cl,k,"paired n",len(j),"inst-retbid gap med %.1f"%(j.i-j.b).median())
# day-0 retail buy vs offering: what a post-issue buyer would pay
