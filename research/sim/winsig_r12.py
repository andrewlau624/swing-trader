"""Round 12 diagnostic: timing of the CEF/preferred oscillator reversal (no gate)."""
import numpy as np, pandas as pd
from research.sim import winsig as w, winsig_fam as F
lines = []
for kind in ("cef", "pref"):
    t = w.load_panel(kind=kind)
    g = t.groupby("ticker", sort=False); adjf = t.closeadj / t.close
    t["co"] = g["open"].shift(-1) * adjf.groupby(t.ticker, sort=False).shift(-1) / t.closeadj - 1
    t["cc5"] = g["closeadj"].shift(-5) / t.closeadj - 1
    t["cc3"] = g["closeadj"].shift(-3) / t.closeadj - 1
    L = t.liq
    for c in ("co", "f5", "cc3", "cc5"):
        t["x_" + c] = t[c] - t.date.map(t[L].groupby("date")[c].mean())
    win = L & (t.date >= w.DISC[0]) & (t.date <= w.DISC[1])
    for lab, m in (F.F4(t) | F.F5(t)).items():
        s = t[m.fillna(False) & win]
        cells = []
        for c, h in (("co", 1), ("f5", 5), ("cc3", 3), ("cc5", 5)):
            x = s["x_" + c].dropna(); d = x.groupby(s.loc[x.index, "date"]).mean()
            cells.append(f"{c} {x.mean()*1e4:+6.1f} (t {w.nw_t(d, h):+4.1f}, med {x.median()*1e4:+5.1f})")
        lines.append(f"{kind.upper():4} {lab:42} n {len(s):6} | " + " | ".join(cells))
txt = "\n".join(lines); print(txt); open(F.OUT, "a").write(f"# Round 12 diag {pd.Timestamp.now():%Y-%m-%d %H:%M}\n{txt}\n\n")
