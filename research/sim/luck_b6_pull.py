"""LUCK-B6 data pull. CRSP shrcd 73 (dsenames/dsf/dsedelist, 2003-07-01..2013-01-31 only) + CRSP MF daily NAV link tables. Cache: data/research/wrds_b6/."""
import sys, time
from pathlib import Path
import pandas as pd, wrds

OUT = Path("data/research/wrds_b6"); OUT.mkdir(parents=True, exist_ok=True)
S0, S1 = "2003-07-01", "2013-01-31"


def conn():
    U = open(Path.home() / ".pgpass").readline().strip().split(":")[3]
    for a in range(8):
        try: return wrds.Connection(wrds_username=U)
        except Exception as e:
            print("conn retry", a, type(e).__name__, flush=True); time.sleep(20 * (a + 1))
    raise SystemExit("no connection")


def q(db, sql, **kw):
    for a in range(5):
        try: return db.raw_sql(sql, **kw)
        except Exception as e:
            print("query retry", a, type(e).__name__, str(e)[:120], flush=True); time.sleep(15); db.close(); db = conn()
    raise SystemExit("query failed")


def main():
    db = conn()
    if not (OUT / "names.parquet").exists():
        nm = q(db, "select permno, namedt, nameendt, shrcd, exchcd, ticker, ncusip, comnam from crsp.dsenames where shrcd = 73", date_cols=["namedt", "nameendt"])
        nm.to_parquet(OUT / "names.parquet"); print("names", len(nm), nm.permno.nunique(), flush=True)
    nm = pd.read_parquet(OUT / "names.parquet"); perms = sorted(nm.permno.unique().tolist())
    if not (OUT / "dsf.parquet").exists():
        parts = []
        for k in range(0, len(perms), 400):
            ch = ",".join(map(str, perms[k:k + 400]))
            parts.append(q(db, f"select permno, date, prc, openprc, ret, vol, shrout, cfacshr from crsp.dsf where permno in ({ch}) and date between '{S0}' and '{S1}'", date_cols=["date"]))
            print("dsf chunk", k, len(parts[-1]), flush=True)
        pd.concat(parts, ignore_index=True).to_parquet(OUT / "dsf.parquet")
    if not (OUT / "delist.parquet").exists():
        ch = ",".join(map(str, perms))
        q(db, f"select permno, dlstdt, dlstcd, dlret from crsp.dsedelist where permno in ({ch}) and dlstdt <= '{S1}'", date_cols=["dlstdt"]).to_parquet(OUT / "delist.parquet")
    for t in ("fund_hdr", "fund_hdr_hist"):
        if not (OUT / f"{t}.parquet").exists():
            try:
                cols = q(db, f"select column_name from information_schema.columns where table_schema='crsp_q_mutualfunds' and table_name='{t}'")
                print(t, "cols", cols.column_name.tolist(), flush=True)
                q(db, f"select * from crsp_q_mutualfunds.{t}").to_parquet(OUT / f"{t}.parquet")
            except SystemExit: raise
    if not (OUT / "nav.parquet").exists():
        h = pd.read_parquet(OUT / "fund_hdr.parquet"); h = h[h["et_flag"].isin(["F", "N"])]
        fn = sorted(h["crsp_fundno"].dropna().astype(int).unique().tolist()); parts = []
        for k in range(0, len(fn), 500):
            ch = ",".join(map(str, fn[k:k + 500]))
            parts.append(q(db, f"select crsp_fundno, caldt, dnav from crsp_q_mutualfunds.daily_nav where crsp_fundno in ({ch}) and caldt between '{S0}' and '{S1}'", date_cols=["caldt"]))
            print("nav chunk", k, len(parts[-1]), flush=True)
        pd.concat([p for p in parts if len(p)], ignore_index=True).to_parquet(OUT / "nav.parquet")
    print("done", flush=True)


if __name__ == "__main__":
    main()
