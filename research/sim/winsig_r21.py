"""Round 21: CEF pre-ex accumulation window (T-10 close -> T-1 close)."""
import numpy as np, pandas as pd
from research.sim import winsig as w, winsig_fam as F
t = w.load_panel(kind="cef")
g = t.groupby("ticker", sort=False)
r = g["closeadj"].shift(1) / g["closeadj"].shift(10) - 1        # close T-10 -> close T-1 (row = ex-date T)
t["pre"] = r - r.groupby(t.date).transform(lambda s: np.nan)    # placeholder, replaced below
bench = (t.closeadj / g["closeadj"].shift(1) - 1)[t.liq].groupby(t.date[t.liq]).mean()
cum = (1 + bench.fillna(0)).cumprod()
dates = cum.index
a = pd.read_parquet(w.STORE / "actions.parquet", columns=["date", "action", "ticker", "value"])
a = a[(a.action == "dividend") & a.ticker.isin(set(t.ticker))].copy(); a["date"] = pd.to_datetime(a.date); a = a.sort_values(["ticker", "date"])
v = a.groupby("ticker").value; P = pd.concat([v.shift(1), v.shift(2), v.shift(3)], axis=1)
stable = P.notna().all(axis=1) & ((P.max(axis=1) / P.min(axis=1) - 1) <= 0.02)
normal = (a.value / P.median(axis=1) - 1).abs() < 0.10
ev = a[stable & normal][["ticker", "date"]].merge(t[["ticker", "date", "liq"]].assign(pre=r.values), on=["ticker", "date"])
ev = ev[ev.liq & ev.pre.notna() & (ev.date >= w.DISC[0]) & (ev.date <= w.DISC[1])].copy()
pos = dates.searchsorted(ev.date)
ok = pos >= 10
ev = ev[ok].copy(); pos = pos[ok]
ev["bm"] = cum.iloc[pos - 1].to_numpy() / cum.iloc[pos - 10].to_numpy() - 1
ev["x"] = ev.pre - ev.bm
d = ev.groupby("date").x.mean(); tt = w.nw_t(d, 9); mid = ev.date.min() + (ev.date.max() - ev.date.min()) / 2
h = (ev[ev.date < mid].x.mean()*1e4, ev[ev.date >= mid].x.mean()*1e4); s = d.sort_values(); ex5 = s.iloc[:-5].mean()*1e4
net = (ev.x.mean() - 20e-4) * 1e4
okk = net >= 25 and tt >= 3 and min(h) > 0 and ev.x.median() > 0 and ex5 > 0
line = (f"R21 CEF pre-ex T-10->T-1: events {len(ev)} ({len(ev)/10.7:.0f}/yr) | excess {ev.x.mean()*1e4:+.1f}bp med {ev.x.median()*1e4:+.1f} hit {(ev.x>0).mean():.0%}"
        f" NW t {tt:+.1f} halves {h[0]:+.1f}/{h[1]:+.1f} ex5 {ex5:+.1f} net {net:+.1f} -> {'PASS' if okk else 'fail'}")
print(line); open(F.OUT, "a").write(f"# Round 21 {pd.Timestamp.now():%Y-%m-%d %H:%M}\n{line}\n\n")
