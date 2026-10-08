"""Round 22 diagnostic: chain the pre-ex window with the ex-night (T-10 close -> ex close incl. dividend), preferreds."""
import numpy as np, pandas as pd
from research.sim import winsig as w, winsig_fam as F
t = w.load_panel(kind="pref")
g = t.groupby("ticker", sort=False)
a = pd.read_parquet(w.STORE / "actions.parquet", columns=["date", "action", "ticker", "value"])
a = a[(a.action == "dividend") & a.ticker.isin(set(t.ticker))].copy(); a["date"] = pd.to_datetime(a.date); a = a.sort_values(["ticker", "date"])
v = a.groupby("ticker").value; P = pd.concat([v.shift(1), v.shift(2), v.shift(3)], axis=1)
keep = (P.notna().all(axis=1) & ((P.max(axis=1) / P.min(axis=1) - 1) <= 0.02)) & ((a.value / P.median(axis=1) - 1).abs() < 0.10)
t["pre"] = g["closeadj"].shift(1) / g["closeadj"].shift(10) - 1           # T-10 -> T-1 (total return)
t["ch"] = t.closeadj / g["closeadj"].shift(10) - 1                        # T-10 -> T close (incl. the ex-night + dividend)
t["exn"] = t.closeadj / g["closeadj"].shift(1) - 1                        # T-1 -> T close (ex-night, total return)
for c in ("pre", "ch", "exn"):
    t["x" + c] = t[c] - t[c][t.liq].groupby(t.date[t.liq]).transform("mean").reindex(t.index)
ev = a[keep][["ticker", "date"]].merge(t[["ticker", "date", "liq", "xpre", "xch", "xexn"]], on=["ticker", "date"])
ev = ev[ev.liq & (ev.date >= "2005-01-01") & (ev.date <= "2015-12-31")].dropna()
q = pd.qcut(ev.xpre, 3, labels=["lo", "mid", "hi"])
lines = [f"PREF-CHAIN JUDGE 2005-15 n {len(ev)}: pre-ex {ev.xpre.mean()*1e4:+.1f} | ex-night {ev.xexn.mean()*1e4:+.1f} | chained T-10->ex close {ev.xch.mean()*1e4:+.1f}bp "
         f"(med {ev.xch.median()*1e4:+.1f}, NW t {w.nw_t(ev.groupby('date').xch.mean(), 10):+.1f}); net of ONE 40bp round trip {(ev.xch.mean()-40e-4)*1e4:+.1f}",
         "  ex-night by pre-ex run-up tercile: " + " | ".join(f"{k} {ev[q==k].xexn.mean()*1e4:+.1f}" for k in ["lo", "mid", "hi"])]
txt = "\n".join(lines); print(txt); open(F.OUT, "a").write(f"# PREF-CHAIN judge {pd.Timestamp.now():%Y-%m-%d %H:%M}\n{txt}\n\n")
mid = pd.Timestamp("2011-01-01")
h = (ev[ev.date < mid].xch.mean()*1e4, ev[ev.date >= mid].xch.mean()*1e4)
d = ev.groupby("date").xch.mean(); tt = w.nw_t(d, 10); ex5 = d.sort_values().iloc[:-5].mean()*1e4; net = (ev.xch.mean()-40e-4)*1e4
ok = net >= 25 and tt >= 3 and min(h) > 0 and ev.xch.median() > 0 and ex5 > 0
yr = ev.groupby(ev.date.dt.year).xch.agg(["size", "mean"])
line = (f"PREF-CHAIN verdict: n {len(ev)} net {net:+.1f}bp shock {(ev.xch.mean()-120e-4)*1e4:+.1f} NW t {tt:+.1f} halves {h[0]:+.1f}/{h[1]:+.1f} med {ev.xch.median()*1e4:+.1f} "
        f"ex5 {ex5:+.1f} -> {'PASS' if ok else 'KILL'}\n  by year: " + " ".join(f"{y}:{r['mean']*1e4:+.0f}(n{int(r['size'])})" for y, r in yr.iterrows()))
print(line); open(F.OUT, "a").write(line + "\n\n")
