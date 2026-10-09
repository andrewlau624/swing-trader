"""Study OPENSIG (round1_prose.md, N 907 -> 911): open-time signal to hold a night pick to the close instead of selling at the 09:30 auction.
Judge 2016-20 exact picks; S4 fit on 2021-26. Reuses NEXIT picks + fm1 minute bars. One run, no tuning.
Run: PYTHONPATH=. .venv/bin/python research/sim/opensig.py"""
import sys, os
REPO = "/Users/andrewlau/Documents/Code/Projects/swing-trader"; sys.path.insert(0, f"{REPO}/research/sim"); os.chdir(REPO)
import numpy as np, pandas as pd
from nexit import picks, FM, N
OUT = f"{REPO}/data/research/program/opensig_out.txt"

df = picks()
a = pd.read_parquet(f"{REPO}/data/research/program/night_exact_pre2021.parquet").reset_index()[["date", "sym", "day_ret"]]
a["date"] = pd.to_datetime(a.date)
P = pd.read_pickle(f"{N}/panel.pkl"); C = P["close"]; R1 = C / C.shift(1) - 1
df = df.merge(a, on=["date", "sym"], how="left")
m = df.day_ret.isna()
df.loc[m, "day_ret"] = [R1.at[d, s] if s in R1 and d in R1.index else np.nan for d, s in zip(df.date[m], df.sym[m])]
e = pd.read_parquet(f"{N}/etf_daily.parquet"); e = e[e.symbol == "SPY"].copy()
e["d"] = pd.to_datetime(e.timestamp).dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
e = e.set_index("d").sort_index(); spy = (e.open / e.close.shift(1) - 1)

rows = []
for nd, g in df.groupby("nd"):
    p = f"{FM}/{nd.date()}.parquet"
    if not os.path.exists(p): continue
    mb = pd.read_parquet(p)
    if not len(mb): continue
    t = pd.to_datetime(mb.timestamp).dt.tz_convert("America/New_York"); mb["hm"] = t.dt.hour * 100 + t.dt.minute
    mb = mb[(mb.hm >= 930) & (mb.hm <= 1559)]
    for r in g.itertuples():
        b = mb[mb.symbol == r.sym]
        if len(b) < 30 or b.hm.iloc[0] != 930: continue
        rows.append({"date": r.date, "era": r.era, "ovn": r.ovn, "drop": r.day_ret, "spy": spy.get(nd, np.nan),
                     "lp": np.log(b.open.iloc[0]), "oc": b.close.iloc[-1] / b.open.iloc[0] - 1})
X = pd.DataFrame(rows).dropna()
F = ["ovn", "spy", "drop", "lp"]
fit = X[X.era == "report"]; A = np.c_[np.ones(len(fit)), fit[F].clip(-.25, .25)]
beta = np.linalg.lstsq(A, fit.oc.clip(-.25, .25), rcond=None)[0]
X["pred"] = np.c_[np.ones(len(X)), X[F].clip(-.25, .25)] @ beta
RULES = {"S1 ovn<=0": X.ovn <= 0, "S2 ovn<=-2%": X.ovn <= -0.02, "S3 ovn<=0 & spy<=0": (X.ovn <= 0) & (X.spy <= 0), "S4 OLS pred>=20bp": X.pred >= 20e-4}
L = [f"OPENSIG  n {len(X)} (judge {sum(X.era=='judge')}, report {sum(X.era=='report')})",
     "S4 beta (const, " + ", ".join(F) + "): " + ", ".join(f"{b:+.4f}" for b in beta)]
for era in ["judge", "report"]:
    E = X.era == era; split = "2019" if era == "judge" else "2024"
    L.append(f"\n== {era}  {X.date[E].min().date()}..{X.date[E].max().date()}  days {X.date[E].nunique()}  B0 open mean {X.ovn[E].mean()*1e4:+.1f}bp")
    for k, h in RULES.items():
        h = h & E; held = X.oc[h]
        out = []
        for cost in [0, 5]:
            d = np.where(h, (1 + X.ovn) * X.oc - cost / 1e4, 0.0)[E]
            dm = pd.Series(d).groupby(X.date[E].values).mean()
            t = dm.mean() / dm.std() * np.sqrt(len(dm))
            if cost == 0:
                h1 = dm[dm.index < split].mean(); h2 = dm[dm.index >= split].mean(); ex5 = dm.drop(dm.nlargest(5).index).mean()
                exm = dm[~((dm.index >= "2020-03-01") & (dm.index < "2020-04-01"))].mean()
                m0, t0 = dm.mean(), t
            else: m5 = dm.mean()
        ok = m0 >= 10e-4 and m5 > 0 and t0 >= 2.5 and h1 > 0 and h2 > 0 and ex5 > 0 and exm > 0 and held.median() > 0
        L.append(f"  {k:20s} held {100*h[E].mean():4.0f}%  held o->c mean {held.mean()*1e4:+6.1f} med {held.median()*1e4:+6.1f}  | per-day gain {m0*1e4:+6.1f}bp (5bp {m5*1e4:+6.1f})"
                 f"  t {t0:+5.2f}  halves {h1*1e4:+6.1f}/{h2*1e4:+6.1f}  ex-top5d {ex5*1e4:+6.1f}  ex-Mar20 {exm*1e4:+6.1f}" + (f"  GATE {'PASS' if ok else 'fail'}" if era == "judge" else ""))
open(OUT, "w").write("\n".join(L) + "\n"); print("\n".join(L))
