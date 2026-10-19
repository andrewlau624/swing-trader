"""BRANCH R probe 1: TAQ pull for PREF/ETD E-1 closing crosses (execution-economics, touched data, no N).
    .venv/bin/python -m research.sim.branch_r_probe.taq_pull [ndates]
Symbol convention (found, not guessed): preferreds root=issuer, suffix='PR'+series ('BAC.PRO' -> BAC/PRO);
baby bonds/ETDs of >=5 letters root=ticker[:-1], suffix=last letter (TANNZ -> TANN/Z), <=4 letters root=ticker, suffix NULL.
Closing cross = trade with tr_scond containing '6' (size = cross shares, price = official close)."""
import sys, pathlib, numpy as np, pandas as pd, wrds
ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = ROOT / "data/research/branch_r"; OUT.mkdir(parents=True, exist_ok=True)

def pairs(sym, src):
    if src == "pref" and ".PR" in sym:
        r, s = sym.split("."); return [(r, s)]
    if len(sym) >= 5: return [(sym[:-1], sym[-1]), (sym, None)]
    return [(sym, None)]

def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 220
    ev = []
    for src in ("pref", "etdx"):
        e = pd.read_parquet(ROOT / f"data/research/{src}/events.parquet"); e["src"] = src; ev.append(e)
    ev = pd.concat(ev); ev = ev[(ev.d0 >= "2021-01-01") & (ev.d0 <= "2025-11-30")]
    dates = np.array(sorted(ev.d0.unique())); rng = np.random.default_rng(7)
    pick = set(rng.choice(dates, min(n, len(dates)), replace=False))
    ev = ev[ev.d0.isin(pick)]
    db = wrds.Connection(wrds_username="andrewlau624"); rows = []
    for k, (d0, g) in enumerate(ev.groupby("d0")):
        ds = pd.Timestamp(d0).strftime("%Y%m%d")
        for r in g.itertuples():
            for root, suf in pairs(r.sym, r.src):
                sc = "sym_suffix is null" if suf is None else f"sym_suffix='{suf}'"
                try:
                    c = db.raw_sql(f"select time_m,price,size,tr_scond,ex from taqmsec.ctm_{ds} where sym_root='{root}' and {sc} and time_m>='09:30:00' and time_m<='16:30:00' order by time_m")
                except Exception as ex_:
                    print("ERR", ds, root, suf, str(ex_)[:80]); continue
                if len(c) == 0: continue
                c["tm"] = pd.to_timedelta(c.time_m.astype(str)).dt.total_seconds()
                cs = c.tr_scond.fillna("").astype(str)
                x = c[cs.str.contains("6") & (c.tm >= 15.99 * 3600)]
                if len(x) == 0: continue
                q = db.raw_sql(f"select time_m,best_bid,best_ask,best_bidsiz,best_asksiz from taqmsec.nbbom_{ds} where sym_root='{root}' and {sc} and time_m<='16:00:00' order by time_m")
                q["tm"] = pd.to_timedelta(q.time_m.astype(str)).dt.total_seconds()
                q = q[(q.best_ask > q.best_bid) & (q.best_bid > 0)]
                def at(t):
                    z = q[q.tm <= t]
                    if len(z) == 0: return (np.nan,) * 4
                    z = z.iloc[-1]; return (z.best_bid, z.best_ask, z.best_bidsiz, z.best_asksiz)
                b50, a50, bs50, as50 = at(15 * 3600 + 50 * 60); b59, a59, bs59, as59 = at(15 * 3600 + 59 * 60 + 50)
                pre = c[(c.tm < 16 * 3600 - 5) & ~cs.str.contains("6|M")]
                px = float((x.price * x["size"]).sum() / x["size"].sum())
                rows.append(dict(t=r.ticker, src=r.src, d0=d0, d=r.date, pc=r.pc, dv=r.dv, X_sh=float(x["size"].sum()), px=px,
                                 b50=b50, a50=a50, bs50=bs50, as50=as50, b59=b59, a59=a59, bs59=bs59, as59=as59,
                                 pre_usd=float((pre.price * pre["size"]).sum()), pre_n=len(pre),
                                 last_pre=float(pre.price.iloc[-1]) if len(pre) else np.nan))
                break
        if k % 20 == 0:
            print(k, len(rows), flush=True); pd.DataFrame(rows).to_parquet(OUT / "taq_cross.parquet")
    pd.DataFrame(rows).to_parquet(OUT / "taq_cross.parquet"); print("done", len(rows))

if __name__ == "__main__": main()
