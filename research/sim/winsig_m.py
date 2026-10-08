"""Round 7: repeat-signal windows on the IBS ETF rule (M1/M2)."""
import numpy as np, pandas as pd
from research.sim import winsig as w, winsig_fam as F
e = w.load_panel(kind="etf")
g = e.groupby("ticker", sort=False); adjf = e.closeadj / e.close
e["oo"] = g["open"].shift(-2) * adjf.groupby(e.ticker, sort=False).shift(-2) / (g["open"].shift(-1) * adjf.groupby(e.ticker, sort=False).shift(-1)) - 1
e["xoo"] = e.oo - e.date.map(e[e.liq].groupby("date")["oo"].mean())
low = ((e.close - e.low) / (e.high - e.low).replace(0, np.nan) < 0.2).astype(float)
prev1 = w.lag(e, low) == 1
prior5 = w.lag(e, F.gsum(e, low, 5))
base = (low == 1) & e.liq & (e.date >= w.DISC[0]) & (e.date <= w.DISC[1])
lines = []
def split(lab, a, b):
    da = e[a].groupby("date").xoo.mean(); db = e[b].groupby("date").xoo.mean(); d = (da - db).dropna()
    tt = d.mean() / (d.std() / np.sqrt(len(d))); mid = d.index[len(d)//2]
    h = (d[d.index < mid].mean()*1e4, d[d.index >= mid].mean()*1e4)
    ok = abs(d.mean())*1e4 >= 15 and abs(tt) >= 2.5 and np.sign(h[0]) == np.sign(h[1]) == np.sign(d.mean())
    lines.append(f"{lab:46} A n {int(a.sum()):6} {e.loc[a,'xoo'].mean()*1e4:+6.1f}bp med {e.loc[a,'xoo'].median()*1e4:+5.1f} | B n {int(b.sum()):6} {e.loc[b,'xoo'].mean()*1e4:+6.1f}bp med {e.loc[b,'xoo'].median()*1e4:+5.1f}"
                 f" | paired {d.mean()*1e4:+6.1f} (t {tt:+4.1f}) halves {h[0]:+5.1f}/{h[1]:+5.1f} -> {'PASS' if ok else 'fail'}")
split("M1 2nd consecutive IBS<0.2 vs first", base & prev1, base & ~prev1)
split("M2 >=2 IBS<0.2 days in prior 5 vs none", base & (prior5 >= 2), base & (prior5 == 0))
txt = "\n".join(lines); print(txt); open(F.OUT, "a").write(f"# Round 7 {pd.Timestamp.now():%Y-%m-%d %H:%M}\n{txt}\n\n")
