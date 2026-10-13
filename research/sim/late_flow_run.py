"""LATE-FLOW daily aggregation driver: resumable, per-day cache data/research/late_flow/days/YYYYMMDD.parquet, <=4 workers.
usage: late_flow_run.py START END [NWORK] [LIMIT_DAYS]"""
import sys, time, traceback
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import pandas as pd, wrds
sys.path.insert(0, "research/sim")
import late_flow_univ as U
from late_flow_day import agg_day
OUT = Path("data/research/late_flow/days"); OUT.mkdir(parents=True, exist_ok=True)
_db = None; _f = None; _nm = None
def work(d):
    global _db, _f, _nm
    fn = OUT / f"{d:%Y%m%d}.parquet"
    if fn.exists(): return d, "cached", 0.0
    t = time.time()
    try:
        if _db is None:
            _db = wrds.Connection(wrds_username=open(Path.home() / ".pgpass").readline().split(":")[3].strip())
            _f = U.load(); _nm = U.names()
        x = U.universe(_f, _nm, d)
        lk = _db.raw_sql(f"select sym_root,sym_suffix,permno,match_lvl from wrdsapps_link_crsp_taqm.taqmclink where date='{d:%Y-%m-%d}' "
                         f"and permno in ({','.join(map(str, x.permno))})")
        lk = lk.sort_values("match_lvl").drop_duplicates("permno")
        pairs = [(r.sym_root, "" if pd.isna(r.sym_suffix) else r.sym_suffix, int(r.permno)) for r in lk.itertuples()]
        a = agg_day(_db, d, pairs)
        a["permno"] = a.permno.astype("int64")
        r = x[["permno", "adv_sh", "adv_dv", "pclose"]].merge(a, on="permno", how="left")
        r["date"] = d; r["n_univ"] = len(x); r["n_linked"] = len(lk)
        r.to_parquet(fn)
        return d, "ok", time.time() - t
    except Exception as e:
        _db = None
        return d, "ERR " + repr(e)[:150], time.time() - t
if __name__ == "__main__":
    a, b = pd.Timestamp(sys.argv[1]), pd.Timestamp(sys.argv[2]); nw = min(4, int(sys.argv[3]) if len(sys.argv) > 3 else 4)
    lim = int(sys.argv[4]) if len(sys.argv) > 4 else None
    f = pd.read_parquet("data/research/late_flow/dsf.parquet", columns=["date"])
    days = [d for d in sorted(f.date.unique()) if a <= d <= b]
    days = [pd.Timestamp(d) for d in days]
    if lim: days = days[:lim]
    t0 = time.time(); n = 0
    with ProcessPoolExecutor(nw) as ex:
        for d, st, dt in ex.map(work, days):
            n += 1; print(f"{d:%Y-%m-%d} {st} {dt:.0f}s  [{n}/{len(days)} {time.time()-t0:.0f}s]", flush=True)
