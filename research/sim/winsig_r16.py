"""Round 16: CEF distribution-cut windows (spec in the loop ledger)."""
import numpy as np, pandas as pd
from research.sim import winsig as w, winsig_fam as F
t = w.load_panel(kind="cef")
g = t.groupby("ticker", sort=False)
for k in (5, 10, 20):
    t[f"c{k}"] = g["closeadj"].shift(-k) / t.closeadj - 1
    t[f"x{k}"] = t[f"c{k}"] - t.date.map(t[t.liq].groupby("date")[f"c{k}"].mean())
t["pre10"] = t.closeadj / g["closeadj"].shift(10) - 1
t["xpre10"] = t.pre10 - t.date.map(t[t.liq].groupby("date")["pre10"].mean())
a = pd.read_parquet(w.STORE / "actions.parquet", columns=["date", "action", "ticker", "value"])
a = a[(a.action == "dividend") & a.ticker.isin(set(t.ticker))].copy()
a["date"] = pd.to_datetime(a.date); a = a.sort_values(["ticker", "date"])
v = a.groupby("ticker").value
p1, p2, p3 = v.shift(1), v.shift(2), v.shift(3)
med = pd.concat([p1, p2, p3], axis=1).median(axis=1)
stable = p3.notna() & (pd.concat([p1, p2, p3], axis=1).max(axis=1) / pd.concat([p1, p2, p3], axis=1).min(axis=1) - 1) <= 0.02
ev = a[stable & (a.value <= 0.9 * med)][["ticker", "date"]]
ev = ev.merge(t[["ticker", "date", "liq", "x5", "x10", "x20", "xpre10"]], on=["ticker", "date"], how="inner")
ev = ev[ev.liq & (ev.date >= w.DISC[0]) & (ev.date <= w.DISC[1])]
lines = [f"R16 CEF distribution cuts 2016-26: events {len(ev)} ({len(ev)/10.7:.0f}/yr), funds {ev.ticker.nunique()}"]
for c, lag in (("xpre10", 10), ("x5", 5), ("x10", 10), ("x20", 20)):
    x = ev[c].dropna(); d = x.groupby(ev.loc[x.index, "date"]).mean()
    mid = ev.date.min() + (ev.date.max() - ev.date.min()) / 2
    h = (x[ev.loc[x.index, "date"] < mid].mean()*1e4, x[ev.loc[x.index, "date"] >= mid].mean()*1e4)
    s = x.sort_values(); ex5 = s.iloc[:-5].mean()*1e4
    tt = w.nw_t(d, lag) if len(d) >= 30 else np.nan
    tag = ""
    if c == "x10":
        ok = (x.mean() - 20e-4)*1e4 >= 50 and tt >= 2.5 and min(h) > 0 and x.median() > 0
        tag = f" net {(x.mean()-20e-4)*1e4:+.1f} -> {'PASS' if ok else 'fail'}"
    lines.append(f"  {c:7} mean {x.mean()*1e4:+7.1f}bp med {x.median()*1e4:+6.1f} hit {(x>0).mean():.0%} t {tt:+4.1f} halves {h[0]:+6.1f}/{h[1]:+6.1f} ex-top5 {ex5:+6.1f}{tag}")
txt = "\n".join(lines); print(txt); open(F.OUT, "a").write(f"# Round 16 {pd.Timestamp.now():%Y-%m-%d %H:%M}\n{txt}\n\n")
