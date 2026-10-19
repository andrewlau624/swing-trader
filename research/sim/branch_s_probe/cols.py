import wrds,pathlib
U=open(pathlib.Path.home()/".pgpass").readline().split(":")[3]
db=wrds.Connection(wrds_username=U)
for t in ["fisd.fisd_mergedissue","wrdsapps_bondret.trace_enhanced_clean"]:
    s,n=t.split(".")
    print(t,list(db.raw_sql(f"select * from {t} limit 1").columns))
