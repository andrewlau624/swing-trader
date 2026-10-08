"""Round 5: industry-residual short-window reversal (K1-K3). Spec in the loop ledger."""
import numpy as np, pandas as pd
from research.sim import winsig as w, winsig_fam as F
t = w.add_bench(w.load_panel())
tk = pd.read_parquet(w.STORE / "tickers.parquet", columns=["table", "ticker", "famaindustry"])
ind = tk[tk.table == "SEP"].drop_duplicates("ticker").set_index("ticker").famaindustry
t["ind"] = t.ticker.map(ind).fillna("NA")
lines = []
for k, lab in ((5, "K1 resid r5 bottom decile"), (2, "K2 resid r2 bottom decile")):
    r = t.closeadj / w.lag(t, t.closeadj, k) - 1
    L = t.liq & r.notna()
    im = r[L].groupby([t.date[L], t.ind[L]]).transform("mean")
    res = pd.Series(np.nan, index=t.index); res[L] = r[L] - im
    pct = res[L].groupby(t.date[L]).rank(pct=True)
    m = pd.Series(False, index=t.index); m[L] = pct <= 0.1
    rr = w.judge(t, m, *w.DISC, lab + " [2016-26]"); lines.append(w.fmt(rr))
    if k == 5:
        mid = m & (t.adv20 < 100e6)
        rr = w.judge(t, mid, *w.DISC, "K3 resid r5 bottom decile, ADV $20-100M [2016-26]"); lines.append(w.fmt(rr))
txt = "\n".join(lines); print(txt); open(F.OUT, "a").write(f"# Round 5 {pd.Timestamp.now():%Y-%m-%d %H:%M}\n{txt}\n\n")
