"""Round 17: CEF-RV trades split by a recent distribution cut (R16 definition)."""
import numpy as np, pandas as pd
from research.sim import winsig as w, winsig_fam as F, cef_rv
nav = cef_rv.load_nav(); fS = cef_rv.load_sfp(sorted(nav.ticker.unique()))
tr = cef_rv.build_trades(nav, fS)
tr["edate"] = pd.to_datetime(tr.edate); tr["xdate"] = pd.to_datetime(tr.xdate)
t = w.load_panel(kind="cef")
t["r"] = t.groupby("ticker", sort=False).closeadj.pct_change()   # consecutive bars of each fund (fixed: was liquid rows only)
ew = t[t.liq].copy()
idx = (1 + ew.groupby("date").r.mean().fillna(0)).cumprod()
def ewret(a, b):
    ia = idx.index.searchsorted(a); ib = idx.index.searchsorted(b)
    ia, ib = min(ia, len(idx)-1), min(ib, len(idx)-1)
    return idx.iloc[ib] / idx.iloc[ia] - 1
tr["exs"] = tr.ret - [ewret(a, b) for a, b in zip(tr.edate, tr.xdate)]
a = pd.read_parquet(w.STORE / "actions.parquet", columns=["date", "action", "ticker", "value"])
a = a[(a.action == "dividend") & a.ticker.isin(set(tr.ticker))].copy(); a["date"] = pd.to_datetime(a.date); a = a.sort_values(["ticker", "date"])
v = a.groupby("ticker").value; P = pd.concat([v.shift(1), v.shift(2), v.shift(3)], axis=1)
exd = a[["ticker", "date"]]
cd = exd.groupby("ticker").date.apply(list).to_dict()
tr["cut30"] = [any(0 < (c - e).days <= 14 for c in cd.get(tk, [])) for tk, e in zip(tr.ticker, tr.edate)]  # entry within ~10 sessions BEFORE an ex-date
A, B = tr[tr.cut30], tr[~tr.cut30]
mid = tr.edate.min() + (tr.edate.max() - tr.edate.min()) / 2
h = tuple((A[A.edate < mid].exs.mean() - B[B.edate < mid].exs.mean(), A[A.edate >= mid].exs.mean() - B[B.edate >= mid].exs.mean()))
diff = A.exs.mean() - B.exs.mean()
se = np.sqrt(A.exs.var() / len(A) + B.exs.var() / len(B)) if len(A) > 2 else np.nan
ok = diff * 1e4 >= 50 and diff / se >= 2.5 and h[0] > 0 and h[1] > 0
line = (f"R28 CEF-RV trades {len(tr)} (2016-26 panel): pre-ex-entry n {len(A)} excess {A.exs.mean()*1e4:+.0f}bp med {A.exs.median()*1e4:+.0f} | rest n {len(B)} {B.exs.mean()*1e4:+.0f}bp med {B.exs.median()*1e4:+.0f}"
        f" | diff {diff*1e4:+.0f}bp (t {diff/se:+.1f}) halves {h[0]*1e4:+.0f}/{h[1]*1e4:+.0f} -> {'PASS (timing gate)' if ok else 'fail'}")
print(line); open(F.OUT, "a").write(f"# Round 28 {pd.Timestamp.now():%Y-%m-%d %H:%M}\n{line}\n\n")
