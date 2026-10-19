"""BRANCH R probe 2: open cross on ex-date E (tr_scond 'Q' at ~09:30) for the same sampled events as taq_pull."""
import pathlib, numpy as np, pandas as pd, wrds
from .taq_pull import pairs, ROOT, OUT

def main():
    base = pd.read_parquet(OUT / "taq_cross.parquet")
    ev = pd.concat([pd.read_parquet(ROOT / f"data/research/{s}/events.parquet").assign(src=s) for s in ("pref", "etdx")])
    ev = ev.rename(columns={"ticker": "t"})[["t", "src", "date", "sym"]].drop_duplicates(["t", "date"])
    base = base.merge(ev, left_on=["t", "src", "d"], right_on=["t", "src", "date"], how="left")
    db = wrds.Connection(wrds_username="andrewlau624"); rows = []
    for k, (d, g) in enumerate(base.groupby("d")):
        ds = pd.Timestamp(d).strftime("%Y%m%d")
        for r in g.itertuples():
            for root, suf in pairs(r.sym, r.src):
                sc = "sym_suffix is null" if suf is None else f"sym_suffix='{suf}'"
                c = db.raw_sql(f"select time_m,price,size,tr_scond from taqmsec.ctm_{ds} where sym_root='{root}' and {sc} and time_m>='09:29:00' and time_m<='09:31:00' order by time_m")
                if len(c) == 0: continue
                cs = c.tr_scond.fillna("").astype(str)
                x = c[cs.str.contains("Q")]
                if len(x) == 0: continue
                q = db.raw_sql(f"select time_m,best_bid,best_ask from taqmsec.nbbom_{ds} where sym_root='{root}' and {sc} and time_m<='09:31:00' order by time_m")
                q["tm"] = pd.to_timedelta(q.time_m.astype(str)).dt.total_seconds()
                q = q[(q.best_ask > q.best_bid) & (q.best_bid > 0)]
                def at(t):
                    z = q[q.tm <= t]
                    return (np.nan, np.nan) if len(z) == 0 else (z.iloc[-1].best_bid, z.iloc[-1].best_ask)
                bo, ao = at(9 * 3600 + 30 * 60 + 30); bp, ap = at(9 * 3600 + 29 * 60 + 50)
                rows.append(dict(t=r.t, d=d, open_sh=float(x["size"].iloc[0]), open_px=float(x.price.iloc[0]),
                                 bo=bo, ao=ao, bpre=bp, apre=ap)); break
        if k % 25 == 0: print(k, len(rows), flush=True)
    pd.DataFrame(rows).to_parquet(OUT / "taq_open.parquet"); print("done", len(rows))

if __name__ == "__main__": main()
