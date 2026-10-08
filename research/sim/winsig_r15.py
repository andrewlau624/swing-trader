"""Round 15: F4 on preferreds split by distance to $25 par."""
import numpy as np, pandas as pd
from research.sim import winsig as w, winsig_fam as F
t = w.load_panel(kind="pref")
g = t.groupby("ticker", sort=False)
t["cc5"] = g["closeadj"].shift(-5) / t.closeadj - 1
t["x"] = t.cc5 - t.date.map(t[t.liq].groupby("date")["cc5"].mean())
m = list(F.F4(t).values())[0].fillna(False) & t.liq & (t.date >= w.DISC[0]) & (t.date <= w.DISC[1])
a, b = m & (t.closeunadj < 24), m & (t.closeunadj >= 24)
da = t[a].groupby("date").x.mean(); db = t[b].groupby("date").x.mean(); d = (da - db).dropna()
tt = d.mean() / (d.std() / np.sqrt(len(d))); mid = d.index[len(d)//2]
h = (d[d.index < mid].mean()*1e4, d[d.index >= mid].mean()*1e4)
ok = abs(d.mean())*1e4 >= 15 and abs(tt) >= 2.5 and np.sign(h[0]) == np.sign(h[1]) == np.sign(d.mean())
line = (f"R15 PREF F4 below $24 n {int(a.sum())} {t.loc[a,'x'].mean()*1e4:+.1f}bp med {t.loc[a,'x'].median()*1e4:+.1f} | >= $24 n {int(b.sum())} "
        f"{t.loc[b,'x'].mean()*1e4:+.1f}bp med {t.loc[b,'x'].median()*1e4:+.1f} | paired {d.mean()*1e4:+.1f} (t {tt:+.1f}, days {len(d)}) halves {h[0]:+.1f}/{h[1]:+.1f} -> {'PASS' if ok else 'fail'}")
print(line); open(F.OUT, "a").write(f"# Round 15 {pd.Timestamp.now():%Y-%m-%d %H:%M}\n{line}\n\n")
