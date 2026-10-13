"""LUCK-B4 data pull (discovery window only: 2000-06..2011-01). Caches to data/research/wrds_b4/."""
import pandas as pd, wrds
from pathlib import Path
O = Path("data/research/wrds_b4"); O.mkdir(parents=True, exist_ok=True)
u = open(Path.home() / ".pgpass").readline().split(":")[3].strip()
db = wrds.Connection(wrds_username=u)
A, B = "2000-06-01", "2011-02-04"   # B: exits of late-2010 entries (21d) use Jan-2011 closes only
def sv(df, n): df.to_parquet(O / n); print(n, len(df), flush=True)
sv(db.raw_sql(f"select permno,date,prc,openprc,ret,vol,shrout from crsp.dsf where date between '{A}' and '{B}'", date_cols=["date"]), "dsf.parquet")
sv(db.raw_sql("select permno,namedt,nameendt,shrcd,exchcd from crsp.dsenames", date_cols=["namedt", "nameendt"]), "names.parquet")
sv(db.raw_sql(f"select permno,dlstdt,dlstcd,dlret from crsp.dsedelist where dlstdt between '{A}' and '{B}'", date_cols=["dlstdt"]), "delist.parquet")
sv(db.raw_sql("select secid,sdate,edate,permno,score from wrdsapps.opcrsphist", date_cols=["sdate", "edate"]), "link.parquet")
sv(db.raw_sql("select gvkey,iid,shortint,datadate from comp.sec_shortint where datadate<='2011-01-31'", date_cols=["datadate"]), "si.parquet")
sv(db.raw_sql("select gvkey,lpermno as permno,linktype,linkprim,linkdt,linkenddt from crsp.ccmxpf_linktable where linktype in ('LC','LU')", date_cols=["linkdt", "linkenddt"]), "ccm.parquet")
sv(db.raw_sql(f"select secid,date,cp_flag,volume from optionm.opvold where date between '{A}' and '{B}' and cp_flag in ('C','P')", date_cols=["date"]), "opvold.parquet")
for y in range(2000, 2012):
    sv(db.raw_sql(f"select secid,date,days,delta,impl_volatility as iv from optionm.vsurfd{y} where days in (30,91) and delta in (50,-50,-25) and date between '{A}' and '{B}' and impl_volatility is not null", date_cols=["date"]), f"vs{y}.parquet")
