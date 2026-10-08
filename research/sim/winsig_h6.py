"""H6: live IBS rule on ETFs split by weekly RSI(14) (multi-timeframe). Gate as G4."""
import numpy as np, pandas as pd
from research.sim import winsig as w, winsig_fam as F
e = w.load_panel(kind="etf")
g = e.groupby("ticker", sort=False); adjf = e.closeadj / e.close
e["oo"] = g["open"].shift(-2) * adjf.groupby(e.ticker, sort=False).shift(-2) / (g["open"].shift(-1) * adjf.groupby(e.ticker, sort=False).shift(-1)) - 1
e["xoo"] = e.oo - e.date.map(e[e.liq].groupby("date")["oo"].mean())
ibs = (e.close - e.low) / (e.high - e.low).replace(0, np.nan)
# weekly RSI from completed weeks only (last bar of each prior week), forward-filled to the daily rows
wk = e.date.dt.to_period("W-FRI")
last = wk != wk.groupby(e.ticker, sort=False).shift(-1)
sub = e.loc[last, ["ticker", "close"]].copy()
sub["rsi"] = F.rsi(sub.assign(ticker=sub.ticker))
e["wrsi"] = np.nan; e.loc[last, "wrsi"] = sub["rsi"]
e["wrsi"] = e.groupby("ticker", sort=False)["wrsi"].shift(1)       # completed weeks only: shift past today's bar
e["wrsi"] = e.groupby("ticker", sort=False)["wrsi"].ffill()
base = (ibs < 0.2) & e.liq & (e.date >= w.DISC[0]) & (e.date <= w.DISC[1])
a, b = base & (e.wrsi < 35), base & (e.wrsi >= 35)
da = e[a].groupby("date").xoo.mean(); db = e[b].groupby("date").xoo.mean(); d = (da - db).dropna()
tt = d.mean() / (d.std() / np.sqrt(len(d))); mid = d.index[len(d)//2]
h = (d[d.index < mid].mean()*1e4, d[d.index >= mid].mean()*1e4)
ok = abs(d.mean())*1e4 >= 15 and abs(tt) >= 2.5 and np.sign(h[0]) == np.sign(h[1]) == np.sign(d.mean())
line = (f"H6 IBS<0.2 ETFs split weekly RSI<35 vs >=35: A n {int(a.sum())} {e.loc[a,'xoo'].mean()*1e4:+.1f}bp | B n {int(b.sum())} "
        f"{e.loc[b,'xoo'].mean()*1e4:+.1f}bp | paired {d.mean()*1e4:+.1f} (t {tt:+.1f}, nights {len(d)}) halves {h[0]:+.1f}/{h[1]:+.1f} -> {'PASS' if ok else 'fail'}")
print(line); open(F.OUT, "a").write(f"# H6 {pd.Timestamp.now():%Y-%m-%d %H:%M}\n{line}\n\n")
