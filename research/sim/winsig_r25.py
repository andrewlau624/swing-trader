"""Round 25: new-issue window in preferreds / baby bonds (session 5 -> 30 after listing)."""
import sys, numpy as np, pandas as pd
from research.sim import winsig as w, winsig_fam as F
CONF = "--confirm" in sys.argv
t = w.load_panel(kind="pref")
g = t.groupby("ticker", sort=False)
t["k"] = g.cumcount()
for H in (30, 45):
    t[f"r{H}"] = g["closeadj"].shift(-(H - 5)) / t.closeadj - 1
    bench = t[f"r{H}"][t.liq].groupby(t.date[t.liq]).mean()
    t[f"x{H}"] = t[f"r{H}"] - t.date.map(bench)
first = g.date.transform("min")
lo, hi = ("2005-01-01", "2015-12-31") if CONF else ("2016-01-01", "2026-09-30")
ev = t[(t.k == 5) & (first >= lo) & (first <= hi) & (t.closeunadj >= 5) & (first > pd.Timestamp("2002-07-01"))].dropna(subset=["x30"])
d = ev.groupby("date").x30.mean(); tt = w.nw_t(d, 25); mid = pd.Timestamp(lo) + (pd.Timestamp(hi) - pd.Timestamp(lo)) / 2
h = (ev[ev.date < mid].x30.mean()*1e4, ev[ev.date >= mid].x30.mean()*1e4); ex5 = d.sort_values().iloc[:-5].mean()*1e4
net = (ev.x30.mean() - 40e-4)*1e4
ok = net >= 25 and tt >= 3 and min(h) > 0 and ev.x30.median() > 0 and ex5 > 0
line = (f"R25 {'CONFIRM ' if CONF else ''}{lo[:4]}-{hi[:4]} new issues n {len(ev)} ({len(ev)/10.7:.0f}/yr) | s5->s30 excess {ev.x30.mean()*1e4:+.1f}bp med {ev.x30.median()*1e4:+.1f} "
        f"hit {(ev.x30>0).mean():.0%} NW t {tt:+.1f} halves {h[0]:+.1f}/{h[1]:+.1f} ex5 {ex5:+.1f} net {net:+.1f} | s5->s45 {ev.x45.mean()*1e4:+.1f} (med {ev.x45.median()*1e4:+.1f})"
        f" | entry px med ${ev.closeunadj.median():.2f} -> {'PASS' if ok else 'fail'}")
print(line); open(F.OUT, "a").write(f"# Round 25 {pd.Timestamp.now():%Y-%m-%d %H:%M}\n{line}\n\n")
