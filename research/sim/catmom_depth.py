"""Study CAT-MOM + DEPTH (N 912 -> 916): category momentum (CM12, CM6) and trade-deeper (TOP2, DEPTHW) for the night leg.
Pre-reg research/drafts/round1_prose.md. Harness = HC-BAN (nx daily-bar proxy, delisted-complete). Run once.
  PYTHONPATH=. .venv/bin/python -m research.sim.catmom_depth"""
import numpy as np, pandas as pd
from research.sim import shar_surv as ss, nx
OUT = ss.ROOT / "data/research/program/catmom_depth_out.txt"
COST = 5e-4
L = []
def P(s=""): print(s, flush=True); L.append(s)
M = ss.load_master()

def picks(lo, hi):
    bars = ss.load_bars(lo - pd.Timedelta(days=400), hi + pd.Timedelta(days=10))
    pn = nx.build_panel(bars)
    tr = nx.collect_trades(pn, M, ss.load_actions(), "primary", lo - pd.Timedelta(days=380), hi)["trades"].copy()
    tr["r"] = tr.ret - 2 * COST; tr["cat"] = tr.sector.fillna("NA").astype(str)
    return tr

def catmom(tr, months):
    tr = tr.sort_values("date"); tr["m"] = tr.date.dt.to_period("M")
    keep = pd.Series(True, index=tr.index)
    for m in tr.m.unique():
        lo = (m - months).to_timestamp(); hi = m.to_timestamp()
        past = tr[(tr.date >= lo) & (tr.date < hi)]
        st = past.groupby("cat").r.agg(["mean", "count"]); st = st[st["count"] >= 30]
        if len(st) < 2: continue
        bad = st.index[st["mean"] < st["mean"].median()]
        cur = tr.m == m
        keep[cur & tr.cat.isin(bad)] = False
    return keep

def nightly(tr, mask=None, w=None):
    t = tr if mask is None else tr[mask]
    if w is None: return t.groupby("date").r.mean()
    ww = w.loc[t.index]; return (t.r * ww).groupby(t.date).sum() / ww.groupby(t.date).sum()

def judge(name, arm, base, gate):
    arm = arm.reindex(base.index).fillna(0.0); dd = arm - base
    t = dd.mean() / dd.std(ddof=1) * np.sqrt(len(dd)); mid = dd.index[len(dd) // 2]
    h = (dd[dd.index < mid].mean(), dd[dd.index >= mid].mean()); ex5 = dd.drop(dd.abs().nlargest(5).index).mean()
    sh = lambda s: s.mean() / s.std() * np.sqrt(252)
    P(f"  {name:7s} arm {arm.mean()*1e4:+6.1f}bp/night (std {arm.std()*1e4:5.0f}, Sharpe {sh(arm):4.2f}, worst {arm.min()*1e4:+6.0f}) vs base {base.mean()*1e4:+6.1f} "
      f"(std {base.std()*1e4:5.0f}, Sharpe {sh(base):4.2f}) | diff {dd.mean()*1e4:+6.2f} t {t:+5.2f} halves {h[0]*1e4:+6.2f}/{h[1]*1e4:+6.2f} ex-top5 {ex5*1e4:+6.2f}"
      + (f"  {'PASS' if (dd.mean() >= 1e-3 and t >= 2.5 and min(h) > 0 and ex5 > 0) else 'FAIL'}" if gate else ""))

for name, lo, hi, gate in [("JUDGE 1999-2015", "1999-01-04", "2015-12-31", True), ("REPORT 2016-26 (touched)", "2016-01-04", "2026-09-18", False)]:
    lo, hi = pd.Timestamp(lo), pd.Timestamp(hi)
    full = picks(lo, hi)
    km12, km6 = catmom(full.copy(), 12), catmom(full.copy(), 6)
    tr = full[full.date >= lo]; km12, km6 = km12.loc[tr.index], km6.loc[tr.index]
    P(f"== {name}: picks {len(tr)}, nights {tr.date.nunique()}, categories {tr.cat.nunique()}; CM12 keeps {km12.mean()*100:.0f}%, CM6 {km6.mean()*100:.0f}%")
    base = nightly(tr)
    judge("CM12", nightly(tr, km12), base, gate); judge("CM6", nightly(tr, km6), base, gate)
    rk = tr.groupby("date").day_ret.rank(method="first"); judge("TOP2", nightly(tr, rk <= 2), base, gate)
    judge("DEPTHW", nightly(tr, None, tr.day_ret.abs()), base, gate)
    P()
OUT.write_text("\n".join(L))
