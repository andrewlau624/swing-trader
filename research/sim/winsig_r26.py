"""Round 26: pre-ex window / chain in high-yield liquid commons."""
import sys, numpy as np, pandas as pd
from research.sim import winsig as w, winsig_fam as F
CONF = "--confirm" in sys.argv
t = w.load_panel()
g = t.groupby("ticker", sort=False)
a = pd.read_parquet(w.STORE / "actions.parquet", columns=["date", "action", "ticker", "value"])
a = a[(a.action == "dividend") & a.ticker.isin(set(t.ticker))].copy(); a["date"] = pd.to_datetime(a.date); a = a.sort_values(["ticker", "date"])
v = a.groupby("ticker").value; P = pd.concat([v.shift(1), v.shift(2), v.shift(3)], axis=1)
a["keep"] = (P.notna().all(axis=1) & ((P.max(axis=1) / P.min(axis=1) - 1) <= 0.02)) & ((a.value / P.median(axis=1) - 1).abs() < 0.10)
a["ann"] = a.value + v.shift(1) + v.shift(2) + v.shift(3)                       # last 4 payouts incl. current
a["gap"] = a.groupby("ticker").date.diff().dt.days
a.loc[a.gap <= 45, "ann"] = a.value * 12                                         # monthly payers: annualise
t["pre"] = g["closeadj"].shift(1) / g["closeadj"].shift(10) - 1
t["ch"] = t.closeadj / g["closeadj"].shift(10) - 1
t["px10"] = g["closeunadj"].shift(10); t["liq10"] = g["liq"].shift(10)
for c in ("pre", "ch"):
    t["x" + c] = t[c] - t[c][t.liq].groupby(t.date[t.liq]).transform("mean").reindex(t.index)
ev = a[a.keep][["ticker", "date", "ann"]].merge(t[["ticker", "date", "px10", "liq10", "xpre", "xch"]], on=["ticker", "date"])
ev = ev[(ev.liq10 == True) & (ev.ann / ev.px10 >= 0.06)].dropna(subset=["xch"])
lo, hi = ("2003-01-01", "2015-12-31") if CONF else ("2016-01-01", "2026-09-30")
ev = ev[(ev.date >= lo) & (ev.date <= hi)]
d = ev.groupby("date").xch.mean(); tt = w.nw_t(d, 10); mid = pd.Timestamp(lo) + (pd.Timestamp(hi) - pd.Timestamp(lo)) / 2
h = (ev[ev.date < mid].xch.mean()*1e4, ev[ev.date >= mid].xch.mean()*1e4); ex5 = d.sort_values().iloc[:-5].mean()*1e4
net = (ev.xch.mean() - 10e-4)*1e4
ok = net >= 25 and tt >= 3 and min(h) > 0 and ev.xch.median() > 0 and ex5 > 0
line = (f"R26 {'CONFIRM ' if CONF else ''}{lo[:4]}-{hi[:4]} high-yield commons n {len(ev)} ({len(ev)/(int(hi[:4])-int(lo[:4])+1):.0f}/yr, {ev.ticker.nunique()} names) | "
        f"A pre-ex {ev.xpre.mean()*1e4:+.1f} (med {ev.xpre.median()*1e4:+.1f}) | B chain {ev.xch.mean()*1e4:+.1f} med {ev.xch.median()*1e4:+.1f} hit {(ev.xch>0).mean():.0%} "
        f"t {tt:+.1f} halves {h[0]:+.1f}/{h[1]:+.1f} ex5 {ex5:+.1f} net {net:+.1f} -> {'PASS' if ok else 'fail'}")
print(line); open(F.OUT, "a").write(f"# Round 26 {pd.Timestamp.now():%Y-%m-%d %H:%M}\n{line}\n\n")
