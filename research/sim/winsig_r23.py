"""Round 23: falsification of PREF-CHAIN."""
import numpy as np, pandas as pd
from research.sim import winsig as w, winsig_fam as F
t = w.load_panel(kind="pref")
g = t.groupby("ticker", sort=False)
tk = pd.read_parquet(w.STORE / "tickers.parquet", columns=["table", "ticker", "category"])
etd = set(tk[(tk.table == "SFP") & (tk.category == "ETD")].ticker)
a = pd.read_parquet(w.STORE / "actions.parquet", columns=["date", "action", "ticker", "value"])
a = a[(a.action == "dividend") & a.ticker.isin(set(t.ticker))].copy(); a["date"] = pd.to_datetime(a.date); a = a.sort_values(["ticker", "date"])
v = a.groupby("ticker").value; P = pd.concat([v.shift(1), v.shift(2), v.shift(3)], axis=1)
a["gapdays"] = a.groupby("ticker").date.diff().dt.days
keep = (P.notna().all(axis=1) & ((P.max(axis=1) / P.min(axis=1) - 1) <= 0.02)) & ((a.value / P.median(axis=1) - 1).abs() < 0.10)
def xs(col):
    return t[col] - t[col][t.liq].groupby(t.date[t.liq]).transform("mean").reindex(t.index)
t["ch"] = t.closeadj / g["closeadj"].shift(10) - 1; t["xch"] = xs("ch")                      # row T: T-10 -> T
t["post"] = g["closeadj"].shift(-15) / g["closeadj"].shift(-5) - 1; t["xpost"] = xs("post")  # row T: T+5 -> T+15
t["is_ex"] = t.merge(a[["ticker", "date"]].assign(e=1), on=["ticker", "date"], how="left").e.fillna(0).to_numpy() == 1
# distance (sessions) to the nearest ex-date per ticker, for the random-date placebo
pos = g.cumcount()
expos = pos.where(t.is_ex)
nxt = expos.groupby(t.ticker, sort=False).bfill(); prv = expos.groupby(t.ticker, sort=False).ffill()
far = ((nxt - pos).fillna(999) >= 20) & ((pos - prv).fillna(999) >= 20)
ev = a[keep][["ticker", "date", "gapdays"]].merge(t[["ticker", "date", "liq", "adv20", "xch", "xpost"]], on=["ticker", "date"])
lines = []
for lo, hi in (("2016-01-01", "2026-09-30"), ("2005-01-01", "2015-12-31")):
    e = ev[ev.liq & (ev.date >= lo) & (ev.date <= hi)].dropna(subset=["xch"])
    pl = t[t.liq & far & (t.date >= lo) & (t.date <= hi)].xch.dropna()
    lines.append(f"[{lo[:4]}-{hi[:4]}] chained {e.xch.mean()*1e4:+.1f}bp (n {len(e)}) | Q1a post-ex T+5->T+15 {e.xpost.mean()*1e4:+.1f} | Q1b random far-from-ex 10d {pl.mean()*1e4:+.1f} (n {len(pl)})")
    lines.append(f"   Q2 ADV>=$1M: {e[e.adv20>=1e6].xch.mean()*1e4:+.1f} (n {(e.adv20>=1e6).sum()}) | Q3 SEP pref {e[~e.ticker.isin(etd)].xch.mean()*1e4:+.1f} (n {(~e.ticker.isin(etd)).sum()}) "
                 f"ETD {e[e.ticker.isin(etd)].xch.mean()*1e4:+.1f} (n {e.ticker.isin(etd).sum()}) | Q4 monthly {e[e.gapdays<=45].xch.mean()*1e4:+.1f} (n {(e.gapdays<=45).sum()}) "
                 f"quarterly {e[e.gapdays.between(70,110)].xch.mean()*1e4:+.1f} (n {e.gapdays.between(70,110).sum()})")
txt = "\n".join(lines); print(txt); open(F.OUT, "a").write(f"# Round 23 {pd.Timestamp.now():%Y-%m-%d %H:%M}\n{txt}\n\n")
