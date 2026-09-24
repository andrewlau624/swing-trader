"""Feature audit: which entry-time features actually carry information?

Runs the baseline once, then for every trade computes candidate features on the
DECISION bar (the bar before the fill) and correlates them with trade P&L.
This is the honest version of "does this feature separate winners from losers",
with both halves shown and a feature-correlation matrix for redundancy.
"""
import numpy as np
import pandas as pd
from scipy import stats
from h import (bars, run, vol_z, ibs, close_loc_5, dist_52w_high,
               overnight_share, z_of, shock_share, down_days)

b = bars()
s, res = run(b, "baseline top8")
print(s, flush=True)

rows = []
for t in res.trades:
    sym = t.symbol
    if sym not in b:
        continue
    hist = b[sym].loc[b[sym].index < t.entry_date]
    if len(hist) < 30:
        continue
    rows.append({
        "sym": sym, "pnl": t.pnl_pct, "date": t.entry_date,
        "ovn5": overnight_share(hist, 5),
        "volz5": vol_z(hist, 5),
        "volz20": vol_z(hist, 20),
        "shock5": shock_share(hist, 5),
        "shock3": shock_share(hist, 3),
        "ibs": ibs(hist),
        "closeloc5": close_loc_5(hist, 5),
        "dist52": dist_52w_high(hist, 252),
        "z20": z_of(hist, 20),
        "downdays5": down_days(hist, 5),
    })

df = pd.DataFrame(rows).dropna(subset=["pnl"])
print(f"\n{len(df)} trades with features", flush=True)

feats = ["ovn5", "volz5", "volz20", "shock5", "shock3", "ibs",
         "closeloc5", "dist52", "z20", "downdays5"]
print("\n=== Spearman(feature, pnl) on all trades / 21-23 / 24-26 ===", flush=True)
for f in feats:
    d = df.dropna(subset=[f])
    r_all, p_all = stats.spearmanr(d[f], d["pnl"])
    h1 = d[d["date"] < "2024-01-01"]
    h2 = d[d["date"] >= "2024-01-01"]
    r1 = stats.spearmanr(h1[f], h1["pnl"])[0] if len(h1) > 8 else np.nan
    r2 = stats.spearmanr(h2[f], h2["pnl"])[0] if len(h2) > 8 else np.nan
    print(f"  {f:10s} n={len(d):3d}  rho={r_all:+.3f} (p={p_all:.3f})  "
          f"21-23 {r1:+.3f}  24-26 {r2:+.3f}", flush=True)

print("\n=== feature correlation matrix (redundancy) ===", flush=True)
print(df[feats].corr(method="spearman").round(2).to_string(), flush=True)

print("\n=== shock5 bucket means ===", flush=True)
d = df.dropna(subset=["shock5"])
d = d.assign(bucket=pd.cut(d["shock5"], [-np.inf, 0.3, 0.5, 0.7, np.inf],
                           labels=["<0.3", "0.3-0.5", "0.5-0.7", ">0.7"]))
print(d.groupby("bucket", observed=True)["pnl"].agg(["count", "mean", "median",
      lambda x: 100 * (x > 0).mean()]).round(2).to_string(), flush=True)

print("\n=== overnight5 bucket means ===", flush=True)
d = df.dropna(subset=["ovn5"])
d = d.assign(bucket=pd.cut(d["ovn5"], [-np.inf, 0.0, 0.3, 0.6, np.inf],
                           labels=["<0", "0-0.3", "0.3-0.6", ">0.6"]))
print(d.groupby("bucket", observed=True)["pnl"].agg(["count", "mean", "median",
      lambda x: 100 * (x > 0).mean()]).round(2).to_string(), flush=True)
