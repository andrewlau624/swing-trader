"""LUCK-B5 data pull (discovery only: statpers 2000-01..2010-12). Caches to data/research/wrds_b5/."""
import pandas as pd, wrds
from pathlib import Path
O = Path("data/research/wrds_b5"); O.mkdir(parents=True, exist_ok=True)
u = open(Path.home() / ".pgpass").readline().split(":")[3].strip()
db = wrds.Connection(wrds_username=u)
def sv(df, n): df.to_parquet(O / n); print(n, len(df), flush=True)
sv(db.raw_sql("select ticker,statpers,fpi,numest,numup,numdown,meanest,medest,stdev,fpedats from ibes.statsumu_epsus "
              "where fpi in ('0','1') and measure='EPS' and statpers between '2000-01-01' and '2010-12-31'", date_cols=["statpers", "fpedats"]), "ibes.parquet")
sv(db.raw_sql("select ticker,permno,sdate,edate,score from wrdsapps.ibcrsphist where score<=2", date_cols=["sdate", "edate"]), "ibcrs.parquet")
