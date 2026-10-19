import wrds,pathlib,pandas as pd
U=open(pathlib.Path.home()/".pgpass").readline().split(":")[3]
db=wrds.Connection(wrds_username=U)
x=db.raw_sql("select * from fisd.fisd_mergedissue where offering_date between '2016-03-01' and '2016-03-31' limit 400")
for c in ["coupon_type","convertible","asset_backed","mtn","rule_144a","private_placement","slob","perpetual","foreign_currency","currency","principal_amt"]: print(c,x[c].astype(str).value_counts().head(5).to_dict())
