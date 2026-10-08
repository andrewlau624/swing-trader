"""Round 27: issuer-common crash -> preferred drift; avoid-screen on PREF-CHAIN."""
import sys, numpy as np, pandas as pd
from research.sim import winsig as w, winsig_fam as F
CONF = "--confirm" in sys.argv
lo, hi = ("2005-01-01", "2015-12-31") if CONF else ("2016-01-01", "2026-09-30")
p = w.load_panel(kind="pref"); s = w.load_panel()
p["issuer"] = p.ticker.str.extract(r"^([A-Z.]+)-P")[0]
sg = s.groupby("ticker", sort=False)
s["dr"] = s.closeadj / sg["closeadj"].shift(1) - 1
crash = s[(s.dr <= -0.08) & (s.closeunadj >= 3)][["ticker", "date"]].rename(columns={"ticker": "issuer"})
g = p.groupby("ticker", sort=False)
for k in (1, 5, 10):
    p[f"r{k}"] = g["closeadj"].shift(-k) / p.closeadj - 1
    p[f"x{k}"] = p[f"r{k}"] - p[f"r{k}"][p.liq].groupby(p.date[p.liq]).transform("mean").reindex(p.index)
e = crash.merge(p[["ticker", "issuer", "date", "liq", "x1", "x5", "x10"]], on=["issuer", "date"])
e = e[e.liq & (e.date >= lo) & (e.date <= hi)]
lines = [f"R27 {'CONFIRM ' if CONF else ''}{lo[:4]}-{hi[:4]} issuer-crash pref events {len(e)} ({e.ticker.nunique()} prefs): "
         + " | ".join(f"+{k}d {e[f'x{k}'].mean()*1e4:+.1f} (med {e[f'x{k}'].median()*1e4:+.1f}, t {w.nw_t(e.groupby('date')[f'x{k}'].mean(), k):+.1f})" for k in (1, 5, 10))]
# avoid-screen on PREF-CHAIN
a = pd.read_parquet(w.STORE / "actions.parquet", columns=["date", "action", "ticker", "value"])
a = a[(a.action == "dividend") & a.ticker.isin(set(p.ticker))].copy(); a["date"] = pd.to_datetime(a.date); a = a.sort_values(["ticker", "date"])
v = a.groupby("ticker").value; P = pd.concat([v.shift(1), v.shift(2), v.shift(3)], axis=1)
keep = (P.notna().all(axis=1) & ((P.max(axis=1) / P.min(axis=1) - 1) <= 0.02)) & ((a.value / P.median(axis=1) - 1).abs() < 0.10)
p["ch"] = p.closeadj / g["closeadj"].shift(10) - 1
p["xch"] = p.ch - p.ch[p.liq].groupby(p.date[p.liq]).transform("mean").reindex(p.index)
p["d10"] = g["date"].shift(10)                                     # entry date T-10
ev = a[keep][["ticker", "date"]].merge(p[["ticker", "issuer", "date", "liq", "xch", "d10"]], on=["ticker", "date"])
ev = ev[ev.liq & (ev.date >= lo) & (ev.date <= hi)].dropna(subset=["xch", "d10"])
cd = crash.groupby("issuer").date.apply(lambda x: np.sort(x.values)).to_dict()
def hit(iss, d):
    arr = cd.get(iss)
    if arr is None: return False
    i = np.searchsorted(arr, np.datetime64(d), side="right")
    return i > 0 and (np.datetime64(d) - arr[i - 1]) <= np.timedelta64(14, "D")
ev["after"] = [hit(i, d) for i, d in zip(ev.issuer, ev.d10)]
A, B = ev[ev.after], ev[~ev.after]
diff = A.xch.mean() - B.xch.mean(); se = np.sqrt(A.xch.var()/max(len(A),1) + B.xch.var()/len(B))
mid = pd.Timestamp(lo) + (pd.Timestamp(hi) - pd.Timestamp(lo)) / 2
h = (A[A.date < mid].xch.mean() - B[B.date < mid].xch.mean(), A[A.date >= mid].xch.mean() - B[B.date >= mid].xch.mean())
ok = diff*1e4 <= -50 and diff/se <= -2.5 and h[0] < 0 and h[1] < 0
lines.append(f"  avoid-screen on PREF-CHAIN: after-crash n {len(A)} {A.xch.mean()*1e4:+.1f}bp (med {A.xch.median()*1e4:+.1f}) | rest n {len(B)} {B.xch.mean()*1e4:+.1f} | "
             f"diff {diff*1e4:+.1f} (t {diff/se:+.1f}) halves {h[0]*1e4:+.1f}/{h[1]*1e4:+.1f} -> {'PASS' if ok else 'fail'}")
txt = "\n".join(lines); print(txt); open(F.OUT, "a").write(f"# Round 27 {pd.Timestamp.now():%Y-%m-%d %H:%M}\n{txt}\n\n")
