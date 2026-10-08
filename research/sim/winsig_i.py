"""Round 4: I1/I2 opening-gap fade (same day), I3 vol-compression (index ETFs). Spec in the loop ledger."""
import numpy as np, pandas as pd
from research.sim import winsig as w, winsig_fam as F
lines = []
def gapfade(kind, thr, cost, label):
    t = w.load_panel(kind=kind)
    g = t.groupby("ticker", sort=False)
    gap = t.open / g["close"].shift(1) - 1
    oc = (t.close / t.open - 1)            # same-day, split-adjusted both legs (no dividend inside a session)
    lv = g["liq"].shift(0)                 # liq uses prior-20d ADV and today's raw close; use yesterday's flag
    lq = g["liq"].shift(1).fillna(False).astype(bool)
    bench = oc[lq].groupby(t.date[lq]).mean()
    x = oc - t.date.map(bench)
    m = lq & (gap <= thr) & (t.date >= w.DISC[0]) & (t.date <= w.DISC[1])
    xs = x[m].dropna(); d = xs.groupby(t.date[xs.index]).mean()
    tt = w.nw_t(d, 1); mid = d.index[len(d)//2]
    h = (d[d.index < mid].mean()*1e4, d[d.index >= mid].mean()*1e4)
    ex5 = d.sort_values().iloc[:-5].mean()*1e4; net = (xs.mean()-cost)*1e4
    ok = net >= 25 and tt >= 3 and min(h) > 0 and xs.median() > 0 and ex5 > 0
    lines.append(f"{label}: n {len(xs)} ({len(xs)/10.7:.0f}/yr) days {len(d)} | raw {oc[m].mean()*1e4:+.1f}bp excess {xs.mean()*1e4:+.1f} (NW t {tt:+.1f}) "
                 f"med {xs.median()*1e4:+.1f} hit {(xs>0).mean():.0%} halves {h[0]:+.1f}/{h[1]:+.1f} ex5 {ex5:+.1f} net {net:+.1f} shock {(xs.mean()-3*cost)*1e4:+.1f} -> {'PASS' if ok else 'fail'}")
    return t
e = gapfade("etf", -0.01, 5e-4, "I1 ETF gap <= -1% fade (open->close)")
gapfade("stock", -0.03, 10e-4, "I2 stock gap <= -3% fade (open->close)")
for sym in ("SPY", "QQQ", "IWM"):
    s = e[e.ticker == sym].set_index("date")
    r = np.log(s.closeadj).diff()
    ratio = r.rolling(5).std() / r.rolling(60).std()
    b = s[(s.index >= w.DISC[0]) & (s.index <= w.DISC[1])]
    on = ratio.reindex(b.index) <= 0.5
    x = (b.f5 - b.f5.mean())[on]
    tt = w.nw_t(x, 5) if len(x) >= 30 else np.nan; mid = b.index[len(b)//2]
    h = (x[x.index < mid].mean()*1e4, x[x.index >= mid].mean()*1e4)
    ok = (x.mean()-w.COST)*1e4 >= 25 and tt >= 3 and min(h) > 0 and x.median() > 0
    lines.append(f"I3 {sym} 5d/60d vol <= 0.5 -> H5: days {int(on.sum())} | cond {b.f5[on].mean()*1e4:+.1f}bp vs all {b.f5.mean()*1e4:+.1f} | excess {x.mean()*1e4:+.1f} (t {tt:+.1f}) halves {h[0]:+.1f}/{h[1]:+.1f} -> {'PASS' if ok else 'fail'}")
txt = "\n".join(lines); print(txt); open(F.OUT, "a").write(f"# Round 4 {pd.Timestamp.now():%Y-%m-%d %H:%M}\n{txt}\n\n")
