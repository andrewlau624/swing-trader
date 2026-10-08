"""G3 breadth timing + G4 IBS conditioning (spec frozen in window_signals_loop_2026-10-07.md)."""
import numpy as np, pandas as pd
from research.sim import winsig as w, winsig_fam as F

OUT = F.OUT
lines = []
# ---------------- G3: breadth of window states across liquid stocks -> SPY next 5d
t = w.load_panel()
main, sig = F.tmo(t)
m20, sd = F.sma(t, t.close, 20), F.std(t, t.close, 20)
sq = (2 * sd) < (1.5 * F.sma(t, F.true_range(t), 20))
L = t.liq
br = pd.DataFrame({"os": (main <= -10)[L].groupby(t.date[L]).mean(), "sq": sq[L].groupby(t.date[L]).mean()})
e = w.load_panel(kind="etf")
spy = e[e.ticker == "SPY"].set_index("date")[["f1", "f5", "f10"]]
br = br.join(spy, how="inner")
for col in ("os", "sq"):
    thr = br[col].rolling(252, min_periods=200).quantile(0.9)
    for lo, hi, tag in [(*w.DISC, "2016-26"), ("2003-01-01", "2015-12-31", "2003-15 (diagnostic only if 2016-26 passes)")]:
        b = br[(br.index >= lo) & (br.index <= hi)]
        on = b[col] >= thr.reindex(b.index)
        x = (b.f5 - b.f5.mean())[on]
        tt = w.nw_t(x, 5)
        halves = [x[x.index < b.index[len(b)//2]].mean()*1e4, x[x.index >= b.index[len(b)//2]].mean()*1e4]
        lines.append(f"G3 breadth {col} top-decile -> SPY H5 [{tag}]: days {on.sum()} | SPY H5 cond {b.f5[on].mean()*1e4:+6.1f}bp vs all {b.f5.mean()*1e4:+6.1f}"
                     f" | excess {x.mean()*1e4:+6.1f} (NW t {tt:+4.1f}) med {x.median()*1e4:+6.1f} halves {halves[0]:+6.1f}/{halves[1]:+6.1f}"
                     f" net(10bp) {(x.mean()-w.COST)*1e4:+6.1f} -> {'PASS' if (x.mean()-w.COST)*1e4>=25 and tt>=3 and min(halves)>0 and x.median()>0 else 'fail'}")
        if tag != "2016-26":
            pass
del t
# ---------------- G4: IBS<0.2 ETF entries (open t+1 -> open t+2) split by window state
e = e.copy()
g = e.groupby("ticker", sort=False)
adjf = e.closeadj / e.close
oadj = e.open * adjf
e["oo"] = g["open"].shift(-2) * (adjf.groupby(e.ticker, sort=False).shift(-2)) / (g["open"].shift(-1) * adjf.groupby(e.ticker, sort=False).shift(-1)) - 1
bench = e[e.liq].groupby("date")["oo"].mean()
e["xoo"] = e.oo - e.date.map(bench)
ibs = (e.close - e.low) / (e.high - e.low).replace(0, np.nan)
main, sig = F.tmo(e)
osd = F.gsum(e, (main <= -10).astype(float), 10)
m20, sd = F.sma(e, e.close, 20), F.std(e, e.close, 20)
sqe = (2 * sd) < (1.5 * F.sma(e, F.true_range(e), 20))
c = e.close.astype("float64"); macd = w.ema(e, c, 12) - w.ema(e, c, 26); hist = macd - w.ema(e, macd, 9)
base = (ibs < 0.2) & e.liq & (e.date >= w.DISC[0]) & (e.date <= w.DISC[1])
def split(name, a, b):
    xa, xb = e.loc[base & a, ["date", "xoo"]].dropna(), e.loc[base & b, ["date", "xoo"]].dropna()
    da, db = xa.groupby("date").xoo.mean(), xb.groupby("date").xoo.mean()
    d = (da - db).dropna()
    tt = d.mean() / (d.std() / np.sqrt(len(d)))
    mid = d.index[len(d)//2]
    h = (d[d.index < mid].mean()*1e4, d[d.index >= mid].mean()*1e4)
    ok = abs(d.mean())*1e4 >= 15 and abs(tt) >= 2.5 and np.sign(h[0]) == np.sign(h[1]) == np.sign(d.mean())
    lines.append(f"G4 IBS<0.2 ETFs split {name:34}: A n {len(xa):6} {xa.xoo.mean()*1e4:+6.1f}bp | B n {len(xb):6} {xb.xoo.mean()*1e4:+6.1f}bp | "
                 f"paired A-B {d.mean()*1e4:+6.1f} (t {tt:+4.1f}, nights {len(d)}) halves {h[0]:+6.1f}/{h[1]:+6.1f} -> {'PASS' if ok else 'fail'}")
lines.append(f"G4 base IBS<0.2 liquid ETFs 2016-26: n {int(base.sum())}, open->open excess {e.loc[base,'xoo'].mean()*1e4:+.1f}bp, raw {e.loc[base,'oo'].mean()*1e4:+.1f}bp")
split("TMO oversold >=5/10 vs <5", osd >= 5, osd < 5)
split("squeeze ON vs OFF", sqe, ~sqe)
split("MACD hist <0 vs >=0", hist < 0, hist >= 0)
txt = "\n".join(lines); print(txt)
open(OUT, "a").write(f"# G3/G4 {pd.Timestamp.now():%Y-%m-%d %H:%M}\n{txt}\n\n")
