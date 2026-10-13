"""Study BOND-LEAD data pull. TRACE enhanced-clean: last institutional (>=100k) trade by 15:59:59 per (cusip, date), server-side.
Flags used (checked by distinct query): wis_fl='N', cmsn_trd IS DISTINCT FROM 'Y' (NULL = unflagged; field is NULL on every row from 2012-02 on), spcl_trd_fl IS NULL (only 'Y' observed),
asof_cd IS NULL (only 'A' observed). trd_exctn_tm is seconds since midnight; 15:59:59 = 57599.
Usage: .venv/bin/python -m research.sim.bond_lead_pull [start_year end_year]   (cache data/research/bond_lead/trace_YYYYMM.parquet)
Also pulls CRSP (dsf 2005-10..2016-01, dsenames, dsedelist) to data/research/bond_lead/crsp_*.parquet. Nothing after 2016-01-08 is read.
"""
import sys, pathlib, calendar, concurrent.futures as cf
import pandas as pd, wrds
D = pathlib.Path("data/research/bond_lead"); D.mkdir(parents=True, exist_ok=True)
U = open(pathlib.Path.home() / ".pgpass").readline().split(":")[3]
SQL = """select distinct on (cusip_id, trd_exctn_dt) cusip_id, trd_exctn_dt as d, trd_exctn_tm as tm, rptd_pr as px, entrd_vol_qt as vol
from wrdsapps_bondret.trace_enhanced_clean
where trd_exctn_dt between '{a}' and '{b}' and entrd_vol_qt >= 100000 and trd_exctn_tm <= 57599
  and wis_fl = 'N' and cmsn_trd is distinct from 'Y' and spcl_trd_fl is null and asof_cd is null and rptd_pr > 0
order by cusip_id, trd_exctn_dt, trd_exctn_tm desc, msg_seq_nb desc"""
def conn():
    import time
    for k in range(40):
        try: return wrds.Connection(wrds_username=U)
        except BaseException as e: time.sleep(min(60, 5 * (k + 1)))
    raise RuntimeError('wrds connect failed')
def month(ym):
    try: return month_(ym)
    except Exception as e: return f'FAIL {ym} {e}'
def month_(ym):
    y, m = ym; f = D / f"trace_{y}{m:02d}.parquet"
    if f.exists(): return f.name
    db = conn()
    try:
        df = db.raw_sql(SQL.format(a=f"{y}-{m:02d}-01", b=f"{y}-{m:02d}-{calendar.monthrange(y, m)[1]}"))
    finally: db.close()
    df["px"] = df.px.astype("float64"); df["vol"] = df.vol.astype("float64"); df["tm"] = df.tm.astype("float64")
    df.to_parquet(f); return f"{f.name} {len(df)}"
def crsp():
    db = conn()
    if not (D / "crsp_dsf.parquet").exists():
        x = db.raw_sql("select permno,date,ret,prc,vol,openprc,shrout from crsp.dsf where date between '2005-10-01' and '2016-01-08'")
        for c in ["ret","prc","vol","openprc","shrout"]: x[c] = pd.to_numeric(x[c], errors="coerce").astype("float64")
        x.to_parquet(D / "crsp_dsf.parquet")
    db.raw_sql("select 1")
    db.raw_sql("select permno,ncusip,shrcd,exchcd,namedt,nameendt from crsp.dsenames").to_parquet(D / "crsp_names.parquet")
    db.raw_sql("select permno,dlstdt,dlstcd,dlret,dlprc from crsp.dsedelist where dlstdt between '2005-10-01' and '2016-01-08'").to_parquet(D / "crsp_delist.parquet")
    db.close()
if __name__ == "__main__":
    a, b = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) > 2 else (2005, 2015)
    ms = [(y, m) for y in range(a, b + 1) for m in range(1, 13) if (y, m) >= (2005, 12)]
    if "--crsp" in sys.argv: crsp(); sys.exit()
    with cf.ThreadPoolExecutor(3) as ex:
        for r in ex.map(month, ms): print(r, flush=True)
