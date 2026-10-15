"""Study TREND-NIGHT (N 916 -> 919): night picks split by the stock's own prior trend (200d SMA, 126d, 252d return), bars before the shock day.
Pre-reg research/drafts/round1_prose.md. Harness = CAT-MOM (nx daily-bar proxy, delisted-complete). Run once.
  PYTHONPATH=. .venv/bin/python -m research.sim.trend_night"""
import numpy as np, pandas as pd
from research.sim import shar_surv as ss, nx
OUT = ss.ROOT / "data/research/program/trend_night_out.txt"
COST = 5e-4
CRASH = {2000, 2001, 2002, 2008, 2009, 2020}
L = []
def P(s=""): print(s, flush=True); L.append(s)
M = ss.load_master()

def picks(lo, hi):
    bars = ss.load_bars(lo - pd.Timedelta(days=430), hi + pd.Timedelta(days=10))
    pn = nx.build_panel(bars)
    tr = nx.collect_trades(pn, M, ss.load_actions(), "primary", lo, hi)["trades"].copy()
    c, pos = pn["c"], pn["pos"]
    # SMA200 via exact per-ticker rolling mean (a cumsum version lost precision: some adjusted closes are ~1e10+)
    sma_all = pd.Series(c).groupby(pn["code"]).transform(lambda s: s.rolling(200).mean().shift(1)).to_numpy()
    i = tr.row.to_numpy(int)
    ok200, ok126, ok252 = pos[i] >= 200, pos[i] >= 126, pos[i] >= 252
    cprev = c[np.maximum(i - 1, 0)]
    sma = sma_all[i]
    tr["ta"] = np.where(ok200, cprev > sma, np.nan)
    tr["tb"] = np.where(ok126, cprev / c[np.maximum(i - 126, 0)] - 1 > 0, np.nan)
    tr["tc"] = np.where(ok252, cprev / c[np.maximum(i - 252, 0)] - 1 > 0, np.nan)
    tr["ta"] = tr.ta.where(pd.Series(ok200, index=tr.index)); tr["tb"] = tr.tb.where(pd.Series(ok126, index=tr.index)); tr["tc"] = tr.tc.where(pd.Series(ok252, index=tr.index))
    return tr

def nightly(tr, cost, mask=None):
    t = tr if mask is None else tr[mask]
    return (t.ret - 2 * cost).groupby(t.date).mean()

def tstat(s): return s.mean() / s.std(ddof=1) * np.sqrt(len(s))

def judge(name, tr, col, gate):
    base = nightly(tr, COST); arm = nightly(tr, COST, tr[col] == 1.0).reindex(base.index).fillna(0.0)
    dd = arm - base; t = tstat(dd); mid = dd.index[len(dd) // 2]
    h = (dd[dd.index < mid].mean(), dd[dd.index >= mid].mean()); ex5 = dd.drop(dd.abs().nlargest(5).index).mean()
    med = dd[dd != 0].median()
    base2 = nightly(tr, 2 * COST); arm2 = nightly(tr, 2 * COST, tr[col] == 1.0).reindex(base2.index).fillna(0.0); dd2 = arm2 - base2
    nc = ~dd.index.year.isin(CRASH); exc = dd[nc].mean()
    lev = base.mean() * arm.std() / base.std()
    sh = lambda s: s.mean() / s.std() * np.sqrt(252)
    up, dn, unk = tr[tr[col] == 1.0].ret.mean() - 2 * COST, tr[tr[col] == 0.0].ret.mean() - 2 * COST, tr[tr[col].isna()].ret.mean() - 2 * COST
    P(f"  {name}: picks up {int((tr[col]==1.0).sum())} / down {int((tr[col]==0.0).sum())} / unknown {int(tr[col].isna().sum())}; per-trade net up {up*1e4:+6.1f} down {dn*1e4:+6.1f} unknown {unk*1e4:+6.1f} bp")
    P(f"     arm {arm.mean()*1e4:+6.1f}bp/night (std {arm.std()*1e4:4.0f}, Sharpe {sh(arm):4.2f}) vs base {base.mean()*1e4:+6.1f} (std {base.std()*1e4:4.0f}, Sharpe {sh(base):4.2f}) | "
      f"diff {dd.mean()*1e4:+6.2f} t {t:+5.2f} halves {h[0]*1e4:+6.2f}/{h[1]*1e4:+6.2f} median(diff!=0) {med*1e4:+6.2f} ex-top5 {ex5*1e4:+6.2f} 2xcost {dd2.mean()*1e4:+6.2f} (t {tstat(dd2):+4.2f}) "
      f"ex-crash {exc*1e4:+6.2f} | levered-base {lev*1e4:+6.1f} vs arm {arm.mean()*1e4:+6.1f}")
    if gate:
        ok = dd.mean() >= 1e-3 and t >= 3.06 and min(h) > 0 and med > 0 and ex5 > 0 and dd2.mean() > 0 and exc > 0 and arm.mean() > lev
        P(f"     => {'PASS' if ok else 'FAIL'}")

for name, lo, hi, gate in [("JUDGE 1999-2015", "1999-01-04", "2015-12-31", True), ("REPORT 2016-26 (touched)", "2016-01-04", "2026-09-18", False)]:
    lo, hi = pd.Timestamp(lo), pd.Timestamp(hi)
    tr = picks(lo, hi); tr = tr[tr.date >= lo]
    P(f"== {name}: picks {len(tr)}, nights {tr.date.nunique()}")
    for col, nm in [("ta", "TA c_prev>SMA200"), ("tb", "TB 126d ret>0"), ("tc", "TC 252d ret>0")]:
        judge(nm, tr, col, gate)
    # descriptive (no N): the 'unknown' bucket = fewer than 252 prior bars = young listings; exclude the window's first 430 days (warm-up truncation)
    late = tr[tr.date >= lo + pd.Timedelta(days=430)]
    yg, old = late[late.tc.isna()], late[late.tc.notna()]
    P(f"  young-listing check (ex first 430d): young n {len(yg)} mean {(yg.ret.mean()-2*COST)*1e4:+6.1f} median {(yg.ret.median()-2*COST)*1e4:+6.1f} | old n {len(old)} mean {(old.ret.mean()-2*COST)*1e4:+6.1f} median {(old.ret.median()-2*COST)*1e4:+6.1f}")
    yb = yg.groupby(yg.date.dt.year).ret.mean()*1e4; ob = old.groupby(old.date.dt.year).ret.mean()*1e4
    P("  young-old by year: " + " ".join(f"{y}:{yb[y]-ob.get(y, np.nan):+.0f}" for y in yb.index))
    P()
OUT.write_text("\n".join(L))
