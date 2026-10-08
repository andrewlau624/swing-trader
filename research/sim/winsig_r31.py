"""Round 31: PREF-CHAIN portfolio sim vs EW preferred buy-and-hold."""
import numpy as np, pandas as pd
from research.sim import winsig as w, winsig_fam as F
p = w.load_panel(kind="pref"); g = p.groupby("ticker", sort=False)
p["r"] = p.closeadj / g["closeadj"].shift(1) - 1
a = pd.read_parquet(w.STORE / "actions.parquet", columns=["date", "action", "ticker", "value"])
a = a[(a.action == "dividend") & a.ticker.isin(set(p.ticker))].copy(); a["date"] = pd.to_datetime(a.date); a = a.sort_values(["ticker", "date"])
v = a.groupby("ticker").value; P = pd.concat([v.shift(1), v.shift(2), v.shift(3)], axis=1)
keep = (P.notna().all(axis=1) & ((P.max(axis=1) / P.min(axis=1) - 1) <= 0.02)) & ((a.value / P.median(axis=1) - 1).abs() < 0.10)
p["k"] = g.cumcount()
ev = a[keep][["ticker", "date"]].merge(p[["ticker", "date", "liq", "k"]], on=["ticker", "date"])
ev = ev[ev.liq & (ev.k >= 10) & (ev.date >= "2005-01-01")]
# held rows: for each event, the 10 daily returns T-9..T (return of day d = close d / close d-1)
idx = p.set_index(["ticker", "k"]).index
key = {(t, k): i for i, (t, k) in enumerate(zip(p.ticker, p.k))}
rows = []
for t_, k in zip(ev.ticker, ev.k):
    for j in range(k - 9, k + 1):
        i = key.get((t_, j))
        if i is not None: rows.append(i)
h = p.iloc[rows][["date", "r"]]
port = h.groupby("date").r.mean() - 4e-4                     # 40bp RT spread over 10 sessions
ew = p[p.liq].groupby("date").r.mean()
ew = ew[ew.index >= "2005-01-01"]
cal = ew.index
port = port.reindex(cal).fillna(0.0)
def stats(x, lab):
    eq = (1 + x).cumprod(); yrs = len(x) / 252
    dd = (eq / eq.cummax() - 1).min()
    return f"{lab:24} CAGR {eq.iloc[-1]**(1/yrs)-1:+.1%}  vol {x.std()*np.sqrt(252):.1%}  maxDD {dd:+.1%}"
lines = [stats(port, "PREF-CHAIN book (net)"), stats(ew, "EW pref buy&hold")]
yr = pd.DataFrame({"chain": port, "ew": ew}).groupby(cal.year).apply(lambda d: (1 + d).prod() - 1)
lines.append("by year chain/EW: " + " ".join(f"{y}:{r.chain:+.0%}/{r.ew:+.0%}" for y, r in yr.iterrows()))
exp = h.groupby("date").size().reindex(cal).fillna(0)
lines.append(f"days with no open window: {(exp == 0).mean():.1%} (cash)")
txt = "\n".join(lines); print(txt); open(F.OUT, "a").write(f"# Round 31 {pd.Timestamp.now():%Y-%m-%d %H:%M}\n{txt}\n\n")
for lo, hi in (("2005-01-01", "2009-12-31"), ("2010-01-01", "2026-09-30"), ("2013-01-01", "2026-09-30")):
    m = (cal >= lo) & (cal <= hi)
    l = [stats(port[m], f"chain {lo[:4]}-{hi[:4]}"), stats(ew[m], f"EW    {lo[:4]}-{hi[:4]}"), f"   open windows/day median {exp[m].median():.0f}"]
    print("\n".join(l)); open(F.OUT, "a").write("\n".join(l) + "\n")
m = cal >= "2010-01-01"
spread = (port - ew)[m]
eq = (1 + spread).cumprod(); dd = (eq / eq.cummax() - 1).min()
ys = spread.groupby(spread.index.year).apply(lambda x: (1 + x).prod() - 1)
hh = p.iloc[rows][["date", "ticker"]]; hh = hh[hh.date >= "2010-01-01"]
hh["issuer"] = hh.ticker.str.extract(r"^([A-Z.]+)-P")[0].fillna(hh.ticker)
top = hh.groupby("date").issuer.agg(lambda s: s.value_counts(normalize=True).iloc[0])
l = [f"R32 edge-only spread 2010-26: CAGR {eq.iloc[-1]**(252/len(spread))-1:+.1%}, vol {spread.std()*np.sqrt(252):.1%}, maxDD {dd:+.1%}, worst year {ys.min():+.1%} ({ys.idxmin()}), years > 0: {(ys>0).sum()}/{len(ys)}",
     f"    issuer concentration: top issuer share of open windows median {top.median():.0%}, 90th pct {top.quantile(.9):.0%}"]
print("\n".join(l)); open(F.OUT, "a").write("\n".join(l) + "\n\n")
