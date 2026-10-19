import wrds,pathlib,pandas as pd,numpy as np
D=pathlib.Path("research/sim/branch_s_probe/out");D.mkdir(exist_ok=True)
U=open(pathlib.Path.home()/".pgpass").readline().split(":")[3]
db=wrds.Connection(wrds_username=U)
iss=db.raw_sql("""select issue_id,complete_cusip as cusip,offering_date,offering_price,offering_yield,offering_amt,coupon,maturity,principal_amt,denomination,
 coupon_type,convertible,asset_backed,mtn,rule_144a,private_placement,slob,perpetual,foreign_currency,currency
from fisd.fisd_mergedissue where offering_date between '2015-01-01' and '2019-12-31' and complete_cusip is not null""")
n0=len(iss)
for c,v in dict(coupon_type='F',convertible='N',asset_backed='N',mtn='N',rule_144a='N',private_placement='N',slob='N',perpetual='N',foreign_currency='N').items():
    iss=iss[iss[c].astype(str)==v]
for c in ["principal_amt","offering_amt","offering_price","denomination"]: iss[c]=pd.to_numeric(iss[c],errors="coerce")
iss=iss[(iss.principal_amt==1000)&(iss.offering_amt>=300000)&iss.offering_price.between(98,101.5)]
print(n0,len(iss))
r=db.raw_sql("select issue_id,rating_type,rating,rating_date from fisd.fisd_ratings where issue_id in (%s) and rating_type in ('MR','SPR')"%",".join("'%s'"%i for i in iss.issue_id))
iss.to_parquet(D/"iss.parquet");r.to_parquet(D/"rat.parquet");print(len(r))
