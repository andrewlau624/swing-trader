"""LATE-FLOW data pull: CRSP dsf 2009-11..2016-01 + names/delist + taqmclink. Cache data/research/late_flow/."""
import pandas as pd, wrds
from pathlib import Path
O = Path("data/research/late_flow"); O.mkdir(parents=True, exist_ok=True)
u = open(Path.home() / ".pgpass").readline().split(":")[3].strip()
db = wrds.Connection(wrds_username=u)
A, B = "2009-10-01", "2016-01-31"
def sv(df, n): df.to_parquet(O / n); print(n, len(df), flush=True)
sv(db.raw_sql(f"select permno,date,prc,openprc,ret,vol,shrout from crsp.dsf where date between '{A}' and '{B}'", date_cols=["date"]), "dsf.parquet")
sv(db.raw_sql("select permno,namedt,nameendt,shrcd,exchcd from crsp.dsenames", date_cols=["namedt", "nameendt"]), "names.parquet")
sv(db.raw_sql(f"select permno,dlstdt,dlstcd,dlret from crsp.dsedelist where dlstdt between '{A}' and '{B}'", date_cols=["dlstdt"]), "delist.parquet")
sv(db.raw_sql(f"select permno,exdt,divamt,distcd from crsp.dsedist where exdt between '{A}' and '{B}'", date_cols=["exdt"]), "dist.parquet")
print(db.describe_table("wrdsapps_link_crsp_taqm","taqmclink")[["name","type"]].values.tolist())
sv(db.raw_sql("select * from wrdsapps_link_crsp_taqm.taqmclink where date between '2010-01-01' and '2015-12-31'"), "taqmclink.parquet")
