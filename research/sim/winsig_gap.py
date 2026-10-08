"""Diagnostic (no gate): where does each window rule's edge sit? close t -> open t+1 (MOC entry) vs open t+1 -> close t+5."""
import numpy as np, pandas as pd
from research.sim import winsig as w, winsig_fam as F
t = w.add_bench(w.load_panel())
g = t.groupby("ticker", sort=False); adjf = t.closeadj / t.close
t["co"] = g["open"].shift(-1) * adjf.groupby(t.ticker, sort=False).shift(-1) / t.closeadj - 1
t["xco"] = t.co - t.date.map(t[t.liq].groupby("date")["co"].mean())
tk = pd.read_parquet(w.STORE / "tickers.parquet", columns=["table", "ticker", "famaindustry"])
t["ind"] = t.ticker.map(tk[tk.table == "SEP"].drop_duplicates("ticker").set_index("ticker").famaindustry).fillna("NA")
r = t.closeadj / w.lag(t, t.closeadj, 5) - 1; L = t.liq & r.notna()
res = pd.Series(np.nan, index=t.index); res[L] = r[L] - r[L].groupby([t.date[L], t.ind[L]]).transform("mean")
k1 = pd.Series(False, index=t.index); k1[L] = res[L].groupby(t.date[L]).rank(pct=True) <= 0.1
rules = {"K1 resid r5 bottom decile": k1} | F.F6(t) | F.F9(t) | F.H1(t) | F.F1(t) | F.H3(t) | F.F8(t)
win = (t.date >= w.DISC[0]) & (t.date <= w.DISC[1]) & t.liq
lines = []
for lab, m in rules.items():
    s = t[m.fillna(False) & win]
    d = s.groupby("date").xco.mean()
    lines.append(f"{lab:44} n {len(s):7} | close->next open excess {s.xco.mean()*1e4:+6.1f}bp (NW t {w.nw_t(d,1):+5.1f}, med {s.xco.median()*1e4:+5.1f}) | open t+1->close t+5 {s.x5.mean()*1e4:+6.1f}bp")
txt = "\n".join(lines); print(txt); open(F.OUT, "a").write(f"# gap-location diagnostic {pd.Timestamp.now():%Y-%m-%d %H:%M}\n{txt}\n\n")
