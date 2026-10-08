"""Round 29 audit: PREF-CHAIN raw vs adjusted; ex-date incidence in R27 windows."""
import numpy as np, pandas as pd
from research.sim import winsig as w, winsig_fam as F
p = w.load_panel(kind="pref")
g = p.groupby("ticker", sort=False)
a = pd.read_parquet(w.STORE / "actions.parquet", columns=["date", "action", "ticker", "value"])
a = a[(a.action == "dividend") & a.ticker.isin(set(p.ticker))].copy(); a["date"] = pd.to_datetime(a.date); a = a.sort_values(["ticker", "date"])
v = a.groupby("ticker").value; P = pd.concat([v.shift(1), v.shift(2), v.shift(3)], axis=1)
keep = (P.notna().all(axis=1) & ((P.max(axis=1) / P.min(axis=1) - 1) <= 0.02)) & ((a.value / P.median(axis=1) - 1).abs() < 0.10)
p["c10u"] = g["closeunadj"].shift(10); p["c10a"] = g["closeadj"].shift(10)
ev = a[keep].merge(p[["ticker", "date", "liq", "closeunadj", "closeadj", "c10u", "c10a"]], on=["ticker", "date"])
ev = ev[ev.liq].dropna()
ev["raw"] = (ev.closeunadj + ev.value) / ev.c10u - 1
ev["adj"] = ev.closeadj / ev.c10a - 1
for lo, hi in (("2005-01-01", "2015-12-31"), ("2016-01-01", "2026-09-30")):
    e = ev[(ev.date >= lo) & (ev.date <= hi)]
    dif = (e.adj - e.raw)
    lines = [f"R29 {lo[:4]}-{hi[:4]} PREF-CHAIN raw chain {e.raw.mean()*1e4:+.1f}bp (med {e.raw.median()*1e4:+.1f}) vs adjusted {e.adj.mean()*1e4:+.1f} (med {e.adj.median()*1e4:+.1f}); "
             f"|adj-raw| median {dif.abs().median()*1e4:.1f}bp, >50bp in {(dif.abs()>0.005).mean():.1%} of events"]
    print(lines[0]); open(F.OUT, "a").write(lines[0] + "\n")
# ex-date incidence: share of liquid pref rows whose (t, t+10] window contains an ex-date
p["ex"] = p.merge(a[["ticker", "date"]].assign(e=1), on=["ticker", "date"], how="left").e.fillna(0).to_numpy()
fwd = sum(g["ex"].shift(-k).fillna(0) if False else p.groupby("ticker", sort=False)["ex"].shift(-k).fillna(0) for k in range(1, 11)) > 0
p["fwd_ex"] = fwd
s = w.load_panel(); s["issuer"] = s.ticker
sg = s.groupby("ticker", sort=False); s["dr"] = s.closeadj / sg["closeadj"].shift(1) - 1
crash = s[(s.dr <= -0.08) & (s.closeunadj >= 3)][["ticker", "date"]].rename(columns={"ticker": "issuer"})
p["issuer"] = p.ticker.str.extract(r"^([A-Z.]+)-P")[0]
e = crash.merge(p[["issuer", "date", "liq", "fwd_ex"]], on=["issuer", "date"]); e = e[e.liq & (e.date >= "2016-01-01")]
base = p[p.liq & (p.date >= "2016-01-01")].fwd_ex.mean()
line = f"R29 R27 windows: share of issuer-crash pref windows (t, t+10] containing an ex-date {e.fwd_ex.mean():.1%} vs all liquid pref rows {base:.1%}"
print(line); open(F.OUT, "a").write(line + "\n\n")
