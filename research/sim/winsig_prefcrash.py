"""PREF-CRASH judge (2005-15, one look): issuer-common crash -> buy preferred close t+1, sell close t+11."""
import numpy as np, pandas as pd
from research.sim import winsig as w, winsig_fam as F
lo, hi = "2005-01-01", "2015-12-31"
p = w.load_panel(kind="pref"); s = w.load_panel()
p["issuer"] = p.ticker.str.extract(r"^([A-Z.]+)-P")[0]
sg = s.groupby("ticker", sort=False); s["dr"] = s.closeadj / sg["closeadj"].shift(1) - 1
crash = s[(s.dr <= -0.08) & (s.closeunadj >= 3)][["ticker", "date"]].rename(columns={"ticker": "issuer"})
g = p.groupby("ticker", sort=False)
p["r"] = g["closeadj"].shift(-11) / g["closeadj"].shift(-1) - 1
p["x"] = p.r - p.r[p.liq].groupby(p.date[p.liq]).transform("mean").reindex(p.index)
p["liq1"] = g["liq"].shift(-1)
e = crash.merge(p[["ticker", "issuer", "date", "liq1", "closeunadj", "x"]], on=["issuer", "date"])
e = e[(e.liq1 == True) & (e.date >= lo) & (e.date <= hi)].dropna(subset=["x"])
d = e.groupby("date").x.mean(); tt = w.nw_t(d, 10); mid = pd.Timestamp("2010-01-01")
h = (e[e.date < mid].x.mean()*1e4, e[e.date >= mid].x.mean()*1e4); ex5 = d.sort_values().iloc[:-5].mean()*1e4
net = (e.x.mean() - 40e-4)*1e4
ok = net >= 25 and tt >= 3 and min(h) > 0 and e.x.median() > 0 and ex5 > 0
yr = e.groupby(e.date.dt.year).x.agg(["size", "mean", "median"])
line = (f"PREF-CRASH verdict 2005-15: n {len(e)} ({e.ticker.nunique()} prefs) excess {e.x.mean()*1e4:+.1f}bp med {e.x.median()*1e4:+.1f} hit {(e.x>0).mean():.0%} "
        f"NW t {tt:+.1f} halves {h[0]:+.1f}/{h[1]:+.1f} ex5 {ex5:+.1f} net {net:+.1f} -> {'PASS' if ok else 'KILL'}\n  by year: "
        + " ".join(f"{y}:{r['mean']*1e4:+.0f}/med{r['median']*1e4:+.0f}(n{int(r['size'])})" for y, r in yr.iterrows()))
print(line); open(F.OUT, "a").write(f"# PREF-CRASH judge {pd.Timestamp.now():%Y-%m-%d %H:%M}\n{line}\n\n")
